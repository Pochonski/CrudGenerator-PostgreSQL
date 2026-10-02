-- tests/security/13_conflict_real_matrix.sql
-- NEG-06R — Política de procedures existentes contra la extensión REAL (Joseph).
-- Cierra CR-JOYCE-004 / ADR-010 con evidencia ejecutable:
--   * generate_crud sin flag ante rutinas existentes → status='procedure_conflict',
--     sin tocar rutinas ni GRANTs.
--   * generate_crud con do_replace=true → success vía CREATE OR REPLACE,
--     preservando los GRANT EXECUTE ya otorgados.
--
-- MODO REALES (no corre en CI con fixtures):
--   1. tests/fixtures/01_roles.sql + 02_schema.sql
--   2. generate_crud('lab','producto', 4 ops) como crud_admin + 04_grants.sql
-- Usa lab.producto (PK simple) como tabla de prueba. Idempotente: termina con
-- las rutinas regeneradas y los grants originales intactos. NO toca tabla_virgen.

-- CONF-00 | precondición: las 4 rutinas de producto existen y tienen GRANTs.
DO $$
DECLARE
  v_n integer;
BEGIN
  SELECT count(*) INTO v_n
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname IN
    ('producto_insertar','producto_consultar',
     'producto_actualizar','producto_eliminar');
  IF v_n = 4 THEN
    RAISE NOTICE 'CONF-00 OK: 4 rutinas lab.producto_* presentes';
  ELSE
    RAISE NOTICE 'CONF-00 FAIL: hay %/4 rutinas (generar primero)', v_n;
  END IF;
END $$;

-- CONF-01 | regenerar sin flag → procedure_conflict en las 4, nada modificado.
SET ROLE crud_admin;
DO $$
DECLARE
  r RECORD;
  v_conflict integer := 0;
  v_total integer := 0;
BEGIN
  FOR r IN
    SELECT operation, status FROM crud_generator.generate_crud('lab','producto',
      ARRAY['INSERT','READ','UPDATE','DELETE'], false)
  LOOP
    v_total := v_total + 1;
    IF r.status = 'procedure_conflict' THEN v_conflict := v_conflict + 1; END IF;
  END LOOP;
  IF v_total = 4 AND v_conflict = 4 THEN
    RAISE NOTICE 'CONF-01 OK: 4/4 procedure_conflict sin flag (nada tocado)';
  ELSE
    RAISE NOTICE 'CONF-01 FAIL: total=% conflict=% (esperado 4/4)', v_total, v_conflict;
  END IF;
END $$;
RESET ROLE;

-- CONF-02 | tras el conflicto, los GRANTs siguen intactos (matriz 04_grants).
SELECT 'CONF-02 vendedor EXECUTE insertar=' ||
  has_function_privilege('crud_vendedor',
    'lab.producto_insertar(integer,text,numeric)', 'EXECUTE')::text ||
  ' / eliminar=' ||
  has_function_privilege('crud_vendedor',
    'lab.producto_eliminar(integer)', 'EXECUTE')::text ||
  ' (esperado t/f)' AS conf02;

-- CONF-03 | con do_replace=true → success en las 4 (CREATE OR REPLACE).
SET ROLE crud_admin;
DO $$
DECLARE
  r RECORD;
  v_ok integer := 0;
  v_total integer := 0;
BEGIN
  FOR r IN
    SELECT operation, status FROM crud_generator.generate_crud('lab','producto',
      ARRAY['INSERT','READ','UPDATE','DELETE'], true)
  LOOP
    v_total := v_total + 1;
    IF r.status = 'success' THEN v_ok := v_ok + 1; END IF;
  END LOOP;
  IF v_total = 4 AND v_ok = 4 THEN
    RAISE NOTICE 'CONF-03 OK: 4/4 success con do_replace=true';
  ELSE
    RAISE NOTICE 'CONF-03 FAIL: total=% ok=% (esperado 4/4)', v_total, v_ok;
  END IF;
END $$;
RESET ROLE;

-- CONF-04 | tras el reemplazo, los GRANTs sobrevivieron (sin re-otorgar).
-- Si fuera DROP+CREATE, el ACL se habría perdido: la prueba lo detectaría.
DO $$
DECLARE
  v_sup boolean;
  v_adm boolean;
  v_ven_insert boolean;
  v_ven_del boolean;
BEGIN
  SELECT has_function_privilege('crud_supervisor',
      'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE') INTO v_sup;
  SELECT has_function_privilege('crud_administrador',
      'lab.producto_eliminar(integer)', 'EXECUTE') INTO v_adm;
  SELECT has_function_privilege('crud_vendedor',
      'lab.producto_insertar(integer,text,numeric)', 'EXECUTE') INTO v_ven_insert;
  SELECT has_function_privilege('crud_vendedor',
      'lab.producto_eliminar(integer)', 'EXECUTE') INTO v_ven_del;
  IF v_sup AND v_adm AND v_ven_insert AND NOT v_ven_del THEN
    RAISE NOTICE 'CONF-04 OK: GRANTs preservados tras do_replace (matriz intacta)';
  ELSE
    RAISE NOTICE 'CONF-04 FAIL: sup=% adm=% ven_ins=% ven_del=% (esperado t/t/t/f)',
      v_sup, v_adm, v_ven_insert, v_ven_del;
  END IF;
END $$;

-- CONF-05 | comportamiento: vendedor INSERT+READ siguen funcionando tras reemplazar.
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer := 801;
  v_nom text;
  v_pre numeric;
BEGIN
  CALL lab.producto_insertar(801, 'ConfOK', 5.00);
  CALL lab.producto_consultar(v_id, v_nom, v_pre);
  IF v_nom = 'ConfOK' AND v_pre = 5.00 THEN
    RAISE NOTICE 'CONF-05 OK: CALL funciona tras do_replace (nombre=% precio=%)', v_nom, v_pre;
  ELSE
    RAISE NOTICE 'CONF-05 FAIL: nom=% pre=%', v_nom, v_pre;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'CONF-05 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Limpieza (como owner; fila 801 reservada de este archivo)
SET ROLE crud_admin;
DELETE FROM lab.producto WHERE id_producto = 801;
RESET ROLE;
