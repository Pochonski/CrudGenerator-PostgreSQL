"""Pruebas de la matriz de privilegios (modelos puros, sin PostgreSQL ni SQL)."""

from __future__ import annotations

import pytest

from crud_generator.models import CrudOperation
from crud_generator.privileges import PrivilegeAssignment, PrivilegeMatrix


def matrix_with_vendedor() -> PrivilegeMatrix:
    matrix = PrivilegeMatrix()
    matrix.enable("vendedor", CrudOperation.INSERT)
    matrix.enable("vendedor", CrudOperation.READ)
    return matrix


def test_new_matrix_denies_everything() -> None:
    matrix = PrivilegeMatrix()

    assert len(matrix) == 0
    assert matrix.assignments() == ()
    assert matrix.roles() == ()
    assert not matrix.is_allowed("cualquiera", CrudOperation.INSERT)


def test_create_with_one_role() -> None:
    matrix = PrivilegeMatrix(
        [PrivilegeAssignment("ana", CrudOperation.READ)],
    )

    assert matrix.is_allowed("ana", CrudOperation.READ)
    assert not matrix.is_allowed("ana", CrudOperation.DELETE)


def test_create_with_multiple_roles() -> None:
    matrix = PrivilegeMatrix(
        [
            PrivilegeAssignment("ana", CrudOperation.INSERT),
            PrivilegeAssignment("jefe", CrudOperation.DELETE),
        ],
    )

    assert matrix.roles() == ("ana", "jefe")
    assert matrix.is_allowed("jefe", CrudOperation.DELETE)
    assert not matrix.is_allowed("ana", CrudOperation.DELETE)


def test_enable_single_operation() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("vendedor", CrudOperation.INSERT)

    assert matrix.is_allowed("vendedor", CrudOperation.INSERT)
    assert len(matrix) == 1


def test_enable_multiple_operations() -> None:
    matrix = matrix_with_vendedor()

    assert matrix.operations_for("vendedor") == (
        CrudOperation.INSERT,
        CrudOperation.READ,
    )


def test_enable_is_idempotent_without_duplicates() -> None:
    matrix = matrix_with_vendedor()
    matrix.enable("vendedor", CrudOperation.INSERT)

    assert len(matrix) == 2
    assert matrix.assignments().count(
        PrivilegeAssignment("vendedor", CrudOperation.INSERT)
    ) == 1


def test_disable_enabled_operation() -> None:
    matrix = matrix_with_vendedor()
    matrix.disable("vendedor", CrudOperation.READ)

    assert not matrix.is_allowed("vendedor", CrudOperation.READ)
    assert matrix.is_allowed("vendedor", CrudOperation.INSERT)


def test_disable_already_disabled_is_defined_noop() -> None:
    matrix = matrix_with_vendedor()
    matrix.disable("vendedor", CrudOperation.DELETE)  # no estaba habilitada
    matrix.disable("nadie", CrudOperation.READ)  # rol sin asignaciones

    assert len(matrix) == 2
    assert not matrix.is_allowed("vendedor", CrudOperation.DELETE)


def test_unknown_role_is_denied() -> None:
    matrix = matrix_with_vendedor()

    assert not matrix.is_allowed("desconocido", CrudOperation.INSERT)
    assert matrix.operations_for("desconocido") == ()


def test_operations_for_unknown_role_is_empty() -> None:
    assert PrivilegeMatrix().operations_for("nadie") == ()


def test_assignments_are_deterministic() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("zeta", CrudOperation.DELETE)
    matrix.enable("ana", CrudOperation.UPDATE)
    matrix.enable("ana", CrudOperation.INSERT)
    matrix.enable("zeta", CrudOperation.INSERT)

    assert matrix.assignments() == (
        PrivilegeAssignment("ana", CrudOperation.INSERT),
        PrivilegeAssignment("ana", CrudOperation.UPDATE),
        PrivilegeAssignment("zeta", CrudOperation.INSERT),
        PrivilegeAssignment("zeta", CrudOperation.DELETE),
    )
    assert matrix.roles() == ("ana", "zeta")


def test_empty_role_is_rejected() -> None:
    matrix = PrivilegeMatrix()

    with pytest.raises(ValueError):
        PrivilegeAssignment("  ", CrudOperation.READ)
    with pytest.raises(ValueError):
        matrix.enable("  ", CrudOperation.READ)
    with pytest.raises(ValueError):
        matrix.disable("", CrudOperation.READ)
    with pytest.raises(ValueError):
        matrix.is_allowed("", CrudOperation.READ)
    with pytest.raises(ValueError):
        matrix.operations_for("  ")


