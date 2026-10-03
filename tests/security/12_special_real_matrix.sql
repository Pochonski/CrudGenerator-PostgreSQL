-- tests/security/12_special_real_matrix.sql
-- T6R — Matriz tipos especiales + tabla sin PK contra PROCEDURES REALES (Joseph).
--
-- DIFERENCIA con 09_special_nopk_matrix.sql (fixtures):
--   * `catalogo_especial_insertar` REAL: (IN nombre text, IN id integer, ...)
--     (obligatorios antes que opcionales, CONTRACTS.md §3.2; el id BY DEFAULT
--     se genera pasando NULL). El resto de firmas coincide en tipos con el
--     fixture, pero los CALL de READ usan variables (PK INOUT, ADR-015).
--   * `bitacora` REAL: `bitacora_insertar(id,mensaje,creado_en)` +
--     `bitacora_consultar(OUT resultado refcursor)` (ADR-009, listado completo).
--     No existe `bitacora_contar`; el conteo se hace vía FETCH del refcursor
--     dentro del mismo bloque DO (el cursor vive en la transacción del DO).
--   * Política sin PK RESUELTA (ADR-009/CR-JOYCE-003): UPDATE/DELETE reportan
--     `not_applicable` en generate_crud y las rutinas no existen (42883).
--
-- MODO REALES (no corre en CI con fixtures):
--   1. tests/fixtures/01_roles.sql + 02_schema.sql
--   2. SET ROLE crud_admin + generate_crud('lab','catalogo_especial'|'bitacora',
--      4 ops) + grants reales (plantilla 05 con firmas del handoff §2.4)
-- NO requiere 08_special_nopk_fixtures.sql. NO toca tabla_virgen.
-- Marcadores: "Nombre Ítem" LIKE 'SPCR-%', mensaje LIKE 'LOGR-%'
-- (disjuntos de 'SPC-%'/'LOG-%' de 09). Idempotente.
--
-- Convenciones: OK → success; denegado → 42501; inexistente → P0002;
-- rutina ausente (policy) → 42883; nulo en NOT NULL → 23502.

-- S-00R | catálogo: PK simple en catalogo_especial, 0 PK en bitacora, quoting real.
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
    RAISE NOTICE 'S-00R OK: catalogo PK simple + bitacora sin PK + quoting "Nombre Ítem"/"precio$"';
  ELSE
    RAISE NOTICE 'S-00R FAIL: pk_cat=% pk_bit=% quot=% (esperado 1/0/2)',
      v_pk_cat, v_pk_bit, v_quot;
  END IF;
END $$;

-- Preparación (como owner): regenera reales (idempotente), limpieza + fila SPCR-S3.
SET ROLE crud_admin;
SELECT * FROM crud_generator.generate_crud('lab','catalogo_especial',
  ARRAY['INSERT','READ','UPDATE','DELETE'], true);
SELECT * FROM crud_generator.generate_crud('lab','bitacora',
  ARRAY['INSERT','READ','UPDATE','DELETE'], true);
DELETE FROM lab.catalogo_especial WHERE "Nombre Ítem" LIKE 'SPCR-%';
DELETE FROM lab.bitacora WHERE mensaje LIKE 'LOGR-%';
INSERT INTO lab.catalogo_especial("Nombre Ítem", "precio$", activo, datos, fecha)
VALUES ('SPCR-S3', 1.00, true, '{}', CURRENT_DATE);
RESET ROLE;

