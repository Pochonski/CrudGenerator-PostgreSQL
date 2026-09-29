-- tests/security/07_ticket_matrix.sql
-- T2 — Matriz IDENTITY/DEFAULT permitido vs denegado (Joseph). Caso 3 §9.
-- Verifica EXECUTE+tabla reales con SET ROLE + CALL sobre los fixtures de
-- lab.ticket (id_ticket GENERATED ALWAYS AS IDENTITY + DEFAULTs).
-- Esperado OK → success; esperado DENEGADO → SQLSTATE 42501;
-- fila inexistente → SQLSTATE P0002; valor explícito en identity → 428C9.
-- Requiere: fixtures/07_ticket_fixtures.sql. Cada bloque deja constancia en NOTICE.
-- Filas de prueba marcadas con codigo LIKE 'TIX-%' (los ids los genera PG).
-- Limpieza como crud_admin al inicio (idempotencia) y al final.
-- NO toca tabla_virgen.

-- TIX-00 | catálogo: identity + defaults reales en lab.ticket
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
    RAISE NOTICE 'TIX-00 OK: id_ticket GENERATED ALWAYS + DEFAULTs en codigo/creado_en';
  ELSE
    RAISE NOTICE 'TIX-00 FAIL: identity=% def_cod=% def_ts=% (esperado a/1/1)',
      v_ident, v_def_cod, v_def_ts;
  END IF;
END $$;

-- Preparación (como owner): limpieza de restos de corridas anteriores.
SET ROLE crud_admin;
DELETE FROM lab.ticket WHERE codigo LIKE 'TIX-%';
INSERT INTO lab.ticket(codigo) VALUES ('TIX-T3');
RESET ROLE;

-- MAT-T1 | vendedor → INSERT con codigo explícito → SUCCESS (id generado por PG)
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_ts timestamptz;
BEGIN
  v_id := NULL;
  CALL lab.ticket_insertar(v_id, 'TIX-T1', v_ts);
  IF v_id IS NOT NULL AND v_ts IS NOT NULL THEN
    RAISE NOTICE 'MAT-T1 OK: vendedor INSERT id_generado=% creado_en=%', v_id, v_ts;
  ELSE
    RAISE NOTICE 'MAT-T1 FAIL: id=% ts=% (PG debió generarlos)', v_id, v_ts;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T1 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T2 | vendedor → READ por PK → SUCCESS (round-trip)
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_ts timestamptz;
  v_cod text;
  v_ts2 timestamptz;
BEGIN
  CALL lab.ticket_insertar(v_id, 'TIX-T2', v_ts);
  CALL lab.ticket_consultar(v_id, v_cod, v_ts2);
  IF v_cod = 'TIX-T2' AND v_ts2 = v_ts THEN
    RAISE NOTICE 'MAT-T2 OK: vendedor READ devuelve codigo=% (id=%)', v_cod, v_id;
  ELSE
    RAISE NOTICE 'MAT-T2 FAIL: codigo=% ts=% (esperado TIX-T2/%)', v_cod, v_ts2, v_ts;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T2 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T3 | vendedor → UPDATE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIX-T3';
  CALL lab.ticket_actualizar(v_id, 'TIX-HACK');
  RAISE NOTICE 'MAT-T3 FAIL: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T3 OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T3 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T4 | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIX-T3';
  CALL lab.ticket_eliminar(v_id);
  RAISE NOTICE 'MAT-T4 FAIL: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T4 OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T4 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T5 | supervisor → UPDATE permitido → SUCCESS (verificado con READ)
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIX-T3';
  CALL lab.ticket_actualizar(v_id, 'TIX-T3U');
  CALL lab.ticket_consultar(v_id, v_cod, v_ts);
  IF v_cod = 'TIX-T3U' THEN
    RAISE NOTICE 'MAT-T5 OK: supervisor UPDATE permitido funciona (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-T5 FAIL: codigo=% tras UPDATE (esperado TIX-T3U)', v_cod;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T5 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T6 | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIX-T3U';
  CALL lab.ticket_eliminar(v_id);
  RAISE NOTICE 'MAT-T6 FAIL: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-T6 OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T6 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T7 | administrador → DELETE permitido → SUCCESS (fila inexistente P0002)
SET ROLE crud_administrador;
DO $$
DECLARE
  v_id integer;
  v_cod text;
  v_ts timestamptz;
BEGIN
  SELECT t.id_ticket INTO v_id FROM lab.ticket AS t WHERE t.codigo = 'TIX-T3U';
  CALL lab.ticket_eliminar(v_id);
  BEGIN
    CALL lab.ticket_consultar(v_id, v_cod, v_ts);
    RAISE NOTICE 'MAT-T7 FAIL: la fila debió desaparecer tras DELETE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = 'P0002' THEN
      RAISE NOTICE 'MAT-T7 OK: administrador DELETE cierra el ciclo (P0002)';
    ELSE
      RAISE NOTICE 'MAT-T7 resultado distinto al verificar: % %', SQLSTATE, SQLERRM;
    END IF;
  END;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T7 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T8 | IDENTITY manda: valor entrante de p_id_ticket se ignora, PG genera.
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer := 1999999999;
  v_ts timestamptz;
