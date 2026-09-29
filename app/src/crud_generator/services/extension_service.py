"""Detección de la extensión PostgreSQL (§4.2 del enunciado).

Responsabilidad única: verificar contra PostgreSQL si la extensión requerida
está instalada en la base actual y disponible para el usuario conectado.
No analiza tablas, no genera CRUD y no concede privilegios.
"""

from __future__ import annotations

from contextlib import suppress

from psycopg import errors as pg_errors
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import ExtensionState, ExtensionStatus

#: Nombre provisional: tomado del diagrama de ARCHITECTURE.md. El nombre
#: definitivo del `.control` lo confirma Joyce (REQUIERE COORDINACIÓN).
#: La lógica nunca lo hardcodea: `check_extension()` recibe el nombre.
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


class ExtensionService:
    """Verifica el estado de una extensión usando la conexión del manager.

    Nunca abre conexiones por su cuenta y respeta ownership de transacciones
    (igual que `CatalogService`): solo revierte la transacción que su lectura
    inició (``autocommit=False`` + estado inicial ``IDLE``).
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
