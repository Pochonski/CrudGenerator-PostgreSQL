"""Pruebas unitarias de PrivilegeService (sin PostgreSQL real)."""

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
from crud_generator.privileges import PrivilegeMatrix, PrivilegeService

_SUFFIX = {
    CrudOperation.INSERT: "insertar",
    CrudOperation.READ: "consultar",
    CrudOperation.UPDATE: "actualizar",
    CrudOperation.DELETE: "eliminar",
}

_TABLE_PRIV = {
    CrudOperation.INSERT: "INSERT",
    CrudOperation.READ: "SELECT",
    CrudOperation.UPDATE: "UPDATE",
    CrudOperation.DELETE: "DELETE",
}


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


class FakeTransaction:
    def __init__(self, conn: FakePrivConnection) -> None:
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


class FakeCursor:
    def __init__(self, conn: FakePrivConnection) -> None:
        self._conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: Any, params: Any = None) -> None:
        self._conn.statements.append((query, params))
        if (
            self._conn.fail_at is not None
            and len(self._conn.statements) == self._conn.fail_at
            and self._conn.error is not None
        ):
            raise self._conn.error
        if isinstance(query, str) and "role_table_grants" in query:
            assert isinstance(params, tuple) and len(params) == 4
            key = (str(params[1]), str(params[0]))
            self._conn.pending_rows = [(1,)] if key in self._conn.schema_grants else []
            return
        if isinstance(query, str) and "pg_proc" in query:
            assert isinstance(params, tuple) and len(params) == 2
            key = (str(params[0]), str(params[1]))
            self._conn.catalog_queries.append((query, params))
            self._conn.pending_rows = list(
                self._conn.catalog.get(key, [])
            )

    def fetchall(self) -> list[tuple[Any, ...]]:
        rows = list(self._conn.pending_rows)
        self._conn.pending_rows = []
        return rows

    def fetchone(self) -> tuple[Any, ...] | None:
        rows = self.fetchall()
        return rows[0] if rows else None


class FakePrivConnection:
    def __init__(
        self,
        catalog: dict[tuple[str, str], list[tuple[Any, ...]]] | None = None,
        *,
        autocommit: bool = True,
        transaction_status: TransactionStatus = TransactionStatus.IDLE,
        error: BaseException | None = None,
        fail_at: int | None = None,
        schema_grants: set[tuple[str, str]] | None = None,
    ) -> None:
        self.catalog = dict(catalog or {})
        # Pares (esquema, rol) con grants directos residuales en el esquema
        # (para el chequeo previo a REVOKE USAGE; vacío = sin nada).
        self.schema_grants = set(schema_grants or set())
        self.autocommit = autocommit
        self.info = FakeInfo(transaction_status)
        self.closed = False
        self.statements: list[tuple[Any, Any]] = []
        self.catalog_queries: list[tuple[Any, Any]] = []
        self.pending_rows: list[tuple[Any, ...]] = []
        self.error = error
        self.fail_at = fail_at
        self.txn_opened = 0
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    catalog: dict[tuple[str, str], list[tuple[Any, ...]]] | None = None,
    *,
    autocommit: bool = True,
    transaction_status: TransactionStatus = TransactionStatus.IDLE,
    error: BaseException | None = None,
    fail_at: int | None = None,
    schema_grants: set[tuple[str, str]] | None = None,
) -> tuple[PrivilegeService, FakePrivConnection]:
    fake = FakePrivConnection(
        catalog,
        autocommit=autocommit,
        transaction_status=transaction_status,
        error=error,
        fail_at=fail_at,
        schema_grants=schema_grants,
    )
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: fake)
    return PrivilegeService(ConnectionManager(make_config())), fake


def _success(
    operation: CrudOperation,
    *,
    table: str = "t",
    schema: str = "lab",
    identity: str | None = "IN p_1 integer",
    routine: str | None = None,
) -> GenerationResult:
    return GenerationResult(
        operation=operation,
        status=GenerationStatus.SUCCESS,
        schema_name=schema,
        routine_name=routine if routine is not None else f"{table}_{_SUFFIX[operation]}",
        identity_arguments=identity,
        message="ok",
        sqlstate=None,
    )