-- MAT-S1R | vendedor → INSERT real con valores hostiles/unicode → SUCCESS + id.
-- Orden real: (nombre, id NULL→generado, precio, activo, datos, fecha).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  CALL lab.catalogo_especial_insertar('SPCR-Ñoño "X" — 50%',
    NULL, 1234.56, false, '{"a":[1,{"b":null}],"s":"x\"y"}'::jsonb, '2024-02-29'::date);
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c
  WHERE c."Nombre Ítem" = 'SPCR-Ñoño "X" — 50%';
  IF v_id IS NOT NULL THEN
    RAISE NOTICE 'MAT-S1R OK: vendedor INSERT real especial id=%', v_id;
  ELSE
    RAISE NOTICE 'MAT-S1R FAIL: id nulo (identity debió generar)';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S1R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S2R | vendedor → READ round-trip exacto (PK INOUT ⇒ variable).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c
  WHERE c."Nombre Ítem" = 'SPCR-Ñoño "X" — 50%';
  CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
  IF v_nom = 'SPCR-Ñoño "X" — 50%' AND v_pre = 1234.56 AND v_act = false
     AND v_dat = '{"a":[1,{"b":null}],"s":"x\"y"}'::jsonb AND v_fec = '2024-02-29'::date THEN
    RAISE NOTICE 'MAT-S2R OK: round-trip exacto tipos especiales (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-S2R FAIL: nom=% pre=% act=% dat=% fec=%', v_nom, v_pre, v_act, v_dat, v_fec;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S2R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S3R | vendedor → UPDATE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPCR-S3';
  CALL lab.catalogo_especial_actualizar(v_id, 'SPCR-HACK', 0, true, '{}', CURRENT_DATE);
  RAISE NOTICE 'MAT-S3R FAIL: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S3R OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S3R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S4R | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPCR-S3';
  CALL lab.catalogo_especial_eliminar(v_id);
  RAISE NOTICE 'MAT-S4R FAIL: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S4R OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S4R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S5R | supervisor → UPDATE permitido → SUCCESS (verificado con READ)
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPCR-S3';
  CALL lab.catalogo_especial_actualizar(v_id, 'SPCR-S3U', 2.50, false,
    '{"k":"v"}', '2025-01-15'::date);
  CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
  IF v_nom = 'SPCR-S3U' AND v_pre = 2.50 AND v_act = false THEN
    RAISE NOTICE 'MAT-S5R OK: supervisor UPDATE real especial funciona (id=%)', v_id;
  ELSE
    RAISE NOTICE 'MAT-S5R FAIL: nom=% pre=% act=%', v_nom, v_pre, v_act;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S5R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S6R | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_id integer;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPCR-S3U';
  CALL lab.catalogo_especial_eliminar(v_id);
  RAISE NOTICE 'MAT-S6R FAIL: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-S6R OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S6R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S7R | administrador → DELETE permitido → SUCCESS (P0002 después)
SET ROLE crud_administrador;
DO $$
DECLARE
  v_id integer;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  SELECT c.id INTO v_id FROM lab.catalogo_especial AS c WHERE c."Nombre Ítem" = 'SPCR-S3U';
  CALL lab.catalogo_especial_eliminar(v_id);
  BEGIN
    CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
    RAISE NOTICE 'MAT-S7R FAIL: la fila debió desaparecer tras DELETE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = 'P0002' THEN
      RAISE NOTICE 'MAT-S7R OK: administrador DELETE cierra el ciclo (P0002)';
    ELSE
      RAISE NOTICE 'MAT-S7R resultado distinto al verificar: % %', SQLSTATE, SQLERRM;
    END IF;
  END;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S7R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-S8R | DEFAULTs del esquema (vía directa admin): precio$=0, activo, '{}', hoy.
SET ROLE crud_admin;
DO $$
DECLARE
  v_id integer;
  v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  INSERT INTO lab.catalogo_especial("Nombre Ítem") VALUES ('SPCR-DEF')
  RETURNING lab.catalogo_especial.id INTO v_id;
  SELECT c."precio$", c.activo, c.datos, c.fecha INTO v_pre, v_act, v_dat, v_fec
  FROM lab.catalogo_especial AS c WHERE c.id = v_id;
  IF v_pre = 0 AND v_act = true AND v_dat = '{}'::jsonb AND v_fec = CURRENT_DATE THEN
    RAISE NOTICE 'MAT-S8R OK: DEFAULTs 0/true/{}/hoy aplicados por el esquema';
  ELSE
    RAISE NOTICE 'MAT-S8R FAIL: pre=% act=% dat=% fec=%', v_pre, v_act, v_dat, v_fec;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-S8R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B1R | vendedor → bitacora INSERT ×2 + READ refcursor (2 filas, sin identidad).
SET ROLE crud_vendedor;
DO $$
DECLARE
  c refcursor;
  r RECORD;
  v_n integer := 0;
