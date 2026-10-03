"""Matriz rol × operación CRUD (representa intención del usuario).

Una matriz indica qué operaciones el administrador *desea* permitir a cada
rol. NO representa permisos efectivos de PostgreSQL: `allowed` no ejecuta
`GRANT`, no consulta catálogos y no conoce procedures, tablas ni conexiones.
La aplicación futura de permisos reales vivirá en otra capa.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from crud_generator.models import CrudOperation

#: Orden canónico de operaciones (el de definición de `CrudOperation`).
_OPERATION_ORDER: dict[CrudOperation, int] = {
    operation: index for index, operation in enumerate(CrudOperation)
}


def _check_role(role: str) -> str:
    if not isinstance(role, str):
        raise TypeError(
            "El nombre del rol debe ser str, "
            f"no {type(role).__name__}."
        )
    if not role.strip():
        raise ValueError("El nombre del rol no puede estar vacío.")
    return role


def _check_operation(operation: CrudOperation) -> CrudOperation:
    if not isinstance(operation, CrudOperation):
        raise TypeError(
            "La operación debe ser un miembro de CrudOperation, "
            f"no {type(operation).__name__}."
        )
    return operation


@dataclass(frozen=True)
class PrivilegeAssignment:
    """Una operación habilitada para un rol (intención, no GRANT)."""

    role: str
    operation: CrudOperation

    def __post_init__(self) -> None:
        _check_role(self.role)
        _check_operation(self.operation)


class PrivilegeMatrix:
    """Matriz mutable controlada de `rol → operaciones habilitadas`.

    Denegación por defecto: una matriz nueva niega todo y solo guarda pares
    habilitados, por lo que no existen duplicados ni estados ambiguos.
    Además conserva el universo de roles configurados: un rol explícitamente
    denegado en todo sigue presente (importante para la futura fase REVOKE,
    donde perder la última operación no debe borrar al rol ni dejar
    privilegios residuales).
    La mutación es intencional: la matriz se configura progresivamente en la
    UI antes de aplicarse; nada es concurrente y copiar instancias añadiría
    complejidad sin beneficio.
    """

    def __init__(self, assignments: Iterable[PrivilegeAssignment] = ()) -> None:
        self._roles: set[str] = set()
        self._allowed: set[PrivilegeAssignment] = set()
        for assignment in assignments:
            self._roles.add(assignment.role)
            self._allowed.add(assignment)

    def __len__(self) -> int:
        return len(self._allowed)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrivilegeMatrix):
            return NotImplemented
        return self._roles == other._roles and self._allowed == other._allowed

    def __repr__(self) -> str:
        items = ", ".join(
            f"{a.role}:{a.operation.value}" for a in self.assignments()
        )
        bare = ", ".join(sorted(self._roles - {a.role for a in self._allowed}))
        detail = f"{items}; solo roles: {bare}" if bare else items
        return f"PrivilegeMatrix({detail})"

    def add_role(self, role: str) -> None:
        """Registra un rol configurado, aunque no tenga operaciones habilitadas."""
        self._roles.add(_check_role(role))

    def enable(self, role: str, operation: CrudOperation) -> None:
        """Habilita una operación. Idempotente: repetir no duplica.

        Registra automáticamente el rol si todavía no existe.
        """
        role = _check_role(role)
        operation = _check_operation(operation)
        self._roles.add(role)
        self._allowed.add(PrivilegeAssignment(role=role, operation=operation))

    def disable(self, role: str, operation: CrudOperation) -> None:
        """Deshabilita una operación. Idempotente: ausente no es error.

        Registra el rol porque expresa una decisión explícita de "denegado".
        """
        role = _check_role(role)
        operation = _check_operation(operation)
        self._roles.add(role)
        self._allowed.discard(PrivilegeAssignment(role=role, operation=operation))

    def is_allowed(self, role: str, operation: CrudOperation) -> bool:
        """`True` solo si el par fue habilitado; rol desconocido → `False`.

        No distingue rol desconocido de rol configurado sin permisos (ambos
        `False`); la distinción se obtiene con `roles()`.
        """
        _check_role(role)
        _check_operation(operation)
        return PrivilegeAssignment(role=role, operation=operation) in self._allowed

    def operations_for(self, role: str) -> tuple[CrudOperation, ...]:
        """Operaciones habilitadas de un rol, en orden canónico."""
        _check_role(role)
        return tuple(
            assignment.operation
            for assignment in self.assignments()
            if assignment.role == role
        )

    def roles(self) -> tuple[str, ...]:
        """Roles configurados (con o sin operaciones), ordenados."""
        return tuple(sorted(self._roles))

    def assignments(self) -> tuple[PrivilegeAssignment, ...]:
        """Todas las asignaciones, ordenadas por rol y operación."""
        return tuple(
            sorted(self._allowed, key=_assignment_key),
        )


def _assignment_key(assignment: PrivilegeAssignment) -> tuple[str, int]:
    return (assignment.role, _OPERATION_ORDER[assignment.operation])
