"""Pruebas unitarias de ExtensionService (sin PostgreSQL real)."""

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
from crud_generator.models import (
    CrudOperation,
    ExtensionState,
    GenerationStatus,
)
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

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._conn.rows)


class FakeExtConnection:
    def __init__(
        self,
        row: tuple[Any, ...] | None = None,
        *,
        rows: tuple[tuple[Any, ...], ...] = (),
        error: BaseException | None = None,
        autocommit: bool = True,
        transaction_status: TransactionStatus = TransactionStatus.IDLE,
    ) -> None:
        self.row = row
        self.rows = list(rows)
        self.error = error
        self.autocommit = autocommit
        self.info = FakeConnInfo(transaction_status)
        self.closed = False
        self.queries: list[tuple[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeExtCursor:
        return FakeExtCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    row: tuple[Any, ...] | None = None,
    *,
    rows: tuple[tuple[Any, ...], ...] = (),
    error: BaseException | None = None,
    autocommit: bool = True,
    transaction_status: TransactionStatus = TransactionStatus.IDLE,
) -> tuple[ExtensionService, FakeExtConnection]:
    fake = FakeExtConnection(
        row,
        rows=rows,
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


def test_default_extension_name_is_confirmed() -> None:
    # Nombre confirmado por Joyce (01-10): extension/crud_generator.control
    # (schema = crud_generator) + CONTRACTS.md §3. Ya no es provisional.
    assert DEFAULT_EXTENSION_NAME == "crud_generator"


def test_non_postgres_error_is_not_masked_as_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(monkeypatch, error=RuntimeError("bug interno"))

    with pytest.raises(RuntimeError):
        service.check_extension("crud_generator")


# ---------------------------------------------------------------------------
# analyze_table (CONTRACTS.md §3.1)
# ---------------------------------------------------------------------------


def _column_row(**overrides: Any) -> tuple[Any, ...]:
    base: dict[str, Any] = {
        "column_name": "id",
        "data_type": "integer",
        "ordinal_position": 1,
        "is_primary_key": False,
        "pk_position": None,
        "is_nullable": False,
        "has_default": False,
        "default_expression": None,
        "is_identity": False,
        "identity_generation": None,
        "is_generated": False,
        "generated_expression": None,
    }
    base.update(overrides)
    return (
        base["column_name"],
        base["data_type"],
        base["ordinal_position"],
        base["is_primary_key"],
        base["pk_position"],
        base["is_nullable"],
        base["has_default"],
        base["default_expression"],
        base["is_identity"],
        base["identity_generation"],
        base["is_generated"],
        base["generated_expression"],
    )


def test_analyze_maps_simple_column(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(monkeypatch, rows=(_column_row(),))

    (column,) = service.analyze_table("lab", "producto")

    assert column.column_name == "id"
    assert column.data_type == "integer"
    assert column.ordinal_position == 1
    assert column.is_primary_key is False
    assert column.pk_position is None
    assert column.is_nullable is False
    assert column.has_default is False
    assert column.default_expression is None
    assert column.is_identity is False
    assert column.identity_generation is None
    assert column.is_generated is False
    assert column.generated_expression is None


def test_analyze_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _column_row(column_name="b", ordinal_position=2),
            _column_row(column_name="a", ordinal_position=1),
        ),
    )

    columns = service.analyze_table("lab", "t")

    # La extensión garantiza orden por ordinal_position; Python preserva
    # el orden de las filas tal cual llegan (sin reordenar).
    assert [column.column_name for column in columns] == ["b", "a"]


def test_analyze_simple_pk(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, rows=(_column_row(is_primary_key=True, pk_position=1),)
    )

    (column,) = service.analyze_table("lab", "t")

    assert column.is_primary_key is True
    assert column.pk_position == 1


def test_analyze_composite_pk_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _column_row(column_name="a", ordinal_position=1, is_primary_key=True, pk_position=1),
            _column_row(column_name="b", ordinal_position=2, is_primary_key=True, pk_position=2),
            _column_row(column_name="c", ordinal_position=3),
        ),
    )

    columns = service.analyze_table("lab", "t")

    assert [(c.column_name, c.pk_position) for c in columns] == [
        ("a", 1),
        ("b", 2),
        ("c", None),
    ]


def test_analyze_default_expression_null_and_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _column_row(column_name="a", has_default=False, default_expression=None),
            _column_row(
                column_name="b",
                has_default=True,
                default_expression="now()",
            ),
        ),
    )

    a, b = service.analyze_table("lab", "t")

    assert a.default_expression is None
    assert b.has_default is True
    assert b.default_expression == "now()"


