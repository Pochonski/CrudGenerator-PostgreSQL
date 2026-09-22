-- tests/fixtures/04_grants.sql
-- Fase 0 — Matriz GRANT/REVOKE hipótesis SECURITY INVOKER (Joseph).
-- Dos llaves bajo INVOKER: EXECUTE sobre procedure + permiso sobre tabla.
-- Requiere: 03_security_fixtures.sql. Ejecutar como owner (crud_admin o postgres).

SET ROLE crud_admin;

-- 0) Higiene: nadie hereda nada por defecto
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL ROUTINES IN SCHEMA lab FROM PUBLIC;
REVOKE ALL ON SCHEMA lab FROM crud_vendedor, crud_supervisor, crud_administrador;
REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM crud_vendedor, crud_supervisor, crud_administrador;
REVOKE ALL ON ALL ROUTINES IN SCHEMA lab FROM crud_vendedor, crud_supervisor, crud_administrador;

-- 1) USAGE para calificar objetos (los tres roles)
GRANT USAGE ON SCHEMA lab TO crud_vendedor, crud_supervisor, crud_administrador;

-- 2) EXECUTE selectivo sobre fixtures de lab.producto
GRANT EXECUTE ON PROCEDURE lab.producto_insertar(integer, text, numeric)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.producto_consultar(integer, text, numeric)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.producto_actualizar(integer, text, numeric)
  TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.producto_eliminar(integer)
  TO crud_administrador;

-- 3) Permisos de tabla (llave 2 bajo INVOKER)
GRANT SELECT, INSERT                 ON lab.producto TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON lab.producto TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.producto TO crud_administrador;

-- 4) Resto del lab: sin acceso por defecto (las pruebas lo abren según necesiten)
--    lab.tabla_virgen queda sin grants de negocio a propósito.

RESET ROLE;
