"""Pruebas de ProcedureService (sin PostgreSQL real)."""

from __future__ import annotations

from typing import Any, Self

import pytest
from psycopg.pq import TransactionStatus

from crud_generator.db import ConnectionManager
from crud_generator.services.procedure_service import (
    ProcedureService,
    normalize_call_value,
    split_identity_arguments,
)


class FakeInfo:
    def __init__(self, status: TransactionStatus) -> None:
        self.transaction_status = status


class FakeCursor:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: Any, params: Any = None) -> None:
        self._conn.statements.append((query, params))

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conn.next_row()

    def fetchall(self) -> list[tuple[Any, ...]]:
        rows = list(self._conn.pending_rows)
        self._conn.pending_rows = []
        return rows

    @property
    def description(self) -> Any:
        return self._conn.description


class FakeTransaction:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        self._conn.txn_opened += 1
        return self

    def __exit__(self, exc_type: object, *args: object) -> bool:
        if exc_type is None:
            self._conn.commits += 1
        else:
            self._conn.rollbacks += 1
        return False


class FakeConnection:
    def __init__(
        self,
        *,
        autocommit: bool = True,
        status: TransactionStatus = TransactionStatus.IDLE,
        rows: list[tuple[Any, ...]] | None = None,
        description: Any = True,
        fail_at: int | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.autocommit = autocommit
        self.info = FakeInfo(status)
        self.pending_rows = list(rows or [])
        self.description = description
        self.statements: list[tuple[Any, Any]] = []
        self.fail_at = fail_at
        self.error = error
        self.txn_opened = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def next_row(self) -> tuple[Any, ...] | None:
        if not self.pending_rows:
            return None
        return self.pending_rows.pop(0)

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch, conn: FakeConnection
) -> ProcedureService:
    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: conn)
    config = {
        "host": "h",
        "port": 5432,
        "database": "d",
        "user": "u",
        "password": "p",
    }
    from crud_generator.config import DatabaseConfig

    return ProcedureService(ConnectionManager(DatabaseConfig(**config)))


def test_split_respects_parentheses() -> None:
    assert split_identity_arguments(
        "IN p_2 text, IN p_1 integer, IN p_3 numeric(10,2)"
    ) == ("IN p_2 text", "IN p_1 integer", "IN p_3 numeric(10,2)")
    assert split_identity_arguments("OUT resultado refcursor") == (
        "OUT resultado refcursor",
    )
    assert split_identity_arguments("") == ()


def test_normalize_empty_is_null() -> None:
    assert normalize_call_value("") is None
    assert normalize_call_value("   ") is None
    assert normalize_call_value("  Teclado ") == "Teclado"
    assert normalize_call_value("25.50") == "25.50"


def test_call_returns_output_row(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConnection(rows=[(101, "Teclado", 25.50)])
    service = make_service(monkeypatch, conn)

    result = service.call_procedure(
        "lab", "producto_consultar", ("101", None, None)
    )

    assert result.output == (101, "Teclado", 25.50)
    assert result.is_table is False
    assert result.rows == ()


def test_call_without_output_row(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConnection(rows=[], description=None)
    service = make_service(monkeypatch, conn)

    result = service.call_procedure(
        "lab", "producto_insertar", ("1", "x", "2.5")
    )

    assert result.output is None


def test_call_refcursor_fetch_all(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConnection(rows=[("cur1",), (1, "a"), (2, "b")])
    service = make_service(monkeypatch, conn)

    result = service.call_procedure(
        "lab", "bitacora_consultar", (None,), fetch_cursor=True
    )

    assert result.is_table is True
    assert result.rows == ((1, "a"), (2, "b"))
    assert conn.txn_opened == 1


def test_call_refcursor_without_cursor_is_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection(rows=[], description=None)
    service = make_service(monkeypatch, conn)

    with pytest.raises(ValueError):
        service.call_procedure("lab", "x_consultar", (None,), fetch_cursor=True)


def test_call_empty_schema_or_routine_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    service = make_service(monkeypatch, conn)

    with pytest.raises(ValueError):
        service.call_procedure("  ", "r", ())
    with pytest.raises(ValueError):
        service.call_procedure("lab", "", ())
    assert conn.statements == []


def test_call_non_text_values_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConnection()
    service = make_service(monkeypatch, conn)

    with pytest.raises(TypeError):
        service.call_procedure("lab", "r", (101,))  # type: ignore[arg-type]
    assert conn.statements == []
