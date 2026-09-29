"""Pruebas unitarias de ExtensionService (sin PostgreSQL real)."""

from __future__ import annotations

from typing import Any, Self

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager, DatabaseConnectionError
from crud_generator.models import ExtensionState
from crud_generator.services import DEFAULT_EXTENSION_NAME, ExtensionService


def make_config() -> DatabaseConfig:
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="crud_test",
        user="tester",
        password="s3cr3t-pw",
    )


class StubPgError(psycopg.Error):
    """Error PostgreSQL falso con SQLSTATE configurable."""

    def __init__(self, message: str, sqlstate: str | None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


class FakeConnInfo:
    def __init__(
        self, transaction_status: TransactionStatus = TransactionStatus.IDLE
    ) -> None:
        self.transaction_status = transaction_status


class FakeExtCursor:
    def __init__(self, conn: FakeExtConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: Any = None) -> None:
        self._conn.queries.append((query, params))
        if self._conn.error is not None:
            raise self._conn.error

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conn.row


class FakeExtConnection:
    def __init__(
        self,
        row: tuple[Any, ...] | None = None,
        *,
        error: BaseException | None = None,
        autocommit: bool = True,
        transaction_status: TransactionStatus = TransactionStatus.IDLE,
    ) -> None:
        self.row = row
        self.error = error
        self.autocommit = autocommit
        self.info = FakeConnInfo(transaction_status)
        self.closed = False
        self.queries: list[tuple[str, Any]] = []
        self.rollbacks = 0

    def cursor(self) -> FakeExtCursor:
        return FakeExtCursor(self)

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    row: tuple[Any, ...] | None = None,
    *,
    error: BaseException | None = None,
    autocommit: bool = True,
    transaction_status: TransactionStatus = TransactionStatus.IDLE,
) -> tuple[ExtensionService, FakeExtConnection]:
    fake = FakeExtConnection(
        row,
        error=error,
        autocommit=autocommit,
        transaction_status=transaction_status,
    )
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: fake)
    return ExtensionService(ConnectionManager(make_config())), fake


def test_installed_extension_returns_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, ("crud_generator", "1.0", "public", True)
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.INSTALLED
    assert status.name == "crud_generator"
    assert status.version == "1.0"
    assert status.schema == "public"


def test_not_installed_when_no_row(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(monkeypatch, None)

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.NOT_INSTALLED
    assert status.name == "crud_generator"
    assert status.version is None
    assert status.schema is None
    assert status.state is not ExtensionState.ERROR


def test_installed_without_usage_is_not_accessible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, ("crud_generator", "1.0", "restringido", False)
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.NOT_ACCESSIBLE
    assert status.version == "1.0"
    assert status.schema == "restringido"


def test_extension_name_is_parameterized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = "x' OR '1'='1\"; --"
    service, fake = make_service(monkeypatch, None)

    service.check_extension(hostile)

    (query, params) = fake.queries[0]
    assert "pg_extension" in query
    assert "%s" in query
    assert hostile not in query
    assert params == (hostile,)


def test_empty_name_fails_fast_without_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, None)

    with pytest.raises(ValueError):
        service.check_extension("   ")
    assert fake.queries == []


def test_permission_error_is_error_not_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, error=StubPgError("permission denied", "42501")
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.ERROR
    assert status.sqlstate == "42501"
    assert status.state is not ExtensionState.NOT_INSTALLED


def test_unexpected_error_is_error_not_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, error=StubPgError("boom", "XX000"))

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.ERROR
    assert status.sqlstate == "XX000"


def test_connection_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(**kwargs: Any) -> FakeExtConnection:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", _fail)
    service = ExtensionService(ConnectionManager(make_config()))

    with pytest.raises(DatabaseConnectionError):
        service.check_extension("crud_generator")


def test_idle_initial_status_rolls_back_after_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        ("crud_generator", "1.0", "public", True),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.INSTALLED
    assert fake.rollbacks == 1


def test_preexisting_transaction_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        ("crud_generator", "1.0", "public", True),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.INSTALLED
    assert fake.rollbacks == 0


def test_error_inside_preexisting_transaction_keeps_error_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    status = service.check_extension("crud_generator")

    assert status.state is ExtensionState.ERROR
    assert status.sqlstate == "XX000"
    assert fake.rollbacks == 0


def test_default_extension_name_is_documented_provisional() -> None:
    assert DEFAULT_EXTENSION_NAME == "crud_generator"


def test_non_postgres_error_is_not_masked_as_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, error=RuntimeError("bug interno"))

    with pytest.raises(RuntimeError):
        service.check_extension("crud_generator")
