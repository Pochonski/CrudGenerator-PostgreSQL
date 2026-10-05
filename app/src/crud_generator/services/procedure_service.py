"""Ejecución de procedures generados con valores del administrador (§11 pasos 9-10).

Responsabilidad única: ejecutar UN procedure generado vía ``CALL`` real con
valores provistos como texto (vacío = ``NULL``), dejando que PostgreSQL
convierta al tipo del parámetro (``unknown`` → integer/numeric/boolean/date/
jsonb/timestamptz; literal inválido → ``22P02`` como error mostrable, nunca
silenciado). No contiene lógica CRUD: no sabe qué hace cada procedure, solo
compone ``CALL esquema.rutina(... )`` con identificadores seguros (ADR-013).

Casos:
- INSERT/UPDATE/DELETE y READ con PK: ``CALL`` directo; si el procedure
  retorna fila (parámetros ``OUT``/``INOUT``) se captura con ``fetchone``.
- READ sin PK (``OUT resultado refcursor``, ADR-009): el ``CALL`` y el
  ``FETCH ALL`` ocurren en una transacción explícita (el cursor muere con
  ella); se retornan las filas leídas.

Transacciones: solo confirma/revierte la unidad que el propio método inició
(``IDLE`` + ``autocommit=False`` → transacción explícita con commit, porque
INSERT/UPDATE/DELETE deben persistir); nunca toca una transacción preexistente
del caller (``INTRANS``).
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from psycopg import errors as pg_errors
from psycopg import sql
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import ConnectionManager, DatabaseConnectionError
from crud_generator.models import CallResult


def split_identity_arguments(identity_arguments: str) -> tuple[str, ...]:
    """Parte la firma ``pg_get_function_identity_arguments`` por comas de nivel 0.

    Respeta paréntesis (``numeric(10,2)`` no se parte). Solo para contar y
    etiquetar parámetros en la UI; nunca para construir SQL.
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in identity_arguments:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth = max(depth - 1, 0)
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return tuple(parts)


def normalize_call_value(raw: str) -> str | None:
    """Texto del administrador → valor del CALL: vacío es NULL explícito."""
    if not isinstance(raw, str):
        raise TypeError(
            f"El valor debe ser str, no {type(raw).__name__}."
        )
    text = raw.strip()
    return None if text == "" else text


class ProcedureService:
    """Ejecuta procedures generados con valores de texto (solo lectura/escritura real).

    Nunca abre conexiones por su cuenta y respeta ownership de transacciones
    (igual que ``CatalogService``/``ExtensionService``).
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConnectionManager:
        return self._manager

    def call_procedure(
        self,
        schema_name: str,
        routine_name: str,
        values: tuple[str | None, ...],
        *,
        fetch_cursor: bool = False,
    ) -> CallResult:
        """Ejecuta ``CALL esquema.rutina(valores)`` y retorna el resultado.

        ``values`` viaja parametrizado (``%s``/``Placeholder``); ``None`` es
        NULL. Con ``fetch_cursor=True`` (READ sin PK) el ``CALL`` y el
        ``FETCH ALL`` comparten una transacción explícita y se retornan las
        filas; si no, se retorna la fila ``OUT``/``INOUT`` o ``None``.
        Los errores PostgreSQL se propagan mapeados con SQLSTATE
        (``42501``, ``P0002``, ``22P02``, etc.), nunca silenciados.
        """
        if not isinstance(schema_name, str) or not schema_name.strip():
            raise ValueError("El esquema no puede estar vacío.")
        if not isinstance(routine_name, str) or not routine_name.strip():
            raise ValueError("La rutina no puede estar vacía.")
        if not isinstance(values, tuple):
            raise TypeError("values debe ser tuple[str | None, ...].")
        for value in values:
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    "Cada valor debe ser str o None, "
                    f"no {type(value).__name__}."
                )
        conn = self._manager.connect()
        owns_unit = (
            not conn.autocommit
            and conn.info.transaction_status == TransactionStatus.IDLE
        )
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in values)
        call_stmt = sql.SQL("CALL {}.{}({})").format(
            sql.Identifier(schema_name),
            sql.Identifier(routine_name),
            placeholders,
        )
        try:
            if fetch_cursor:
                return self._call_and_fetch(
                    conn, call_stmt, values, owns_unit,
                    schema_name, routine_name,
                )
            with conn.cursor() as cursor:
                cursor.execute(call_stmt, tuple(values))
                output: tuple[Any, ...] | None = None
                if cursor.description is not None:
                    fetched = cursor.fetchone()
                    if fetched is not None:
                        output = tuple(fetched)
            if owns_unit:
                conn.commit()
            return CallResult(
                schema_name=schema_name,
                routine_name=routine_name,
                output=output,
                rows=(),
                is_table=False,
            )
        except DatabaseConnectionError:
            if owns_unit:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise
        except pg_errors.Error as exc:
            if owns_unit:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise self._manager.translate_error(exc) from exc
        except Exception:
            if owns_unit:
                with suppress(pg_errors.Error):
                    conn.rollback()
            raise

    def _call_and_fetch(
        self,
        conn: Any,
        call_stmt: Any,
        values: tuple[str | None, ...],
        owns_unit: bool,
        schema_name: str,
        routine_name: str,
    ) -> CallResult:
        """CALL + FETCH ALL del refcursor en una transacción explícita."""
        try:
            if owns_unit or conn.autocommit:
                with conn.transaction():
                    return self._fetch_inside(conn, call_stmt, values,
                                              schema_name, routine_name)
            return self._fetch_inside(conn, call_stmt, values,
                                      schema_name, routine_name)
        except DatabaseConnectionError:
            raise
        except pg_errors.Error as exc:
            raise self._manager.translate_error(exc) from exc

    def _fetch_inside(
        self,
        conn: Any,
        call_stmt: Any,
        values: tuple[str | None, ...],
        schema_name: str,
        routine_name: str,
    ) -> CallResult:
        with conn.cursor() as cursor:
            cursor.execute(call_stmt, tuple(values))
            if cursor.description is None:
                raise ValueError(
                    f"{schema_name}.{routine_name} no devolvió refcursor."
                )
            fetched = cursor.fetchone()
            if fetched is None or fetched[0] is None:
                raise ValueError(
                    f"{schema_name}.{routine_name} no devolvió refcursor."
                )
            cursor_name = str(fetched[0])
            cursor.execute(
                sql.SQL("FETCH ALL FROM {}").format(
                    sql.Identifier(cursor_name)
                )
            )
            rows = tuple(tuple(row) for row in cursor.fetchall())
        return CallResult(
            schema_name=schema_name,
            routine_name=routine_name,
            output=None,
            rows=rows,
            is_table=True,
        )
