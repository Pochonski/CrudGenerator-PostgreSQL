"""Pruebas unitarias de ConnectionManager (sin PostgreSQL real)."""

from __future__ import annotations

from typing import Any, Self

import psycopg
import pytest

from crud_generator.config import DatabaseConfig
from crud_generator.db import (
    AuthenticationError,
    ConnectionInfo,
    ConnectionManager,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    InsufficientPrivilegeError,
    ServerUnavailableError,
    UnexpectedDatabaseError,
)

PASSWORD = "s3cr3t-pw"


def make_config(**overrides: Any) -> DatabaseConfig:
    values: dict[str, Any] = {
        "host": "localhost",
        "port": 5432,
        "database": "crud_test",
        "user": "tester",
        "password": PASSWORD,
    }
    values.update(overrides)
    return DatabaseConfig(**values)


class FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row
        self.executed: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str) -> None:
        self.executed.append(query)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeConnection:
    def __init__(
        self,
        row: tuple[Any, ...] | None = ("crud_test", "tester", "PostgreSQL 16.4"),
        *,
        autocommit: bool = True,
    ) -> None:
        self.closed = False
        self.autocommit = autocommit
        self.row = row
        self.cursors: list[FakeCursor] = []
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def cursor(self) -> FakeCursor:
        cursor = FakeCursor(self.row)
        self.cursors.append(cursor)
        return cursor

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1
        self.closed = True