BEGIN
  CALL lab.bitacora_insertar(9001, 'LOGR-B1a', NULL);
  CALL lab.bitacora_insertar(9001, 'LOGR-B1b', NULL);
  CALL lab.bitacora_consultar(c);
  FOR r IN EXECUTE 'FETCH ALL FROM ' || quote_ident(c::text) LOOP
    IF (r.mensaje LIKE 'LOGR-%') THEN v_n := v_n + 1; END IF;
  END LOOP;
  IF v_n >= 2 THEN
    RAISE NOTICE 'MAT-B1R OK: vendedor INSERT+READ-refcursor sin PK (n=% LOGR-*)', v_n;
  ELSE
    RAISE NOTICE 'MAT-B1R FAIL: n=% (esperado >=2)', v_n;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B1R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B2R | supervisor → bitacora INSERT + READ-refcursor → SUCCESS
SET ROLE crud_supervisor;
DO $$
DECLARE
  c refcursor;
  r RECORD;
  v_found boolean := false;
BEGIN
  CALL lab.bitacora_insertar(9002, 'LOGR-B2', NULL);
  CALL lab.bitacora_consultar(c);
  FOR r IN EXECUTE 'FETCH ALL FROM ' || quote_ident(c::text) LOOP
    IF r.mensaje = 'LOGR-B2' THEN v_found := true; END IF;
  END LOOP;
  IF v_found THEN
    RAISE NOTICE 'MAT-B2R OK: supervisor INSERT+READ-refcursor sin PK';
  ELSE
    RAISE NOTICE 'MAT-B2R FAIL: LOGR-B2 no aparece en el listado';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B2R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-B3R | administrador → bitacora INSERT + READ-refcursor → SUCCESS
SET ROLE crud_administrador;
DO $$
DECLARE
  c refcursor;
  r RECORD;
  v_found boolean := false;
BEGIN
  CALL lab.bitacora_insertar(9003, 'LOGR-B3', NULL);
  CALL lab.bitacora_consultar(c);
  FOR r IN EXECUTE 'FETCH ALL FROM ' || quote_ident(c::text) LOOP
    IF r.mensaje = 'LOGR-B3' THEN v_found := true; END IF;
  END LOOP;
  IF v_found THEN
    RAISE NOTICE 'MAT-B3R OK: administrador INSERT+READ-refcursor sin PK';
  ELSE
    RAISE NOTICE 'MAT-B3R FAIL: LOGR-B3 no aparece en el listado';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-B3R FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- B-POL | policy ADR-009: generate_crud reporta not_applicable en UPDATE/DELETE
-- de bitacora (sin PK) en vez de inventar una PK.
SET ROLE crud_admin;
DO $$
DECLARE
  v_upd text;
  v_del text;
BEGIN
  SELECT status INTO v_upd FROM crud_generator.generate_crud('lab','bitacora',
    ARRAY['UPDATE'], true) WHERE operation = 'UPDATE';
  SELECT status INTO v_del FROM crud_generator.generate_crud('lab','bitacora',
    ARRAY['DELETE'], true) WHERE operation = 'DELETE';
  IF v_upd = 'not_applicable' AND v_del = 'not_applicable' THEN
    RAISE NOTICE 'B-POL OK: UPDATE/DELETE sin PK → not_applicable (ADR-009)';
  ELSE
    RAISE NOTICE 'B-POL FAIL: upd=% del=% (esperado not_applicable/not_applicable)',
      v_upd, v_del;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'B-POL FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P1R | bitacora_actualizar NO existe → 42883 (no se inventa PK).
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.bitacora_actualizar(9001, 'LOGR-X', now());
  RAISE NOTICE 'N-P1R FAIL: actualizar sin PK no debería existir';
EXCEPTION WHEN undefined_function THEN
  RAISE NOTICE 'N-P1R OK: sin actualizar por fila (42883, ADR-009)';
WHEN OTHERS THEN
  RAISE NOTICE 'N-P1R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P2R | bitacora_eliminar NO existe → 42883.
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.bitacora_eliminar(9001);
  RAISE NOTICE 'N-P2R FAIL: eliminar sin PK no debería existir';
EXCEPTION WHEN undefined_function THEN
  RAISE NOTICE 'N-P2R OK: sin eliminar por fila (42883, ADR-009)';
WHEN OTHERS THEN
  RAISE NOTICE 'N-P2R resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- N-P3R | NULL en "Nombre Ítem" NOT NULL → 23502 (orden real: nombre primero).
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.catalogo_especial_insertar(NULL, NULL, 1.00, true, '{}', CURRENT_DATE);
  RAISE NOTICE 'N-P3R FAIL: NOT NULL debió rechazar';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = '23502' THEN
    RAISE NOTICE 'N-P3R OK: NOT NULL impone 23502 (capa constraint, no permiso)';
  ELSE
    RAISE NOTICE 'N-P3R resultado distinto (investigar): % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- N-P4R | consultar catalogo inexistente → P0002 (PK INOUT ⇒ variable).
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_id integer := -999;
  v_nom text; v_pre numeric; v_act boolean; v_dat jsonb; v_fec date;
