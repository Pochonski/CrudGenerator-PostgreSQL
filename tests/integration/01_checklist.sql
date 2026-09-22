-- tests/integration/01_checklist.sql
-- Fase 0 — Checklist pre-integración (Joseph). Solo LEE estado, no modifica.
-- Cada bloque devuelve NOTICE OK / PENDIENTE para saber qué falta de Joyce/Armando.

-- INT-01: extensión crud_generator disponible (Joyce)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'crud_generator') THEN
    RAISE NOTICE 'INT-01 OK: extensión crud_generator instalada';
  ELSE
    RAISE NOTICE 'INT-01 PENDIENTE Joyce: extensión no instalada (CR-JOYCE-001/002)';
  END IF;
END $$;

-- INT-02: fixtures de seguridad presentes
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
             WHERE n.nspname='lab' AND p.proname='producto_insertar') THEN
    RAISE NOTICE 'INT-02 OK: fixtures lab.producto_* presentes';
  ELSE RAISE NOTICE 'INT-02 FALLO: ejecutar fixtures/03_security_fixtures.sql'; END IF;
END $$;

-- INT-03: EXECUTE otorgado según matriz (vendedor→insertar sí, →eliminar no)
SELECT 'INT-03 vendedor EXECUTE insertar=' ||
  has_function_privilege('crud_vendedor',
    'lab.producto_insertar(integer,text,numeric)', 'EXECUTE')::text ||
  ' / eliminar=' ||
  has_function_privilege('crud_vendedor',
    'lab.producto_eliminar(integer)', 'EXECUTE')::text AS int03;

-- INT-04: USAGE sobre lab para los tres roles
SELECT 'INT-04 USAGE lab: vendedor=' || has_schema_privilege('crud_vendedor','lab','USAGE')::text ||
  ' supervisor=' || has_schema_privilege('crud_supervisor','lab','USAGE')::text ||
  ' admin=' || has_schema_privilege('crud_administrador','lab','USAGE')::text AS int04;

-- INT-05: owner de fixtures es crud_admin (trazabilidad CR-JOYCE-005)
SELECT 'INT-05 owner producto_insertar=' ||
  (SELECT r.rolname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
    JOIN pg_roles r ON r.oid=p.proowner
   WHERE n.nspname='lab' AND p.proname='producto_insertar'
   LIMIT 1) AS int05;

-- INT-06: tabla virgen intacta (cero filas, sin grants de negocio)
SELECT 'INT-06 tabla_virgen filas=' || count(*)::text AS int06 FROM lab.tabla_virgen;
SELECT 'INT-06 virgen EXEC/SELECT vendedor=' ||
  has_table_privilege('crud_vendedor','lab.tabla_virgen','SELECT')::text AS int06b;
