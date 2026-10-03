"""Matriz lógica y aplicación de privilegios PostgreSQL del área Python."""

from crud_generator.privileges.matrix import PrivilegeAssignment, PrivilegeMatrix
from crud_generator.privileges.probe import (
    PermissionProbeResult,
    PermissionProbeService,
    PermissionProbeStatus,
    RoleAssumptionError,
)
from crud_generator.privileges.service import PrivilegeChange, PrivilegeService

__all__ = [
    "PermissionProbeResult",
    "PermissionProbeService",
    "PermissionProbeStatus",
    "PrivilegeAssignment",
    "PrivilegeChange",
    "PrivilegeMatrix",
    "PrivilegeService",
    "RoleAssumptionError",
]
