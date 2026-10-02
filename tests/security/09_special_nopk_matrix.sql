-- tests/security/09_special_nopk_matrix.sql
-- T6 — Matriz tipos especiales + tabla sin PK (Joseph). MODO FIXTURES.
-- Verifica EXECUTE+tabla reales con SET ROLE + CALL sobre fixtures de
-- lab.catalogo_especial (quoting/jsonb/boolean/date/numeric/identity) y
-- lab.bitacora (sin PK, convención fixture: solo insertar+contar).
-- La policy definitiva sin PK (ADR-009, RESUELTA: not_applicable + refcursor)
-- se prueba contra reales en 12_special_real_matrix.sql.
-- Esperado OK → success; denegado → 42501; inexistente → P0002;
-- rutina ausente (policy) → 42883; nulo en NOT NULL → 23502.
-- Requiere: fixtures/08_special_nopk_fixtures.sql. NOTICEs OK/FAIL.
-- Marcadores: catalogo "Nombre Ítem" LIKE 'SPC-%', bitacora mensaje LIKE 'LOG-%'.
-- Limpieza como crud_admin al inicio (idempotencia) y al final.
-- NO toca tabla_virgen.

-- S-00 | catálogo: PK simple en catalogo_especial, 0 PK en bitacora, quoting real.
DO $$
DECLARE
  v_pk_cat integer;
  v_pk_bit integer;
  v_quot integer;
BEGIN
  SELECT count(*) INTO v_pk_cat FROM pg_constraint
  WHERE conrelid = 'lab.catalogo_especial'::regclass AND contype = 'p';
  SELECT count(*) INTO v_pk_bit FROM pg_constraint
  WHERE conrelid = 'lab.bitacora'::regclass AND contype = 'p';
  SELECT count(*) INTO v_quot FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'lab' AND c.relname = 'catalogo_especial'
    AND a.attname IN ('Nombre Ítem', 'precio$');
  IF v_pk_cat = 1 AND v_pk_bit = 0 AND v_quot = 2 THEN
    RAISE NOTICE 'S-00 OK: catalogo PK simple + bitacora sin PK + quoting "Nombre Ítem"/"precio$"';
  ELSE
    RAISE NOTICE 'S-00 FAIL: pk_cat=% pk_bit=% quot=% (esperado 1/0/2)',
      v_pk_cat, v_pk_bit, v_quot;
  END IF;
END $$;

-- Preparación (como owner): limpieza + fila setup SPC-S3.
SET ROLE crud_admin;
DELETE FROM lab.catalogo_especial WHERE "Nombre Ítem" LIKE 'SPC-%';
DELETE FROM lab.bitacora WHERE mensaje LIKE 'LOG-%';
INSERT INTO lab.catalogo_especial("Nombre Ítem", "precio$", activo, datos, fecha)
VALUES ('SPC-S3', 1.00, true, '{}', CURRENT_DATE);
RESET ROLE;

-- MAT-S1 | vendedor → INSERT con valores hostiles/unicode → SUCCESS + id generado.
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  v_id := NULL;
  CALL lab.catalogo_especial_insertar(v_id, 'SPC-Ñoño "X" — 50%',
    1234.56, false, '{"a":[1,{"b":null}],"s":"x\"y"}'::jsonb, '2024-02-29'::date);
  IF v_id IS NOT NULL THEN
    RAISE NOTICE 'MAT-S1 OK: vendedor INSERT especial id=%', v_id;
  ELSE
    RAISE NOTICE 'MAT-S1 FAIL: id nulo (identity debió generar)';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S1 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S2 | vendedor → READ round-trip exacto (quoting/unicode/numeric/bool/jsonb/date).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c
  WHERE c."Nombre Ítem" = 'SPC-Ñoño "X" — 50%';
  CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
  IF v_nom = 'SPC-Ñoño "X" — 50%' AND v_pre = 1234.56 AND v_act = false
     AND v_dat = '{"a":[1,{"b":null}],"s":"x\"y"}'::jsonb AND v_fec = '2024-02-29'::date THEN
    RAISE NOTICE 'MAT-S2 OK: round-trip exacto tipos especiales (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-S2 FAIL: nom=% pre=% act=% dat=% fec=%', v_nom, v_pre, v_act, v_dat, v_fec;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S2 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S3 | vendedor → UPDATE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPC-S3';
  CALL lab.catalogo_especial_actualizar(v_id, 'SPC-HACK', 0, true, '{}', CURRENT_DATE);
  RAISE NOTICE 'MAT-S3 FAIL: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S3 OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S3 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S4 | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPC-S3';
  CALL lab.catalogo_especial_eliminar(v_id);
  RAISE NOTICE 'MAT-S4 FAIL: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S4 OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S4 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S5 | supervisor → UPDATE permitido → SUCCESS (verificado con READ)
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPC-S3';
  CALL lab.catalogo_especial_actualizar(v_id, 'SPC-S3U', 2.50, false,
    '{"k":"v"}', '2025-01-15'::date);
  CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
  IF v_nom = 'SPC-S3U' AND v_pre = 2.50 AND v_act = false THEN
    RAISE NOTICE 'MAT-S5 OK: supervisor UPDATE especial funciona (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-S5 FAIL: nom=% pre=% act=%', v_nom, v_pre, v_act;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S5 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S6 | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPC-S3U';
  CALL lab.catalogo_especial_eliminar(v_id);
  RAISE NOTICE 'MAT-S6 FAIL: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S6 OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S6 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S7 | administrador → DELETE permitido → SUCCESS (P0002 después)
