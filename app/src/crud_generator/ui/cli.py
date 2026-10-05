"""CLI del generador CRUD (presentación y lectura de input, sin SQL).

Toda entrada/salida pasa por funciones inyectables para que la CLI sea
testeable sin un terminal real ni PostgreSQL.
"""

from __future__ import annotations

import getpass
from collections.abc import Callable, Sequence

from crud_generator.config import DatabaseConfig
from crud_generator.db.connection import (
    AuthenticationError,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    InsufficientPrivilegeError,
    ObjectNotFoundError,
    RowNotFoundError,
    ServerUnavailableError,
)
from crud_generator.models import (
    CallResult,
    ColumnMetadata,
    CrudOperation,
    CrudSelection,
    GenerationResult,
    GenerationStatus,
    RoleInfo,
    SchemaInfo,
    TableInfo,
    VerifyOutcome,
)
from crud_generator.privileges.service import PrivilegeChange

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5432

_ALL_TOKEN = "a"

CRUD_OPTIONS: tuple[CrudOperation, ...] = (
    CrudOperation.INSERT,
    CrudOperation.READ,
    CrudOperation.UPDATE,
    CrudOperation.DELETE,
)


class Cli:
    """Interfaz de línea de comandos con I/O inyectable."""

    def __init__(
        self,
        *,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
        read_password: Callable[[str], str] = getpass.getpass,
    ) -> None:
        self._read = read
        self._write = write
        self._read_password = read_password

    def show(self, message: str) -> None:
        self._write(message)

    def ask_connection(self) -> DatabaseConfig:
        """Pide los datos de conexión y retorna un `DatabaseConfig` válido."""
        self.show("CRUD Generator PostgreSQL")
        host = self._ask_with_default("Servidor", DEFAULT_HOST)
        port = self._ask_port()
        database = self._ask_required("Base de datos")
        user = self._ask_required("Usuario")
        # Nunca se imprime ni se registra la contraseña.
        password = self._read_password("Contraseña: ")
        return DatabaseConfig(
            host=host, port=port, database=database, user=user, password=password
        )

    def select_schema(self, schemas: Sequence[SchemaInfo]) -> SchemaInfo:
        """Selección numerada de esquema con reintentos ante índice inválido."""
        if not schemas:
            raise ValueError("No hay esquemas visibles para seleccionar.")
        self.show("Seleccionar esquema:")
        for index, schema in enumerate(schemas, start=1):
            self.show(f"{index}. {schema.name}")
        while True:
            raw = self._read("Esquema [número]: ").strip()
            try:
                choice = int(raw)
            except ValueError:
                self.show("Selección inválida: escriba el número del esquema.")
                continue
            if 1 <= choice <= len(schemas):
                return schemas[choice - 1]
            self.show("Selección inválida: número fuera de rango.")

    def select_tables(self, tables: Sequence[TableInfo]) -> list[TableInfo]:
        """Selección de tablas: `1`, `1,3,5` o `a` (todas). Sin duplicados."""
        names = [table.name for table in tables]
        self.show("Seleccionar tablas (ej. 1,3,5 o 'a' para todas):")
        for index, name in enumerate(names, start=1):
            self.show(f"{index}. {name}")
        while True:
            raw = self._read("Tablas: ").strip()
            try:
                chosen = parse_number_selection(raw, len(names))
            except ValueError as exc:
                self.show(f"Selección inválida: {exc}")
                continue
            return [tables[index - 1] for index in chosen]

    def select_operations(self) -> list[CrudOperation]:
        """Selección de operaciones CRUD: `1`, `1,2` o `a` (todas)."""
        self.show("Seleccionar operaciones (ej. 1,2 o 'a' para todas):")
        for index, operation in enumerate(CRUD_OPTIONS, start=1):
            self.show(f"{index}. {operation.value}")
        while True:
            raw = self._read("Operaciones: ").strip()
            try:
                chosen = parse_number_selection(raw, len(CRUD_OPTIONS))
            except ValueError as exc:
                self.show(f"Selección inválida: {exc}")
                continue
            return [CRUD_OPTIONS[index - 1] for index in chosen]

    def show_summary(self, selection: CrudSelection) -> None:
        self.show("Resumen:")
        self.show(f"Esquema: {selection.schema}")
        self.show("Tablas:")
        for name in selection.tables:
            self.show(f"- {name}")
        self.show("Operaciones:")
        for operation in selection.operations:
            self.show(f"- {operation.value}")

    def ask_replace_existing(self) -> bool:
        """Pregunta si se reemplazan procedures existentes (do_replace)."""
        self.show("¿Reemplazar procedures existentes? [s/n] (default: n):")
        while True:
            raw = self._read("Reemplazar: ").strip().lower()
            if raw in ("", "n", "no"):
                return False
            if raw in ("s", "si", "sí"):
                return True
            self.show("Respuesta inválida: escriba 's' o 'n'.")

    def show_table_metadata(
        self,
        schema_name: str,
        table_name: str,
        columns: Sequence[ColumnMetadata],
    ) -> None:
        """Muestra la metadata real devuelta por la extensión, sin inferir."""
        self.show(f"Estructura de {schema_name}.{table_name}:")
        for column in columns:
            details = [column.data_type]
            details.append("PK" if column.is_primary_key else "no PK")
            details.append(
                "nullable" if column.is_nullable else "NOT NULL"
            )
            if column.has_default and column.default_expression is not None:
                details.append(f"DEFAULT {column.default_expression}")
            elif column.has_default:
                details.append("DEFAULT")
            if column.is_identity:
                details.append(
                    f"identity {column.identity_generation or ''}".strip()
                )
            if column.is_generated:
                if column.generated_expression is not None:
                    details.append(
                        f"generated ({column.generated_expression})"
                    )
                else:
                    details.append("generated")
            self.show(f"- {column.column_name}: {', '.join(details)}")

    def show_generation_results(
        self,
        table_name: str,
        results: Sequence[GenerationResult],
    ) -> None:
        """Muestra cada fila de generate_crud sin ocultar ningún status."""
        self.show(f"Generación para {table_name}:")
        for result in results:
            operation_label = (
                result.operation.value
                if result.operation is not None
                else "(sin operación)"
            )
            self.show(
                f"- {operation_label}: {result.status.value}"
            )
            if result.routine_name is not None:
                self.show(f"  rutina: {result.routine_name}")
            self.show(f"  mensaje: {result.message}")
            if result.sqlstate is not None:
                self.show(f"  SQLSTATE: {result.sqlstate}")

    def select_roles(self, roles: Sequence[RoleInfo]) -> list[RoleInfo]:
        """Selección de roles: `1`, `1,3` o `a` (todos). Sin duplicados."""
        if not roles:
            raise ValueError("No hay roles visibles para seleccionar.")
        self.show("Seleccionar roles (ej. 1,3 o 'a' para todos):")
        for index, role in enumerate(roles, start=1):
            marker = " (superusuario)" if role.is_superuser else ""
            login = "" if role.can_login else " [NOLOGIN]"
            self.show(f"{index}. {role.name}{marker}{login}")
            if role.is_superuser:
                self.show(
                    "  Aviso: es superusuario; las comprobaciones normales de "
                    "privilegios no lo restringen efectivamente y otorgarle "
                    "EXECUTE es innecesario (ya puede hacerlo todo)."
                )
        while True:
            raw = self._read("Roles: ").strip()
            try:
                chosen = parse_number_selection(raw, len(roles))
            except ValueError as exc:
                self.show(f"Selección inválida: {exc}")
                continue
            return [roles[index - 1] for index in chosen]

    def ask_operation_allowed(
        self, role: RoleInfo, operation: CrudOperation
    ) -> bool:
        """Pregunta si un rol puede ejecutar una operación (s/n, sin default)."""
        while True:
            raw = self._read(
                f"Rol: {role.name}\nPermitir {operation.value}? [s/n]: "
            ).strip().lower()
            if raw in ("s", "si", "sí"):
                return True
            if raw in ("n", "no"):
                return False
            self.show("Respuesta inválida: escriba 's' o 'n'.")

    def show_privilege_changes(
        self, table_name: str, changes: Sequence[PrivilegeChange]
    ) -> None:
        """Muestra los cambios aplicados por tabla (solo rol × SUCCESS)."""
        self.show(f"Privilegios aplicados para {table_name}:")
        for change in changes:
            if change.allowed:
                state = "habilitado (privilegios directos aplicados)"
            else:
                state = "deshabilitado (privilegios directos revocados)"
            self.show(
                f"- {change.role} {change.operation.value}: {state} "
                f"({change.routine_name})"
            )

    def ask_verify(self) -> bool:
        """¿Verificar permisos ejecutando cada procedure como cada rol? (default: s)."""
        self.show(
            "Verificar permisos ejecutando cada procedure generado "
            "como cada rol (con 42501 = denegado) [s/n] (default: s):"
        )
        while True:
            raw = self._read("Verificar: ").strip().lower()
            if raw in ("", "s", "si", "sí"):
                return True
            if raw in ("n", "no"):
                return False
            self.show("Respuesta inválida: escriba 's' o 'n'.")

    def show_verify_results(self, outcomes: Sequence[VerifyOutcome]) -> None:
        """Muestra matriz vs realidad sin ocultar discrepancias."""
        self.show("Verificación de permisos (matriz vs PostgreSQL):")
        for outcome in outcomes:
            operation_label = (
                outcome.operation.value
                if outcome.operation is not None
                else "(sin operación)"
            )
            expected = "permitido" if outcome.expected_allowed else "denegado"
            mark = "OK" if outcome.matched else "DISCREPANCIA"
            self.show(
                f"- {mark} {outcome.role} {operation_label}: "
                f"matriz={expected}, {outcome.detail}"
            )

    def ask_execute(self) -> bool:
        """¿Ejecutar una operación con valores del administrador? (default: n)."""
        self.show(
            "Ejecutar una operación CRUD con valores (vacío = NULL) "
            "[s/n] (default: n):"
        )
        while True:
            raw = self._read("Ejecutar: ").strip().lower()
            if raw in ("", "n", "no"):
                return False
            if raw in ("s", "si", "sí"):
                return True
            self.show("Respuesta inválida: escriba 's' o 'n'.")

    def select_success_operation(
        self, results: Sequence[GenerationResult]
    ) -> GenerationResult:
        """Elige una operación SUCCESS generada para ejecutarla con valores."""
        options = [
            result
            for result in results
            if result.status is GenerationStatus.SUCCESS
            and result.operation is not None
        ]
        if not options:
            raise ValueError("No hay operaciones generadas para ejecutar.")
        self.show("Seleccionar operación a ejecutar:")
        for index, result in enumerate(options, start=1):
            assert result.operation is not None
            self.show(f"{index}. {result.operation.value} ({result.routine_name})")
        while True:
            raw = self._read("Operación [número]: ").strip()
            try:
                choice = int(raw)
            except ValueError:
                self.show("Selección inválida: escriba el número de la operación.")
                continue
            if 1 <= choice <= len(options):
                return options[choice - 1]
            self.show("Selección inválida: número fuera de rango.")

    def ask_call_values(self, labels: Sequence[str]) -> list[str | None]:
        """Pide un valor de texto por parámetro (vacío = NULL explícito).

        Los valores viajan como texto y PostgreSQL los convierte al tipo del
        parámetro; un literal inválido produce un error mostrable (p. ej.
        22P02), nunca un SQL inyectado (parametrización + identificadores).
        """
        from crud_generator.services.procedure_service import normalize_call_value

        values: list[str | None] = []
        for position, label in enumerate(labels, start=1):
            raw = self._read(f"Valor {position} — {label} (vacío = NULL): ")
            values.append(normalize_call_value(raw))
        return values

    def show_call_result(self, result: CallResult, max_rows: int = 20) -> None:
        """Muestra el resultado del CALL (fila OUT/INOUT o filas del refcursor)."""
        self.show(f"Resultado de {result.routine_name}:")
        if result.is_table:
            self.show(f"- filas devueltas: {len(result.rows)}")
            for row in result.rows[:max_rows]:
                self.show(f"  {row!r}")
            if len(result.rows) > max_rows:
                self.show(f"  ... ({len(result.rows) - max_rows} más)")
        elif result.output is not None:
            self.show(f"- valores de retorno: {result.output!r}")
        else:
            self.show("- ejecutado sin valores de retorno.")

    def describe_error(self, exc: DatabaseConnectionError) -> str:
        """Mensaje comprensible para el usuario, sin traceback."""
        if isinstance(exc, AuthenticationError):
            return f"Credenciales incorrectas: {exc}"
        if isinstance(exc, DatabaseNotFoundError):
            return f"Base de datos no encontrada: {exc}"
        if isinstance(exc, ServerUnavailableError):
            return f"No se pudo conectar al servidor: {exc}"
        if isinstance(exc, InsufficientPrivilegeError):
            return f"Permiso insuficiente: {exc}"
        if isinstance(exc, ObjectNotFoundError):
            return f"Objeto no encontrado: {exc}"
        if isinstance(exc, RowNotFoundError):
            return f"Fila inexistente: {exc}"
        return f"Error inesperado: {exc}"

    def _ask_with_default(self, label: str, default: str) -> str:
        raw = self._read(f"{label} [{default}]: ").strip()
        return raw or default

    def _ask_required(self, label: str) -> str:
        while True:
            raw = self._read(f"{label}: ").strip()
            if raw:
                return raw
            self.show(f"{label} no puede estar vacío.")

    def _ask_port(self) -> int:
        while True:
            raw = self._read(f"Puerto [{DEFAULT_PORT}]: ").strip() or str(DEFAULT_PORT)
            try:
                port = int(raw)
            except ValueError:
                self.show("Puerto inválido: debe ser un número.")
                continue
            if 1 <= port <= 65535:
                return port
            self.show("Puerto inválido: debe estar entre 1 y 65535.")


def parse_number_selection(raw: str, total: int) -> list[int]:
    """Convierte `1,3,5` o `a` en índices 1-based, ordenados y sin duplicados.

    Lanza `ValueError` con el motivo si la entrada no es válida o la
    selección queda vacía.
    """
    text = raw.strip().lower()
    if not text:
        raise ValueError("selección vacía.")
    if text == _ALL_TOKEN:
        if total <= 0:
            raise ValueError("no hay elementos para seleccionar.")
        return list(range(1, total + 1))
    chosen: list[int] = []
    for token in text.replace(",", " ").split():
        try:
            number = int(token)
        except ValueError:
            raise ValueError(f"'{token}' no es un número.") from None
        if not 1 <= number <= total:
            raise ValueError(f"'{number}' está fuera de rango (1-{total}).")
        if number not in chosen:
            chosen.append(number)
    if not chosen:
        raise ValueError("selección vacía.")
    return sorted(chosen)