def _matrix_all(table_ops: list[CrudOperation], roles: list[str]) -> PrivilegeMatrix:
    matrix = PrivilegeMatrix()
    for role in roles:
        matrix.add_role(role)
        for operation in table_ops:
            matrix.enable(role, operation)
    return matrix


def _identifiers(stmt: Any) -> list[Any]:
    found: list[Any] = []

    def walk(node: Any) -> None:
        if isinstance(node, sql.Identifier):
            obj = node._obj
            if isinstance(obj, tuple):
                found.extend(obj)
            else:
                found.append(obj)
        elif isinstance(node, sql.Composed):
            for part in node:
                walk(part)

    walk(stmt)
    return found


def _normalized(stmt: Any) -> str:
    return " ".join(" ".join(map(str, _sql_fragments(stmt))).split())


def _sql_fragments(stmt: Any) -> list[Any]:
    found: list[Any] = []

    def walk(node: Any) -> None:
        if isinstance(node, sql.SQL):
            found.append(node._obj)
        elif isinstance(node, sql.Composed):
            for part in node:
                walk(part)

    walk(stmt)
    return found


def _mutations(fake: FakePrivConnection) -> list[Any]:
    return [
        query
        for query, _ in fake.statements
        if not (isinstance(query, str) and "pg_proc" in query)
    ]


# --- validación de inputs -------------------------------------------------


def test_matrix_must_be_privilege_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)

    with pytest.raises(TypeError):
        service.apply_matrix("lab", "t", "no-matrix", [_success(CrudOperation.INSERT)])  # type: ignore[arg-type]
    assert fake.statements == []


def test_matrix_without_roles_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", PrivilegeMatrix(), [_success(CrudOperation.INSERT)]
        )
    assert fake.statements == []


def test_empty_schema_fails_without_query(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix("   ", "t", matrix, [_success(CrudOperation.INSERT)])
    assert fake.statements == []


def test_empty_table_fails_without_query(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "  ", matrix, [_success(CrudOperation.INSERT)])
    assert fake.statements == []


def test_special_names_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    schema, table = "Mi Esquema", "Catálogo Especial"
    identity = "IN p_1 integer"
    routine = f"{table}_insertar"
    service, fake = make_service(
        monkeypatch, catalog={(schema, routine): [(1, identity)]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["rol ñ"])

    changes = service.apply_matrix(
        schema, table, matrix, [_success(CrudOperation.INSERT, table=table, schema=schema)]
    )

    assert changes[0].schema_name == schema
    assert changes[0].table_name == table
    (query, params) = fake.catalog_queries[0]
    assert params == (schema, routine)
    assert schema not in query


def test_empty_generation_results_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [])
    assert fake.statements == []


def test_non_generation_result_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(TypeError):
        service.apply_matrix("lab", "t", matrix, ["INSERT"])  # type: ignore[list-item]
    assert fake.statements == []


def test_duplicate_operation_is_rejected_before_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab",
            "t",
            matrix,
            [_success(CrudOperation.INSERT), _success(CrudOperation.INSERT)],
        )
    assert _mutations(fake) == []


def test_success_without_routine_name_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])
    bad = GenerationResult(
        operation=CrudOperation.INSERT,
        status=GenerationStatus.SUCCESS,
        schema_name="lab",
        routine_name=None,
        identity_arguments="IN p_1 integer",
        message="ok",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [bad])
    assert _mutations(fake) == []


def test_success_with_none_identity_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT, identity=None)]
        )
    assert _mutations(fake) == []


def test_empty_identity_string_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(7, "")]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    (change,) = service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT, identity="")]
    )

    assert change.routine_name == "t_insertar"
    assert _mutations(fake) != []


def test_mismatched_schema_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT, schema="otro")]
        )
    assert _mutations(fake) == []


def test_wrong_routine_name_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab",
            "t",
            matrix,
            [_success(CrudOperation.INSERT, routine="t_crear")],
        )
    assert _mutations(fake) == []


