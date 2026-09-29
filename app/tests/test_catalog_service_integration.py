"""Prueba de integración opcional de CatalogService contra PostgreSQL real.

No se ejecuta por defecto: requiere un servidor accesible y la variable
``CRUDGEN_TEST_POSTGRES=1``. Nunca debe hacer fallar ``pytest`` en máquinas
sin PostgreSQL configurado.
"""

from __future__ import annotations

import os

import pytest

from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager
from crud_generator.services import CatalogService


def _config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


@pytest.mark.integration
def test_catalog_against_real_postgres() -> None:
    if os.getenv("CRUDGEN_TEST_POSTGRES") != "1":
        pytest.skip("Requiere CRUDGEN_TEST_POSTGRES=1 y un PostgreSQL accesible.")
    with ConnectionManager(_config_from_env()) as manager:
        service = CatalogService(manager)
        schemas = service.list_schemas()
        roles = service.list_roles()
    assert isinstance(schemas, list)
    assert isinstance(roles, list)
    assert all(role.name for role in roles)
