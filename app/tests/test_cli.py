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
from crud_generator.models import CrudOperation, SchemaInfo, TableInfo
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
