-- tests/fixtures/01_roles.sql
-- Fase 0 — Roles de prueba (Joseph).
-- Idempotente. Ejecutar como superuser/postgres o crud_admin.
--
-- Modelo:
--   crud_admin         → owner del lab, único que GENERA (propuesta pendiente Joyce).
--   crud_vendedor      → INSERT + READ
--   crud_supervisor    → INSERT + READ + UPDATE
--   crud_administrador → INSERT + READ + UPDATE + DELETE
-- Roles de negocio NOLOGIN: solo se usan vía SET ROLE en pruebas.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'crud_admin') THEN
    CREATE ROLE crud_admin NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'crud_vendedor') THEN
    CREATE ROLE crud_vendedor NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'crud_supervisor') THEN
    CREATE ROLE crud_supervisor NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'crud_administrador') THEN
    CREATE ROLE crud_administrador NOLOGIN;
  END IF;
END
$$;

-- Esquema de laboratorio, owner crud_admin.
CREATE SCHEMA IF NOT EXISTS lab AUTHORIZATION crud_admin;

-- El owner necesita CREATE+USAGE; el resto solo USAGE (se otorga en 04_grants.sql).
GRANT USAGE, CREATE ON SCHEMA lab TO crud_admin;
