"""Orquestador de la aplicación (flujo de alto nivel, sin SQL ni CRUD).

Responsabilidades: pedir configuración a la UI, validar conexión, verificar
extensión, obtener esquema/tablas/operaciones, ejecutar análisis y generación
reales vía la extensión, aplicar la matriz de privilegios elegida, verificar
permisos efectivos (SET ROLE + CALL real) y ejecutar operaciones con valores
del administrador. Se detiene de forma limpia ante errores o cancelación.
"""

from __future__ import annotations

from collections.abc import Callable

from crud_generator.config import DatabaseConfig
from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import (
    CrudOperation,
    CrudSelection,
    ExtensionState,
    GenerationResult,
    GenerationStatus,
    RoleInfo,
    VerifyOutcome,
)
from crud_generator.privileges.matrix import PrivilegeMatrix
from crud_generator.privileges.probe import (
    PermissionProbeService,
    PermissionProbeStatus,
)
from crud_generator.privileges.service import PrivilegeService
from crud_generator.services.catalog_service import CatalogService
from crud_generator.services.extension_service import (
    DEFAULT_EXTENSION_NAME,
    ExtensionService,
)
from crud_generator.services.procedure_service import (
    ProcedureService,
    split_identity_arguments,
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
        make_probe_service: Callable[
            [ConnectionManager], PermissionProbeService
        ] = PermissionProbeService,
        make_procedure_service: Callable[
            [ConnectionManager], ProcedureService
        ] = ProcedureService,
    ) -> None:
        self._cli = cli
        self._extension_name = extension_name
        self._admin_role = admin_role
        self._make_manager = make_manager
        self._make_catalog = make_catalog
        self._make_extension = make_extension
        self._make_privilege_service = make_privilege_service
        self._make_probe_service = make_probe_service
        self._make_procedure_service = make_procedure_service

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
        has_pk_by_table: dict[str, bool] = {}
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
            has_pk_by_table[table_name] = any(
                column.is_primary_key for column in columns
            )
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
        return self._run_privileges(
            manager, catalog, selection, results_by_table, has_pk_by_table
        )

    def _run_privileges(
        self,
        manager: ConnectionManager,
        catalog: CatalogService,
        selection: CrudSelection,
        results_by_table: dict[str, tuple[GenerationResult, ...]],
        has_pk_by_table: dict[str, bool],
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
            self._run_verify(manager, matrix, chosen_roles, table_name, results)
            self._run_execute(
                manager, table_name, results, has_pk_by_table.get(table_name, True)
            )
        return EXIT_OK

    def _run_verify(
        self,
        manager: ConnectionManager,
        matrix: PrivilegeMatrix,
        chosen_roles: list[RoleInfo],
        table_name: str,
        results: tuple[GenerationResult, ...],
    ) -> None:
        """Verifica la matriz ejecutando cada SUCCESS como cada rol (§11 paso 9).

        Usa argumentos NULL: un rol denegado recibe 42501 antes de ejecutar;
        cualquier otro desenlace prueba que NO fue denegado. Nunca aborta el
        flujo: las discrepancias se muestran, no se lanzan.
        """
        cli = self._cli
        verify = cli.ask_verify()
        if not verify:
            return
        probe = self._make_probe_service(manager)
        outcomes: list[VerifyOutcome] = []
        for role in chosen_roles:
            for result in results:
                if result.status is not GenerationStatus.SUCCESS:
                    continue
                if result.identity_arguments is None:
                    continue
                expected = matrix.is_allowed(role.name, result.operation)
                arg_count = len(
                    split_identity_arguments(result.identity_arguments)
                )
                try:
                    probe_result = probe.probe(
                        role.name, result, (None,) * arg_count
                    )
                except DatabaseConnectionError as exc:
                    sqlstate = exc.sqlstate or "desconocido"
                    if sqlstate == "42501":
                        denied, detail = True, "denegado (42501)."
                    else:
                        # Solo el SQLSTATE: el mensaje completo (DETAIL,
                        # CONTEXT) ensucia la pantalla y no aporta al veredicto.
                        denied = False
                        detail = f"no denegado (error {sqlstate})."
                    outcomes.append(
                        VerifyOutcome(
                            role=role.name,
                            operation=result.operation,
                            expected_allowed=expected,
                            matched=denied is not expected,
                            detail=detail,
                        )
                    )
                    continue
                except (TypeError, ValueError) as exc:
                    outcomes.append(
                        VerifyOutcome(
                            role=role.name,
                            operation=result.operation,
                            expected_allowed=expected,
                            matched=False,
                            detail=f"error de validación: {exc}.",
                        )
                    )
                    continue
                if probe_result.status is PermissionProbeStatus.DENIED:
                    denied, detail = True, "denegado (42501)."
                else:
                    denied, detail = False, "permitido y ejecutado."
                outcomes.append(
                    VerifyOutcome(
                        role=role.name,
                        operation=result.operation,
                        expected_allowed=expected,
                        matched=denied is not expected,
                        detail=detail,
                    )
                )
        cli.show_verify_results(outcomes)

    def _run_execute(
        self,
        manager: ConnectionManager,
        table_name: str,
        results: tuple[GenerationResult, ...],
        has_pk: bool,
    ) -> None:
        """Ejecuta una operación con valores del administrador (§11 paso 10).

        Los valores viajan como texto (vacío = NULL) y PostgreSQL los
        convierte; un literal inválido se muestra como error (p. ej. 22P02).
        READ sin PK trae el listado vía refcursor. Nunca aborta el flujo.
        """
        cli = self._cli
        execute = cli.ask_execute()
        if not execute:
            return
        try:
            chosen = cli.select_success_operation(results)
        except ValueError as exc:
            cli.show(f"Error de validación: {exc}")
            return
        if chosen.identity_arguments is None or chosen.routine_name is None:
            cli.show("Error de validación: resultado sin firma para ejecutar.")
            return
        labels = split_identity_arguments(chosen.identity_arguments)
        values = cli.ask_call_values(labels)
        runner = self._make_procedure_service(manager)
        fetch_cursor = (
            chosen.operation is CrudOperation.READ and not has_pk
        )
        try:
            call_result = runner.call_procedure(
                chosen.schema_name,
                chosen.routine_name,
                tuple(values),
                fetch_cursor=fetch_cursor,
            )
        except DatabaseConnectionError as exc:
            cli.show(cli.describe_error(exc))
            return
        except (TypeError, ValueError) as exc:
            cli.show(f"Error de validación: {exc}")
            return
        cli.show_call_result(call_result)