def test_analyze_identity_always_and_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _column_row(
                column_name="a",
                has_default=True,
                is_identity=True,
                identity_generation="ALWAYS",
            ),
            _column_row(
                column_name="b",
                has_default=True,
                is_identity=True,
                identity_generation="BY DEFAULT",
            ),
        ),
    )

    a, b = service.analyze_table("lab", "t")

    assert a.is_identity is True
    assert a.identity_generation == "ALWAYS"
    assert b.identity_generation == "BY DEFAULT"


def test_analyze_generated_column(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _column_row(
                column_name="total",
                data_type="numeric(10,2)",
                is_generated=True,
                generated_expression="(precio * cantidad)",
            ),
        ),
    )

    (column,) = service.analyze_table("lab", "t")

    assert column.is_generated is True
    assert column.generated_expression == "(precio * cantidad)"
    assert column.data_type == "numeric(10,2)"


def test_analyze_special_names_are_parameterized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_column_row(),))
    schema = "Mi Esquema"
    table = "Catálogo Especial"

    service.analyze_table(schema, table)

    (query, params) = fake.queries[0]
    assert "crud_generator.analyze_table(%s, %s)" in query
    assert "%s" in query
    assert schema not in query
    assert table not in query
    assert params == (schema, table)


def test_analyze_empty_schema_fails_without_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_column_row(),))

    with pytest.raises(ValueError):
        service.analyze_table("   ", "t")
    assert fake.queries == []


def test_analyze_empty_table_fails_without_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_column_row(),))

    with pytest.raises(ValueError):
        service.analyze_table("lab", "  ")
    assert fake.queries == []


def test_analyze_non_str_identifiers_raise_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_column_row(),))

    with pytest.raises(TypeError):
        service.analyze_table(123, "t")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        service.analyze_table("lab", None)  # type: ignore[arg-type]
    assert fake.queries == []


def test_analyze_pg_42p01_propagates_with_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, error=StubPgError('relation "lab.fantasma" does not exist', "42P01")
    )

    with pytest.raises(UnexpectedDatabaseError) as exc_info:
        service.analyze_table("lab", "fantasma")

    assert exc_info.value.sqlstate == "42P01"


def test_analyze_idle_initial_status_rolls_back_after_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_column_row(),),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    service.analyze_table("lab", "t")

    assert fake.rollbacks == 1
    assert fake.commits == 0


def test_analyze_preexisting_transaction_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_column_row(),),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    service.analyze_table("lab", "t")

    assert fake.rollbacks == 0
    assert fake.commits == 0


def test_analyze_error_with_owned_transaction_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    with pytest.raises(UnexpectedDatabaseError):
        service.analyze_table("lab", "t")

    assert fake.rollbacks == 1


def test_analyze_non_postgres_bug_is_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_column_row(),),
        error=RuntimeError("bug interno"),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    with pytest.raises(RuntimeError):
        service.analyze_table("lab", "t")

    assert fake.rollbacks == 1


# ---------------------------------------------------------------------------
# generate_crud (CONTRACTS.md §3.2–3.3)
# ---------------------------------------------------------------------------


def _generation_row(
    operation: str | None = "INSERT",
    status: str = "success",
    schema_name: str = "lab",
    routine_name: str | None = "producto_insertar",
    identity_arguments: str | None = "IN p_1 integer",
    message: str = "ok",
    sqlstate: str | None = None,
) -> tuple[Any, ...]:
    return (
        operation,
        status,
        schema_name,
        routine_name,
        identity_arguments,
        message,
        sqlstate,
    )


def test_generate_sends_parameterized_query(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch, rows=(_generation_row(),), autocommit=True
    )

    service.generate_crud("lab", "producto", [CrudOperation.INSERT])

    (query, params) = fake.queries[0]
    assert "crud_generator.generate_crud(%s, %s, %s, %s)" in query
    assert "lab" not in query
    assert "producto" not in query
    assert params[0] == "lab"
    assert params[1] == "producto"


def test_generate_operations_sent_as_value_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(
            _generation_row("INSERT"),
            _generation_row("READ"),
        ),
    )

    service.generate_crud(
        "lab", "t", [CrudOperation.INSERT, CrudOperation.READ], do_replace=True
    )

    (_, params) = fake.queries[0]
    assert params[2] == ["INSERT", "READ"]
    assert params[3] is True


def test_generate_maps_success(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(monkeypatch, rows=(_generation_row(status="success"),))

    (result,) = service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert result.status is GenerationStatus.SUCCESS
    assert result.operation is CrudOperation.INSERT


def test_generate_maps_not_applicable(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _generation_row(
                operation="UPDATE",
                status="not_applicable",
                routine_name=None,
                identity_arguments=None,
            ),
        ),
    )

    (result,) = service.generate_crud("lab", "t", [CrudOperation.UPDATE])

    assert result.status is GenerationStatus.NOT_APPLICABLE
    assert result.routine_name is None