def test_procedure_conflict_rejects_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])
    conflict = GenerationResult(
        operation=CrudOperation.INSERT,
        status=GenerationStatus.PROCEDURE_CONFLICT,
        schema_name="lab",
        routine_name="t_insertar",
        identity_arguments=None,
        message="conflicto",
        sqlstate="42723",
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [conflict])
    assert _mutations(fake) == []


def test_validation_error_rejects_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])
    invalid = GenerationResult(
        operation=CrudOperation.INSERT,
        status=GenerationStatus.VALIDATION_ERROR,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="inválido",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [invalid])
    assert _mutations(fake) == []


def test_null_operation_validation_error_rejects_without_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fila NULL/validation_error (operations vacío): ValueError claro, sin AttributeError."""
    service, fake = make_service(monkeypatch)
    matrix = _matrix_all([], ["r1"])
    invalid = GenerationResult(
        operation=None,
        status=GenerationStatus.VALIDATION_ERROR,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="Debe indicar al menos una operacion.",
        sqlstate=None,
    )

    with pytest.raises(ValueError, match="sin operación"):
        service.apply_matrix("lab", "t", matrix, [invalid])
    assert _mutations(fake) == []


def test_not_applicable_enabled_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.enable("r1", CrudOperation.UPDATE)
    not_applicable = GenerationResult(
        operation=CrudOperation.UPDATE,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="sin PK",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [not_applicable])
    assert _mutations(fake) == []


def test_not_applicable_denied_everywhere_cleans_table_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")
    matrix.enable("r1", CrudOperation.INSERT)
    denied_update = GenerationResult(
        operation=CrudOperation.UPDATE,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="sin PK",
        sqlstate=None,
    )

    changes = service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT), denied_update]
    )

    # Solo SUCCESS genera PrivilegeChange; la limpieza NOT_APPLICABLE no.
    assert [c.operation for c in changes] == [CrudOperation.INSERT]
    mutations = _mutations(fake)
    # USAGE + GRANT EXECUTE + GRANT tabla (INSERT) + REVOKE UPDATE tabla.
    assert len(mutations) == 4
    assert any(
        "REVOKE UPDATE ON" in _normalized(s) for s in mutations
    )
    # La limpieza no toca EXECUTE: el único EXECUTE es el de INSERT.
    execute_stmts = [s for s in mutations if "EXECUTE" in _normalized(s)]
    assert len(execute_stmts) == 1
    assert "t_insertar" in _identifiers(execute_stmts[0])
    for stmt in mutations:
        assert "actualizar" not in _identifiers(stmt)


# --- catálogo --------------------------------------------------------------


def test_catalog_zero_rows_is_contract_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, catalog={})
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )
    assert _mutations(fake) == []


def test_catalog_multiple_rows_is_overload_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer"), (2, "IN p_1 integer")]},
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )
    assert _mutations(fake) == []


def test_catalog_signature_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 text")]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )
    assert _mutations(fake) == []


def test_catalog_signature_match_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    (change,) = service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert change.allowed is True
    assert _mutations(fake) != []


# --- mutaciones ------------------------------------------------------------


@pytest.mark.parametrize(
    "operation,table_priv",
    [
        (CrudOperation.INSERT, "INSERT"),
        (CrudOperation.READ, "SELECT"),
        (CrudOperation.UPDATE, "UPDATE"),
        (CrudOperation.DELETE, "DELETE"),
    ],
)
def test_allowed_grants_execute_and_table(
    monkeypatch: pytest.MonkeyPatch,
    operation: CrudOperation,
    table_priv: str,
) -> None:
    routine = f"t_{_SUFFIX[operation]}"
    service, fake = make_service(
        monkeypatch, catalog={("lab", routine): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.enable("r1", operation)

    (change,) = service.apply_matrix("lab", "t", matrix, [_success(operation)])

    assert change.allowed is True
    mutations = _mutations(fake)
    assert len(mutations) == 3  # USAGE + EXECUTE + tabla
    fragments = [_normalized(s) for s in mutations]
    assert any("GRANT USAGE ON SCHEMA" in f for f in fragments)
    assert any("GRANT EXECUTE ON PROCEDURE" in f for f in fragments)
    assert any(f"GRANT {table_priv} ON" in f for f in fragments)


@pytest.mark.parametrize(
    "operation,table_priv",
    [
        (CrudOperation.INSERT, "INSERT"),
        (CrudOperation.READ, "SELECT"),
        (CrudOperation.UPDATE, "UPDATE"),
        (CrudOperation.DELETE, "DELETE"),
    ],
)
def test_denied_revokes_execute_and_table(
    monkeypatch: pytest.MonkeyPatch,
    operation: CrudOperation,
    table_priv: str,
) -> None:
    routine = f"t_{_SUFFIX[operation]}"
    service, fake = make_service(
        monkeypatch, catalog={("lab", routine): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    (change,) = service.apply_matrix("lab", "t", matrix, [_success(operation)])

    assert change.allowed is False
    mutations = _mutations(fake)
    # REVOKE EXECUTE + REVOKE tabla + chequeo de grants + REVOKE USAGE.
    assert len(mutations) == 4
    fragments = [_normalized(s) for s in mutations]
    assert any("REVOKE EXECUTE ON PROCEDURE" in f for f in fragments)
    assert any(f"REVOKE {table_priv} ON" in f for f in fragments)
    assert any("REVOKE USAGE ON SCHEMA" in f for f in fragments)


def test_fully_denied_role_still_produces_revokes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = [CrudOperation.INSERT, CrudOperation.READ]
    service, fake = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_consultar"): [(2, "IN p_1 integer")],
        },
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("solo-denegado")

    changes = service.apply_matrix(
        "lab", "t", matrix, [_success(op) for op in ops]
    )

    assert len(changes) == 2
    assert all(c.allowed is False for c in changes)
    # 2×(REVOKE EXECUTE + REVOKE tabla) + chequeo + REVOKE USAGE.
    assert len(_mutations(fake)) == 6


def test_usage_granted_once_per_allowed_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = [CrudOperation.INSERT, CrudOperation.READ]
    service, fake = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_consultar"): [(2, "IN p_1 integer")],
        },
    )
    matrix = _matrix_all(ops, ["r1"])

    service.apply_matrix("lab", "t", matrix, [_success(op) for op in ops])

    usage = [s for s in _mutations(fake) if "GRANT USAGE ON SCHEMA" in _normalized(s)]
    assert len(usage) == 1


def test_fully_denied_role_gets_usage_revoked_not_granted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rol sin nada habilitado y sin otros grants: USAGE se revoca, no se otorga."""
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    fragments = [_normalized(s) for s in _mutations(fake)]
    assert any("REVOKE USAGE ON SCHEMA" in f for f in fragments)
    assert not any("GRANT USAGE ON SCHEMA" in f for f in fragments)


