"""Integración real de ApplicationFlow (sin mocks, I/O programado).

Requiere ``CRUDGEN_TEST_POSTGRES=1`` y el laboratorio base (roles +
``lab.producto`` + extensión instalada). Prepara un estado limpio de primera
ejecución (revoca privilegios directos de ``crud_vendedor`` sobre
``lab.producto`` y elimina los procedures ``producto_*`` si existen) y usa
``do_replace=True`` para ser repetible. Nunca toca ``lab.tabla_virgen``.
"""

from __future__ import annotations

import os

import pytest

from crud_generator.application import EXIT_OK, ApplicationFlow
from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager
from crud_generator.services.catalog_service import CatalogService
from crud_generator.ui.cli import Cli


def _config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


class ScriptedIO:
    def __init__(self, inputs: list[str], passwords: list[str]) -> None:
        self._inputs = list(inputs)
        self._passwords = list(passwords)
        self.outputs: list[str] = []

    def read(self, prompt: str) -> str:
        self.outputs.append(prompt)
        return self._inputs.pop(0)

    def write(self, message: str) -> None:
        self.outputs.append(message)

    def read_password(self, prompt: str) -> str:
        self.outputs.append(prompt)
        return self._passwords.pop(0)


def _prepare_clean_product(manager: ConnectionManager) -> None:
    """Revoca privilegios directos y elimina producto_* (solo test dedicado)."""
    conn = manager.connect()
    with conn.cursor() as cur:
        cur.execute("REVOKE ALL ON TABLE lab.producto FROM crud_vendedor")
        cur.execute("REVOKE USAGE ON SCHEMA lab FROM crud_vendedor")
        cur.execute(
            "SELECT p.oid::regprocedure FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'lab' AND p.proname LIKE 'producto\\_%'"
        )
        routines = [row[0] for row in cur.fetchall()]
        for routine in routines:
            cur.execute(f"DROP PROCEDURE {routine}")
    conn.commit()


def _assert_clean_product(manager: ConnectionManager) -> None:
    conn = manager.connect()
    with conn.cursor() as cur:
        for priv in ("INSERT", "SELECT", "UPDATE", "DELETE"):
            cur.execute(
                "SELECT has_table_privilege(%s, %s, %s)",
                ("crud_vendedor", "lab.producto", priv),
            )
            assert cur.fetchone()[0] is False, f"{priv} directo residual"
        cur.execute(
            "SELECT has_schema_privilege(%s, %s, %s)",
            ("crud_vendedor", "lab", "USAGE"),
        )
        assert cur.fetchone()[0] is False, "USAGE residual"
        cur.execute(
            "SELECT count(*) FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'lab' AND p.proname LIKE 'producto\\_%'"
        )
        assert cur.fetchone()[0] == 0, "producto_* residuales"
    if not conn.autocommit:
        conn.rollback()


@pytest.mark.integration
def test_real_flow_lab_producto() -> None:
    if os.getenv("CRUDGEN_TEST_POSTGRES") != "1":
        pytest.skip("Requiere CRUDGEN_TEST_POSTGRES=1 y un PostgreSQL accesible.")
    config = _config_from_env()
    with ConnectionManager(config) as manager:
        catalog = CatalogService(manager)
        schemas = [s.name for s in catalog.list_schemas()]
        if "lab" not in schemas:
            pytest.skip("Sin esquema lab: laboratorio real no preparado.")
        schema_choice = str(schemas.index("lab") + 1)
        tables = [t.name for t in catalog.list_tables("lab")]
        if "producto" not in tables:
            pytest.skip("Sin lab.producto: laboratorio real no preparado.")
        table_choice = str(tables.index("producto") + 1)
        roles = [r.name for r in catalog.list_roles()]
        if "crud_vendedor" not in roles:
            pytest.skip("Sin rol crud_vendedor: laboratorio real no preparado.")
        role_choice = str(roles.index("crud_vendedor") + 1)
        _prepare_clean_product(manager)
        _assert_clean_product(manager)

    io = ScriptedIO(
        [
            config.host,
            str(config.port),
            config.database,
            config.user,
            schema_choice,
            table_choice,
            "a",  # INSERT + READ + UPDATE + DELETE
            "s",  # do_replace=True (repetible)
            role_choice,
            "s",  # INSERT=True
            "s",  # READ=True
            "n",  # UPDATE=False
            "n",  # DELETE=False
            "s",  # verificar permisos con probe real
            "n",  # no ejecutar operaciones con valores
        ],
        [config.password],
    )
    cli = Cli(read=io.read, write=io.write, read_password=io.read_password)
    flow = ApplicationFlow(cli)

    assert flow.run() == EXIT_OK
    text = "\n".join(io.outputs)
    assert "producto_insertar" in text
    assert "producto_eliminar" in text
    assert "Privilegios aplicados para producto" in text
    assert "Verificación de permisos" in text
    assert "OK crud_vendedor INSERT" in text
    assert "OK crud_vendedor READ" in text

    with ConnectionManager(_config_from_env()) as manager:
        conn = manager.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT has_schema_privilege(%s, %s, %s)",
                ("crud_vendedor", "lab", "USAGE"),
            )
            assert cur.fetchone()[0] is True
            for priv, expected in (
                ("INSERT", True),
                ("SELECT", True),
                ("UPDATE", False),
                ("DELETE", False),
            ):
                cur.execute(
                    "SELECT has_table_privilege(%s, %s, %s)",
                    ("crud_vendedor", "lab.producto", priv),
                )
                assert cur.fetchone()[0] is expected, priv
            for routine, expected in (
                ("lab.producto_insertar(integer, text, numeric)", True),
                ("lab.producto_consultar(integer, text, numeric)", True),
                ("lab.producto_actualizar(integer, text, numeric)", False),
                ("lab.producto_eliminar(integer)", False),
            ):
                cur.execute(
                    "SELECT has_function_privilege(%s, %s, %s)",
                    ("crud_vendedor", routine, "EXECUTE"),
                )
                assert cur.fetchone()[0] is expected, routine
            cur.execute(
                "SELECT p.proname, r.rolname, p.prosecdef "
                "FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "JOIN pg_roles r ON r.oid = p.proowner "
                "WHERE n.nspname = 'lab' AND p.proname LIKE 'producto\\_%' "
                "ORDER BY p.proname"
            )
            ownership = cur.fetchall()
            assert [row[0] for row in ownership] == [
                "producto_actualizar",
                "producto_consultar",
                "producto_eliminar",
                "producto_insertar",
            ]
            for _name, owner, secdef in ownership:
                assert owner == "crud_admin", f"owner={owner}"
                assert secdef is False
        if not conn.autocommit:
            conn.rollback()
    # Esta prueba solo opera sobre lab.producto, jamás tabla_virgen.