SET ROLE crud_administrador;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPC-S3U';
  CALL lab.catalogo_especial_eliminar(v_id);
  BEGIN
    CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
    RAISE NOTICE 'MAT-S7 FAIL: la fila debió desaparecer tras DELETE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = 'P0002' THEN
      RAISE NOTICE 'MAT-S7 OK: administrador DELETE cierra el ciclo (P0002)';
    ELSE
      RAISE NOTICE 'MAT-S7 resultado distinto al verificar: % %', SQLSTATE, SQLERRM;
    END IF;
  END;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S7 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S8 | DEFAULTs del esquema (vía directa admin): precio$=0, activo, '{}', hoy.
SET ROLE crud_admin;
DO $$
DECLARE
  v_id integer;
  v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  INSERT INTO lab.catalogo_especial("Nombre Ítem") VALUES ('SPC-DEF')
  RETURNING lab.catalogo_especial.id INTO v_id;
  SELECT c."precio$", c.activo, c.datos, c.fecha INTO v_pre, v_act, v_dat, v_fec
  FROM lab.catalogo_especial AS c WHERE c.id = v_id;
  IF v_pre = 0 AND v_act = true AND v_dat = '{}'::jsonb AND v_fec = CURRENT_DATE THEN
    RAISE NOTICE 'MAT-S8 OK: DEFAULTs 0/true/{}/hoy aplicados por el esquema';
  ELSE
    RAISE NOTICE 'MAT-S8 FAIL: pre=% act=% dat=% fec=%', v_pre, v_act, v_dat, v_fec;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S8 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B1 | vendedor → bitacora INSERT + COUNT (2 filas mismo criterio, sin identidad).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_n integer;
BEGIN
  CALL lab.bitacora_insertar(9001, 'LOG-B1a');
  CALL lab.bitacora_insertar(9001, 'LOG-B1b');
  CALL lab.bitacora_contar(9001, v_n);
  IF v_n = 2 THEN
    RAISE NOTICE 'MAT-B1 OK: vendedor INSERT+COUNT sin PK (n=2, sin identidad única)';
  ELSE
    RAISE NOTICE 'MAT-B1 FAIL: n=% (esperado 2)', v_n;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B1 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B2 | supervisor → bitacora INSERT + COUNT → SUCCESS
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_n integer;
BEGIN
  CALL lab.bitacora_insertar(9002, 'LOG-B2');
  CALL lab.bitacora_contar(9002, v_n);
  IF v_n = 1 THEN
    RAISE NOTICE 'MAT-B2 OK: supervisor INSERT+COUNT sin PK';
  ELSE
    RAISE NOTICE 'MAT-B2 FAIL: n=% (esperado 1)', v_n;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B2 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B3 | administrador → bitacora INSERT + COUNT → SUCCESS
SET ROLE crud_administrador;
DO $$
DECLARE
  v_n integer;
BEGIN
  CALL lab.bitacora_insertar(9003, 'LOG-B3');
  CALL lab.bitacora_contar(9003, v_n);
  IF v_n = 1 THEN
    RAISE NOTICE 'MAT-B3 OK: administrador INSERT+COUNT sin PK';
  ELSE
    RAISE NOTICE 'MAT-B3 FAIL: n=% (esperado 1)', v_n;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B3 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P1 | policy provisional: bitacora_actualizar NO existe → 42883 (no inventada).
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.bitacora_actualizar(9001, 'LOG-X');
  RAISE NOTICE 'N-P1 FAIL: actualizar sin PK no debería existir (policy pendiente)';