def test_usage_kept_when_role_has_other_schema_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """USAGE se conserva si al rol le quedan grants en otras tablas del esquema."""
    service, fake = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]},
        schema_grants={("lab", "r1")},
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    fragments = [_normalized(s) for s in _mutations(fake)]
    assert not any("USAGE" in f for f in fragments)


def test_usage_revoke_quotes_hostile_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.add_role('r"; DROP --')

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    revoke = [
        s
        for s in _mutations(fake)
        if "REVOKE USAGE ON SCHEMA" in _normalized(s)
    ]
    assert len(revoke) == 1
    assert 'r"; DROP --' in _identifiers(revoke[0])
    assert "DROP TABLE" not in _normalized(revoke[0])


def test_roles_are_not_hardcoded(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.enable("equipo_zeta_7", CrudOperation.INSERT)

    (change,) = service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert change.role == "equipo_zeta_7"


def test_hostile_names_use_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    role, schema, table = 'r"; DROP --', "s' --", 't" --'
    routine = f"{table}_insertar"
    service, fake = make_service(
        monkeypatch, catalog={(schema, routine): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.enable(role, CrudOperation.INSERT)

    service.apply_matrix(
        schema,
        table,
        matrix,
        [_success(CrudOperation.INSERT, table=table, schema=schema)],
    )

    mutations = _mutations(fake)
    assert mutations != []
    for stmt in mutations:
        # Todo statement de mutación es Composed (nunca str interpolado).
        assert not isinstance(stmt, str)
        assert isinstance(stmt, sql.Composed)
        for fragment in _sql_fragments(stmt):
            for hostile in (role, schema, table, routine):
                assert fragment != hostile
    # Cada valor hostil viaja como Identifier en al menos un statement.
    union = [i for stmt in mutations for i in _identifiers(stmt)]
    for hostile in (role, schema, table, routine):
        assert hostile in union


def test_caller_identity_is_never_used_as_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = 'IN p_1 integer"); DROP TABLE lab.t; --'
    legit = "IN p_1 integer"
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, legit)]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])
    lying = GenerationResult(
        operation=CrudOperation.INSERT,
        status=GenerationStatus.SUCCESS,
        schema_name="lab",
        routine_name="t_insertar",
        identity_arguments=hostile,
        message="ok",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [lying])
    assert _mutations(fake) == []


