-- tests/fixtures/05_grants_template.sql
-- Fase A — PLANTILLA de grants parametrizada (Joseph).
-- Mapea la matriz vendedor/supervisor/administrador sobre una tabla T generada según
-- ADR-007 (`<tabla>_insertar|consultar|actualizar|eliminar`) y ADR-011 (INVOKER).
--
-- ⚠️  PLANTILLA: sustituir <SCHEMA>, <tabla>, y las firmas (...) por los valores reales
-- cuando Joyce entregue la convención definitiva (CR-JOYCE-002). Nada de esto se ejecuta
-- tal cual; es la especificación que reemplazará a fixtures/04_grants.sql en integración.
--
-- Bajo hipótesis INVOKER (ADR-011): DOBLE LLAVE = EXECUTE sobre cada procedure
-- + permisos sobre la tabla. Incluye al final la variante DEFINER comentada.
--
-- Uso: sustituye <SCHEMA>, <tabla> y <firma_*> por los valores reales (por ejemplo
-- lab, producto y las firmas `integer, text, numeric` del fixture), y ejecuta solo
-- cuando existan los procedures. No es un script autónomo: es la especificación
-- operativa de la matriz.

-- 0) Higiene: revocar default público
REVOKE ALL ON SCHEMA <SCHEMA> FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA <SCHEMA> FROM PUBLIC;
REVOKE ALL ON ALL ROUTINES IN SCHEMA <SCHEMA> FROM PUBLIC;

-- 1) USAGE sobre el esquema para los tres roles de negocio
GRANT USAGE ON SCHEMA <SCHEMA>
  TO crud_vendedor, crud_supervisor, crud_administrador;

-- 2) EXECUTE selectivo sobre los 4 procedures (ADR-007) — sustituir firmas reales
GRANT EXECUTE ON PROCEDURE <SCHEMA>.<tabla>_insertar(<firma_insert>)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE <SCHEMA>.<tabla>_consultar(<firma_consultar>)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE <SCHEMA>.<tabla>_actualizar(<firma_actualizar>)
  TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE <SCHEMA>.<tabla>_eliminar(<firma_eliminar>)
  TO crud_administrador;

-- 3) Permisos de tabla (llave 2, solo bajo INVOKER)
GRANT SELECT, INSERT                 ON <SCHEMA>.<tabla> TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON <SCHEMA>.<tabla> TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON <SCHEMA>.<tabla> TO crud_administrador;

-- 4) Tablas sin PK (ADR-009): solo INSERT + READ son aplicables;
--    el resto se reporta "no aplicable" (CR-JOYCE-003). No se otorgan
--    EXECUTE ni permisos de UPDATE/DELETE en ese caso.

-- ============================================================
-- VARIANTE DEFINER (SOLO si el equipo votara lo contrario de ADR-011)
-- Cambiaría la llave 2: revocar tablas a negocio y dejar solo EXECUTE.
-- ============================================================
-- REVOKE ALL ON <SCHEMA>.<tabla> FROM crud_vendedor, crud_supervisor, crud_administrador;
-- GRANT EXECUTE ON PROCEDURE ... (idéntico a bloque 2, sin bloque 3).
-- ⚠️ Requiere que la extensión fije SECURITY DEFINER + search_path explícito
--    (CR-JOYCE-005) y respeta ADR-011 (decisión global aún pendiente de voto).