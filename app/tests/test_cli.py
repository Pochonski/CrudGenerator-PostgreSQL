"""Pruebas de la CLI con I/O simulado (sin terminal ni PostgreSQL)."""

from __future__ import annotations

import pytest

from crud_generator.db.connection import (
    AuthenticationError,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    InsufficientPrivilegeError,
    ServerUnavailableError,
    UnexpectedDatabaseError,
)
from crud_generator.models import (
    CrudOperation,
    RoleInfo,
    SchemaInfo,
    TableInfo,
)
from crud_generator.ui.cli import Cli, parse_number_selection


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


def make_cli(io: ScriptedIO) -> Cli:
    return Cli(read=io.read, write=io.write, read_password=io.read_password)


def test_ask_connection_uses_defaults() -> None:
    io = ScriptedIO(["", "", "mydb", "tester"], ["secret"])
    config = make_cli(io).ask_connection()

    assert (config.host, config.port) == ("localhost", 5432)
    assert (config.database, config.user) == ("mydb", "tester")
    assert config.password == "secret"


def test_ask_connection_accepts_custom_host_port() -> None:
    io = ScriptedIO(["dbhost", "5433", "mydb", "tester"], ["pw"])
    config = make_cli(io).ask_connection()

    assert (config.host, config.port) == ("dbhost", 5433)


def test_ask_connection_retries_invalid_port() -> None:
    io = ScriptedIO(["", "abc", "0", "70000", "5432", "mydb", "tester"], ["pw"])
    config = make_cli(io).ask_connection()

    assert config.port == 5432
    assert sum("inválido" in out for out in io.outputs) == 3


def test_ask_connection_retries_empty_database_and_user() -> None:
    io = ScriptedIO(["", "", "", "mydb", "", "tester"], ["pw"])
    config = make_cli(io).ask_connection()

    assert (config.database, config.user) == ("mydb", "tester")


def test_password_is_never_printed() -> None:
    io = ScriptedIO(["", "", "mydb", "tester"], ["super_secret_pw"])
    make_cli(io).ask_connection()

    assert "super_secret_pw" not in "\n".join(io.outputs)


def test_select_schema_valid() -> None:
    io = ScriptedIO(["2"])
    schemas = [SchemaInfo("a"), SchemaInfo("b")]

    assert make_cli(io).select_schema(schemas) == SchemaInfo("b")


def test_select_schema_retries_invalid_index() -> None:
    io = ScriptedIO(["0", "x", "1"])
    schemas = [SchemaInfo("a"), SchemaInfo("b")]

    assert make_cli(io).select_schema(schemas) == SchemaInfo("a")
    assert sum("inválida" in out for out in io.outputs) == 2


def test_select_schema_empty_list_raises() -> None:
    with pytest.raises(ValueError):
        make_cli(ScriptedIO(["1"])).select_schema([])


def tables() -> list[TableInfo]:
    return [TableInfo("s", name) for name in ("t1", "t2", "t3")]


def test_select_single_table() -> None:
    cli = make_cli(ScriptedIO(["2"]))

    assert [t.name for t in cli.select_tables(tables())] == ["t2"]


def test_select_multiple_tables() -> None:
    cli = make_cli(ScriptedIO(["1,3"]))

    assert [t.name for t in cli.select_tables(tables())] == ["t1", "t3"]


def test_select_all_tables() -> None:
    cli = make_cli(ScriptedIO(["a"]))

    assert [t.name for t in cli.select_tables(tables())] == ["t1", "t2", "t3"]


def test_select_tables_dedupes_and_sorts() -> None:
    cli = make_cli(ScriptedIO(["3,1,1"]))

    assert [t.name for t in cli.select_tables(tables())] == ["t1", "t3"]


def test_select_tables_retries_invalid() -> None:
    io = ScriptedIO(["9", "x", "1"])
    cli = make_cli(io)

    assert [t.name for t in cli.select_tables(tables())] == ["t1"]
    assert sum("inválida" in out for out in io.outputs) == 2


def test_select_single_operation() -> None:
    assert make_cli(ScriptedIO(["3"])).select_operations() == [CrudOperation.UPDATE]


def test_select_multiple_operations() -> None:
    cli = make_cli(ScriptedIO(["1,2,4"]))

    assert cli.select_operations() == [
        CrudOperation.INSERT,
        CrudOperation.READ,
        CrudOperation.DELETE,
    ]


def test_select_all_operations() -> None:
    assert make_cli(ScriptedIO(["a"])).select_operations() == [
        CrudOperation.INSERT,
        CrudOperation.READ,
        CrudOperation.UPDATE,
        CrudOperation.DELETE,
    ]


def test_select_operations_rejects_empty_and_invalid() -> None:
    io = ScriptedIO(["", "7", "2"])
    cli = make_cli(io)

    assert cli.select_operations() == [CrudOperation.READ]
    assert sum("inválida" in out for out in io.outputs) == 2


def test_parse_number_selection_all_with_no_elements_raises() -> None:
    with pytest.raises(ValueError):
        parse_number_selection("a", 0)