def test_legit_signature_is_used_from_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legit = "IN p_2 text, IN p_1 integer"
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, legit)]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT, identity=legit)]
    )

    fragments = [
        fragment for stmt in _mutations(fake) for fragment in _sql_fragments(stmt)
    ]
    assert legit in fragments


# --- atomicidad ------------------------------------------------------------


def test_owner_single_atomic_transaction_autocommit_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = [CrudOperation.INSERT, CrudOperation.READ]
    service, fake = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_consultar"): [(2, "IN p_1 integer")],
        },
        autocommit=True,
        transaction_status=TransactionStatus.IDLE,
    )
    matrix = _matrix_all(ops, ["r1"])

    service.apply_matrix("lab", "t", matrix, [_success(op) for op in ops])

    assert fake.txn_opened == 1
    assert fake.commits == 1
    assert fake.rollbacks == 0


def test_owner_single_atomic_transaction_autocommit_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]},
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert fake.txn_opened == 1
    assert fake.commits == 1
    assert fake.rollbacks == 0


def test_owner_mid_mutation_pg_error_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = [CrudOperation.INSERT, CrudOperation.READ]
    service, fake = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_consultar"): [(2, "IN p_1 integer")],
        },
        autocommit=True,
        transaction_status=TransactionStatus.IDLE,
        error=StubPgError("boom", "XX000"),
        fail_at=4,  # 2 catálogos + USAGE + 1ra mutación fallida
    )
    matrix = _matrix_all(ops, ["r1"])

    with pytest.raises(UnexpectedDatabaseError):
        service.apply_matrix("lab", "t", matrix, [_success(op) for op in ops])

    assert fake.commits == 0
    assert fake.rollbacks == 1


def test_owner_success_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert fake.commits == 1
    assert fake.rollbacks == 0


def test_preexisting_intrans_success_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]},
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert fake.txn_opened == 0
    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_preexisting_intrans_error_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]},
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
        error=StubPgError("boom", "XX000"),
        fail_at=2,
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(UnexpectedDatabaseError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )

    assert fake.txn_opened == 0
    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_pg_42501_preserves_sqlstate(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]},
        error=StubPgError("permission denied", "42501"),
        fail_at=2,
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(InsufficientPrivilegeError) as exc_info:
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )

    assert exc_info.value.sqlstate == "42501"


def test_preflight_value_error_emits_no_mutations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "OTHER")]},
    )
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(ValueError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )

    assert _mutations(fake) == []


