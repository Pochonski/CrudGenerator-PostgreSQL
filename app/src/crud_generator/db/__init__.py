"""Capa de acceso a PostgreSQL (DatabaseConfig -> ConnectionManager -> PostgreSQL).

Esta capa solo gestiona conexiones: abrir, cerrar, validar y manejar
transacciones/errores. No contiene lógica de catálogos, extensión CRUD,
tablas ni privilegios (ver ARCHITECTURE.md).
"""

from crud_generator.db.connection import (
    AuthenticationError,
    ConnectionInfo,
    ConnectionManager,
    DatabaseConnectionError,
    DatabaseNotFoundError,
    InsufficientPrivilegeError,
    ServerUnavailableError,
    UnexpectedDatabaseError,
)

__all__ = [
    "AuthenticationError",
    "ConnectionInfo",
    "ConnectionManager",
    "DatabaseConnectionError",
    "DatabaseNotFoundError",
    "InsufficientPrivilegeError",
    "ServerUnavailableError",
    "UnexpectedDatabaseError",
]
