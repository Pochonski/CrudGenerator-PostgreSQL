-- tests/security/11_ticket_real_matrix.sql
-- T2R — Matriz IDENTITY/DEFAULT contra PROCEDURES REALES de la extensión (Joseph).
-- Caso 3 §9 con el generador real: lab.ticket (id_ticket GENERATED ALWAYS AS
-- IDENTITY + DEFAULTs en codigo/creado_en).
--
-- DIFERENCIA con 07_ticket_matrix.sql (fixtures): el `insertar` REAL es
--   lab.ticket_insertar(IN codigo text, IN creado_en timestamptz)
-- (sin parámetro de id: GENERATED ALWAYS se omite; NULL ⇒ DEFAULT de la tabla).
-- `consultar/actualizar` llevan la PK como INOUT/IN y `actualizar` exige los 3
-- valores (creado_en es NOT NULL: hay que pasar el ts vigente, no NULL).
--
-- MODO REALES (no corre en CI con fixtures):
--   1. tests/fixtures/01_roles.sql + 02_schema.sql
--   2. SET ROLE crud_admin + generate_crud('lab','ticket', 4 ops) + grants reales
--      (plantilla 05 con firmas de CONTRACTS.md §3.2 / handoff §2.4)
-- NO requiere 07_ticket_fixtures.sql. NO toca tabla_virgen.
-- Filas marcadas con codigo LIKE 'TIXR-%' (disjunto de 'TIX-%' de 07).
-- Cada bloque deja constancia en RAISE NOTICE. Idempotente.
--
-- Convenciones: OK → success; denegado → 42501; inexistente → P0002.

-- TIXR-00 | catálogo: identity + defaults reales en lab.ticket (igual que TIX-00)
DO $$
DECLARE
  v_ident char;
  v_def_cod integer;
  v_def_ts integer;
BEGIN
  SELECT a.attidentity INTO v_ident
  FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'lab' AND c.relname = 'ticket' AND a.attname = 'id_ticket';
  SELECT count(*) INTO v_def_cod FROM information_schema.columns
  WHERE table_schema = 'lab' AND table_name = 'ticket' AND column_name = 'codigo'
    AND column_default IS NOT NULL;
  SELECT count(*) INTO v_def_ts FROM information_schema.columns
  WHERE table_schema = 'lab' AND table_name = 'ticket' AND column_name = 'creado_en'
    AND column_default IS NOT NULL;
  IF v_ident = 'a' AND v_def_cod = 1 AND v_def_ts = 1 THEN
    RAISE NOTICE 'TIXR-00 OK: id_ticket GENERATED ALWAYS + DEFAULTs en codigo/creado_en';
  ELSE
    RAISE NOTICE 'TIXR-00 FAIL: identity=% def_cod=% def_ts=% (esperado a/1/1)',
      v_ident, v_def_cod, v_def_ts;
  END IF;
END $$;

-- Preparación (como owner): limpieza + fila setup TIXR-T3 (insert real, sin id).
SET ROLE crud_admin;
DELETE FROM lab.ticket WHERE codigo LIKE 'TIXR-%';
SELECT * FROM crud_generator.generate_crud('lab','ticket',
  ARRAY['INSERT','READ','UPDATE','DELETE'], true);
CALL lab.ticket_insertar('TIXR-T3', NULL);
RESET ROLE;

-- MAT-T1R | vendedor → INSERT real (codigo explícito, creado_en omitido) → SUCCESS
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_ts timestamptz;
  v_cod text;
BEGIN
  CALL lab.ticket_insertar('TIXR-T1', NULL);
  SELECT t.id_ticket, t.creado_en, t.codigo INTO v_id, v_ts, v_cod
  FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T1';
  IF v_id IS NOT NULL AND v_ts IS NOT NULL AND v_cod = 'TIXR-T1' THEN
    RAISE NOTICE 'MAT-T1R OK: vendedor INSERT real id_generado=% creado_en=%', v_id, v_ts;
  ELSE
    RAISE NOTICE 'MAT-T1R FAIL: id=% ts=% cod=%', v_id, v_ts, v_cod;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T1R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T2R | vendedor → READ por PK (INOUT) → SUCCESS round-trip
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
  v_ts2 timestamptz;
BEGIN
  CALL lab.ticket_insertar('TIXR-T2', NULL);
  SELECT t.id_ticket, t.creado_en INTO v_id, v_ts
  FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T2';
  CALL lab.ticket_consultar(v_id, v_cod, v_ts2);
  IF v_cod = 'TIXR-T2' AND v_ts2 = v_ts THEN
    RAISE NOTICE 'MAT-T2R OK: vendedor READ real devuelve codigo=% (id=%)', v_cod, v_id;
  ELSE
    RAISE NOTICE 'MAT-T2R FAIL: codigo=% ts=% (esperado TIXR-T2/%)', v_cod, v_ts2, v_ts;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T2R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T3R | vendedor → UPDATE denegado → 42501 (firma real de 3 params)
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T3';
  CALL lab.ticket_actualizar(v_id, 'TIXR-HACK', now());
  RAISE NOTICE 'MAT-T3R FAIL: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T3R OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T3R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T4R | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T3';
  CALL lab.ticket_eliminar(v_id);
  RAISE NOTICE 'MAT-T4R FAIL: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T4R OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T4R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T5R | supervisor → UPDATE permitido → SUCCESS (con ts vigente, NOT NULL)
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
BEGIN
  SELECT t.id_ticket, t.creado_en INTO v_id, v_ts
  FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T3';
  CALL lab.ticket_actualizar(v_id, 'TIXR-T3U', v_ts);
  CALL lab.ticket_consultar(v_id, v_cod, v_ts);
  IF v_cod = 'TIXR-T3U' THEN
    RAISE NOTICE 'MAT-T5R OK: supervisor UPDATE real funciona (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-T5R FAIL: codigo=% tras UPDATE (esperado TIXR-T3U)', v_cod;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T5R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T6R | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T3U';
  CALL lab.ticket_eliminar(v_id);
  RAISE NOTICE 'MAT-T6R FAIL: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T6R OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T6R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T7R | administrador → DELETE permitido → SUCCESS (P0002 después)
