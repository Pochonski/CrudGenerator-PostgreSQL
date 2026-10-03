-- tests/integration/01_checklist.sql
-- Fase 0 — Checklist pre-integración (Joseph). Solo LEE estado, no modifica.
-- Cada bloque devuelve NOTICE OK / PENDIENTE para saber qué falta de Joyce/Armando.

-- INT-01: extensión crud_generator disponible (Joyce, contrato cerrado CONTRACTS.md §3)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'crud_generator') THEN
    RAISE NOTICE 'INT-01 OK: extensión crud_generator instalada';
  ELSE
    RAISE NOTICE 'INT-01 PENDIENTE: extensión no instalada en esta base (instalar según extension/README.md)';
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

-- INT-07: fixtures PK compuesta presentes (detalle_factura_*, reemplazables por Joyce)
DO $$
BEGIN
  IF (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='lab' AND p.proname IN
        ('detalle_factura_insertar','detalle_factura_consultar',
         'detalle_factura_actualizar','detalle_factura_eliminar')) = 4 THEN
    RAISE NOTICE 'INT-07 OK: fixtures lab.detalle_factura_* presentes';
  ELSE RAISE NOTICE 'INT-07 FALLO: ejecutar fixtures/06_composite_pk_fixtures.sql'; END IF;
END $$;

-- INT-08: EXECUTE matriz compuesta (vendedor→insertar sí, →eliminar no)
SELECT 'INT-08 vendedor EXECUTE insertar=' ||
  has_function_privilege('crud_vendedor',
    'lab.detalle_factura_insertar(integer,integer,integer)', 'EXECUTE')::text ||
  ' / eliminar=' ||
  has_function_privilege('crud_vendedor',
    'lab.detalle_factura_eliminar(integer,integer)', 'EXECUTE')::text AS int08;

-- INT-09: owner de fixtures compuestos es crud_admin (trazabilidad CR-JOYCE-005)
SELECT 'INT-09 owner detalle_factura_insertar=' ||
  (SELECT r.rolname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     JOIN pg_roles r ON r.oid=p.proowner
   WHERE n.nspname='lab' AND p.proname='detalle_factura_insertar'
   LIMIT 1) AS int09;

-- INT-10: auditoría T3 conforme sobre los 8 fixtures (owner+INVOKER+search_path);
-- detalle por procedure en security/05_audit_ownership.sql (AUD-01..05)
SELECT 'INT-10 fixtures conformes=' || count(*)::text || '/8' AS int10
FROM (VALUES
  ('producto_insertar', 'integer, text, numeric'),
  ('producto_consultar', 'integer, text, numeric'),
  ('producto_actualizar', 'integer, text, numeric'),
  ('producto_eliminar', 'integer'),
  ('detalle_factura_insertar', 'integer, integer, integer'),
  ('detalle_factura_consultar', 'integer, integer, integer'),
  ('detalle_factura_actualizar', 'integer, integer, integer'),
  ('detalle_factura_eliminar', 'integer, integer')
) AS e(proc_name, sig)
JOIN pg_namespace n ON n.nspname = 'lab'
JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
     AND replace(p.oid::regprocedure::text, ' ', '')
       = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
JOIN pg_roles r ON r.oid = p.proowner
WHERE r.rolname = 'crud_admin' AND p.prosecdef = false
  AND EXISTS (SELECT 1 FROM unnest(p.proconfig) AS c WHERE trim(c) = 'search_path=lab, pg_temp');

-- INT-11: higiene T4 — PUBLIC sin EXECUTE en los 8 fixtures;
-- detalle en security/06_revoke_public_audit.sql (PUB-01/02/03, REV-01)
SELECT 'INT-11 fugas PUBLIC=' || count(*)::text || '/8 (esperado 0)' AS int11
FROM (VALUES
  ('producto_insertar', 'integer, text, numeric'),
  ('producto_consultar', 'integer, text, numeric'),
  ('producto_actualizar', 'integer, text, numeric'),
  ('producto_eliminar', 'integer'),
  ('detalle_factura_insertar', 'integer, integer, integer'),
  ('detalle_factura_consultar', 'integer, integer, integer'),
  ('detalle_factura_actualizar', 'integer, integer, integer'),
  ('detalle_factura_eliminar', 'integer, integer')
) AS e(proc_name, sig)
JOIN pg_namespace n ON n.nspname = 'lab'
JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
     AND replace(p.oid::regprocedure::text, ' ', '')
       = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
