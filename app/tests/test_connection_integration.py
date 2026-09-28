"""Prueba de integración opcional contra PostgreSQL real.

No se ejecuta por defecto: requiere un servidor accesible y la variable
``CRUDGEN_TEST_POSTGRES=1``. Nunca debe hacer fallar ``pytest`` en máquinas
sin PostgreSQL configurado.
"""

from __future__ import annotations

import os

import pytest

from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager


def _config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


@pytest.mark.integration
def test_validate_against_real_postgres() -> None:
    if os.getenv("CRUDGEN_TEST_POSTGRES") != "1":
        pytest.skip("Requiere CRUDGEN_TEST_POSTGRES=1 y un PostgreSQL accesible.")
    with ConnectionManager(_config_from_env()) as manager:
        info = manager.validate()
    assert info.database
    assert info.current_user
    assert "PostgreSQL" in info.server_version