SET ROLE crud_administrador;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T3U';
  CALL lab.ticket_eliminar(v_id);
  BEGIN
    CALL lab.ticket_consultar(v_id, v_cod, v_ts);
    RAISE NOTICE 'MAT-T7R FAIL: la fila debió desaparecer tras DELETE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = 'P0002' THEN
      RAISE NOTICE 'MAT-T7R OK: administrador DELETE cierra el ciclo (P0002)';
    ELSE
      RAISE NOTICE 'MAT-T7R resultado distinto al verificar: % %', SQLSTATE, SQLERRM;
    END IF;
  END;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T7R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T8R | DEFAULT manda en creado_en: NULL ⇒ now() del esquema (no hardcodeado).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_ts timestamptz;
BEGIN
  CALL lab.ticket_insertar('TIXR-T8', NULL);
  SELECT t.creado_en INTO v_ts FROM lab.ticket AS t WHERE t.codigo = 'TIXR-T8';
  IF v_ts IS NOT NULL THEN
    RAISE NOTICE 'MAT-T8R OK: DEFAULT aplicado creado_en=%', v_ts;
  ELSE
    RAISE NOTICE 'MAT-T8R FAIL: creado_en nulo (DEFAULT debió aplicar)';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T8R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T9R | DEFAULT manda en codigo: NULL ⇒ 'SIN-CODIGO' del esquema.
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
BEGIN
  CALL lab.ticket_insertar(NULL, NULL);
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t
  WHERE t.codigo = 'SIN-CODIGO'
  ORDER BY t.id_ticket DESC LIMIT 1;
  CALL lab.ticket_consultar(v_id, v_cod, v_ts);
  IF v_cod = 'SIN-CODIGO' AND v_ts IS NOT NULL THEN
    RAISE NOTICE 'MAT-T9R OK: DEFAULT aplicado codigo=% (id=%)', v_cod, v_id;
  ELSE
    RAISE NOTICE 'MAT-T9R FAIL: codigo=% ts=% (esperado SIN-CODIGO/no-nulo)', v_cod, v_ts;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T9R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- TIXR-AUD | auto-auditoría (owner/INVOKER/search_path/PUBLIC) de los 4 REALES.
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
  v_total integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.reg, rol.rolname AS ownername, p.prosecdef,
           p.proconfig, p.proacl
    FROM (VALUES
      ('ticket_insertar', 'lab.ticket_insertar(text,timestamp with time zone)'),
      ('ticket_consultar', 'lab.ticket_consultar(integer,text,timestamp with time zone)'),
      ('ticket_actualizar', 'lab.ticket_actualizar(integer,text,timestamp with time zone)'),
      ('ticket_eliminar', 'lab.ticket_eliminar(integer)')
    ) AS e(proc_name, reg)
    JOIN pg_namespace n ON n.nspname = 'lab'
    JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '') = replace(e.reg, ' ', '')
    JOIN pg_roles rol ON rol.oid = p.proowner
  LOOP
    v_total := v_total + 1;
    IF r.ownername <> 'crud_admin' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIXR-AUD FAIL: % owner=% (esperado crud_admin)', r.reg, r.ownername;
    ELSIF r.prosecdef THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIXR-AUD FAIL: % SECURITY DEFINER (esperado INVOKER)', r.reg;
    ELSIF NOT EXISTS (SELECT 1 FROM unnest(r.proconfig) AS c
                      WHERE trim(c) = 'search_path=lab, pg_temp') THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIXR-AUD FAIL: % search_path=[%] (esperado lab, pg_temp)',
        r.reg, COALESCE(array_to_string(r.proconfig, ' | '), '(sin proconfig)');
    ELSIF r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
       OR r.proacl::text LIKE '%,=X/%' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIXR-AUD FAIL: % fuga EXECUTE a PUBLIC', r.reg;
    ELSE
      RAISE NOTICE 'TIXR-AUD OK: % owner+INVOKER+search_path+PUBLIC conformes', r.reg;
    END IF;
  END LOOP;
  IF v_fail > 0 OR v_total <> 4 THEN
    RAISE NOTICE 'TIXR-AUD RESULTADO: % procedure(s) no conformes, % auditados (esperado 4)',
      v_fail, v_total;
  ELSE
    RAISE NOTICE 'TIXR-AUD RESULTADO: 4/4 conformes';
  END IF;
END $$;

-- Limpieza (como owner; rastros TIXR-* y el SIN-CODIGO de MAT-T9R desaparecen)
SET ROLE crud_admin;
DELETE FROM lab.ticket WHERE codigo LIKE 'TIXR-%';
DELETE FROM lab.ticket WHERE codigo = 'SIN-CODIGO';
RESET ROLE;
