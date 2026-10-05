"""Servicio de catálogo PostgreSQL (ConnectionManager -> CatalogService).

Responsabilidad única: listar esquemas, tablas y roles para que el
administrador seleccione sobre qué objetos trabajar. No analiza columnas,
no detecta la extensión, no genera CRUD y no concede privilegios.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from typing import Any

from psycopg import errors as pg_errors
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import RoleInfo, SchemaInfo, TableInfo

#: Esquemas de sistema: política genérica, sin hardcodear esquemas del proyecto.
_LIST_SCHEMAS_QUERY = (
    "SELECT nspname FROM pg_catalog.pg_namespace "
    "WHERE nspname NOT IN ('pg_catalog', 'information_schema') "
    "AND NOT starts_with(nspname, 'pg_temp_') "
    "AND NOT starts_with(nspname, 'pg_toast') "
    "ORDER BY nspname"
)

#: Solo tablas reales ('r') y particionadas ('p'): sin vistas ni objetos internos.
_LIST_TABLES_QUERY = (
    "SELECT c.relname FROM pg_catalog.pg_class AS c "
    "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
    "WHERE n.nspname = %s AND c.relkind IN ('r', 'p') "
    "ORDER BY c.relname"
)

#: pg_roles es legible por cualquier rol; se excluyen por patrón genérico los
#: roles predefinidos del sistema (pg_*), nunca asignables a negocio, sin
#: hardcodear nombres concretos del proyecto.
_LIST_ROLES_QUERY = (
    "SELECT rolname, rolcanlogin, rolsuper "
    "FROM pg_catalog.pg_roles "
    "WHERE rolname NOT LIKE 'pg\\_%' "
    "ORDER BY rolname"
)


class CatalogService:
    """Lee el catálogo PostgreSQL usando la conexión del manager.

    Las lecturas reutilizan ``manager.connect()`` (igual que ``validate()``:
    autoconexión para operaciones de solo lectura) y nunca abren conexiones
    por su cuenta.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConnectionManager:
        return self._manager

    def _fetch_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[tuple[Any, ...]]:
        """Ejecuta una consulta de solo lectura y retorna todas las filas.

        Respeta ownership de transacciones: solo revierte la transacción que
        esta lectura inició (``autocommit=False`` + estado inicial ``IDLE``).
        Nunca toca una transacción preexistente del caller (``INTRANS``).
        """
        conn = self._manager.connect()
        owns_transaction = (
            not conn.autocommit
            and conn.info.transaction_status == TransactionStatus.IDLE
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            if owns_transaction:
                conn.rollback()
            return list(rows)
        except DatabaseConnectionError:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
        except Exception as exc:
            if owns_transaction:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise self._manager.translate_error(exc) from exc

    def list_schemas(self) -> list[SchemaInfo]:
        """Esquemas visibles para el administrador, ordenados por nombre."""
        rows = self._fetch_all(_LIST_SCHEMAS_QUERY)
        return [SchemaInfo(name=str(row[0])) for row in rows]

    def list_tables(self, schema_name: str) -> list[TableInfo]:
        """Tablas reales de un esquema, ordenadas. Vacío si no hay tablas."""
        if not schema_name.strip():
            raise ValueError("El nombre del esquema no puede estar vacío.")
        rows = self._fetch_all(_LIST_TABLES_QUERY, (schema_name,))
        return [TableInfo(schema=schema_name, name=str(row[0])) for row in rows]

    def list_roles(self) -> list[RoleInfo]:
        """Roles del servidor, ordenados, con atributos útiles para la UI."""
        rows = self._fetch_all(_LIST_ROLES_QUERY)
        return [
            RoleInfo(
                name=str(row[0]),
                can_login=bool(row[1]),
                is_superuser=bool(row[2]),
            )
            for row in rows
        ]
