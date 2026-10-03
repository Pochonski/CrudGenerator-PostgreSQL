"""Pruebas unitarias de PermissionProbeService (sin PostgreSQL real)."""

from __future__ import annotations

from typing import Any, Self

import psycopg
import pytest
from psycopg import sql
from psycopg.pq import TransactionStatus

from crud_generator.config import DatabaseConfig
from crud_generator.db import (
    ConnectionManager,
    DatabaseConnectionError,
    InsufficientPrivilegeError,
    UnexpectedDatabaseError,
)
from crud_generator.models import CrudOperation, GenerationResult, GenerationStatus
from crud_generator.privileges import (
    PermissionProbeService,
    PermissionProbeStatus,
    RoleAssumptionError,
)


def make_config() -> DatabaseConfig:
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="crud_test",
        user="tester",
        password="s3cr3t-pw",
    )


class StubPgError(psycopg.Error):
    def __init__(self, message: str, sqlstate: str | None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


class FakeInfo:
    def __init__(
        self, transaction_status: TransactionStatus = TransactionStatus.IDLE
    ) -> None:
        self.transaction_status = transaction_status


class FakeProbeTransaction:
    def __init__(self, conn: FakeProbeConnection, **kwargs: Any) -> None:
        self._conn = conn
        self._conn.txn_kwargs = kwargs

    def __enter__(self) -> Self:
        self._conn.txn_opened += 1
        return self

    def __exit__(self, exc_type: object, *args: object) -> bool:
        self._conn.txn_closed += 1
        return False


class FakeProbeCursor:
    def __init__(self, conn: FakeProbeConnection) -> None:
        self._conn = conn
        self._step: str | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: Any, params: Any = None) -> None:
        self._conn.executed.append((query, params))
        template = _normalized(query)
        if "SET LOCAL ROLE" in template:
            self._step = "set_role"
            self._conn.order.append("set_role")
            if self._conn.fail_set_role is not None:
                raise self._conn.fail_set_role
        elif "current_user" in template:
            self._step = "verify"
            self._conn.order.append("verify")
            if self._conn.fail_verify is not None:
                raise self._conn.fail_verify
        elif template.startswith("CALL"):
            self._step = "call"
            self._conn.order.append("call")
            self._conn.call_params = params
            if self._conn.fail_call is not None:
                raise self._conn.fail_call
        else:  # pragma: no cover - defensa ante SQL inesperado
            raise AssertionError(f"SQL inesperado en probe: {template!r}")

    @property
    def description(self) -> Any:
        if self._step == "call":
            return self._conn.call_description
        return None

    def fetchone(self) -> tuple[Any, ...] | None:
        if self._step == "verify":
            return self._conn.verify_row
        if self._step == "call":
            return self._conn.call_row
        return None


class FakeProbeConnection:
    """Fake mínimo: sin commit()/rollback() manuales a propósito."""

    def __init__(
        self,
        *,
        autocommit: bool = True,
        transaction_status: TransactionStatus = TransactionStatus.IDLE,
        verify_row: tuple[Any, ...] | None = None,
        call_description: Any = None,
        call_row: tuple[Any, ...] | None = None,
        fail_set_role: BaseException | None = None,
        fail_verify: BaseException | None = None,
        fail_call: BaseException | None = None,
    ) -> None:
        self.autocommit = autocommit
        self.info = FakeInfo(transaction_status)
        self.closed = False
        self.executed: list[tuple[Any, Any]] = []
        self.order: list[str] = []
        self.call_params: Any = None
        self.verify_row = verify_row
        self.call_description = call_description
        self.call_row = call_row
        self.fail_set_role = fail_set_role
        self.fail_verify = fail_verify
        self.fail_call = fail_call
        self.txn_opened = 0
        self.txn_closed = 0
        self.txn_kwargs: dict[str, Any] = {}

    def cursor(self) -> FakeProbeCursor:
        return FakeProbeCursor(self)

    def transaction(self, **kwargs: Any) -> FakeProbeTransaction:
        return FakeProbeTransaction(self, **kwargs)

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch, **kwargs: Any
) -> tuple[PermissionProbeService, FakeProbeConnection]:
    fake = FakeProbeConnection(**kwargs)
    monkeypatch.setattr(psycopg, "connect", lambda **kw: fake)
    return PermissionProbeService(ConnectionManager(make_config())), fake


def _result(
    operation: CrudOperation = CrudOperation.DELETE,
    *,
    status: GenerationStatus = GenerationStatus.SUCCESS,
    schema: str = "lab",
    routine: str | None = None,
) -> GenerationResult:
    suffix = {
        CrudOperation.INSERT: "insertar",
        CrudOperation.READ: "consultar",
        CrudOperation.UPDATE: "actualizar",
        CrudOperation.DELETE: "eliminar",
    }[operation]
    return GenerationResult(
        operation=operation,
        status=status,
        schema_name=schema,
        routine_name=routine if routine is not None else f"producto_{suffix}",
        identity_arguments="IN p_1 integer",
        message="ok",
        sqlstate=None,
    )