def test_generate_maps_procedure_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, rows=(_generation_row(status="procedure_conflict", sqlstate="42723"),)
    )

    (result,) = service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert result.status is GenerationStatus.PROCEDURE_CONFLICT
    assert result.sqlstate == "42723"


def test_generate_maps_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _generation_row(
                operation="DELETE",
                status="validation_error",
                routine_name=None,
                identity_arguments=None,
            ),
        ),
    )

    (result,) = service.generate_crud("lab", "t", [CrudOperation.DELETE])

    assert result.status is GenerationStatus.VALIDATION_ERROR


def test_generate_preserves_routine_name(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch, rows=(_generation_row(routine_name="producto_insertar"),)
    )

    (result,) = service.generate_crud("lab", "producto", [CrudOperation.INSERT])

    assert result.routine_name == "producto_insertar"


def test_generate_preserves_identity_arguments_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = "IN p_2 text, IN p_1 integer, IN p_3 numeric(10,2)"
    service, _ = make_service(
        monkeypatch, rows=(_generation_row(identity_arguments=identity),)
    )

    (result,) = service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert result.identity_arguments == identity


def test_generate_preserves_message_and_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(_generation_row(message="Ya existe lab.t_insertar.", sqlstate="42723"),),
    )

    (result,) = service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert result.message == "Ya existe lab.t_insertar."
    assert result.sqlstate == "42723"


def test_generate_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(
            _generation_row("UPDATE"),
            _generation_row("INSERT"),
        ),
    )

    first, second = service.generate_crud(
        "lab", "t", [CrudOperation.UPDATE, CrudOperation.INSERT]
    )

    assert first.operation is CrudOperation.UPDATE
    assert second.operation is CrudOperation.INSERT


def test_generate_empty_operations_fails_without_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_generation_row(),))

    with pytest.raises(ValueError):
        service.generate_crud("lab", "t", [])
    assert fake.queries == []


def test_generate_non_crudoperation_raises_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_generation_row(),))

    with pytest.raises(TypeError):
        service.generate_crud("lab", "t", ["INSERT"])  # type: ignore[list-item]
    assert fake.queries == []


def test_generate_duplicate_operations_raise_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_generation_row(),))

    with pytest.raises(ValueError):
        service.generate_crud(
            "lab", "t", [CrudOperation.INSERT, CrudOperation.INSERT]
        )
    assert fake.queries == []


def test_generate_non_bool_do_replace_raises_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(monkeypatch, rows=(_generation_row(),))

    with pytest.raises(TypeError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT], do_replace=1)  # type: ignore[arg-type]
    assert fake.queries == []


def test_generate_pg_42501_propagates_with_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, error=StubPgError("permission denied", "42501")
    )

    with pytest.raises(InsufficientPrivilegeError) as exc_info:
        service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert exc_info.value.sqlstate == "42501"


def test_generate_owned_success_commits_once(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_generation_row(),),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.commits == 1
    assert fake.rollbacks == 0


def test_generate_owned_error_rolls_back_once(monkeypatch: pytest.MonkeyPatch) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    with pytest.raises(UnexpectedDatabaseError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.rollbacks == 1
    assert fake.commits == 0


def test_generate_preexisting_success_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_generation_row(),),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_generate_preexisting_error_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        error=StubPgError("boom", "XX000"),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    with pytest.raises(UnexpectedDatabaseError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_generate_autocommit_true_does_no_manual_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch, rows=(_generation_row(),), autocommit=True
    )

    service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.commits == 0
    assert fake.rollbacks == 0


def test_generate_unexpected_python_error_is_not_a_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch,
        rows=(_generation_row(status="algo_nuevo"),),
    )

    with pytest.raises(ValueError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])


def test_generate_null_operation_is_contract_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = make_service(
        monkeypatch, rows=(_generation_row(operation=None),)
    )

    with pytest.raises(ValueError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])


def test_generate_null_operation_with_owned_transaction_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_generation_row(operation=None),),
        autocommit=False,
        transaction_status=TransactionStatus.IDLE,
    )

    with pytest.raises(ValueError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.rollbacks == 1
    assert fake.commits == 0


def test_generate_null_operation_with_preexisting_transaction_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, fake = make_service(
        monkeypatch,
        rows=(_generation_row(operation=None),),
        autocommit=False,
        transaction_status=TransactionStatus.INTRANS,
    )

    with pytest.raises(ValueError):
        service.generate_crud("lab", "t", [CrudOperation.INSERT])

    assert fake.commits == 0
    assert fake.rollbacks == 0
