"""Conexión a PostgreSQL con psycopg.

Responsabilidad única: abrir, reutilizar, validar y cerrar conexiones,
además de traducir los errores de psycopg/PostgreSQL a una jerarquía
propia que la UI podrá mostrar sin exponer la contraseña.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self

import psycopg
from psycopg import errors as pg_errors
from psycopg import sql

from crud_generator.config import DatabaseConfig

#: Consulta de validación: una sola ida y vuelta, sin tocar catálogos.
_VALIDATE_QUERY = (
    "SELECT current_database() AS database, current_user AS user, version() AS version"
)


class DatabaseConnectionError(Exception):
    """Base de los errores de conexión. Preserva SQLSTATE y causa original."""

    def __init__(
        self,
        message: str,
        *,
        sqlstate: str | None = None,
        original: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate
        self.original = original


class AuthenticationError(DatabaseConnectionError):
    """Credenciales incorrectas (clase SQLSTATE 28)."""


class DatabaseNotFoundError(DatabaseConnectionError):
    """La base de datos no existe (SQLSTATE 3D000)."""


class ServerUnavailableError(DatabaseConnectionError):
    """Servidor no disponible: red, DNS, puerto cerrado o timeout (clase 08)."""


class InsufficientPrivilegeError(DatabaseConnectionError):
    """Permiso insuficiente al conectar/validar (SQLSTATE 42501)."""


class UnexpectedDatabaseError(DatabaseConnectionError):
    """Error PostgreSQL inesperado: conserva SQLSTATE y mensaje original."""


@dataclass(frozen=True)
class ConnectionInfo:
    """Resultado de validar una conexión. La UI decide cómo mostrarlo."""

    database: str
    current_user: str
    server_version: str


def _scrub_password(message: str, password: str) -> str:
    """Elimina la contraseña del mensaje si psycopg la hubiera incluido."""
    if password and password in message:
        return message.replace(password, "***")
    return message


def _map_error(exc: BaseException, config: DatabaseConfig) -> DatabaseConnectionError:
    """Traduce una excepción a la jerarquía propia sin exponer la contraseña."""
    if isinstance(exc, DatabaseConnectionError):
        return exc
    raw = _scrub_password(str(exc), config.password)
    sqlstate: str | None = getattr(exc, "sqlstate", None)

    if sqlstate is not None:
        if sqlstate.startswith("28"):
            return AuthenticationError(
                f"Credenciales incorrectas para el usuario "
                f"'{config.user}': {raw}",
                sqlstate=sqlstate,
                original=exc,
            )
        if sqlstate == "3D000":
            return DatabaseNotFoundError(
                f"La base de datos '{config.database}' no existe: {raw}",
                sqlstate=sqlstate,
                original=exc,
            )
        if sqlstate == "42501":
            return InsufficientPrivilegeError(
                f"Permiso insuficiente para el usuario '{config.user}': {raw}",
                sqlstate=sqlstate,
                original=exc,
            )
        if sqlstate.startswith("08"):
            return ServerUnavailableError(
                f"No se pudo conectar a {config.host}:{config.port}: {raw}",
                sqlstate=sqlstate,
                original=exc,
            )
        return UnexpectedDatabaseError(
            f"Error inesperado de PostgreSQL (SQLSTATE {sqlstate}): {raw}",
            sqlstate=sqlstate,
            original=exc,
        )

    if isinstance(exc, pg_errors.OperationalError):
        # Sin SQLSTATE: el servidor no respondió (red/DNS/puerto/timeout).
        return ServerUnavailableError(
            f"No se pudo conectar a {config.host}:{config.port}: {raw}",
            original=exc,
        )
    if isinstance(exc, pg_errors.Error):
        return UnexpectedDatabaseError(
            f"Error inesperado de PostgreSQL: {raw}",
            original=exc,
        )
    if isinstance(exc, OSError | TimeoutError):
        return ServerUnavailableError(
            f"No se pudo conectar a {config.host}:{config.port}: {raw}",
            original=exc,
        )
    return UnexpectedDatabaseError(
        f"Error inesperado de conexión: {raw}",
        original=exc,
    )


class ConnectionManager:
    """Abre, reutiliza, valida y cierra conexiones PostgreSQL con psycopg.

    Uso típico::

        with ConnectionManager(config) as manager:
            info = manager.validate()

    Decisiones locales (área Python):
    - ``autocommit=True`` por defecto para no dejar transacciones abiertas
      en validaciones de solo lectura; las operaciones administrativas
      futuras que requieran atomicidad usarán transacciones explícitas.
    - ``connect()`` es idempotente: reutiliza la conexión abierta.
    - El context manager garantiza el cierre (sin conexiones huérfanas).
    """

    def __init__(
        self,
        config: DatabaseConfig,
        *,
        connect_timeout: int = 10,
        autocommit: bool = True,
    ) -> None:
        self._config = config
        self._connect_timeout = connect_timeout
        self._autocommit = autocommit
        self._connection: psycopg.Connection[Any] | None = None

    def __repr__(self) -> str:
        cfg = self._config
        return (
            f"ConnectionManager(host={cfg.host!r}, port={cfg.port!r}, "
            f"database={cfg.database!r}, user={cfg.user!r}, "
            f"connected={self.is_connected!r})"
        )

    @property
    def config(self) -> DatabaseConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        conn = self._connection
        return conn is not None and not conn.closed

    @property
    def connection(self) -> psycopg.Connection[Any]:
        """Conexión activa. Lanza error si no hay conexión abierta."""
        if not self.is_connected or self._connection is None:
            raise DatabaseConnectionError("No hay una conexión abierta.")
        return self._connection

    def _connection_params(self) -> dict[str, Any]:
        cfg = self._config
        return {
            "host": cfg.host,
            "port": cfg.port,
            "dbname": cfg.database,
            "user": cfg.user,
            "password": cfg.password,
            "connect_timeout": self._connect_timeout,
            "autocommit": self._autocommit,
        }

    def connect(self) -> psycopg.Connection[Any]:
        """Abre la conexión si no existe y la reutiliza en caso contrario."""
        if self.is_connected and self._connection is not None:
            return self._connection
        # La conexión anterior quedó cerrada por el servidor: descartarla.
        self._connection = None
        try:
            self._connection = psycopg.connect(**self._connection_params())
        except Exception as exc:
            self._connection = None
            raise _map_error(exc, self._config) from exc
        return self._connection

    def close(self) -> None:
        """Cierra la conexión. Idempotente: llamar dos veces no falla."""
        conn, self._connection = self._connection, None
        if conn is None or conn.closed:
            return
        try:
            conn.close()
        finally:
            self._connection = None

    def commit(self) -> None:
        """Confirma la transacción activa. Sin conexión lanza error."""
        conn = self.connection
        try:
            conn.commit()
        except Exception as exc:
            raise _map_error(exc, self._config) from exc

    def translate_error(self, exc: BaseException) -> DatabaseConnectionError:
        """Traduce una excepción a la jerarquía propia (para otros servicios)."""
        return _map_error(exc, self._config)

    def rollback(self) -> None:
        """Revierte la transacción activa. Sin conexión lanza error."""
        conn = self.connection
        try:
            conn.rollback()
        except Exception as exc:
            raise _map_error(exc, self._config) from exc

    @contextmanager
    def assume_role(self, role_name: str) -> Iterator[None]:
        """Asume un rol vía ``SET ROLE`` session-level y revierte con ``RESET ROLE``.

        El rol es un identificador: se compone con ``sql.Identifier``, nunca
        interpolado. Tras ``SET ROLE`` verifica ``current_user`` y falla si no
        coincide. Si ``current_user`` ya es el rol pedido, es no-op seguro
        (sin ``SET``/``RESET``). Si ``SET ROLE`` tuvo éxito, ``RESET ROLE`` se
        intenta siempre en ``finally``, incluso si falla la verificación
        posterior o el cuerpo (preservando el error original si ``RESET``
        también falla). Los errores
        ``psycopg.Error`` (p. ej. ``42501`` sin capacidad ``SET``) se mapean
        con la jerarquía propia preservando ``SQLSTATE``.

        Nota transaccional: ``SET ROLE`` es session-level y este contexto está
        pensado para conexiones con ``autocommit=True`` (el default, usado por
        ``ApplicationFlow``). No cambia ``SESSION AUTHORIZATION`` ni concede
        memberships.
        """
        if not isinstance(role_name, str):
            raise TypeError(
                f"El rol debe ser str, no {type(role_name).__name__}."
            )
        if not role_name.strip():
            raise ValueError("El rol no puede estar vacío.")
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_user")
                row = cursor.fetchone()
            current = str(row[0]) if row is not None else None
        except Exception as exc:
            raise _map_error(exc, self._config) from exc
        if current == role_name:
            yield
            return
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL("SET ROLE {}").format(sql.Identifier(role_name))
                )
        except Exception as exc:
            raise _map_error(exc, self._config) from exc
        role_was_set = True
        body_error: BaseException | None = None
        try:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT current_user, session_user")
                    row = cursor.fetchone()
                if row is None or str(row[0]) != role_name:
                    raise UnexpectedDatabaseError(
                        f"Inconsistencia tras SET ROLE {role_name!r}: "
                        f"current_user es {row[0] if row else None!r}."
                    )
            except DatabaseConnectionError:
                raise
            except Exception as exc:
                raise _map_error(exc, self._config) from exc
            try:
                yield
            except BaseException as exc:
                body_error = exc
                raise
        finally:
            if role_was_set:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("RESET ROLE")
                except Exception as exc:
                    if body_error is None:
                        raise _map_error(exc, self._config) from exc

    def validate(self) -> ConnectionInfo:
        """Comprueba que la conexión funciona y retorna datos del servidor."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(_VALIDATE_QUERY)
                row = cursor.fetchone()
            if row is None:
                raise UnexpectedDatabaseError(
                    "La validación no retornó información del servidor."
                )
            database, current_user, server_version = row[0], row[1], row[2]
            info = ConnectionInfo(
                database=str(database),
                current_user=str(current_user),
                server_version=str(server_version),
            )
            if not conn.autocommit:
                # Consulta de solo lectura: no dejarla en idle-in-transaction.
                conn.rollback()
            return info
        except DatabaseConnectionError:
            if not conn.autocommit:
                with suppress(psycopg.Error):
                    conn.rollback()
            raise
        except Exception as exc:
            if not conn.autocommit:
                with suppress(psycopg.Error):
                    conn.rollback()
            raise _map_error(exc, self._config) from exc

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
