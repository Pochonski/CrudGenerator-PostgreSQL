"""Pruebas del orquestador con servicios falsos (sin PostgreSQL)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Self

from crud_generator.application import EXIT_OK, EXIT_STOPPED, ApplicationFlow
from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionInfo, ServerUnavailableError
from crud_generator.models import (
    ColumnMetadata,
    CrudOperation,
    ExtensionState,
    ExtensionStatus,
    GenerationResult,
    GenerationStatus,
    RoleInfo,
    SchemaInfo,
    TableInfo,
)
from crud_generator.privileges.matrix import PrivilegeMatrix
from crud_generator.privileges.service import PrivilegeChange
from crud_generator.ui.cli import Cli


class ScriptedIO:
    def __init__(self, inputs: list[str], passwords: list[str] | None = None) -> None:
        self._inputs = list(inputs)
        self._passwords = list(passwords or [])
        self.outputs: list[str] = []

    def read(self, prompt: str) -> str:
        self.outputs.append(prompt)
        return self._inputs.pop(0)

    def write(self, message: str) -> None:
        self.outputs.append(message)

    def read_password(self, prompt: str) -> str:
        self.outputs.append(prompt)
        return self._passwords.pop(0)

    @property
    def remaining_inputs(self) -> int:
        return len(self._inputs)


class FakeManager:
    def __init__(
        self,
        config: DatabaseConfig,
        *,
        error: Exception | None = None,
        assume_error: Exception | None = None,
    ) -> None:
        self.config = config
        self._error = error
        self._assume_error = assume_error
        self.assumed: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    @contextmanager
    def assume_role(self, role_name: str) -> Iterator[None]:
        self.assumed.append(role_name)
        if self._assume_error is not None:
            raise self._assume_error
        yield

    def validate(self) -> ConnectionInfo:
        if self._error is not None:
            raise self._error
        return ConnectionInfo(
            database=self.config.database,
            current_user=self.config.user,
            server_version="PostgreSQL 16.4",
        )


class FakeCatalog:
    def __init__(
        self,
        manager: FakeManager,
        *,
        schemas: list[SchemaInfo] | None = None,
        tables: list[TableInfo] | None = None,
        roles: list[RoleInfo] | None = None,
    ) -> None:
        self._schemas = schemas if schemas is not None else [SchemaInfo("public")]
        self._tables = tables if tables is not None else [TableInfo("public", "t1")]
        self._roles = (
            roles
            if roles is not None
            else [RoleInfo("ana", can_login=True, is_superuser=False)]
        )

    def list_schemas(self) -> list[SchemaInfo]:
        return list(self._schemas)

    def list_tables(self, schema_name: str) -> list[TableInfo]:
        assert schema_name
        return list(self._tables)

    def list_roles(self) -> list[RoleInfo]:
        return list(self._roles)


_SUFFIX = {
    CrudOperation.INSERT: "insertar",
    CrudOperation.READ: "consultar",
    CrudOperation.UPDATE: "actualizar",
    CrudOperation.DELETE: "eliminar",
}


def _column(name: str = "id") -> ColumnMetadata:
    return ColumnMetadata(
        column_name=name,
        data_type="integer",
        ordinal_position=1,
        is_primary_key=True,
        pk_position=1,
        is_nullable=False,
        has_default=False,
        default_expression=None,
        is_identity=False,
        identity_generation=None,
        is_generated=False,
        generated_expression=None,
    )


def _success(table: str, operation: CrudOperation) -> GenerationResult:
    return GenerationResult(
        operation=operation,
        status=GenerationStatus.SUCCESS,
        schema_name="public",
        routine_name=f"{table}_{_SUFFIX[operation]}",
        identity_arguments="IN p_1 integer",
        message="ok",
        sqlstate=None,
    )


def _not_applicable(table: str, operation: CrudOperation) -> GenerationResult:
    return GenerationResult(
        operation=operation,
        status=GenerationStatus.NOT_APPLICABLE,
        schema_name="public",
        routine_name=None,
        identity_arguments=None,
        message="sin PK",
        sqlstate=None,
    )


class FakeExtension:
    def __init__(
        self,
        manager: FakeManager,
        *,
        status: ExtensionStatus,
        analyze_error: Exception | None = None,
        generate_error: Exception | None = None,
        not_applicable: tuple[CrudOperation, ...] = (),
        conflict: tuple[CrudOperation, ...] = (),
        validation_error: tuple[CrudOperation, ...] = (),
    ) -> None:
        self._status = status
        self.analyze_calls: list[tuple[str, str]] = []
        self.generate_calls: list[
            tuple[str, str, tuple[CrudOperation, ...], bool]
        ] = []
        self._analyze_error = analyze_error
        self._generate_error = generate_error
        self._not_applicable = not_applicable
        self._conflict = conflict
        self._validation_error = validation_error

    def check_extension(self, extension_name: str) -> ExtensionStatus:
        assert extension_name
        return self._status

    def analyze_table(self, schema_name: str, table_name: str) -> tuple[Any, ...]:
        self.analyze_calls.append((schema_name, table_name))
        if self._analyze_error is not None:
            raise self._analyze_error
        return (_column("id"),)

    def generate_crud(
        self,
        schema_name: str,
        table_name: str,
        operations: Any,
        *,
        do_replace: bool = False,
    ) -> tuple[GenerationResult, ...]:
        ops = tuple(operations)
        self.generate_calls.append((schema_name, table_name, ops, do_replace))
        if self._generate_error is not None:
            raise self._generate_error
        rows: list[GenerationResult] = []
        for operation in ops:
            if operation in self._not_applicable:
                rows.append(_not_applicable(table_name, operation))
            elif operation in self._conflict:
                rows.append(
                    GenerationResult(
                        operation=operation,
                        status=GenerationStatus.PROCEDURE_CONFLICT,
                        schema_name=schema_name,
                        routine_name=f"{table_name}_{_SUFFIX[operation]}",
                        identity_arguments=None,
                        message="conflicto",
                        sqlstate="42723",
                    )
                )
            elif operation in self._validation_error:
                rows.append(
                    GenerationResult(
                        operation=operation,
                        status=GenerationStatus.VALIDATION_ERROR,
                        schema_name=schema_name,
                        routine_name=None,
                        identity_arguments=None,
                        message="inválido",
                        sqlstate=None,
                    )
                )
            else:
                rows.append(_success(table_name, operation))
        return tuple(rows)


class FakePrivilegeService:
    def __init__(self, manager: FakeManager) -> None:
        self.calls: list[
            tuple[str, str, PrivilegeMatrix, tuple[GenerationResult, ...]]
        ] = []

    def apply_matrix(
        self,
        schema_name: str,
        table_name: str,
        matrix: PrivilegeMatrix,
        results: Any,
    ) -> tuple[PrivilegeChange, ...]:
        results = tuple(results)
        self.calls.append((schema_name, table_name, matrix, results))
        return tuple(
            PrivilegeChange(
                role=role,
                operation=result.operation,
                allowed=matrix.is_allowed(role, result.operation),
                schema_name=schema_name,
                table_name=table_name,
                routine_name=result.routine_name or "",
            )
            for role in matrix.roles()
            for result in results
            if result.status is GenerationStatus.SUCCESS
        )


def installed_status() -> ExtensionStatus:
    return ExtensionStatus(
        name="crud_generator",
        state=ExtensionState.INSTALLED,
        version="1.0",
        schema="public",
        message="instalada",
    )


def make_flow(
    io: ScriptedIO,
    status: ExtensionStatus,
    *,
    manager_error: Exception | None = None,
    assume_error: Exception | None = None,
    schemas: list[SchemaInfo] | None = None,
    tables: list[TableInfo] | None = None,
    roles: list[RoleInfo] | None = None,
    extension: FakeExtension | None = None,
    privilege_service: FakePrivilegeService | None = None,
) -> tuple[ApplicationFlow, FakeExtension, FakePrivilegeService]:
    cli = Cli(read=io.read, write=io.write, read_password=io.read_password)
    fake_extension = (
        extension
        if extension is not None
        else FakeExtension(FakeManager, status=status)  # type: ignore[arg-type]
    )
    fake_privileges = (
        privilege_service
        if privilege_service is not None
        else FakePrivilegeService(FakeManager)  # type: ignore[arg-type]
    )
    managers: list[FakeManager] = []

    def _make_manager(config: DatabaseConfig) -> FakeManager:
        manager = FakeManager(
            config, error=manager_error, assume_error=assume_error
        )
        managers.append(manager)
        return manager

    flow = ApplicationFlow(
        cli,
        make_manager=_make_manager,
        make_catalog=lambda manager: FakeCatalog(
            manager, schemas=schemas, tables=tables, roles=roles
        ),
        make_extension=lambda manager: fake_extension,
        make_privilege_service=lambda manager: fake_privileges,
    )
    flow.managers = managers  # type: ignore[attr-defined]
    return flow, fake_extension, fake_privileges


def connection_inputs() -> list[str]:
    return ["", "", "mydb", "tester"]


def happy_inputs(
    *,
    tables: str = "1",
    operations: str = "1,2",
    replace: str = "n",
    roles: str = "1",
    answers: list[str] | None = None,
    extra_tables: int = 0,
) -> list[str]:
    if answers is None:
        answers = ["s", "s"]
    inputs = [*connection_inputs(), "1", tables, operations, replace]
    for _ in range(extra_tables):
        inputs += [roles, *answers]
    return [*inputs, roles, *answers]


def test_installed_runs_real_flow_to_privileges() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    flow, extension, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "Conexión exitosa" in text
    assert "Resumen:" in text
    assert "Estructura de public.t1" in text
    assert "t1_insertar" in text
    assert "Privilegios aplicados para t1" in text
    assert extension.analyze_calls == [("public", "t1")]
    assert len(extension.generate_calls) == 1
    assert len(privileges.calls) == 1


def test_analyze_called_once_per_table() -> None:
    io = ScriptedIO(
        happy_inputs(tables="1,2", answers=["s", "s"], extra_tables=1), ["pw"]
    )
    flow, extension, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1"), TableInfo("public", "t2")],
    )

    assert flow.run() == EXIT_OK
    assert extension.analyze_calls == [("public", "t1"), ("public", "t2")]


def test_generate_called_once_per_table_with_operations() -> None:
    io = ScriptedIO(
        happy_inputs(tables="1,2", answers=["s", "s"], extra_tables=1), ["pw"]
    )
    flow, extension, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1"), TableInfo("public", "t2")],
    )

    assert flow.run() == EXIT_OK
    assert extension.generate_calls == [
        (
            "public",
            "t1",
            (CrudOperation.INSERT, CrudOperation.READ),
            False,
        ),
        (
            "public",
            "t2",
            (CrudOperation.INSERT, CrudOperation.READ),
            False,
        ),
    ]


def test_do_replace_is_forwarded() -> None:
    io = ScriptedIO(happy_inputs(replace="s"), ["pw"])
    flow, extension, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    assert extension.generate_calls[0][3] is True


def test_metadata_and_success_results_shown() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    flow, _, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "id" in text and "integer" in text and "PK" in text
    assert "success" in text


def test_not_applicable_shown_and_not_asked() -> None:
    io = ScriptedIO(happy_inputs(operations="a", answers=["s"] * 6), ["pw"])
    extension = FakeExtension(
        FakeManager,  # type: ignore[arg-type]
        status=installed_status(),
        not_applicable=(CrudOperation.UPDATE, CrudOperation.DELETE),
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
        extension=extension,
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "not_applicable" in text
    assert "Permitir UPDATE" not in text
    assert "Permitir DELETE" not in text
    assert len(privileges.calls) == 1


def test_conflict_skips_privileges_for_that_table() -> None:
    io = ScriptedIO(
        happy_inputs(tables="1,2", answers=["s", "s"], extra_tables=1), ["pw"]
    )
    extension = FakeExtension(
        FakeManager,  # type: ignore[arg-type]
        status=installed_status(),
        conflict=(CrudOperation.INSERT,),
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1"), TableInfo("public", "t2")],
        extension=extension,
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "procedure_conflict" in text
    # Ninguna tabla recibe privilegios porque ambas tienen conflicto.
    assert privileges.calls == []
    assert "conflictos o errores" in text


def test_validation_error_skips_privileges() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    extension = FakeExtension(
        FakeManager,  # type: ignore[arg-type]
        status=installed_status(),
        validation_error=(CrudOperation.INSERT,),
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
        extension=extension,
    )

    assert flow.run() == EXIT_OK
    assert "validation_error" in "\n".join(io.outputs)
    assert privileges.calls == []


def test_real_roles_listed_and_denied_role_kept() -> None:
    io = ScriptedIO(happy_inputs(roles="1,2", answers=["s", "n", "s", "n"]), ["pw"])
    roles = [
        RoleInfo("vendedor", can_login=False, is_superuser=False),
        RoleInfo("jefa", can_login=True, is_superuser=False),
    ]
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
        roles=roles,
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "vendedor" in text and "jefa" in text
    _, _, matrix, _ = privileges.calls[0]
    assert matrix.roles() == ("jefa", "vendedor")
    assert matrix.is_allowed("vendedor", CrudOperation.INSERT) is True
    assert matrix.is_allowed("jefa", CrudOperation.INSERT) is False


def test_tables_do_not_share_results() -> None:
    io = ScriptedIO(
        happy_inputs(tables="1,2", answers=["s", "s"], extra_tables=1), ["pw"]
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1"), TableInfo("public", "t2")],
    )

    assert flow.run() == EXIT_OK
    assert len(privileges.calls) == 2
    first = {r.routine_name for r in privileges.calls[0][3]}
    second = {r.routine_name for r in privileges.calls[1][3]}
    assert first == {"t1_insertar", "t1_consultar"}
    assert second == {"t2_insertar", "t2_consultar"}


def test_privilege_service_receives_correct_scope() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    schema, table, _, results = privileges.calls[0]
    assert (schema, table) == ("public", "t1")
    assert [r.operation for r in results] == [
        CrudOperation.INSERT,
        CrudOperation.READ,
    ]


def test_generate_pg_error_stops_flow() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    extension = FakeExtension(
        FakeManager,  # type: ignore[arg-type]
        status=installed_status(),
        generate_error=ServerUnavailableError("adiós servidor"),
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
        extension=extension,
    )

    assert flow.run() == EXIT_STOPPED
    assert "No se pudo conectar" in "\n".join(io.outputs)
    assert privileges.calls == []


def test_contract_value_error_stops_flow() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    extension = FakeExtension(
        FakeManager,  # type: ignore[arg-type]
        status=installed_status(),
        analyze_error=ValueError("contrato roto"),
    )
    flow, _, privileges = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
        extension=extension,
    )

    assert flow.run() == EXIT_STOPPED
    assert "validación" in "\n".join(io.outputs)
    assert privileges.calls == []


def test_no_generation_pending_message() -> None:
    assert not hasattr(Cli, "show_generation_pending")
    io = ScriptedIO(happy_inputs(), ["pw"])
    flow, _, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    assert "cuando la API" not in "\n".join(io.outputs)


def test_not_installed_stops_flow() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    status = ExtensionStatus(
        name="x", state=ExtensionState.NOT_INSTALLED, message="no instalada"
    )

    flow, _, _ = make_flow(io, status)
    assert flow.run() == EXIT_STOPPED
    assert "no instalada" in "\n".join(io.outputs)
    assert io.remaining_inputs == 0


def test_not_accessible_stops_flow() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    status = ExtensionStatus(
        name="x", state=ExtensionState.NOT_ACCESSIBLE, message="no accesible"
    )

    flow, _, _ = make_flow(io, status)
    assert flow.run() == EXIT_STOPPED
    assert "no accesible" in "\n".join(io.outputs)
    assert io.remaining_inputs == 0


def test_error_status_stops_flow_and_shows_sqlstate() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    status = ExtensionStatus(
        name="x",
        state=ExtensionState.ERROR,
        message="falló la consulta",
        sqlstate="42501",
    )

    flow, _, _ = make_flow(io, status)
    assert flow.run() == EXIT_STOPPED
    text = "\n".join(io.outputs)
    assert "falló la consulta" in text
    assert "42501" in text
    assert io.remaining_inputs == 0


def test_connection_failure_shows_friendly_error() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    flow, _, _ = make_flow(
        io,
        installed_status(),
        manager_error=ServerUnavailableError("adiós servidor"),
    )

    assert flow.run() == EXIT_STOPPED
    assert "No se pudo conectar" in "\n".join(io.outputs)


def test_empty_schemas_stops_cleanly() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    flow, _, _ = make_flow(io, installed_status(), schemas=[])

    assert flow.run() == EXIT_STOPPED
    assert "esquemas" in "\n".join(io.outputs)


def test_empty_tables_stops_cleanly() -> None:
    io = ScriptedIO([*connection_inputs(), "1"], ["pw"])
    flow, _, _ = make_flow(io, installed_status(), tables=[])

    assert flow.run() == EXIT_STOPPED
    assert "no tiene tablas" in "\n".join(io.outputs)


def test_cancelled_input_stops_cleanly() -> None:
    def _boom(prompt: str) -> Any:
        raise EOFError

    io = ScriptedIO([], [])
    cli = Cli(read=_boom, write=io.write, read_password=io.read_password)
    flow = ApplicationFlow(
        cli,
        make_manager=lambda config: FakeManager(config),
        make_catalog=lambda manager: FakeCatalog(manager),
        make_extension=lambda manager: FakeExtension(
            manager, status=installed_status()
        ),
    )

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)


class FailAfterIO(ScriptedIO):
    """Entrega N lecturas y luego lanza el error indicado (EOF/KeyboardInterrupt)."""

    def __init__(
        self,
        inputs: list[str],
        passwords: list[str] | None = None,
        *,
        reads_before_fail: int,
        error: type[BaseException] = EOFError,
    ) -> None:
        super().__init__(inputs, passwords)
        self._remaining = reads_before_fail
        self._error = error

    def read(self, prompt: str) -> str:
        if self._remaining <= 0:
            raise self._error
        self._remaining -= 1
        return super().read(prompt)


def test_cancel_during_schema_selection() -> None:
    io = FailAfterIO([*connection_inputs(), "1"], ["pw"], reads_before_fail=4)
    flow, _, _ = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)


def test_cancel_during_table_selection() -> None:
    io = FailAfterIO(
        [*connection_inputs(), "1", "1"],
        ["pw"],
        reads_before_fail=5,
        error=KeyboardInterrupt,
    )
    flow, _, _ = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)


def test_flow_assumes_admin_role() -> None:
    io = ScriptedIO(happy_inputs(), ["pw"])
    flow, _, _ = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1")],
    )

    assert flow.run() == EXIT_OK
    assert flow.managers[0].assumed == ["crud_admin"]  # type: ignore[attr-defined]


def test_assume_role_failure_stops_flow() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    flow, _, _ = make_flow(
        io,
        installed_status(),
        assume_error=ServerUnavailableError("sin capacidad SET"),
    )

    assert flow.run() == EXIT_STOPPED
    assert "No se pudo conectar" in "\n".join(io.outputs)


def test_cancel_during_operation_selection() -> None:
    io = FailAfterIO(
        [*connection_inputs(), "1", "1", "1,2"], ["pw"], reads_before_fail=6
    )
    flow, _, _ = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)
