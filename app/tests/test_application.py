"""Pruebas del orquestador con servicios falsos (sin PostgreSQL)."""

from __future__ import annotations

from typing import Any, Self

from crud_generator.application import EXIT_OK, EXIT_STOPPED, ApplicationFlow
from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionInfo, ServerUnavailableError
from crud_generator.models import (
    ExtensionState,
    ExtensionStatus,
    SchemaInfo,
    TableInfo,
)
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
    ) -> None:
        self.config = config
        self._error = error

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

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
    ) -> None:
        self._schemas = schemas if schemas is not None else [SchemaInfo("public")]
        self._tables = tables if tables is not None else [TableInfo("public", "t1")]

    def list_schemas(self) -> list[SchemaInfo]:
        return list(self._schemas)

    def list_tables(self, schema_name: str) -> list[TableInfo]:
        assert schema_name
        return list(self._tables)


class FakeExtension:
    def __init__(self, manager: FakeManager, *, status: ExtensionStatus) -> None:
        self._status = status

    def check_extension(self, extension_name: str) -> ExtensionStatus:
        assert extension_name
        return self._status


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
    schemas: list[SchemaInfo] | None = None,
    tables: list[TableInfo] | None = None,
) -> ApplicationFlow:
    cli = Cli(read=io.read, write=io.write, read_password=io.read_password)
    return ApplicationFlow(
        cli,
        make_manager=lambda config: FakeManager(config, error=manager_error),
        make_catalog=lambda manager: FakeCatalog(
            manager, schemas=schemas, tables=tables
        ),
        make_extension=lambda manager: FakeExtension(manager, status=status),
    )


def connection_inputs() -> list[str]:
    return ["", "", "mydb", "tester"]


def test_installed_continues_to_summary() -> None:
    io = ScriptedIO([*connection_inputs(), "1", "1,2", "1,2"], ["pw"])
    flow = make_flow(
        io,
        installed_status(),
        schemas=[SchemaInfo("public")],
        tables=[TableInfo("public", "t1"), TableInfo("public", "t2")],
    )

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "Conexión exitosa" in text
    assert "Resumen:" in text
    assert "Esquema: public" in text
    assert "- t1" in text
    assert "- INSERT" in text
    assert "API de la extensión" in text


def test_not_installed_stops_flow() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    status = ExtensionStatus(
        name="x", state=ExtensionState.NOT_INSTALLED, message="no instalada"
    )

    assert make_flow(io, status).run() == EXIT_STOPPED
    assert "no instalada" in "\n".join(io.outputs)
    assert io.remaining_inputs == 0


def test_not_accessible_stops_flow() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    status = ExtensionStatus(
        name="x", state=ExtensionState.NOT_ACCESSIBLE, message="no accesible"
    )

    assert make_flow(io, status).run() == EXIT_STOPPED
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

    assert make_flow(io, status).run() == EXIT_STOPPED
    text = "\n".join(io.outputs)
    assert "falló la consulta" in text
    assert "42501" in text
    assert io.remaining_inputs == 0


def test_connection_failure_shows_friendly_error() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    flow = make_flow(
        io,
        installed_status(),
        manager_error=ServerUnavailableError("adiós servidor"),
    )

    assert flow.run() == EXIT_STOPPED
    assert "No se pudo conectar" in "\n".join(io.outputs)


def test_empty_schemas_stops_cleanly() -> None:
    io = ScriptedIO(connection_inputs(), ["pw"])
    flow = make_flow(io, installed_status(), schemas=[])

    assert flow.run() == EXIT_STOPPED
    assert "esquemas" in "\n".join(io.outputs)


def test_empty_tables_stops_cleanly() -> None:
    io = ScriptedIO([*connection_inputs(), "1"], ["pw"])
    flow = make_flow(io, installed_status(), tables=[])

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
    flow = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)


def test_cancel_during_table_selection() -> None:
    io = FailAfterIO(
        [*connection_inputs(), "1", "1"],
        ["pw"],
        reads_before_fail=5,
        error=KeyboardInterrupt,
    )
    flow = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)


def test_cancel_during_operation_selection() -> None:
    io = FailAfterIO(
        [*connection_inputs(), "1", "1", "1,2"], ["pw"], reads_before_fail=6
    )
    flow = make_flow(io, installed_status())

    assert flow.run() == EXIT_STOPPED
    assert "cancelada" in "\n".join(io.outputs)