def test_non_string_role_raises_type_error() -> None:
    matrix = PrivilegeMatrix()

    with pytest.raises(TypeError):
        PrivilegeAssignment(None, CrudOperation.READ)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.add_role(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.enable(123, CrudOperation.READ)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.disable(None, CrudOperation.READ)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.is_allowed(123, CrudOperation.READ)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.operations_for(None)  # type: ignore[arg-type]


def test_role_name_is_preserved_exactly() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("Vendedor_X", CrudOperation.READ)
    matrix.add_role("Mi_Rol")

    assert matrix.roles() == ("Mi_Rol", "Vendedor_X")
    assert matrix.is_allowed("Vendedor_X", CrudOperation.READ)
    assert not matrix.is_allowed("vendedor_x", CrudOperation.READ)


def test_invalid_operation_is_rejected() -> None:
    matrix = PrivilegeMatrix()

    with pytest.raises(TypeError):
        PrivilegeAssignment("ana", "INSERT")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.enable("ana", "INSERT")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.disable("ana", None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        matrix.is_allowed("ana", 42)  # type: ignore[arg-type]


def test_role_names_are_not_hardcoded() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("vendedor_2026", CrudOperation.INSERT)
    matrix.enable("x", CrudOperation.DELETE)

    assert matrix.is_allowed("vendedor_2026", CrudOperation.INSERT)
    assert matrix.is_allowed("x", CrudOperation.DELETE)
    assert not matrix.is_allowed("crud_vendedor", CrudOperation.INSERT)


def test_matrices_compare_by_content() -> None:
    first = matrix_with_vendedor()
    second = matrix_with_vendedor()
    other = PrivilegeMatrix()
    other.enable("vendedor", CrudOperation.INSERT)

    assert first == second
    assert first != other
    assert first != "no es matriz"


def test_add_role_registers_role_without_permissions() -> None:
    matrix = PrivilegeMatrix()
    matrix.add_role("auditor")

    assert matrix.roles() == ("auditor",)
    assert matrix.operations_for("auditor") == ()
    assert not matrix.is_allowed("auditor", CrudOperation.READ)
    assert len(matrix) == 0


def test_fully_denied_role_stays_in_roles() -> None:
    matrix = PrivilegeMatrix()
    matrix.add_role("vendedor")

    assert matrix.roles() == ("vendedor",)
    assert "vendedor" in repr(matrix)


def test_removing_last_allowed_operation_keeps_role() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("vendedor", CrudOperation.READ)
    matrix.disable("vendedor", CrudOperation.READ)

    assert matrix.roles() == ("vendedor",)
    assert matrix.operations_for("vendedor") == ()
    assert not matrix.is_allowed("vendedor", CrudOperation.READ)


def test_multiple_roles_including_bare_one() -> None:
    matrix = matrix_with_vendedor()
    matrix.add_role("auditor")
    matrix.enable("jefe", CrudOperation.DELETE)

    assert matrix.roles() == ("auditor", "jefe", "vendedor")
    assert matrix.operations_for("auditor") == ()
    assert matrix.is_allowed("jefe", CrudOperation.DELETE)


def test_enable_on_new_role_registers_it() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("nuevo", CrudOperation.UPDATE)

    assert matrix.roles() == ("nuevo",)
    assert matrix.is_allowed("nuevo", CrudOperation.UPDATE)


def test_disable_on_new_role_registers_denied_role() -> None:
    matrix = PrivilegeMatrix()
    matrix.disable("nuevo", CrudOperation.DELETE)

    # Semántica documentada: disable expresa "denegado" explícito,
    # por lo que el rol queda configurado aunque sin permisos.
    assert matrix.roles() == ("nuevo",)
    assert not matrix.is_allowed("nuevo", CrudOperation.DELETE)
    assert len(matrix) == 0


def test_determinism_with_bare_roles() -> None:
    matrix = PrivilegeMatrix()
    matrix.enable("zeta", CrudOperation.DELETE)
    matrix.add_role("auditor")
    matrix.enable("ana", CrudOperation.INSERT)

    assert matrix.roles() == ("ana", "auditor", "zeta")
    assert matrix.assignments() == (
        PrivilegeAssignment("ana", CrudOperation.INSERT),
        PrivilegeAssignment("zeta", CrudOperation.DELETE),
    )