BEGIN
  CALL lab.catalogo_especial_consultar(v_id, v_nom, v_pre, v_act, v_dat, v_fec);
  RAISE NOTICE 'N-P4R FAIL: debió reportar P0002';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = 'P0002' THEN
    RAISE NOTICE 'N-P4R OK: fila inexistente reporta P0002';
  ELSE
    RAISE NOTICE 'N-P4R resultado distinto: % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- S-AUDR | auto-auditoría (owner/INVOKER/search_path/PUBLIC) de los 6 REALES.
-- `bitacora_consultar` figura como `lab.bitacora_consultar()` en regprocedure
-- (único OUT): el lookup por texto no la resuelve, se verifica por oid + EXECUTE.
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
  v_total integer := 0;
  v_exec boolean;
BEGIN
  FOR r IN
    SELECT e.reg, rol.rolname AS ownername, p.prosecdef, p.proconfig, p.proacl,
           p.oid AS poid
    FROM (VALUES
      ('lab.catalogo_especial_insertar(text,integer,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_consultar(integer,text,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_actualizar(integer,text,numeric,boolean,jsonb,date)'),
      ('lab.catalogo_especial_eliminar(integer)'),
      ('lab.bitacora_insertar(integer,text,timestamp with time zone)'),
      ('lab.bitacora_consultar()')
    ) AS e(reg)
    JOIN pg_namespace n ON n.nspname = 'lab'
    JOIN pg_proc p ON p.pronamespace = n.oid
         AND replace(p.oid::regprocedure::text, ' ', '') = replace(e.reg, ' ', '')
    JOIN pg_roles rol ON rol.oid = p.proowner
  LOOP
    v_total := v_total + 1;
    IF r.ownername <> 'crud_admin' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUDR FAIL: % owner=% (esperado crud_admin)', r.reg, r.ownername;
    ELSIF r.prosecdef THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUDR FAIL: % SECURITY DEFINER (esperado INVOKER)', r.reg;
    ELSIF NOT EXISTS (SELECT 1 FROM unnest(r.proconfig) AS c
                      WHERE trim(c) = 'search_path=lab, pg_temp') THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUDR FAIL: % search_path=[%] (esperado lab, pg_temp)',
        r.reg, COALESCE(array_to_string(r.proconfig, ' | '), '(sin proconfig)');
    ELSIF r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
       OR r.proacl::text LIKE '%,=X/%' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'S-AUDR FAIL: % fuga EXECUTE a PUBLIC', r.reg;
    ELSE
      RAISE NOTICE 'S-AUDR OK: % conforme', r.reg;
    END IF;
  END LOOP;
  -- bitacora_consultar: EXECUTE real por oid (vendedor) como 7ma verificación.
  SELECT has_function_privilege('crud_vendedor',
    (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'lab' AND p.proname = 'bitacora_consultar'),
    'EXECUTE') INTO v_exec;
  v_total := v_total + 1;
  IF v_exec THEN
    RAISE NOTICE 'S-AUDR OK: bitacora_consultar EXECUTE vendedor=t (vía oid)';
  ELSE
    v_fail := v_fail + 1;
    RAISE NOTICE 'S-AUDR FAIL: bitacora_consultar EXECUTE vendedor=f';
  END IF;
  IF v_fail > 0 OR v_total <> 7 THEN
    RAISE NOTICE 'S-AUDR RESULTADO: % no conformes, % auditados (esperado 7)',
      v_fail, v_total;
  ELSE
    RAISE NOTICE 'S-AUDR RESULTADO: 7/7 conformes';
  END IF;
END $$;

-- Limpieza (como owner; todo rastro SPCR-*/LOGR-* desaparece)
SET ROLE crud_admin;
DELETE FROM lab.catalogo_especial WHERE "Nombre Ítem" LIKE 'SPCR-%';
DELETE FROM lab.bitacora WHERE mensaje LIKE 'LOGR-%';
RESET ROLE;
