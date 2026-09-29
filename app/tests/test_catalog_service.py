"""Pruebas unitarias de CatalogService (sin PostgreSQL real)."""

from __future__ import annotations

from typing import Any, Self

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from crud_generator.config import DatabaseConfig
from crud_generator.db import (
    ConnectionManager,
    DatabaseConnectionError,
    InsufficientPrivilegeError,
    UnexpectedDatabaseError,
)
from crud_generator.models import RoleInfo, SchemaInfo, TableInfo
from crud_generator.services import CatalogService


def make_config() -> DatabaseConfig:
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="crud_test",
        user="tester",
        password="s3cr3t-pw",
    )


class StubPgError(Exception):
    def __init__(self, message: str, sqlstate: str | None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


class FakeCatalogCursor:
    def __init__(self, conn: FakeCatalogConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: Any = None) -> None:
        self._conn.queries.append((query, params))
        if self._conn.error is not None:
            raise self._conn.error

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._conn.rows)


class FakeConnInfo:
    def __init__(
        self, transaction_status: TransactionStatus = TransactionStatus.IDLE
    ) -> None:
        self.transaction_status = transaction_status


class FakeCatalogConnection:
    def __init__(
        self,
        rows: tuple[tuple[Any, ...], ...] = (),
        *,
        error: BaseException | None = None,
        autocommit: bool = True,
        transaction_status: TransactionStatus = TransactionStatus.IDLE,
    ) -> None:
        self.rows = list(rows)
        self.error = error
        self.autocommit = autocommit
        self.info = FakeConnInfo(transaction_status)
        self.closed = False
        self.queries: list[tuple[str, Any]] = []
        self.rollbacks = 0

    def cursor(self) -> FakeCatalogCursor:
        return FakeCatalogCursor(self)

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    rows: tuple[tuple[Any, ...], ...] = (),
    *,
    error: BaseException | None = None,
    autocommit: bool = True,
    transaction_status: TransactionStatus = TransactionStatus.IDLE,
) -> tuple[CatalogService, FakeCatalogConnection]:
    fake = FakeCatalogConnection(
        rows,
        error=error,
        autocommit=autocommit,
        transaction_status=transaction_status,
    )
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: fake)
    manager = ConnectionManager(make_config(), autocommit=autocommit)
    return CatalogService(manager), fake


def test_list_schemas_returns_schema_infos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, (("lab",), ("public",), ("ventas",))
    )

    assert service.list_schemas() == [
        SchemaInfo(name="lab"),
        SchemaInfo(name="public"),
        SchemaInfo(name="ventas"),
    ]


def test_list_schemas_excludes_system_via_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, (("public",),))
    service.list_schemas()

    (query, params) = fake.queries[0]
    assert "pg_catalog" in query
    assert "information_schema" in query
    assert "pg_temp_" in query
    assert "pg_toast" in query
    assert "ORDER BY" in query
    # Sin hardcodear esquemas del proyecto en la consulta.
    assert "public" not in query
    assert "lab" not in query
    assert params is None


def test_list_schemas_empty_when_no_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, ())

    assert service.list_schemas() == []


def test_list_tables_passes_schema_as_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, (("cliente",),))
    service.list_tables("general")

    (query, params) = fake.queries[0]
    assert params == ("general",)
    assert "%s" in query
    assert "ORDER BY" in query
    # El valor nunca se interpola dentro del SQL.
    assert "general" not in query


def test_list_tables_returns_multiple_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, (("cliente",), ("factura",), ("producto",))
    )

    assert service.list_tables("general") == [
        TableInfo(schema="general", name="cliente"),
        TableInfo(schema="general", name="factura"),
        TableInfo(schema="general", name="producto"),
    ]


def test_list_tables_empty_when_schema_has_no_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, ())

    assert service.list_tables("vacio") == []


def test_list_tables_rejects_empty_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, (("t",),))

    with pytest.raises(ValueError):
        service.list_tables("   ")
    assert fake.queries == []


def test_list_tables_never_interpolates_user_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = "x' OR '1'='1\"; --"
    service, fake = make_service(monkeypatch, ())

    service.list_tables(hostile)

    (query, params) = fake.queries[0]
    assert hostile not in query
    assert params == (hostile,)


def test_list_roles_returns_names_and_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        (
            ("ana", True, False),
            ("jefatura", True, False),
            ("solo_grupo", False, False),
        ),
    )

    assert service.list_roles() == [
        RoleInfo(name="ana", can_login=True, is_superuser=False),
        RoleInfo(name="jefatura", can_login=True, is_superuser=False),
        RoleInfo(name="solo_grupo", can_login=False, is_superuser=False),
    ]


def test_list_roles_query_has_no_hardcoded_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, (("alguien", True, False),))
    service.list_roles()

    (query, params) = fake.queries[0]
    assert "ORDER BY" in query
    assert "postgres" not in query
    assert "crud_" not in query
    assert params is None


def test_catalog_error_is_mapped_not_silenced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, error=StubPgError("permission denied", "42501")
    )

    with pytest.raises(InsufficientPrivilegeError):
        service.list_schemas()


def test_catalog_unexpected_error_preserves_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, error=StubPgError("boom", "XX000")
    )

    with pytest.raises(UnexpectedDatabaseError) as exc_info:
        service.list_tables("general")

    assert exc_info.value.sqlstate == "XX000"


def test_connection_failure_propagates_as_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(**kwargs: Any) -> FakeCatalogConnection:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", _fail)
    service = CatalogService(ConnectionManager(make_config()))

    with pytest.raises(DatabaseConnectionError):
        service.list_roles()


def test_no_transaction_left_open_when_autocommit_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, (("public",),), autocommit=False
    )
    service.list_schemas()

    assert fake.rollbacks >= 1


def test_idle_initial_status_rolls_back_after_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        (("public",),),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    schemas = service.list_schemas()

    assert [schema.name for schema in schemas] == ["public"]
    assert fake.rollbacks == 1


def test_preexisting_transaction_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        (("public",),),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    schemas = service.list_schemas()

    assert [schema.name for schema in schemas] == ["public"]
    assert fake.rollbacks == 0


def test_error_inside_preexisting_transaction_propagates_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    with pytest.raises(UnexpectedDatabaseError):
        service.list_tables("general")

    assert fake.rollbacks == 0


def test_error_with_owned_transaction_still_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    with pytest.raises(UnexpectedDatabaseError):
        service.list_tables("general")

    assert fake.rollbacks == 1