EXCEPTION WHEN undefined_function THEN
  RAISE NOTICE 'N-P1 OK: sin actualizar por fila hasta decisión CR-JOYCE-003 (42883)';
WHEN OTHERS THEN
  RAISE NOTICE 'N-P1 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P2 | policy provisional: bitacora_eliminar NO existe → 42883.
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.bitacora_eliminar(9001);
  RAISE NOTICE 'N-P2 FAIL: eliminar sin PK no debería existir (policy pendiente)';
EXCEPTION WHEN undefined_function THEN
  RAISE NOTICE 'N-P2 OK: sin eliminar por fila hasta decisión CR-JOYCE-003 (42883)';
WHEN OTHERS THEN
  RAISE NOTICE 'N-P2 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P3 | NULL en "Nombre Ítem" NOT NULL → 23502 (no 42501: es constraint, no permiso).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  CALL lab.catalogo_especial_insertar(v_id, NULL, 1.00, true, '{}', CURRENT_DATE);
  RAISE NOTICE 'N-P3 FAIL: NOT NULL debió rechazar';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = '23502' THEN
    RAISE NOTICE 'N-P3 OK: NOT NULL impone 23502 (capa constraint, no permiso)';
  ELSE
    RAISE NOTICE 'N-P3 resultado distinto (investigar): % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- N-P4 | consultar catalogo inexistente → P0002 (convención fixtures).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  CALL lab.catalogo_especial_consultar(-999, v_nom, v_pre, v_act, v_dat, v_fec);
  RAISE NOTICE 'N-P4 FAIL: debió reportar P0002';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = 'P0002' THEN
    RAISE NOTICE 'N-P4 OK: fila inexistente reporta P0002';
  ELSE
    RAISE NOTICE 'N-P4 resultado distinto: % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- S-AUD | auto-auditoría T6 (owner/INVOKER/search_path/PUBLIC) de los 6 fixtures.
-- Autocontenida para no modificar T3/T4; replica sus criterios exactos.
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
  v_total integer := 0;
BEGIN
  FOR r IN
    SELECT e.reg, rol.rolname AS ownername, p.prosecdef, p.proconfig, p.proacl
    FROM (VALUES
      ('lab.catalogo_especial_insertar(integer,text,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_consultar(integer,text,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_actualizar(integer,text,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_eliminar(integer)'),
      ('lab.bitacora_insertar(integer,text)'),
      ('lab.bitacora_contar(integer,integer)')
    ) AS e(reg)
    JOIN pg_namespace n ON n.nspname = 'lab'
    JOIN pg_proc p ON p.pronamespace = n.oid
         AND replace(p.oid::regprocedure::text, ' ', '') = replace(e.reg, ' ', '')
    JOIN pg_roles rol ON rol.oid = p.proowner
  LOOP
    v_total := v_total + 1;
    IF r.ownername <> 'crud_admin' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUD FAIL: % owner=% (esperado crud_admin)', r.reg, r.ownername;
    ELSIF r.prosecdef THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUD FAIL: % SECURITY DEFINER (esperado INVOKER)', r.reg;
    ELSIF NOT EXISTS (SELECT 1 FROM unnest(r.proconfig) AS c
                      WHERE trim(c) = 'search_path=lab, pg_temp') THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUD FAIL: % search_path=[%] (esperado lab, pg_temp)',
        r.reg, COALESCE(array_to_string(r.proconfig, ' | '), '(sin proconfig)');
    ELSIF r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
       OR r.proacl::text LIKE '%,=X/%' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUD FAIL: % fuga EXECUTE a PUBLIC', r.reg;
    ELSE
      RAISE NOTICE 'S-AUD OK: % conforme', r.reg;
    END IF;
  END LOOP;
  IF v_fail > 0 OR v_total <> 6 THEN
    RAISE NOTICE 'S-AUD RESULTADO: % no conformes, % auditados (esperado 6)',
      v_fail, v_total;
  ELSE
    RAISE NOTICE 'S-AUD RESULTADO: 6/6 conformes';
  END IF;
END $$;

-- Limpieza (como owner; todo rastro SPC-*/LOG-* desaparece)
SET ROLE crud_admin;
DELETE FROM lab.catalogo_especial WHERE "Nombre Ítem" LIKE 'SPC-%';
DELETE FROM lab.bitacora WHERE mensaje LIKE 'LOG-%';
RESET ROLE;