def test_changes_are_deterministic_and_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = [CrudOperation.DELETE, CrudOperation.INSERT]
    service, _ = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_eliminar"): [(2, "IN p_1 integer")],
        },
    )
    matrix = PrivilegeMatrix()
    matrix.enable("b_rol", CrudOperation.INSERT)
    matrix.add_role("a_rol")

    changes = service.apply_matrix("lab", "t", matrix, [_success(op) for op in ops])

    assert [(c.role, c.operation) for c in changes] == [
        ("a_rol", CrudOperation.DELETE),
        ("a_rol", CrudOperation.INSERT),
        ("b_rol", CrudOperation.DELETE),
        ("b_rol", CrudOperation.INSERT),
    ]
    assert [c.allowed for c in changes] == [False, False, False, True]
    assert all(
        c.schema_name == "lab" and c.table_name == "t" for c in changes
    )
    assert [c.routine_name for c in changes] == [
        "t_eliminar",
        "t_insertar",
        "t_eliminar",
        "t_insertar",
    ]


def test_connection_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(**kwargs: Any) -> FakePrivConnection:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", _fail)
    service = PrivilegeService(ConnectionManager(make_config()))
    matrix = _matrix_all([CrudOperation.INSERT], ["r1"])

    with pytest.raises(DatabaseConnectionError):
        service.apply_matrix(
            "lab", "t", matrix, [_success(CrudOperation.INSERT)]
        )


# --- reconciliación: habilitadas sin resultado / NOT_APPLICABLE ----------


def _not_applicable(operation: CrudOperation) -> GenerationResult:
    return GenerationResult(
        operation=operation,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="sin PK",
        sqlstate=None,
    )


def test_enabled_operation_without_result_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.enable("vendedor", CrudOperation.INSERT)
    matrix.enable("vendedor", CrudOperation.READ)
    matrix.enable("vendedor", CrudOperation.UPDATE)

    with pytest.raises(ValueError, match="UPDATE"):
        service.apply_matrix(
            "lab",
            "t",
            matrix,
            [_success(CrudOperation.INSERT), _success(CrudOperation.READ)],
        )
    # Preflight: cero GRANT/REVOKE y ni siquiera lookup en pg_catalog.
    assert _mutations(fake) == []
    assert fake.catalog_queries == []


def test_absent_but_fully_denied_operations_are_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, catalog={("lab", "t_insertar"): [(1, "IN p_1 integer")]}
    )
    matrix = PrivilegeMatrix()
    matrix.enable("r1", CrudOperation.INSERT)
    matrix.add_role("r2")

    changes = service.apply_matrix(
        "lab", "t", matrix, [_success(CrudOperation.INSERT)]
    )

    assert [(c.role, c.operation, c.allowed) for c in changes] == [
        ("r1", CrudOperation.INSERT, True),
        ("r2", CrudOperation.INSERT, False),
    ]
    assert _mutations(fake) != []


