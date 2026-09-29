"""Prueba de integración opcional de ExtensionService contra PostgreSQL real.

No se ejecuta por defecto: requiere un servidor accesible y la variable
``CRUDGEN_TEST_POSTGRES=1``. Nunca debe hacer fallar ``pytest`` en máquinas
sin PostgreSQL configurado. Como la extensión real puede no existir, verifica
el caso `NOT_INSTALLED` con un nombre que no puede existir.
"""

from __future__ import annotations

import os

import pytest

from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager
from crud_generator.models import ExtensionState
from crud_generator.services import ExtensionService


def _config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


@pytest.mark.integration
def test_missing_extension_against_real_postgres() -> None:
    if os.getenv("CRUDGEN_TEST_POSTGRES") != "1":
        pytest.skip("Requiere CRUDGEN_TEST_POSTGRES=1 y un PostgreSQL accesible.")
    with ConnectionManager(_config_from_env()) as manager:
        status = ExtensionService(manager).check_extension(
            "crudgen_extension_inexistente_xyz"
        )
    assert status.state is ExtensionState.NOT_INSTALLED
