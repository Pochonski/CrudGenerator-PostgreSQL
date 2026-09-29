"""Pruebas de CrudOperation/CrudSelection (modelos de selección)."""

from __future__ import annotations

import pytest

from crud_generator.models import CrudOperation, CrudSelection


def test_valid_selection_keeps_values() -> None:
    selection = CrudSelection(
        schema="ventas",
        tables=("cliente", "pedido"),
        operations=(CrudOperation.INSERT, CrudOperation.READ),
    )

    assert selection.schema == "ventas"
    assert selection.tables == ("cliente", "pedido")
    assert selection.operations == (CrudOperation.INSERT, CrudOperation.READ)


def test_empty_schema_is_rejected() -> None:
    with pytest.raises(ValueError):
        CrudSelection(schema="  ", tables=("t",), operations=(CrudOperation.READ,))


def test_empty_tables_is_rejected() -> None:
    with pytest.raises(ValueError):
        CrudSelection(schema="s", tables=(), operations=(CrudOperation.READ,))


def test_empty_operations_is_rejected() -> None:
    with pytest.raises(ValueError):
        CrudSelection(schema="s", tables=("t",), operations=())