@pytest.mark.parametrize(
    "operation,table_priv",
    [
        (CrudOperation.UPDATE, "UPDATE"),
        (CrudOperation.DELETE, "DELETE"),
    ],
)
def test_not_applicable_denied_cleans_table_privilege(
    monkeypatch: pytest.MonkeyPatch,
    operation: CrudOperation,
    table_priv: str,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    changes = service.apply_matrix(
        "lab", "t", matrix, [_not_applicable(operation)]
    )

    assert changes == ()
    mutations = _mutations(fake)
    # REVOKE tabla + chequeo + REVOKE USAGE (sin otros grants en el esquema).
    assert len(mutations) == 3
    assert _normalized(mutations[0]) == f"REVOKE {table_priv} ON . FROM"
    assert "EXECUTE" not in _normalized(mutations[0])
    assert "GRANT" not in _normalized(mutations[0])
    assert "USAGE" not in _normalized(mutations[0])


def test_not_applicable_cleanup_for_each_denied_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")
    matrix.add_role("r2")

    service.apply_matrix(
        "lab", "t", matrix, [_not_applicable(CrudOperation.DELETE)]
    )

    mutations = _mutations(fake)
    # 2 roles × (REVOKE tabla + chequeo + REVOKE USAGE).
    assert len(mutations) == 6
    assert "REVOKE DELETE ON" in _normalized(mutations[0])
    assert "REVOKE DELETE ON" in _normalized(mutations[3])


def test_mixed_success_and_not_applicable(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch,
        catalog={
            ("lab", "t_insertar"): [(1, "IN p_1 integer")],
            ("lab", "t_consultar"): [(2, "IN p_1 integer")],
        },
    )
    matrix = PrivilegeMatrix()
    matrix.enable("role_a", CrudOperation.INSERT)
    matrix.enable("role_a", CrudOperation.READ)
    matrix.add_role("role_b")
    results = [
        _success(CrudOperation.INSERT),
        _success(CrudOperation.READ),
        _not_applicable(CrudOperation.UPDATE),
    ]

    changes = service.apply_matrix("lab", "t", matrix, results)

    # role_a recibe GRANT USAGE una sola vez (role_b recibe REVOKE USAGE).
    usage = [s for s in _mutations(fake) if "GRANT USAGE ON SCHEMA" in _normalized(s)]
    assert len(usage) == 1
    assert "role_a" in _identifiers(usage[0])
    # role_a: GRANT INSERT/SELECT + REVOKE UPDATE tabla.
    fragments = [_normalized(s) for s in _mutations(fake)]
    assert any("GRANT INSERT ON" in f for f in fragments)
    assert any("GRANT SELECT ON" in f for f in fragments)
    assert any("REVOKE UPDATE ON" in f for f in fragments)
    # role_b no recibe GRANT USAGE (solo REVOKEs + REVOKE USAGE al quedar sin nada).
    assert not any(
        "role_b" in _identifiers(s) and "GRANT USAGE" in _normalized(s)
        for s in _mutations(fake)
    )
    assert any(
        "role_b" in _identifiers(s) and "REVOKE USAGE" in _normalized(s)
        for s in _mutations(fake)
    )
    # PrivilegeChange solo para rol × SUCCESS (2 roles × 2 ops).
    assert len(changes) == 4
    assert {(c.role, c.operation) for c in changes} == {
        ("role_a", CrudOperation.INSERT),
        ("role_a", CrudOperation.READ),
        ("role_b", CrudOperation.INSERT),
        ("role_b", CrudOperation.READ),
    }
    assert [c.allowed for c in changes if c.role == "role_a"] == [True, True]
    assert [c.allowed for c in changes if c.role == "role_b"] == [False, False]


def test_not_applicable_revoke_pg_error_rolls_back_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        autocommit=True,
        transaction_status=TransactionStatus.IDLE,
        error=StubPgError("boom", "XX000"),
        fail_at=1,  # el único statement es el REVOKE de limpieza
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    with pytest.raises(UnexpectedDatabaseError):
        service.apply_matrix(
            "lab", "t", matrix, [_not_applicable(CrudOperation.UPDATE)]
        )

    assert fake.commits == 0
    assert fake.rollbacks == 1


def test_not_applicable_revoke_error_intrans_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
        error=StubPgError("boom", "XX000"),
        fail_at=1,
    )
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")

    with pytest.raises(UnexpectedDatabaseError):
        service.apply_matrix(
            "lab", "t", matrix, [_not_applicable(CrudOperation.UPDATE)]
        )

    assert fake.txn_opened == 0
    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_not_applicable_schema_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")
    foreign = GenerationResult(
        operation=CrudOperation.UPDATE,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="otro",
        routine_name=None,
        identity_arguments=None,
        message="sin PK",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [foreign])
    assert fake.statements == []
    assert fake.catalog_queries == []


@pytest.mark.parametrize(
    "operation",
    [CrudOperation.INSERT, CrudOperation.READ],
)
def test_not_applicable_insert_read_is_contract_violation(
    monkeypatch: pytest.MonkeyPatch, operation: CrudOperation
) -> None:
    service, fake = make_service(monkeypatch)
    matrix = PrivilegeMatrix()
    matrix.add_role("r1")
    bogus = GenerationResult(
        operation=operation,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="lab",
        routine_name=None,
        identity_arguments=None,
        message="n/a",
        sqlstate=None,
    )

    with pytest.raises(ValueError):
        service.apply_matrix("lab", "t", matrix, [bogus])
    assert _mutations(fake) == []
    assert fake.catalog_queries == []