def test_describe_error_maps_each_type() -> None:
    cli = make_cli(ScriptedIO([]))

    assert "Credenciales" in cli.describe_error(AuthenticationError("x"))
    assert "no encontrada" in cli.describe_error(DatabaseNotFoundError("x"))
    assert "conectar" in cli.describe_error(ServerUnavailableError("x"))
    assert "Permiso" in cli.describe_error(InsufficientPrivilegeError("x"))
    assert "inesperado" in cli.describe_error(UnexpectedDatabaseError("x"))
    assert "inesperado" in cli.describe_error(DatabaseConnectionError("x"))


def roles() -> list[RoleInfo]:
    return [
        RoleInfo("ana", can_login=True, is_superuser=False),
        RoleInfo("jefa", can_login=True, is_superuser=True),
        RoleInfo("grupo", can_login=False, is_superuser=False),
    ]


def test_select_single_role() -> None:
    assert [r.name for r in make_cli(ScriptedIO(["1"])).select_roles(roles())] == [
        "ana"
    ]


def test_select_multiple_roles() -> None:
    cli = make_cli(ScriptedIO(["1,3"]))

    assert [r.name for r in cli.select_roles(roles())] == ["ana", "grupo"]


def test_select_all_roles() -> None:
    assert [r.name for r in make_cli(ScriptedIO(["a"])).select_roles(roles())] == [
        "ana",
        "jefa",
        "grupo",
    ]


def test_select_roles_retries_invalid() -> None:
    io = ScriptedIO(["9", "x", "2"])
    cli = make_cli(io)

    assert [r.name for r in cli.select_roles(roles())] == ["jefa"]
    assert sum("inválida" in out for out in io.outputs) == 2


def test_select_roles_empty_list_raises() -> None:
    with pytest.raises(ValueError):
        make_cli(ScriptedIO(["1"])).select_roles([])


def test_select_roles_warns_superuser_keeps_it() -> None:
    io = ScriptedIO(["2"])
    cli = make_cli(io)

    assert [r.name for r in cli.select_roles(roles())] == ["jefa"]
    text = "\n".join(io.outputs)
    assert "superusuario" in text


def test_ask_replace_existing_accepts_s_n_default() -> None:
    assert make_cli(ScriptedIO(["s"])).ask_replace_existing() is True
    assert make_cli(ScriptedIO(["n"])).ask_replace_existing() is False
    assert make_cli(ScriptedIO([""])).ask_replace_existing() is False


def test_ask_replace_existing_retries_invalid() -> None:
    io = ScriptedIO(["x", "s"])
    cli = make_cli(io)

    assert cli.ask_replace_existing() is True
    assert sum("inválida" in out for out in io.outputs) == 1


def test_ask_operation_allowed_s_n() -> None:
    role = RoleInfo("ana", can_login=True, is_superuser=False)

    assert make_cli(ScriptedIO(["s"])).ask_operation_allowed(
        role, CrudOperation.READ
    ) is True
    assert make_cli(ScriptedIO(["n"])).ask_operation_allowed(
        role, CrudOperation.READ
    ) is False


def test_ask_operation_allowed_retries_empty_and_invalid() -> None:
    io = ScriptedIO(["", "x", "n"])
    cli = make_cli(io)
    role = RoleInfo("ana", can_login=True, is_superuser=False)

    assert cli.ask_operation_allowed(role, CrudOperation.DELETE) is False
    assert sum("inválida" in out for out in io.outputs) == 2


def test_show_table_metadata_lists_columns() -> None:
    from crud_generator.models import ColumnMetadata

    io = ScriptedIO([])
    cli = make_cli(io)
    cli.show_table_metadata(
        "lab",
        "producto",
        [
            ColumnMetadata(
                column_name="id",
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
        ],
    )

    text = "\n".join(io.outputs)
    assert "lab.producto" in text
    assert "id" in text and "integer" in text and "PK" in text


def test_show_generation_results_lists_statuses() -> None:
    from crud_generator.models import GenerationResult, GenerationStatus

    io = ScriptedIO([])
    cli = make_cli(io)
    cli.show_generation_results(
        "t",
        [
            GenerationResult(
                operation=CrudOperation.INSERT,
                status=GenerationStatus.SUCCESS,
                schema_name="lab",
                routine_name="t_insertar",
                identity_arguments="IN p_1 integer",
                message="ok",
                sqlstate=None,
            ),
            GenerationResult(
                operation=CrudOperation.UPDATE,
                status=GenerationStatus.NOT_APPLICABLE,
                schema_name="lab",
                routine_name=None,
                identity_arguments=None,
                message="sin PK",
                sqlstate=None,
            ),
        ],
    )

    text = "\n".join(io.outputs)
    assert "success" in text and "t_insertar" in text
    assert "not_applicable" in text


def test_show_privilege_changes_lists_roles() -> None:
    from crud_generator.privileges.service import PrivilegeChange

    io = ScriptedIO([])
    cli = make_cli(io)
    cli.show_privilege_changes(
        "t",
        [
            PrivilegeChange(
                role="ana",
                operation=CrudOperation.INSERT,
                allowed=True,
                schema_name="lab",
                table_name="t",
                routine_name="t_insertar",
            )
        ],
    )

    text = "\n".join(io.outputs)
    assert "ana" in text and "INSERT" in text and "habilitado" in text