WHERE (p.proacl IS NULL OR p.proacl::text LIKE '{=X/%'
    OR p.proacl::text LIKE '%,=X/%');

-- INT-12: rutinas T2 presentes (ticket_*, IDENTITY/DEFAULT; fixtures 07 o reales).
-- Solo verifica nombres (las firmas difieren por modo, ver 07 vs 11).
DO $$
BEGIN
  IF (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='lab' AND p.proname IN
        ('ticket_insertar','ticket_consultar',
         'ticket_actualizar','ticket_eliminar')) = 4 THEN
    RAISE NOTICE 'INT-12 OK: lab.ticket_* presentes (fixtures o reales)';
  ELSE RAISE NOTICE 'INT-12 FAIL: generar ticket_* (fixtures/07 o generate_crud)'; END IF;
END $$;

-- INT-13: EXECUTE matriz ticket (vendedor→insertar sí, →eliminar no) + owner crud_admin.
-- Bimodal (fixtures o reales): resuelve por oid/nombre, no por firma textual
-- (fixture `insertar(integer,text,timestamptz)` vs real `insertar(text,timestamptz)`).
SELECT 'INT-13 vendedor EXECUTE insertar=' ||
  has_function_privilege('crud_vendedor',
    (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='lab' AND p.proname='ticket_insertar'), 'EXECUTE')::text ||
  ' / eliminar=' ||
  has_function_privilege('crud_vendedor',
    (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='lab' AND p.proname='ticket_eliminar'), 'EXECUTE')::text ||
  ' / owner=' ||
  (SELECT r.rolname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     JOIN pg_roles r ON r.oid=p.proowner
   WHERE n.nspname='lab' AND p.proname='ticket_insertar'
   LIMIT 1) AS int13;

-- INT-15: rutinas T6 presentes — bimodal: fixtures (`bitacora_contar`) o reales
-- (`bitacora_consultar` refcursor). Catalogo_especial tiene los mismos 4 nombres
-- en ambos modos.
DO $$
DECLARE
  v_cat integer;
  v_bitc integer;
BEGIN
  SELECT count(*) INTO v_cat FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='lab' AND p.proname IN
    ('catalogo_especial_insertar','catalogo_especial_consultar',
     'catalogo_especial_actualizar','catalogo_especial_eliminar');
  SELECT count(*) INTO v_bitc FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='lab' AND p.proname IN ('bitacora_insertar')
    AND EXISTS (SELECT 1 FROM pg_proc q JOIN pg_namespace m ON m.oid=q.pronamespace
                WHERE m.nspname='lab'
                  AND q.proname IN ('bitacora_contar','bitacora_consultar'));
  IF v_cat = 4 AND v_bitc = 1 THEN
    RAISE NOTICE 'INT-15 OK: T6 presentes (4 especiales + bitacora insertar+lectura)';
  ELSE
    RAISE NOTICE 'INT-15 FAIL: cat=%/4 bitacora=%/1 (fixtures 08 o reales generate_crud)', v_cat, v_bitc;
  END IF;
END $$;

-- INT-16: EXECUTE matriz T6 (vendedor→insertar sí, →eliminar no) + sin actualizar
-- sin PK. Bimodal por oid (el insertar real reordena params pero conserva el nombre).
SELECT 'INT-16 vendedor EXECUTE insertar=' ||
  has_function_privilege('crud_vendedor',
    (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='lab' AND p.proname='catalogo_especial_insertar'), 'EXECUTE')::text ||
  ' / eliminar=' ||
  has_function_privilege('crud_vendedor',
    (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='lab' AND p.proname='catalogo_especial_eliminar'), 'EXECUTE')::text ||
  ' / bitacora_actualizar_existe=' ||
  (SELECT count(*)::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname='lab' AND p.proname='bitacora_actualizar') AS int16;

-- INT-14: T5 autocontenida — cero residuos dyn_* (sonda, seguros y señuelo
-- se eliminan en la propia prueba); detalle en security/08_dynamic_sql_audit.sql
SELECT 'INT-14 residuos dyn_*=' || count(*)::text || ' (esperado 0)' AS int14
FROM (
  SELECT p.proname AS n FROM pg_proc p JOIN pg_namespace s ON s.oid = p.pronamespace
  WHERE s.nspname = 'lab' AND p.proname LIKE 'dyn\_%'
  UNION ALL
  SELECT c.relname FROM pg_class c JOIN pg_namespace s ON s.oid = c.relnamespace
  WHERE s.nspname = 'lab' AND c.relname LIKE 'dyn\_%'
) AS r;