def _normalized(stmt: Any) -> str:
    if isinstance(stmt, str):
        return " ".join(stmt.split())
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, sql.SQL):
            parts.append(str(node._obj))
        elif isinstance(node, sql.Composed):
            for part in node:
                walk(part)

    walk(stmt)
    return " ".join(" ".join(parts).split())


def _placeholders(stmt: Any) -> int:
    count = 0

    def walk(node: Any) -> None:
        nonlocal count
        if isinstance(node, sql.Placeholder):
            count += 1
        elif isinstance(node, sql.Composed):
            for part in node:
                walk(part)

    walk(stmt)
    return count


def _identifiers(stmt: Any) -> list[Any]:
    found: list[Any] = []

    def walk(node: Any) -> None:
        if isinstance(node, sql.Identifier):
            obj = node._obj
            found.extend(obj if isinstance(obj, tuple) else [obj])
        elif isinstance(node, sql.Composed):
            for part in node:
                walk(part)

    walk(stmt)
    return found


# --- validación ------------------------------------------------------------


def test_role_non_str_is_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch, verify_row=("r", "s"))

    with pytest.raises(TypeError):
        service.probe(123, _result())  # type: ignore[arg-type]
    assert fake.executed == []


def test_role_empty_is_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch, verify_row=("r", "s"))

    with pytest.raises(ValueError):
        service.probe("   ", _result())
    assert fake.executed == []


def test_non_generation_result_is_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, verify_row=("r", "s"))

    with pytest.raises(TypeError):
        service.probe("r1", "no-result")  # type: ignore[arg-type]
    assert fake.executed == []


def test_non_success_status_is_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, verify_row=("r", "s"))

    with pytest.raises(ValueError):
        service.probe(
            "r1", _result(status=GenerationStatus.NOT_APPLICABLE)
        )
    assert fake.executed == []


def test_none_routine_name_is_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, verify_row=("r", "s"))
    bad = GenerationResult(
        operation=CrudOperation.DELETE,
        status=GenerationStatus.SUCCESS,
        schema_name="lab",
        routine_name=None,
        identity_arguments="IN p_1 integer",
        message="ok",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.probe("r1", bad)
    assert fake.executed == []


def test_str_arguments_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    with pytest.raises(TypeError):
        service.probe("crud_vendedor", _result(), "texto")  # type: ignore[arg-type]
    assert fake.executed == []


def test_arguments_materialized_once(monkeypatch: pytest.MonkeyPatch) -> None:
    consumed = iter([1, "x", None])
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    result = service.probe("crud_vendedor", _result(), consumed)

    assert result.status is PermissionProbeStatus.ALLOWED
    assert fake.call_params == (1, "x", None)


def test_hostile_names_use_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    role, schema = 'r"; DROP --', "s' --"
    service, fake = make_service(monkeypatch, verify_row=(role, "admin"))
    res = _result(schema=schema, routine="t_eliminar")

    service.probe(role, res, (1,))

    composed = [stmt for stmt, _ in fake.executed if not isinstance(stmt, str)]
    assert composed != []
    union = [i for stmt in composed for i in _identifiers(stmt)]
    for hostile in (role, schema, "t_eliminar"):
        assert hostile in union


def test_call_without_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    result = service.probe("crud_vendedor", _result(), ())

    assert result.status is PermissionProbeStatus.ALLOWED
    assert fake.call_params == ()
    call_stmt = fake.executed[-1][0]
    assert _normalized(call_stmt).endswith("( )")
    assert _placeholders(call_stmt) == 0


@pytest.mark.parametrize("args", [(1,), (1, "Teclado", 25.50)])
def test_call_arguments_use_placeholders(
    monkeypatch: pytest.MonkeyPatch, args: tuple[Any, ...]
) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), args)

    call_stmt, params = fake.executed[-1]
    assert params == args
    assert _placeholders(call_stmt) == len(args)
    for hostile in ("Teclado", "DROP"):
        assert hostile not in _normalized(call_stmt)


def test_hostile_values_never_interpolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), ["x'); DROP TABLE lab.producto; --"])

    call_stmt, params = fake.executed[-1]
    assert params == ("x'); DROP TABLE lab.producto; --",)
    assert "DROP TABLE" not in _normalized(call_stmt)


# --- secuencia y verificación ----------------------------------------------


def test_sql_order_set_verify_call(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), (1,))

    assert _.order == ["set_role", "verify", "call"]


def test_set_role_before_call_uses_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), (1,))

    set_stmt, params = fake.executed[0]
    assert _normalized(set_stmt).startswith("SET LOCAL ROLE")
    assert params is None
    assert "crud_vendedor" in _identifiers(set_stmt)


def test_current_user_mismatch_is_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, verify_row=("otro_rol", "admin"))

    with pytest.raises(ValueError):
        service.probe("crud_vendedor", _result(), (1,))


