"""Modelos simples del área Python (esquemas, tablas, roles).

Son contenedores inmutables para que la UI futura consuma fácilmente los
resultados del catálogo. No contienen lógica SQL ni reglas de negocio.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaInfo:
    """Esquema visible para el administrador."""

    name: str


@dataclass(frozen=True)
class TableInfo:
    """Tabla real dentro de un esquema (incluye el esquema para contexto de UI)."""

    schema: str
    name: str


@dataclass(frozen=True)
class RoleInfo:
    """Rol PostgreSQL candidato para futura asignación de privilegios.

    ``can_login`` distingue usuarios (LOGIN) de roles de grupo (NOLOGIN);
    ``is_superuser`` permite a la UI advertir que otorgar EXECUTE a un
    superusuario es innecesario (ya puede hacerlo todo).
    """

    name: str
    can_login: bool
    is_superuser: bool