class StubPgError(Exception):
    """Excepción con SQLSTATE configurable sin depender de psycopg interno."""

    def __init__(self, message: str, sqlstate: str | None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


def patch_connect(
    monkeypatch: pytest.MonkeyPatch, fake: FakeConnection | BaseException
) -> dict[str, Any]:
    """Reemplaza psycopg.connect. Retorna las llamadas capturadas."""
    calls: dict[str, Any] = {"count": 0, "kwargs": {}}

    def _fake_connect(**kwargs: Any) -> FakeConnection:
        calls["count"] += 1
        calls["kwargs"] = kwargs
        if isinstance(fake, BaseException):
            raise fake
        return fake

    monkeypatch.setattr(psycopg, "connect", _fake_connect)
    return calls


def test_uses_database_config_values(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    calls = patch_connect(monkeypatch, FakeConnection())

    manager = ConnectionManager(config, connect_timeout=7)
    manager.connect()

    assert calls["count"] == 1
    assert calls["kwargs"]["host"] == "localhost"
    assert calls["kwargs"]["port"] == 5432
    assert calls["kwargs"]["dbname"] == "crud_test"
    assert calls["kwargs"]["user"] == "tester"
    assert calls["kwargs"]["password"] == PASSWORD
    assert calls["kwargs"]["connect_timeout"] == 7
    assert calls["kwargs"]["autocommit"] is True
    assert manager.is_connected


def test_connect_reuses_open_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    calls = patch_connect(monkeypatch, fake)

    manager = ConnectionManager(make_config())
    first = manager.connect()
    second = manager.connect()

    assert first is second
    assert calls["count"] == 1


def test_reconnects_when_server_closed_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_fake = FakeConnection()
    calls = patch_connect(monkeypatch, first_fake)

    manager = ConnectionManager(make_config())
    manager.connect()
    first_fake.closed = True  # el servidor cerró la conexión
    assert not manager.is_connected

    second_fake = FakeConnection()
    patch_connect(monkeypatch, second_fake)
    conn = manager.connect()

    assert conn is second_fake
    assert calls["count"] == 1  # solo cuenta la primera captura


def test_close_closes_and_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    patch_connect(monkeypatch, fake)

    manager = ConnectionManager(make_config())
    manager.connect()
    manager.close()

    assert fake.closes == 1
    assert not manager.is_connected
    manager.close()  # no debe fallar
    assert fake.closes == 1


def test_context_manager_opens_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    patch_connect(monkeypatch, fake)

    with ConnectionManager(make_config()) as manager:
        assert manager.is_connected
    assert fake.closed
    assert not manager.is_connected


def test_connection_property_raises_without_open_connection() -> None:
    manager = ConnectionManager(make_config())
    with pytest.raises(DatabaseConnectionError):
        _ = manager.connection


def test_validate_returns_connection_info(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection(row=("mydb", "myuser", "PostgreSQL 16.4 on x86_64"))
    patch_connect(monkeypatch, fake)

    manager = ConnectionManager(make_config())
    info = manager.validate()

    assert isinstance(info, ConnectionInfo)
    assert info.database == "mydb"
    assert info.current_user == "myuser"
    assert "PostgreSQL 16.4" in info.server_version
    assert len(fake.cursors) == 1
    assert "current_database()" in fake.cursors[0].executed[0]
    assert "current_user" in fake.cursors[0].executed[0]


def test_validate_rolls_back_when_autocommit_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeConnection(autocommit=False)
    patch_connect(monkeypatch, fake)

    manager = ConnectionManager(make_config(), autocommit=False)
    manager.validate()

    # La consulta de validación no debe quedar en idle-in-transaction.
    assert fake.rollbacks >= 1


def test_validate_empty_row_is_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_connect(monkeypatch, FakeConnection(row=None))

    with pytest.raises(DatabaseConnectionError):
        ConnectionManager(make_config()).validate()


def test_operational_error_without_sqlstate_maps_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_connect(
        monkeypatch, psycopg.OperationalError("connection failed: port closed")
    )

    with pytest.raises(ServerUnavailableError):
        ConnectionManager(make_config()).connect()


def test_wrong_password_maps_to_authentication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_connect(
        monkeypatch, StubPgError('password authentication failed for user "t"', "28P01")
    )

    with pytest.raises(AuthenticationError) as exc_info:
        ConnectionManager(make_config()).validate()

    assert exc_info.value.sqlstate == "28P01"


def test_missing_database_maps_to_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_connect(monkeypatch, StubPgError('database "x" does not exist', "3D000"))

    with pytest.raises(DatabaseNotFoundError):
        ConnectionManager(make_config()).validate()


def test_connection_exception_class_maps_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_connect(monkeypatch, StubPgError("connection exception", "08001"))

    with pytest.raises(ServerUnavailableError):
        ConnectionManager(make_config()).connect()


def test_insufficient_privilege_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_connect(monkeypatch, StubPgError("permission denied", "42501"))

    with pytest.raises(InsufficientPrivilegeError) as exc_info:
        ConnectionManager(make_config()).validate()

    assert exc_info.value.sqlstate == "42501"


def test_unexpected_sqlstate_preserves_info(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_connect(monkeypatch, StubPgError("syntax error", "42601"))

    with pytest.raises(UnexpectedDatabaseError) as exc_info:
        ConnectionManager(make_config()).validate()

    assert exc_info.value.sqlstate == "42601"
    assert "syntax error" in str(exc_info.value)
    assert isinstance(exc_info.value.original, StubPgError)


def test_connection_failure_is_never_silent_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_connect(monkeypatch, OSError("network unreachable"))

    with pytest.raises(DatabaseConnectionError):
        ConnectionManager(make_config()).validate()


def test_password_not_exposed_in_repr_or_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config()
    manager = ConnectionManager(config)

    assert PASSWORD not in repr(manager)
    assert PASSWORD not in repr(config)

    patch_connect(
        monkeypatch, StubPgError(f"failing with {PASSWORD} inside", "XX000")
    )
    with pytest.raises(DatabaseConnectionError) as exc_info:
        manager.validate()

    assert PASSWORD not in str(exc_info.value)


def test_commit_and_rollback_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    patch_connect(monkeypatch, fake)

    manager = ConnectionManager(make_config())
    manager.connect()
    manager.commit()
    manager.rollback()

    assert fake.commits == 1
    assert fake.rollbacks == 1


def test_commit_without_connection_raises() -> None:
    manager = ConnectionManager(make_config())
    with pytest.raises(DatabaseConnectionError):
        manager.commit()


def test_rollback_without_connection_raises() -> None:
    manager = ConnectionManager(make_config())
    with pytest.raises(DatabaseConnectionError):
        manager.rollback()


class RoleCursor:
    def __init__(self, conn: RoleConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: Any, params: Any = None) -> None:
        self._conn.statements.append((query, params))
        if (
            self._conn.error is not None
            and len(self._conn.statements) == self._conn.error_at
        ):
            raise self._conn.error

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conn.rows.pop(0) if self._conn.rows else None


class RoleConnection:
    def __init__(
        self,
        rows: list[tuple[Any, ...] | None],
        *,
        error: BaseException | None = None,
        error_at: int = 0,
    ) -> None:
        self.rows = list(rows)
        self.error = error
        self.error_at = error_at
        self.autocommit = True
        self.closed = False
        self.statements: list[tuple[Any, Any]] = []

    def cursor(self) -> RoleCursor:
        return RoleCursor(self)

    def close(self) -> None:
        self.closed = True


def patch_role_connect(
    monkeypatch: pytest.MonkeyPatch, fake: RoleConnection
) -> None:
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: fake)


def test_assume_role_sets_before_yield_and_resets_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RoleConnection([("tester",), ("crud_admin", "tester")])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())
    seen: list[bool] = []

    with manager.assume_role("crud_admin"):
        seen.append(True)

    assert seen == [True]
    assert len(fake.statements) == 4
    assert fake.rows == []


def test_assume_role_quotes_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from psycopg import sql as _sql

    role = 'a"; DROP --'
    fake = RoleConnection([("tester",), (role, "tester")])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with manager.assume_role(role):
        pass

    set_stmt = fake.statements[1][0]
    assert isinstance(set_stmt, _sql.Composed)
    assert "DROP" not in " ".join(
        part._obj for part in set_stmt if isinstance(part, _sql.SQL)
    )


def test_assume_role_resets_on_body_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RoleConnection([("tester",), ("crud_admin", "tester")])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with pytest.raises(RuntimeError, match="boom"), manager.assume_role(
        "crud_admin"
    ):
        raise RuntimeError("boom")

    assert len(fake.statements) == 4


def test_assume_role_current_user_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RoleConnection([("tester",), ("otro", "tester")])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with pytest.raises(UnexpectedDatabaseError), manager.assume_role(
        "crud_admin"
    ):
        pass  # pragma: no cover

    # SET tuvo éxito: RESET debe intentarse aunque falle la verificación.
    assert len(fake.statements) == 4
    assert fake.statements[3][0] == "RESET ROLE"


def test_assume_role_verify_error_still_resets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RoleConnection(
        [("tester",)],
        error=StubPgError("boom", "XX000"),
        error_at=3,
    )
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with pytest.raises(UnexpectedDatabaseError) as exc_info, manager.assume_role(
        "crud_admin"
    ):
        pass  # pragma: no cover

    assert exc_info.value.sqlstate == "XX000"
    assert len(fake.statements) == 4
    assert fake.statements[3][0] == "RESET ROLE"


def test_assume_role_statement_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from psycopg import sql as _sql

    fake = RoleConnection([("tester",), ("crud_admin", "tester")])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with manager.assume_role("crud_admin"):
        pass

    assert fake.statements[0][0] == "SELECT current_user"
    assert isinstance(fake.statements[1][0], _sql.Composed)
    assert fake.statements[2][0] == "SELECT current_user, session_user"
    assert fake.statements[3][0] == "RESET ROLE"


def test_assume_role_42501_is_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = RoleConnection(
        [("tester",)],
        error=StubPgError("permission denied", "42501"),
        error_at=2,
    )
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with pytest.raises(
        InsufficientPrivilegeError
    ) as exc_info, manager.assume_role("crud_admin"):
        pass  # pragma: no cover

    assert exc_info.value.sqlstate == "42501"
    # SET falló: no debe intentarse RESET.
    assert len(fake.statements) == 2


def test_assume_role_invalid_names_fail_without_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = patch_connect(monkeypatch, FakeConnection())
    manager = ConnectionManager(make_config())

    with pytest.raises(TypeError), manager.assume_role(123):  # type: ignore[arg-type]
        pass  # pragma: no cover
    with pytest.raises(ValueError), manager.assume_role("   "):
        pass  # pragma: no cover
    assert calls["count"] == 0


def test_assume_role_already_current_is_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RoleConnection([("crud_admin",)])
    patch_role_connect(monkeypatch, fake)
    manager = ConnectionManager(make_config())

    with manager.assume_role("crud_admin"):
        pass

    assert len(fake.statements) == 1