def test_call_without_output_is_allowed_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        call_description=None,
        call_row=None,
    )

    result = service.probe("crud_vendedor", _result(), (1,))

    assert result.status is PermissionProbeStatus.ALLOWED
    assert result.output is None


def test_call_with_inout_output_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        call_description=["p_1"],
        call_row=(102, "Mouse", 10.00),
    )

    result = service.probe(
        "crud_vendedor", _result(CrudOperation.READ), (102, None, None)
    )

    assert result.status is PermissionProbeStatus.ALLOWED
    assert result.output == (102, "Mouse", 10.00)


def test_refcursor_output_preserved_without_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        call_description=["resultado"],
        call_row=("<unnamed portal 1>",),
    )

    result = service.probe("crud_vendedor", _result(CrudOperation.READ), (None,))

    assert result.status is PermissionProbeStatus.ALLOWED
    assert result.output == ("<unnamed portal 1>",)
    kinds = [_normalized(q) for q, _ in fake.executed]
    assert not any(k.startswith("FETCH") for k in kinds)


# --- errores ---------------------------------------------------------------


def test_set_role_42501_is_assumption_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, fail_set_role=StubPgError("cannot set role", "42501")
    )

    with pytest.raises(RoleAssumptionError) as exc_info:
        service.probe("crud_vendedor", _result(), (1,))

    assert exc_info.value.sqlstate == "42501"
    assert isinstance(exc_info.value, InsufficientPrivilegeError)


def test_call_42501_is_denied_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        fail_call=StubPgError("permission denied", "42501"),
    )

    result = service.probe("crud_vendedor", _result(), (1,))

    assert result.status is PermissionProbeStatus.DENIED
    assert result.sqlstate == "42501"
    assert result.output is None


def test_call_p0002_propagates_mapped_not_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_administrador", "admin"),
        fail_call=StubPgError("no data found", "P0002"),
    )

    with pytest.raises(UnexpectedDatabaseError) as exc_info:
        service.probe("crud_administrador", _result(), (1,))

    assert exc_info.value.sqlstate == "P0002"


def test_other_pg_error_preserves_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        fail_call=StubPgError("boom", "XX000"),
    )

    with pytest.raises(UnexpectedDatabaseError) as exc_info:
        service.probe("crud_vendedor", _result(), (1,))

    assert exc_info.value.sqlstate == "XX000"


def test_connection_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(**kwargs: Any) -> FakeProbeConnection:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", _fail)
    service = PermissionProbeService(ConnectionManager(make_config()))

    with pytest.raises(DatabaseConnectionError):
        service.probe("crud_vendedor", _result(), (1,))


# --- transacción ------------------------------------------------------------


def test_idle_requests_force_rollback_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), (1,))

    assert fake.txn_opened == 1
    assert fake.txn_kwargs == {"force_rollback": True}


@pytest.mark.parametrize("autocommit", [True, False])
def test_idle_works_with_either_autocommit(
    monkeypatch: pytest.MonkeyPatch, autocommit: bool
) -> None:
    service, fake = make_service(
        monkeypatch,
        autocommit=autocommit,
        verify_row=("crud_vendedor", "admin"),
    )

    result = service.probe("crud_vendedor", _result(), (1,))

    assert result.status is PermissionProbeStatus.ALLOWED
    assert fake.txn_opened == 1
    assert fake.txn_kwargs == {"force_rollback": True}


def test_intrans_is_rejected_before_any_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        transaction_status=TransactionStatus.INTRANS,
        verify_row=("crud_vendedor", "admin"),
    )

    with pytest.raises(RuntimeError):
        service.probe("crud_vendedor", _result(), (1,))

    assert fake.executed == []
    assert fake.txn_opened == 0


def test_no_manual_commit_or_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), (1,))

    assert not hasattr(fake, "commit")
    assert not hasattr(fake, "rollback")


# --- resultado ----------------------------------------------------------------


def test_result_carries_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    result = service.probe("crud_vendedor", _result(CrudOperation.DELETE), (5,))

    assert result.role == "crud_vendedor"
    assert result.operation is CrudOperation.DELETE
    assert result.schema_name == "lab"
    assert result.routine_name == "producto_eliminar"


def test_allowed_has_no_sqlstate(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    result = service.probe("crud_vendedor", _result(), (1,))

    assert result.sqlstate is None
    assert result.message


def test_denied_has_no_output(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        verify_row=("crud_vendedor", "admin"),
        fail_call=StubPgError("denied", "42501"),
    )

    result = service.probe("crud_vendedor", _result(), (1,))

    assert result.output is None
    assert result.message


def test_no_reset_role_required(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, verify_row=("crud_vendedor", "admin")
    )

    service.probe("crud_vendedor", _result(), (1,))

    assert not any("RESET" in _normalized(q) for q, _ in fake.executed)


def test_no_hardcoded_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    import inspect

    import crud_generator.privileges.probe as probe_module

    source = inspect.getsource(probe_module)
    assert "producto_insertar" not in source
    assert "crud_vendedor" not in source
    assert "crud_admin" not in source