BEGIN
  CALL lab.ticket_insertar(v_id, 'TIX-T8', v_ts);
  IF v_id IS DISTINCT FROM 1999999999 AND v_id IS NOT NULL THEN
    RAISE NOTICE 'MAT-T8 OK: id entrante ignorado, PG generó id=%', v_id;
  ELSE
    RAISE NOTICE 'MAT-T8 FAIL: id=% (GENERATED ALWAYS debió imponerse)', v_id;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T8 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-T9 | DEFAULT manda: codigo NULL → 'SIN-CODIGO' del esquema (no hardcodeado).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_ts timestamptz;
  v_cod text;
  v_ts2 timestamptz;
BEGIN
  CALL lab.ticket_insertar(v_id, NULL, v_ts);
  CALL lab.ticket_consultar(v_id, v_cod, v_ts2);
  IF v_cod = 'SIN-CODIGO' AND v_ts2 IS NOT NULL THEN
    RAISE NOTICE 'MAT-T9 OK: DEFAULT aplicado codigo=% (id=%)', v_cod, v_id;
  ELSE
    RAISE NOTICE 'MAT-T9 FAIL: codigo=% ts=% (esperado SIN-CODIGO/no-nulo)', v_cod, v_ts2;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-T9 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-T1 | INSERT directo con id explícito (admin) → 428C9 GENERATED ALWAYS.
-- La columna identity se impone a nivel de columna, no de GRANTs.
SET ROLE crud_admin;
DO $$
BEGIN
  INSERT INTO lab.ticket(id_ticket, codigo) VALUES (424242, 'TIX-N1');
  RAISE NOTICE 'N-T1 FAIL: identity debió rechazar valor explícito';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = '428C9' THEN
    RAISE NOTICE 'N-T1 OK: valor explícito en GENERATED ALWAYS rechazado con 428C9';
  ELSE
    RAISE NOTICE 'N-T1 resultado distinto (investigar): % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- N-T2 | DELETE de fila inexistente → P0002 (convención fixtures, no 42501).
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.ticket_eliminar(1999999998);
  RAISE NOTICE 'N-T2 FAIL: debió reportar fila inexistente P0002';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = 'P0002' THEN
    RAISE NOTICE 'N-T2 OK: fila inexistente reporta P0002';
  ELSE
    RAISE NOTICE 'N-T2 resultado distinto: % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- N-T3 | vendedor con INSERT sobre tabla intenta id explícito → 428C9 (columna),
-- no 42501: la identity se impone aunque el rol tenga permiso de INSERT.
SET ROLE crud_vendedor;
DO $$
BEGIN
  INSERT INTO lab.ticket(id_ticket, codigo) VALUES (434343, 'TIX-N3');
  RAISE NOTICE 'N-T3 FAIL: identity debió rechazar valor explícito';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = '428C9' THEN
    RAISE NOTICE 'N-T3 OK: identity impone 428C9 aun con INSERT permitido';
  ELSE
    RAISE NOTICE 'N-T3 resultado distinto (investigar): % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- TIX-AUD | auto-auditoría T2 (owner/INVOKER/search_path/PUBLIC) de los 4 fixtures.
-- Autocontenida para no modificar T3/T4; replica sus criterios exactos.
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
      ('ticket_insertar', 'lab.ticket_insertar(integer,text,timestamp with time zone)'),
      ('ticket_consultar', 'lab.ticket_consultar(integer,text,timestamp with time zone)'),
      ('ticket_actualizar', 'lab.ticket_actualizar(integer,text)'),
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
      RAISE NOTICE 'TIX-AUD FAIL: % owner=% (esperado crud_admin)', r.reg, r.ownername;
    ELSIF r.prosecdef THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIX-AUD FAIL: % SECURITY DEFINER (esperado INVOKER)', r.reg;
    ELSIF NOT EXISTS (SELECT 1 FROM unnest(r.proconfig) AS c
                      WHERE trim(c) = 'search_path=lab, pg_temp') THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIX-AUD FAIL: % search_path=[%] (esperado lab, pg_temp)',
        r.reg, COALESCE(array_to_string(r.proconfig, ' | '), '(sin proconfig)');
    ELSIF r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
       OR r.proacl::text LIKE '%,=X/%' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'TIX-AUD FAIL: % fuga EXECUTE a PUBLIC', r.reg;
    ELSE
      RAISE NOTICE 'TIX-AUD OK: % owner+INVOKER+search_path+PUBLIC conformes', r.reg;
    END IF;
  END LOOP;
  IF v_fail > 0 OR v_total <> 4 THEN
    RAISE NOTICE 'TIX-AUD RESULTADO: % procedure(s) no conformes, % auditados (esperado 4)',
      v_fail, v_total;
  ELSE
    RAISE NOTICE 'TIX-AUD RESULTADO: 4/4 conformes';
  END IF;
END $$;

-- Limpieza (como owner; todo rastro TIX-* desaparece)
SET ROLE crud_admin;
DELETE FROM lab.ticket WHERE codigo LIKE 'TIX-%';
RESET ROLE;
