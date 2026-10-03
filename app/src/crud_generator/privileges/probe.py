"""Prueba de permisos efectivos (SET ROLE + CALL real, sin efectos persistentes).

Responsabilidad única: ejecutar UN procedure generado como un rol PostgreSQL
real y reportar si el ``CALL`` fue autorizado o denegado (``42501``). Sirve
para validar privilegios efectivos, demos y futura integración; no configura
permisos (eso es ``PrivilegeService``).

Aislamiento: toda la secuencia ocurre dentro de
``with conn.transaction(force_rollback=True)`` —el ``CALL`` ejecuta de verdad
(permisos y constraints se comprueban, se obtiene output), pero al salir todo
se revierte, incluido el ``SET LOCAL ROLE``. Nunca hace ``commit`` ni deja DML
persistente.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from psycopg import errors as pg_errors
from psycopg import sql
from psycopg.pq import TransactionStatus

from crud_generator.db.connection import (
    ConnectionManager,
    InsufficientPrivilegeError,
)
from crud_generator.models import GenerationResult, GenerationStatus


class PermissionProbeStatus(Enum):
    """Resultado de un probe: autorizado o denegado por PostgreSQL."""

    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True)
class PermissionProbeResult:
    """Resultado de probar UN procedure como UN rol.

    ``output`` es la fila devuelta por el ``CALL`` (parámetros ``OUT``/``INOUT``,
    incluido el nombre del ``refcursor`` en READ sin PK) o ``None`` si el
    procedure no retorna fila. Para ``READ`` sin PK no se hace ``FETCH`` aquí:
    solo se demuestra autorización/denegación; el ``FETCH`` real llegará con
    la ejecución funcional.
    """

    role: str
    operation: Any
    schema_name: str
    routine_name: str
    status: PermissionProbeStatus
    output: tuple[Any, ...] | None
    sqlstate: str | None
    message: str


class RoleAssumptionError(InsufficientPrivilegeError):
    """``SET LOCAL ROLE`` falló: la sesión no pudo asumir el rol solicitado.

    No demuestra que la operación esté denegada para ese rol, solo que la
    sesión administrativa carece de capacidad ``SET`` sobre él (típicamente
    porque no es superusuario ni miembro con privilegio ``SET``). No debe
    confundirse con ``PermissionProbeStatus.DENIED``, que corresponde a un
    ``42501`` durante el ``CALL`` con el rol ya asumido.
    """


def _validate_role(role: str) -> str:
    if not isinstance(role, str):
        raise TypeError(f"El rol debe ser str, no {type(role).__name__}.")
    if not role.strip():
        raise ValueError("El rol no puede estar vacío.")
    return role


def _validate_generation_result(result: GenerationResult) -> GenerationResult:
    if not isinstance(result, GenerationResult):
        raise TypeError(
            "generation_result debe ser GenerationResult, "
            f"no {type(result).__name__}."
        )
    if result.status is not GenerationStatus.SUCCESS:
        raise ValueError(
            f"Solo se puede probar un procedure SUCCESS, no {result.status.value}."
        )
    if not isinstance(result.schema_name, str) or not result.schema_name.strip():
        raise ValueError("El GenerationResult no trae un schema_name válido.")
    if result.routine_name is None:
        raise ValueError("El GenerationResult SUCCESS no trae routine_name.")
    return result


def _materialize_arguments(arguments: Iterable[Any]) -> tuple[Any, ...]:
    if isinstance(arguments, (str, bytes)):
        raise TypeError(
            "arguments debe ser un iterable de valores; para un único texto "
            'use ("texto",), no un str/bytes directo.'
        )
    try:
        return tuple(arguments)
    except TypeError as exc:
        raise TypeError(
            "arguments debe ser un iterable de valores."
        ) from exc


class PermissionProbeService:
    """Prueba UN procedure generado como UN rol real, sin dejar residuos.

    Requiere que la conexión esté inicialmente ``IDLE``; ante cualquier otro
    estado (p. ej. ``INTRANS``) rechaza con ``RuntimeError`` antes de tocar
    PostgreSQL: un ``SET LOCAL ROLE`` dentro de una transacción ajena podría
    dejar al caller con la transacción abortada.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConnectionManager:
        return self._manager

    def probe(
        self,
        role: str,
        generation_result: GenerationResult,
        arguments: Iterable[Any] = (),
    ) -> PermissionProbeResult:
        """Ejecuta ``CALL schema.routine(args)`` como ``role`` con rollback total."""
        role = _validate_role(role)
        generation_result = _validate_generation_result(generation_result)
        args = _materialize_arguments(arguments)
        schema_name = generation_result.schema_name
        routine_name = generation_result.routine_name
        assert routine_name is not None
        operation = generation_result.operation

        conn = self._manager.connect()
        if conn.info.transaction_status is not TransactionStatus.IDLE:
            raise RuntimeError(
                "PermissionProbeService requiere una conexión IDLE "
                "(sin transacción preexistente)."
            )
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in args)
        call_stmt = sql.SQL("CALL {}.{}({})").format(
            sql.Identifier(schema_name),
            sql.Identifier(routine_name),
            placeholders,
        )
        stage = "set_role"
        try:
            with conn.transaction(force_rollback=True):
                with conn.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role))
                    )
                stage = "verify_role"
                with conn.cursor() as cursor:
                    cursor.execute("SELECT current_user, session_user")
                    row = cursor.fetchone()
                if row is None or str(row[0]) != role:
                    raise ValueError(
                        f"Inconsistencia tras SET LOCAL ROLE {role!r}: "
                        f"current_user es {row[0] if row else None!r}."
                    )
                stage = "call"
                with conn.cursor() as cursor:
                    cursor.execute(call_stmt, args)
                    output: tuple[Any, ...] | None = None
                    if cursor.description is not None:
                        fetched = cursor.fetchone()
                        if fetched is not None:
                            output = tuple(fetched)
                return PermissionProbeResult(
                    role=role,
                    operation=operation,
                    schema_name=schema_name,
                    routine_name=routine_name,
                    status=PermissionProbeStatus.ALLOWED,
                    output=output,
                    sqlstate=None,
                    message=(
                        f"CALL {schema_name}.{routine_name} ejecutado "
                        f"como {role}."
                    ),
                )
        except pg_errors.Error as exc:
            sqlstate: str | None = getattr(exc, "sqlstate", None)
            if stage == "set_role" and sqlstate == "42501":
                raise RoleAssumptionError(
                    f"La sesión actual no puede asumir el rol {role!r} "
                    "(42501 en SET LOCAL ROLE).",
                    sqlstate=sqlstate,
                    original=exc,
                ) from exc
            if stage == "call" and sqlstate == "42501":
                return PermissionProbeResult(
                    role=role,
                    operation=operation,
                    schema_name=schema_name,
                    routine_name=routine_name,
                    status=PermissionProbeStatus.DENIED,
                    output=None,
                    sqlstate=sqlstate,
                    message=(
                        f"Acceso denegado para {role} en "
                        f"{schema_name}.{routine_name} (SQLSTATE 42501)."
                    ),
                )
            raise self._manager.translate_error(exc) from exc
