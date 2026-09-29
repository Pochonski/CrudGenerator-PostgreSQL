"""Orquestador de la aplicación (flujo de alto nivel, sin SQL ni CRUD).

Responsabilidades: pedir configuración a la UI, validar conexión, verificar
extensión, obtener esquema/tablas/operaciones y mostrar el resumen. Se detiene
de forma limpia cuando la generación real aún no es posible.
"""

from __future__ import annotations

from collections.abc import Callable

from crud_generator.config import DatabaseConfig
from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import CrudSelection, ExtensionState
from crud_generator.services.catalog_service import CatalogService
from crud_generator.services.extension_service import (
    DEFAULT_EXTENSION_NAME,
    ExtensionService,
)
from crud_generator.ui.cli import Cli

EXIT_OK = 0
EXIT_STOPPED = 1


class ApplicationFlow:
    """Flujo CLI → servicios. Las factorías permiten inyectar fakes en tests."""

    def __init__(
        self,
        cli: Cli,
        *,
        extension_name: str = DEFAULT_EXTENSION_NAME,
        make_manager: Callable[[DatabaseConfig], ConnectionManager] = ConnectionManager,
        make_catalog: Callable[[ConnectionManager], CatalogService] = CatalogService,
        make_extension: Callable[[ConnectionManager], ExtensionService] = ExtensionService,
    ) -> None:
        self._cli = cli
        self._extension_name = extension_name
        self._make_manager = make_manager
        self._make_catalog = make_catalog
        self._make_extension = make_extension

    def run(self) -> int:
        cli = self._cli
        try:
            config = cli.ask_connection()
            manager = self._make_manager(config)
            with manager:
                info = manager.validate()
                cli.show("Conexión exitosa")
                cli.show(f"Base de datos: {info.database}")
                cli.show(f"Usuario: {info.current_user}")
                return self._run_catalog(manager)
        except (EOFError, KeyboardInterrupt):
            # Cancelación limpia en cualquier entrada interactiva.
            cli.show("Operación cancelada por el usuario.")
            return EXIT_STOPPED
        except DatabaseConnectionError as exc:
            cli.show(cli.describe_error(exc))
            return EXIT_STOPPED

    def _run_catalog(self, manager: ConnectionManager) -> int:
        cli = self._cli
        cli.show("Verificando extensión...")
        try:
            status = self._make_extension(manager).check_extension(self._extension_name)
        except DatabaseConnectionError as exc:
            cli.show(cli.describe_error(exc))
            return EXIT_STOPPED
        if status.state is not ExtensionState.INSTALLED:
            cli.show(status.message or "Extensión no disponible.")
            if status.state is ExtensionState.ERROR and status.sqlstate:
                cli.show(f"SQLSTATE: {status.sqlstate}")
            return EXIT_STOPPED
        cli.show(status.message or "Extensión instalada.")

        try:
            catalog = self._make_catalog(manager)
            schemas = catalog.list_schemas()
        except DatabaseConnectionError as exc:
            cli.show(cli.describe_error(exc))
            return EXIT_STOPPED
        if not schemas:
            cli.show("No hay esquemas visibles para el usuario actual.")
            return EXIT_STOPPED
        schema = cli.select_schema(schemas)

        try:
            tables = catalog.list_tables(schema.name)
        except DatabaseConnectionError as exc:
            cli.show(cli.describe_error(exc))
            return EXIT_STOPPED
        if not tables:
            cli.show(f"El esquema '{schema.name}' no tiene tablas.")
            return EXIT_STOPPED
        chosen_tables = cli.select_tables(tables)

        operations = cli.select_operations()
        selection = CrudSelection(
            schema=schema.name,
            tables=tuple(table.name for table in chosen_tables),
            operations=tuple(operations),
        )
        cli.show_summary(selection)
        cli.show_generation_pending()
        return EXIT_OK
