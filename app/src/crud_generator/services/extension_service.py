"""Detección de la extensión PostgreSQL (§4.2 del enunciado).

Responsabilidad única: verificar contra PostgreSQL si la extensión requerida
está instalada en la base actual y disponible para el usuario conectado, y
consumir su API pública real (``analyze_table`` / ``generate_crud`` según
``CONTRACTS.md`` §3). No concede privilegios ni genera SQL CRUD manualmente.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from typing import Any

from psycopg import errors as pg_errors
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import (
    ColumnMetadata,
    CrudOperation,
    ExtensionState,
    ExtensionStatus,
    GenerationResult,
    GenerationStatus,
)

#: Nombre confirmado de la extensión (Joyce, 01-10): ``crud_generator``
#: (``extension/crud_generator.control``, ``schema = crud_generator``).
#: Coincide con ``CONTRACTS.md`` §3 y
#: ``ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md``. La lógica nunca lo hardcodea
#: como valor de usuario: ``check_extension()`` recibe el nombre, y las
#: consultas a ``analyze_table``/``generate_crud`` usan el identificador fijo
#: del contrato (no un nombre proporcionado por el usuario).
DEFAULT_EXTENSION_NAME = "crud_generator"

#: `pg_extension` confirma instalación en la base actual (extname es único
#: por base); `has_schema_privilege(..., 'USAGE')` con OID evita identificadores
#: dinámicos y dice si el usuario conectado puede usar sus objetos.
_CHECK_EXTENSION_QUERY = (
    "SELECT e.extname, e.extversion, n.nspname, "
    "has_schema_privilege(n.oid, 'USAGE') AS has_usage "
    "FROM pg_catalog.pg_extension AS e "
    "JOIN pg_catalog.pg_namespace AS n ON n.oid = e.extnamespace "
    "WHERE e.extname = %s"
)

#: API pública real (CONTRACTS.md §3.1). `crud_generator` es el identificador
#: fijo de la extensión, no un nombre de usuario: nunca se interpola.
_ANALYZE_TABLE_QUERY = "SELECT * FROM crud_generator.analyze_table(%s, %s)"

#: API pública real (CONTRACTS.md §3.2). `operations` es `text[]`: en
#: psycopg3 se pasa como lista Python de strings.
_GENERATE_CRUD_QUERY = "SELECT * FROM crud_generator.generate_crud(%s, %s, %s, %s)"


def _validate_identifier(value: str, *, kind: str) -> str:
    """Valida ``schema_name``/``table_name`` y retorna el valor intacto."""
    if not isinstance(value, str):
        raise TypeError(f"El {kind} debe ser str, no {type(value).__name__}.")
    if not value.strip():
        raise ValueError(f"El {kind} no puede estar vacío.")
    return value


def _validate_operations(operations: Iterable[CrudOperation]) -> list[CrudOperation]:
    """Materializa y valida ``operations`` preservando el orden solicitado."""
    if isinstance(operations, (str, bytes)):
        raise TypeError(
            "operations debe ser un iterable de CrudOperation, no str/bytes."
        )
    try:
        items = list(operations)
    except TypeError as exc:
        raise TypeError(
            "operations debe ser un iterable de CrudOperation."
        ) from exc
    if not items:
        raise ValueError("Debe indicar al menos una operación.")
    for item in items:
        if not isinstance(item, CrudOperation):
            raise TypeError(
                "Cada operación debe ser CrudOperation, "
                f"no {type(item).__name__} (sin conversión silenciosa)."
            )
    if len(set(items)) != len(items):
        raise ValueError("Operaciones duplicadas: cada operación debe aparecer una vez.")
    return items


def _map_column_row(row: tuple[Any, ...]) -> ColumnMetadata:
    """Mapea una fila de `analyze_table` a `ColumnMetadata` (12 columnas)."""
    if len(row) != 12:
        raise ValueError(
            f"Contrato analyze_table violado: se esperaban 12 columnas, llegaron {len(row)}."
        )
    pk_position = row[4]
    return ColumnMetadata(
        column_name=str(row[0]),
        data_type=str(row[1]),
        ordinal_position=int(row[2]),
        is_primary_key=bool(row[3]),
        pk_position=None if pk_position is None else int(pk_position),
        is_nullable=bool(row[5]),
        has_default=bool(row[6]),
        default_expression=None if row[7] is None else str(row[7]),
        is_identity=bool(row[8]),
        identity_generation=None if row[9] is None else str(row[9]),
        is_generated=bool(row[10]),
        generated_expression=None if row[11] is None else str(row[11]),
    )


def _map_generation_row(row: tuple[Any, ...]) -> GenerationResult:
    """Mapea una fila de `generate_crud` a `GenerationResult` (7 columnas)."""
    if len(row) != 7:
        raise ValueError(
            f"Contrato generate_crud violado: se esperaban 7 columnas, llegaron {len(row)}."
        )
    raw_operation = row[0]
    if raw_operation is None:
        raise ValueError(
            "Contrato generate_crud violado: operation NULL "
            "(el servicio nunca envía operations NULL/vacío/None)."
        )
    try:
        operation = CrudOperation(str(raw_operation))
    except ValueError as exc:
        raise ValueError(
            f"Contrato generate_crud violado: operation desconocida {raw_operation!r}."
        ) from exc
    try:
        status = GenerationStatus(str(row[1]))
    except ValueError as exc:
        raise ValueError(
            f"Contrato generate_crud violado: status desconocido {row[1]!r}."
        ) from exc
    if row[2] is None:
        raise ValueError("Contrato generate_crud violado: schema_name NULL.")
    if row[5] is None:
        raise ValueError("Contrato generate_crud violado: message NULL.")
    return GenerationResult(
        operation=operation,
        status=status,
        schema_name=str(row[2]),
        routine_name=None if row[3] is None else str(row[3]),
        identity_arguments=None if row[4] is None else str(row[4]),
        message=str(row[5]),
        sqlstate=None if row[6] is None else str(row[6]),
    )


class ExtensionService:
    """Verifica la extensión y consume su API pública real.

    Nunca abre conexiones por su cuenta y respeta ownership de transacciones:
    solo confirma/revierte la transacción que el propio método inició
    (``autocommit=False`` + estado inicial ``IDLE``); nunca toca una
    transacción preexistente del caller (``INTRANS``).
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConnectionManager:
        return self._manager

    def check_extension(self, extension_name: str) -> ExtensionStatus:
        """Retorna el estado de una extensión en la base de datos actual.

        Un fallo de conexión lanza `DatabaseConnectionError`; un fallo de la
        consulta retorna `ExtensionStatus` con estado `ERROR` (nunca se
        convierte en `NOT_INSTALLED`).
        """
        if not extension_name.strip():
            raise ValueError("El nombre de la extensión no puede estar vacío.")
        conn = self._manager.connect()
        owns_transaction = (
            not conn.autocommit
            and conn.info.transaction_status == TransactionStatus.IDLE
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(_CHECK_EXTENSION_QUERY, (extension_name,))
                row = cursor.fetchone()
            if owns_transaction:
                conn.rollback()
        except DatabaseConnectionError:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
        except pg_errors.Error as exc:
            # Solo fallos PostgreSQL se convierten en estado ERROR; un error
            # ajeno a psycopg sería un bug y debe propagarse sin ocultarse.
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            mapped = self._manager.translate_error(exc)
            return ExtensionStatus(
                name=extension_name,
                state=ExtensionState.ERROR,
                message=str(mapped),
                sqlstate=mapped.sqlstate,
            )
        if row is None:
            return ExtensionStatus(
                name=extension_name,
                state=ExtensionState.NOT_INSTALLED,
                message=(
                    f"La extensión '{extension_name}' no está instalada "
                    "en la base de datos actual."
                ),
            )
        _name, version, schema, has_usage = (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            bool(row[3]),
        )
        if has_usage:
            return ExtensionStatus(
                name=extension_name,
                state=ExtensionState.INSTALLED,
                version=version,
                schema=schema,
                message=(
                    f"La extensión '{extension_name}' está instalada "
                    f"(versión {version}, esquema {schema}) y el usuario actual "
                    "tiene permiso USAGE sobre su esquema. "
                    "La verificación de EXECUTE sobre la API pública está pendiente."
                ),
            )
        return ExtensionStatus(
            name=extension_name,
            state=ExtensionState.NOT_ACCESSIBLE,
            version=version,
            schema=schema,
            message=(
                f"La extensión '{extension_name}' está instalada "
                f"(esquema {schema}) pero el usuario actual no tiene "
                "permiso USAGE sobre ese esquema."
            ),
        )

    def analyze_table(
        self, schema_name: str, table_name: str
    ) -> tuple[ColumnMetadata, ...]:
        """Analiza una tabla vía ``crud_generator.analyze_table`` (solo lectura).

        Retorna una tupla de :class:`ColumnMetadata` en el orden de
        ``ordinal_position`` que garantiza la extensión. Los errores reales de
        PostgreSQL (tabla inexistente ``42P01``, permiso ``42501``, etc.) se
        propagan como el error Python mapeado por
        ``ConnectionManager.translate_error()`` preservando ``SQLSTATE``;
        nunca se convierten en filas ficticias.
        """
        schema_name = _validate_identifier(schema_name, kind="schema_name")
        table_name = _validate_identifier(table_name, kind="table_name")
        conn = self._manager.connect()
        owns_transaction = (
            not conn.autocommit
            and conn.info.transaction_status == TransactionStatus.IDLE
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(_ANALYZE_TABLE_QUERY, (schema_name, table_name))
                rows = cursor.fetchall()
            columns = tuple(_map_column_row(tuple(row)) for row in rows)
            if owns_transaction:
                conn.rollback()
            return columns
        except DatabaseConnectionError:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
        except pg_errors.Error as exc:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise self._manager.translate_error(exc) from exc
        except Exception:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise

    def generate_crud(
        self,
        schema_name: str,
        table_name: str,
        operations: Iterable[CrudOperation],
        *,
        do_replace: bool = False,
    ) -> tuple[GenerationResult, ...]:
        """Genera procedures CRUD vía ``crud_generator.generate_crud`` (DDL real).

        ``operations`` se envía a PostgreSQL como lista de strings
        (``[op.value, ...]``) preservando el orden solicitado. Los errores
        reales de PostgreSQL (``42P01``, ``42501``, etc.) se propagan como el
        error Python mapeado preservando ``SQLSTATE``; nunca se convierten en
        filas de :class:`GenerationResult`.
        """
        schema_name = _validate_identifier(schema_name, kind="schema_name")
        table_name = _validate_identifier(table_name, kind="table_name")
        validated = _validate_operations(operations)
        if not isinstance(do_replace, bool):
            raise TypeError(
                f"do_replace debe ser bool, no {type(do_replace).__name__}."
            )
        payload = [operation.value for operation in validated]
        conn = self._manager.connect()
        owns_transaction = (
            not conn.autocommit
            and conn.info.transaction_status == TransactionStatus.IDLE
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    _GENERATE_CRUD_QUERY,
                    (schema_name, table_name, payload, do_replace),
                )
                rows = cursor.fetchall()
            results = tuple(_map_generation_row(tuple(row)) for row in rows)
            if owns_transaction:
                conn.commit()
            return results
        except DatabaseConnectionError:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
        except pg_errors.Error as exc:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise self._manager.translate_error(exc) from exc
        except Exception:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
