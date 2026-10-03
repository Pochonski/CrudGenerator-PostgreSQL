"""Prueba de integración opcional de PermissionProbeService contra PG real.

No se ejecuta por defecto: requiere ``CRUDGEN_TEST_POSTGRES=1`` y el
laboratorio real de Joseph (roles + ``lab.producto`` + procedures generados
por la extensión + matriz aplicada). Nunca toca ``lab.tabla_virgen``.

Si la sesión actual no puede ``SET ROLE`` sobre los roles de negocio
(típicamente se necesita superusuario), se omite con mensaje claro: eso es
configuración del entorno, no un fallo del servicio.
"""

from __future__ import annotations

import os

import pytest
from psycopg import sql

from crud_generator.config import DatabaseConfig
from crud_generator.db import ConnectionManager
from crud_generator.models import CrudOperation, GenerationResult, GenerationStatus
from crud_generator.privileges import (
    PermissionProbeService,
    PermissionProbeStatus,
    RoleAssumptionError,
)


def _config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


def _result(operation: CrudOperation, routine: str) -> GenerationResult:
    return GenerationResult(
        operation=operation,
        status=GenerationStatus.SUCCESS,
        schema_name="lab",
        routine_name=routine,
        identity_arguments=None,
        message="fila sintética para probe real",
        sqlstate=None,
    )


def _lab_ready(manager: ConnectionManager) -> str | None:
    """Retorna mensaje de skip si el laboratorio real no está preparado."""
    conn = manager.connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", ("crud_vendedor",)
        )
        if cur.fetchone() is None:
            return "Sin rol crud_vendedor: laboratorio real no preparado."
        cur.execute(
            "SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s",
            ("lab", "producto"),
        )
        if cur.fetchone() is None:
            return "Sin lab.producto: laboratorio real no preparado."
        cur.execute(
            "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = %s AND p.proname = %s AND p.prokind = 'p'",
            ("lab", "producto_insertar"),
        )
        if cur.fetchone() is None:
            return "Sin lab.producto_insertar real: genere primero con generate_crud."
        cur.execute(
            "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = %s AND p.proname = %s AND p.prokind = 'p'",
            ("lab", "producto_eliminar"),
        )
        if cur.fetchone() is None:
            return "Sin lab.producto_eliminar real: genere primero con generate_crud."
    if not conn.autocommit:
        conn.rollback()
    return None


@pytest.mark.integration
def test_probe_allowed_and_denied_against_real_lab() -> None:
    if os.getenv("CRUDGEN_TEST_POSTGRES") != "1":
        pytest.skip("Requiere CRUDGEN_TEST_POSTGRES=1 y un PostgreSQL accesible.")
    with ConnectionManager(_config_from_env()) as manager:
        skip_reason = _lab_ready(manager)
        if skip_reason is not None:
            pytest.skip(skip_reason)
        probe = PermissionProbeService(manager)
        conn = manager.connect()
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COALESCE(MAX({}), 0) FROM {}.{}").format(
                    sql.Identifier("id_producto"),
                    sql.Identifier("lab"),
                    sql.Identifier("producto"),
                )
            )
            max_id = int(cur.fetchone()[0])
        if not conn.autocommit:
            conn.rollback()
        temp_id = max_id + 100000

        try:
            allowed = probe.probe(
                "crud_vendedor",
                _result(CrudOperation.INSERT, "producto_insertar"),
                (temp_id, "ProbeTmp", "1.00"),
            )
        except RoleAssumptionError:
            pytest.skip(
                "PGUSER actual no puede SET ROLE crud_vendedor: ejecute como "
                "superusuario o usuario con capacidad SET sobre el rol."
            )
        assert allowed.status is PermissionProbeStatus.ALLOWED

        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM lab.producto WHERE id_producto = %s", (temp_id,)
            )
            assert cur.fetchone() is None, (
                "El INSERT del probe persistió: force_rollback no funcionó."
            )
        if not conn.autocommit:
            conn.rollback()

        denied = probe.probe(
            "crud_vendedor",
            _result(CrudOperation.DELETE, "producto_eliminar"),
            (temp_id,),
        )
        assert denied.status is PermissionProbeStatus.DENIED
        assert denied.sqlstate == "42501"
    # Nunca se tocó lab.tabla_virgen en esta prueba.
