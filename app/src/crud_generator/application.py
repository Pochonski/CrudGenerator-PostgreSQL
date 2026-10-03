"""Orquestador de la aplicación (flujo de alto nivel, sin SQL ni CRUD).

Responsabilidades: pedir configuración a la UI, validar conexión, verificar
extensión, obtener esquema/tablas/operaciones, ejecutar análisis y generación
reales vía la extensión, y aplicar la matriz de privilegios elegida. Se
detiene de forma limpia ante errores o cancelación del usuario.
"""

from __future__ import annotations

from collections.abc import Callable

from crud_generator.config import DatabaseConfig
from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import (
    CrudSelection,
    ExtensionState,
    GenerationResult,
    GenerationStatus,
)
from crud_generator.privileges.matrix import PrivilegeMatrix
from crud_generator.privileges.service import PrivilegeService
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
        admin_role: str = "crud_admin",
        make_manager: Callable[[DatabaseConfig], ConnectionManager] = ConnectionManager,
        make_catalog: Callable[[ConnectionManager], CatalogService] = CatalogService,
        make_extension: Callable[[ConnectionManager], ExtensionService] = ExtensionService,
        make_privilege_service: Callable[
            [ConnectionManager], PrivilegeService
        ] = PrivilegeService,
    ) -> None:
        self._cli = cli
        self._extension_name = extension_name
        self._admin_role = admin_role
        self._make_manager = make_manager
        self._make_catalog = make_catalog
        self._make_extension = make_extension
        self._make_privilege_service = make_privilege_service

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
                # El owner confirmado de los procedures generados es crud_admin
                # (ADR-011): se asume ese rol para que la extensión cree los
                # objetos con el owner correcto aunque se entre como postgres.
                with manager.assume_role(self._admin_role):
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
            extension = self._make_extension(manager)
            status = extension.check_extension(self._extension_name)
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
        return self._run_generation(manager, extension, catalog, selection)

    def _run_generation(
        self,
        manager: ConnectionManager,
        extension: ExtensionService,
        catalog: CatalogService,
        selection: CrudSelection,
    ) -> int:
        cli = self._cli
        do_replace = cli.ask_replace_existing()
        results_by_table: dict[str, tuple[GenerationResult, ...]] = {}
        for table_name in selection.tables:
            try:
                columns = extension.analyze_table(selection.schema, table_name)
            except DatabaseConnectionError as exc:
                cli.show(cli.describe_error(exc))
                return EXIT_STOPPED
            except (TypeError, ValueError) as exc:
                cli.show(f"Error de validación: {exc}")
                return EXIT_STOPPED
            cli.show_table_metadata(selection.schema, table_name, columns)
            try:
                results = extension.generate_crud(
                    selection.schema,
                    table_name,
                    selection.operations,
                    do_replace=do_replace,
                )
            except DatabaseConnectionError as exc:
                cli.show(cli.describe_error(exc))
                return EXIT_STOPPED
            except (TypeError, ValueError) as exc:
                cli.show(f"Error de validación: {exc}")
                return EXIT_STOPPED
            results_by_table[table_name] = results
            cli.show_generation_results(table_name, results)
        return self._run_privileges(manager, catalog, selection, results_by_table)

    def _run_privileges(
        self,
        manager: ConnectionManager,
        catalog: CatalogService,
        selection: CrudSelection,
        results_by_table: dict[str, tuple[GenerationResult, ...]],
    ) -> int:
        cli = self._cli
        privilege_service = self._make_privilege_service(manager)
        for table_name, results in results_by_table.items():
            if any(
                result.status
                in (
                    GenerationStatus.PROCEDURE_CONFLICT,
                    GenerationStatus.VALIDATION_ERROR,
                )
                for result in results
            ):
                cli.show(
                    f"La tabla '{table_name}' tiene conflictos o errores de "
                    "generación: resuélvalos antes de configurar privilegios."
                )
                continue
            try:
                roles = catalog.list_roles()
            except DatabaseConnectionError as exc:
                cli.show(cli.describe_error(exc))
                return EXIT_STOPPED
            if not roles:
                cli.show("No hay roles visibles para configurar privilegios.")
                return EXIT_STOPPED
            chosen_roles = cli.select_roles(roles)
            matrix = PrivilegeMatrix()
            for role in chosen_roles:
                matrix.add_role(role.name)
            for result in results:
                if result.status is not GenerationStatus.SUCCESS:
                    continue
                for role in chosen_roles:
                    if cli.ask_operation_allowed(role, result.operation):
                        matrix.enable(role.name, result.operation)
                    else:
                        matrix.disable(role.name, result.operation)
            try:
                changes = privilege_service.apply_matrix(
                    selection.schema, table_name, matrix, results
                )
            except DatabaseConnectionError as exc:
                cli.show(cli.describe_error(exc))
                return EXIT_STOPPED
            except (TypeError, ValueError) as exc:
                cli.show(f"Error de validación: {exc}")
                return EXIT_STOPPED
            cli.show_privilege_changes(table_name, changes)
        return EXIT_OK
