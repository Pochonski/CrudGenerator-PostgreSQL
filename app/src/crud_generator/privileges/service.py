"""Aplicación real de matrices de privilegios (PrivilegeMatrix → GRANT/REVOKE).

Responsabilidad única: reconciliar sobre UNA tabla la intención almacenada en
``PrivilegeMatrix`` con privilegios PostgreSQL reales sobre los procedures
generados por la extensión y la tabla base (modelo de dos llaves bajo
``SECURITY INVOKER``, ver ``SECURITY_MEMORY.md`` y
``ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md`` §1.5):

- llave 1: ``EXECUTE`` sobre cada procedure generado;
- llave 2: permiso correspondiente sobre la tabla
  (``INSERT``/``SELECT``/``UPDATE``/``DELETE``);
- más ``USAGE ON SCHEMA`` (una vez por rol con al menos una operación
  habilitada) para poder calificar los objetos.

Limitación documentada: este servicio administra ``GRANT``/``REVOKE``
directos. Un ``REVOKE`` directo no garantiza acceso efectivo denegado si el
rol conserva el privilegio por otra vía (membresía en otro rol, ``PUBLIC``,
superusuario u owner). La validación efectiva real (``SET ROLE`` + ``CALL``)
queda pendiente (CR-ARMANDO-003) y no se implementa aquí.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from psycopg import errors as pg_errors
from psycopg import sql
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import ConnectionManager
from crud_generator.models import CrudOperation, GenerationResult, GenerationStatus
from crud_generator.privileges.matrix import PrivilegeMatrix

#: Sufijos oficiales de naming (ADR-007): <tabla>_<sufijo>.
_ROUTINE_SUFFIX: dict[CrudOperation, str] = {
    CrudOperation.INSERT: "insertar",
    CrudOperation.READ: "consultar",
    CrudOperation.UPDATE: "actualizar",
    CrudOperation.DELETE: "eliminar",
}

#: Mapeo fijo operación → keyword de privilegio de tabla (dos llaves INVOKER).
#: Nunca se construye desde strings de usuario.
_TABLE_PRIVILEGE: dict[CrudOperation, str] = {
    CrudOperation.INSERT: "INSERT",
    CrudOperation.READ: "SELECT",
    CrudOperation.UPDATE: "UPDATE",
    CrudOperation.DELETE: "DELETE",
}

#: Resolución del procedure REAL en pg_catalog. El proyecto no soporta
#: overloads: se exige exactamente una fila.
_FIND_PROCEDURE_QUERY = (
    "SELECT p.oid, pg_catalog.pg_get_function_identity_arguments(p.oid) "
    "AS identity_arguments "
    "FROM pg_catalog.pg_proc AS p "
    "JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace "
    "WHERE n.nspname = %s AND p.proname = %s AND p.prokind = 'p' "
    "ORDER BY p.oid"
)


@dataclass(frozen=True)
class PrivilegeChange:
    """Una celda rol × operación SUCCESS reconciliada contra PostgreSQL.

    Solo se genera para ``SUCCESS`` (reconciliación de un procedure generado).
    La limpieza defensiva de tabla para ``NOT_APPLICABLE`` denegada no produce
    ``PrivilegeChange``: no hay rutina aplicable que describir.
    """

    role: str
    operation: CrudOperation
    allowed: bool
    schema_name: str
    table_name: str
    routine_name: str


def _validate_name(value: str, *, kind: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"El {kind} debe ser str, no {type(value).__name__}.")
    if not value.strip():
        raise ValueError(f"El {kind} no puede estar vacío.")
    return value


def _expected_routine(table_name: str, operation: CrudOperation) -> str:
    return f"{table_name}_{_ROUTINE_SUFFIX[operation]}"


class PrivilegeService:
    """Aplica una ``PrivilegeMatrix`` con ``GRANT``/``REVOKE`` reales.

    Nunca abre conexiones por su cuenta: usa ``manager.connect()``. Toda la
    aplicación es atómica cuando el servicio es dueño de la unidad de trabajo
    (estado inicial ``IDLE`` → una transacción explícita vía
    ``conn.transaction()``, válida con ``autocommit=True`` o ``False``). Con
    transacción preexistente (``INTRANS``) ejecuta dentro de ella sin
    ``commit``/``rollback`` propios.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConnectionManager:
        return self._manager

    def apply_matrix(
        self,
        schema_name: str,
        table_name: str,
        matrix: PrivilegeMatrix,
        generation_results: Iterable[GenerationResult],
    ) -> tuple[PrivilegeChange, ...]:
        """Reconcilia una matriz sobre UNA tabla y sus procedures generados.

        FASE 1 (preflight, sin mutar): valida inputs, matriz, resultados,
        exige que toda operación habilitada tenga su GenerationResult,
        valida statuses y nombres, y resuelve cada ``SUCCESS`` contra
        ``pg_catalog`` (existencia, sin overloads, firma idéntica).
        FASE 2 (mutación): solo si todo el preflight pasó, ejecuta los
        ``GRANT``/``REVOKE``. ``PrivilegeChange`` se genera solo para
        rol × operación ``SUCCESS``; el ``REVOKE`` de tabla para
        ``NOT_APPLICABLE`` denegada es limpieza defensiva sin
        ``PrivilegeChange`` (no hay procedure aplicable que reconciliar).
        """
        schema_name = _validate_name(schema_name, kind="schema_name")
        table_name = _validate_name(table_name, kind="table_name")
        if not isinstance(matrix, PrivilegeMatrix):
            raise TypeError(
                "matrix debe ser PrivilegeMatrix, "
                f"no {type(matrix).__name__}."
            )
        roles = matrix.roles()
        if not roles:
            raise ValueError("La matriz no tiene roles configurados.")
        results = self._validate_results(generation_results)
        self._check_enabled_have_results(matrix, results)
        self._validate_statuses(schema_name, table_name, matrix, results)

        success = [r for r in results if r.status is GenerationStatus.SUCCESS]
        conn = self._manager.connect()
        owns_unit = conn.info.transaction_status == TransactionStatus.IDLE
        if owns_unit:
            try:
                with conn.transaction():
                    signatures = self._resolve_signatures(conn, success)
                    return self._mutate(
                        conn,
                        schema_name,
                        table_name,
                        matrix,
                        results,
                        success,
                        signatures,
                    )
            except pg_errors.Error as exc:
                raise self._manager.translate_error(exc) from exc
        else:
            try:
                signatures = self._resolve_signatures(conn, success)
                return self._mutate(
                    conn,
                    schema_name,
                    table_name,
                    matrix,
                    results,
                    success,
                    signatures,
                )
            except pg_errors.Error as exc:
                raise self._manager.translate_error(exc) from exc

    @staticmethod
    def _validate_results(
        generation_results: Iterable[GenerationResult],
    ) -> list[GenerationResult]:
        if isinstance(generation_results, (str, bytes)):
            raise TypeError(
                "generation_results debe ser un iterable de GenerationResult."
            )
        try:
            results = list(generation_results)
        except TypeError as exc:
            raise TypeError(
                "generation_results debe ser un iterable de GenerationResult."
            ) from exc
        if not results:
            raise ValueError("Debe indicar al menos un resultado de generación.")
        for result in results:
            if not isinstance(result, GenerationResult):
                raise TypeError(
                    "Cada resultado debe ser GenerationResult, "
                    f"no {type(result).__name__}."
                )
        operations = [result.operation for result in results]
        if len(set(operations)) != len(operations):
            raise ValueError(
                "Resultados duplicados: una sola fila por CrudOperation."
            )
        return results

    @staticmethod
    def _check_enabled_have_results(
        matrix: PrivilegeMatrix,
        results: list[GenerationResult],
    ) -> None:
        """Exige GenerationResult para toda operación habilitada.

        Un subconjunto de operaciones es válido solo si las ausentes están
        denegadas por todos los roles (fuera del scope de esta aplicación).
        """
        result_operations = {result.operation for result in results}
        enabled_operations = {
            operation
            for role in matrix.roles()
            for operation in matrix.operations_for(role)
        }
        missing = enabled_operations - result_operations
        if missing:
            ordered = ", ".join(
                operation.value for operation in CrudOperation if operation in missing
            )
            raise ValueError(
                "Operaciones habilitadas sin resultado de generación: "
                f"{ordered}."
            )

    @staticmethod
    def _validate_statuses(
        schema_name: str,
        table_name: str,
        matrix: PrivilegeMatrix,
        results: list[GenerationResult],
    ) -> None:
        for result in results:
            if result.schema_name != schema_name:
                raise ValueError(
                    f"GenerationResult de esquema {result.schema_name!r} no "
                    f"corresponde al objetivo {schema_name!r}."
                )
            if result.status in (
                GenerationStatus.PROCEDURE_CONFLICT,
                GenerationStatus.VALIDATION_ERROR,
            ):
                raise ValueError(
                    f"No se puede aplicar privilegios con status "
                    f"{result.status.value} en {result.operation.value}: "
                    "resuelva la generación antes de aplicar la matriz."
                )
            if result.status is GenerationStatus.NOT_APPLICABLE:
                if result.operation not in (
                    CrudOperation.UPDATE,
                    CrudOperation.DELETE,
                ):
                    raise ValueError(
                        f"Contrato violado: {result.operation.value} con "
                        "NOT_APPLICABLE (solo UPDATE/DELETE pueden ser no "
                        "aplicables)."
                    )
                enabled = [
                    role
                    for role in matrix.roles()
                    if matrix.is_allowed(role, result.operation)
                ]
                if enabled:
                    raise ValueError(
                        f"La operación {result.operation.value} es not_applicable "
                        f"pero está habilitada para: {', '.join(enabled)}."
                    )
                continue
            if result.routine_name is None:
                raise ValueError(
                    f"SUCCESS sin routine_name para {result.operation.value}."
                )
            if result.identity_arguments is None:
                raise ValueError(
                    f"SUCCESS sin identity_arguments para {result.operation.value}."
                )
            expected = _expected_routine(table_name, result.operation)
            if result.routine_name != expected:
                raise ValueError(
                    f"routine_name {result.routine_name!r} no coincide con el "
                    f"naming oficial {expected!r}."
                )

    def _resolve_signatures(
        self,
        conn: Any,
        success: list[GenerationResult],
    ) -> dict[CrudOperation, str]:
        """Preflight contra pg_catalog: 1 fila exacta y firma idéntica.

        Retorna el fragmento SQL de confianza
        (``pg_get_function_identity_arguments``) por operación. Solo lectura.
        """
        signatures: dict[CrudOperation, str] = {}
        for result in success:
            assert result.routine_name is not None
            assert result.identity_arguments is not None
            with conn.cursor() as cursor:
                cursor.execute(
                    _FIND_PROCEDURE_QUERY,
                    (result.schema_name, result.routine_name),
                )
                rows = cursor.fetchall()
            if not rows:
                raise ValueError(
                    f"El procedure {result.schema_name}.{result.routine_name} "
                    "no existe en pg_catalog."
                )
            if len(rows) > 1:
                raise ValueError(
                    f"Overload inesperado/no soportado para "
                    f"{result.schema_name}.{result.routine_name} "
                    f"({len(rows)} candidatos)."
                )
            catalog_identity = rows[0][1]
            catalog_identity = (
                None if catalog_identity is None else str(catalog_identity)
            )
            if catalog_identity != result.identity_arguments:
                raise ValueError(
                    f"Firma de {result.schema_name}.{result.routine_name} "
                    "no coincide con GenerationResult."
                )
            signatures[result.operation] = catalog_identity
        return signatures

    @staticmethod
    def _mutate(
        conn: Any,
        schema_name: str,
        table_name: str,
        matrix: PrivilegeMatrix,
        results: list[GenerationResult],
        success: list[GenerationResult],
        signatures: dict[CrudOperation, str],
    ) -> tuple[PrivilegeChange, ...]:
        """Ejecuta GRANT/REVOKE. Solo se llama con el preflight completo.

        Recorre ``results`` en su orden original. ``SUCCESS`` reconcilia las
        dos llaves (con ``PrivilegeChange``); ``NOT_APPLICABLE`` —ya validado
        como denegado por todos— solo limpia el permiso directo de tabla
        (sin ``EXECUTE``, sin ``USAGE``, sin ``PrivilegeChange``: no existe
        procedure aplicable).
        """
        changes: list[PrivilegeChange] = []
        with conn.cursor() as cursor:
            for role in matrix.roles():
                allowed_any = False
                for result in success:
                    operation = result.operation
                    assert result.routine_name is not None
                    if matrix.is_allowed(role, operation):
                        allowed_any = True
                if allowed_any:
                    cursor.execute(
                        sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                            sql.Identifier(schema_name),
                            sql.Identifier(role),
                        )
                    )
                for result in results:
                    operation = result.operation
                    table_priv = _TABLE_PRIVILEGE[operation]
                    if result.status is GenerationStatus.NOT_APPLICABLE:
                        cursor.execute(
                            sql.SQL("REVOKE {} ON {}.{} FROM {}").format(
                                sql.SQL(table_priv),
                                sql.Identifier(schema_name),
                                sql.Identifier(table_name),
                                sql.Identifier(role),
                            )
                        )
                        continue
                    routine = result.routine_name
                    assert routine is not None
                    signature = signatures[operation]
                    allowed = matrix.is_allowed(role, operation)
                    if allowed:
                        cursor.execute(
                            sql.SQL(
                                "GRANT EXECUTE ON PROCEDURE {}.{}({}) TO {}"
                            ).format(
                                sql.Identifier(schema_name),
                                sql.Identifier(routine),
                                sql.SQL(signature),
                                sql.Identifier(role),
                            )
                        )
                        cursor.execute(
                            sql.SQL("GRANT {} ON {}.{} TO {}").format(
                                sql.SQL(table_priv),
                                sql.Identifier(schema_name),
                                sql.Identifier(table_name),
                                sql.Identifier(role),
                            )
                        )
                    else:
                        cursor.execute(
                            sql.SQL(
                                "REVOKE EXECUTE ON PROCEDURE {}.{}({}) FROM {}"
                            ).format(
                                sql.Identifier(schema_name),
                                sql.Identifier(routine),
                                sql.SQL(signature),
                                sql.Identifier(role),
                            )
                        )
                        cursor.execute(
                            sql.SQL("REVOKE {} ON {}.{} FROM {}").format(
                                sql.SQL(table_priv),
                                sql.Identifier(schema_name),
                                sql.Identifier(table_name),
                                sql.Identifier(role),
                            )
                        )
                    changes.append(
                        PrivilegeChange(
                            role=role,
                            operation=operation,
                            allowed=allowed,
                            schema_name=schema_name,
                            table_name=table_name,
                            routine_name=routine,
                        )
                    )
        return tuple(changes)
