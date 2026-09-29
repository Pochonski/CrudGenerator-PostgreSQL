-- tests/security/08_dynamic_sql_audit.sql
-- T5 — Harness de SQL dinámico seguro, ADR-013 (Joseph).
-- Demuestra con pruebas reales que %I (identificadores) + USING (valores)
-- neutralizan inyección, y que el scan estático detecta concatenación insegura.
-- Todo es autocontenido: crea tabla lab.dyn_probe + 4 procedures de prueba
-- (owner crud_admin, SECURITY INVOKER, search_path, REVOKE FROM PUBLIC),
-- los ataca con valores/identificadores hostiles, y AL FINAL LOS ELIMINA.
-- El único ejemplo inseguro (lab.dyn_unsafe_count, concatenación con ||) es un
-- señuelo controlado: sin GRANTs a roles de negocio, detectado por el scan,
-- explotado solo por crud_admin para probar el detector, y eliminado aquí mismo.
-- %L no se usa: USING parametriza valores sin formatearlos (criterio ADR-013).
-- Requiere: fixtures/01_roles.sql + 02_schema.sql. Idempotente.
-- NO toca lab.tabla_virgen ni fixtures T1/T2/T3/T4.

-- Preparación (como owner): tabla sonda + procedures de prueba.
SET ROLE crud_admin;
DROP PROCEDURE IF EXISTS lab.dyn_unsafe_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_ident_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_insert(integer, text);
DROP TABLE IF EXISTS lab.dyn_probe;
CREATE TABLE lab.dyn_probe (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  v  text NOT NULL
);

-- Seguro 1: INSERT dinámico con %I + valor vía USING (+ RETURNING).
CREATE PROCEDURE lab.dyn_safe_insert(INOUT p_id integer DEFAULT NULL, IN p_val text DEFAULT NULL)
  LANGUAGE plpgsql SECURITY INVOKER SET search_path = lab, pg_temp
AS $$
BEGIN
  EXECUTE format('INSERT INTO %I.%I(%I) VALUES ($1) RETURNING %I',
                 'lab', 'dyn_probe', 'v', 'id')
    INTO p_id USING p_val;
END;
$$;

-- Seguro 2: conteo con %I + valor vía USING.
CREATE PROCEDURE lab.dyn_safe_count(IN p_val text DEFAULT NULL, INOUT p_n integer DEFAULT NULL)
  LANGUAGE plpgsql SECURITY INVOKER SET search_path = lab, pg_temp
AS $$
BEGIN
  EXECUTE format('SELECT count(*) FROM %I.%I WHERE %I = $1', 'lab', 'dyn_probe', 'v')
    INTO p_n USING p_val;
END;
$$;

-- Seguro 3: identificador (tabla) vía %I — el detector de inyección de DYN-02.
CREATE PROCEDURE lab.dyn_safe_ident_count(IN p_tabla text DEFAULT NULL, INOUT p_n integer DEFAULT NULL)
  LANGUAGE plpgsql SECURITY INVOKER SET search_path = lab, pg_temp
AS $$
BEGIN
  EXECUTE format('SELECT count(*) FROM %I.%I', 'lab', p_tabla)
    INTO p_n;
END;
$$;

-- SEÑUELO inseguro (concatenación con ||): solo para probar el detector.
-- Sin EXECUTE para ningún rol de negocio; solo crud_admin lo ejecuta aquí.
CREATE PROCEDURE lab.dyn_unsafe_count(IN p_val text DEFAULT NULL, INOUT p_n integer DEFAULT NULL)
  LANGUAGE plpgsql SECURITY INVOKER SET search_path = lab, pg_temp
AS $$
BEGIN
  EXECUTE 'SELECT count(*) FROM lab.dyn_probe WHERE v = ''' || p_val || ''''
    INTO p_n;
END;
$$;
RESET ROLE;

REVOKE ALL ON PROCEDURE lab.dyn_safe_insert(integer, text) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.dyn_safe_count(text, integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.dyn_safe_ident_count(text, integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.dyn_unsafe_count(text, integer) FROM PUBLIC;

-- DYN-00 | los 4 procedures de prueba cumplen owner/INVOKER/search_path/sin PUBLIC.
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
BEGIN
  FOR r IN
    SELECT p.proname, rol.rolname AS ownername, p.prosecdef, p.proconfig, p.proacl
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      JOIN pg_roles rol ON rol.oid = p.proowner
    WHERE n.nspname = 'lab'
      AND p.proname IN ('dyn_safe_insert', 'dyn_safe_count',
                        'dyn_safe_ident_count', 'dyn_unsafe_count')
  LOOP
    IF r.ownername <> 'crud_admin' OR r.prosecdef
       OR NOT EXISTS (SELECT 1 FROM unnest(r.proconfig) AS c
                      WHERE trim(c) = 'search_path=lab, pg_temp')
       OR r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
       OR r.proacl::text LIKE '%,=X/%' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'DYN-00 FAIL: % owner=% defin=% (esperado crud_admin/INVOKER+path+sin PUBLIC)',
        r.proname, r.ownername, r.prosecdef;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'DYN-00 RESULTADO: % procedure(s) de prueba no conformes', v_fail;
  ELSE
    RAISE NOTICE 'DYN-00 RESULTADO: 4/4 procedures de prueba conformes';
  END IF;
END $$;

-- DYN-01 | valores hostiles vía USING quedan como DATOS (round-trip exacto).
-- Incluye comillas, ;, --, SQL aparente, %I/%L/$1 literales y backslash.
SET ROLE crud_admin;
DO $$
DECLARE
  v_vals text[] := ARRAY[
    'O''Brien',
    'x''); DROP TABLE lab.dyn_probe; --',
    '''; DELETE FROM lab.dyn_probe WHERE ''1''=''1',
    '"lab"."dyn_probe"',
    '100% legitimo %I %L $1 sin interpretar',
    'back\slash',
    '-- solo comentario',
    '1; SELECT pg_sleep(10)'
  ];
  v_val text;
  v_id integer;
  v_back text;
  v_fail integer := 0;
BEGIN
  FOREACH v_val IN ARRAY v_vals LOOP
    v_id := NULL;
    CALL lab.dyn_safe_insert(v_id, v_val);
    SELECT p.v INTO v_back FROM lab.dyn_probe AS p WHERE p.id = v_id;
    IF v_back IS DISTINCT FROM v_val THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'DYN-01 FAIL: round-trip alterado para «%» (leído «%»)',
        left(v_val, 40), left(COALESCE(v_back, '(nulo)'), 40);
    END IF;
  END LOOP;
  SELECT count(*) INTO v_id FROM lab.dyn_probe;
  IF v_id <> array_length(v_vals, 1) THEN
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-01 FAIL: filas=% (esperado %; posible inyección consumada)',
      v_id, array_length(v_vals, 1);
  END IF;
  IF v_fail > 0 THEN
    RAISE NOTICE 'DYN-01 RESULTADO: % valores hostiles NO neutralizados', v_fail;
  ELSE
    RAISE NOTICE 'DYN-01 RESULTADO: 8/8 valores hostiles guardados como datos exactos';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'DYN-01 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DYN-02 | identificador hostil vía %I se neutraliza (error, nunca ejecución).
SET ROLE crud_admin;
DO $$
DECLARE
  v_n integer;
  v_fail integer := 0;
BEGIN
  CALL lab.dyn_safe_ident_count('dyn_probe', v_n);
  IF v_n <> 8 THEN
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-02 FAIL: ident válido cuenta % (esperado 8)', v_n;
  ELSE
    RAISE NOTICE 'DYN-02 OK: ident válido dyn_probe cuenta 8';
  END IF;
  BEGIN
    CALL lab.dyn_safe_ident_count('dyn_probe; DROP TABLE lab.dyn_probe --', v_n);
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-02 FAIL: ident con ; debió dar error';
  EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'DYN-02 OK: ident con ; neutralizado (% %)', SQLSTATE, SQLERRM;
  END;
  BEGIN
    CALL lab.dyn_safe_ident_count('dyn_probe" WHERE "1"="1', v_n);
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-02 FAIL: ident con comillas debió dar error';
  EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'DYN-02 OK: ident con comillas neutralizado (% %)', SQLSTATE, SQLERRM;
  END;
  BEGIN
    CALL lab.dyn_safe_ident_count('pg_shadow', v_n);
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-02 FAIL: ident fuera de lab debió dar error';
  EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'DYN-02 OK: ident fuera de lab neutralizado (% %)', SQLSTATE, SQLERRM;
  END;
  IF v_fail > 0 THEN
    RAISE NOTICE 'DYN-02 RESULTADO: % fallo(s) en quoting de identificadores', v_fail;
  ELSE
    RAISE NOTICE 'DYN-02 RESULTADO: %%I neutraliza identificadores (1 válido + 3 hostiles)';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'DYN-02 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DYN-03 | el señuelo inseguro SÍ inyecta (prueba de que el detector no es vacuo).
-- Solo crud_admin lo ejecuta; ningún rol de negocio tiene EXECUTE sobre él.
SET ROLE crud_admin;
DO $$
DECLARE
  v_hostil text := ''' OR ''1''=''1';
  v_seguro integer;
  v_riesgo integer;
BEGIN
  CALL lab.dyn_safe_count(v_hostil, v_seguro);
  CALL lab.dyn_unsafe_count(v_hostil, v_riesgo);
  IF v_seguro = 0 AND v_riesgo = 8 THEN
    RAISE NOTICE 'DYN-03 OK: seguro=0 (dato) vs inseguro=8 (tautología): la concatenación inyecta de verdad';
  ELSE
    RAISE NOTICE 'DYN-03 FAIL: seguro=% inseguro=% (esperado 0/8)', v_seguro, v_riesgo;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'DYN-03 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DYN-04 | scan estático: EXECUTE dinámico sin format/quote_* = FAIL.
-- Debe marcar SOLO el señuelo; los 12 fixtures (sin EXECUTE) y los 3 seguros
-- (format %I; USING se prueba por comportamiento en DYN-01/DYN-05) pasan.
-- Misma limpieza que T3 (stripper corregido + minúsculas).
DO $$
DECLARE
  r RECORD;
  v_clean text;
  v_exec boolean;
  v_seguro boolean;
  v_fail integer := 0;
  v_marcados text[] := '{}';
BEGIN
  FOR r IN
    SELECT p.proname, pg_get_functiondef(p.oid) AS def
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'lab'
      AND (p.proname LIKE 'producto\_%' OR p.proname LIKE 'detalle\_factura\_%'
           OR p.proname LIKE 'ticket\_%' OR p.proname LIKE 'dyn\_%')
  LOOP
    v_clean := regexp_replace(r.def, '/\*.*?\*/', ' ', 'gs');
    v_clean := regexp_replace(v_clean, '--[^\n]*', ' ', 'g');
    v_clean := regexp_replace(v_clean, '''(''''|[^''])*''', ' ', 'g');
    v_clean := lower(v_clean);
    v_exec := (v_clean ~ '\mexecute\s');
    -- Criterio ADR-013 estático: identificadores vía format()/quote_ident() o
    -- literales vía quote_literal(). USING (valores parametrizados) se verifica
    -- por comportamiento en DYN-01/DYN-05, no por texto: un EXECUTE solo de
    -- identificadores (p. ej. dyn_safe_ident_count) no necesita USING.
    v_seguro := (v_clean ~ 'format\s*\(') OR (v_clean ~ 'quote_ident')
                OR (v_clean ~ 'quote_literal');
    IF v_exec AND NOT v_seguro THEN
      v_marcados := v_marcados || r.proname;
      IF r.proname = 'dyn_unsafe_count' THEN
        RAISE NOTICE 'DYN-04 OK-detección: señuelo dyn_unsafe_count marcado como FAIL esperado';
      ELSE
        v_fail := v_fail + 1;
        RAISE NOTICE 'DYN-04 FAIL: % usa EXECUTE sin format/quote_ident/quote_literal', r.proname;
      END IF;
    END IF;
  END LOOP;
  IF NOT ('dyn_unsafe_count' = ANY (v_marcados)) THEN
    v_fail := v_fail + 1;
    RAISE NOTICE 'DYN-04 FAIL-detector: el scan NO marcó el señuelo (detector vacuo)';
  END IF;
  IF v_fail > 0 THEN
    RAISE NOTICE 'DYN-04 RESULTADO: % hallazgo(s) fuera del señuelo', v_fail;
  ELSE
    RAISE NOTICE 'DYN-04 RESULTADO: scan marca solo el señuelo; 12 fixtures + 3 seguros limpios';
  END IF;
END $$;

-- DYN-05 | USING no reinterpreta: valor con %I/%L/$1 ya probado exacto en DYN-01 (#5).
-- Chequeo explícito de que el plan no depende del contenido del valor.
SET ROLE crud_admin;
DO $$
DECLARE
  v_n integer;
BEGIN
  CALL lab.dyn_safe_count('100% legitimo %I %L $1 sin interpretar', v_n);
  IF v_n = 1 THEN
    RAISE NOTICE 'DYN-05 OK: USING cuenta el valor literal con %%I/%%L/$1 sin reinterpretar';
  ELSE
    RAISE NOTICE 'DYN-05 FAIL: conteo=% (esperado 1)', v_n;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'DYN-05 FAIL inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Limpieza T5 (como owner): señuelo + seguros + sonda desaparecen por completo.
SET ROLE crud_admin;
DROP PROCEDURE IF EXISTS lab.dyn_unsafe_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_ident_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_count(text, integer);
DROP PROCEDURE IF EXISTS lab.dyn_safe_insert(integer, text);
DROP TABLE IF EXISTS lab.dyn_probe;
RESET ROLE;
DO $$
DECLARE
  v_rest integer;
BEGIN
  SELECT count(*) INTO v_rest FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname LIKE 'dyn\_%';
  SELECT count(*) + v_rest INTO v_rest FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'lab' AND c.relname LIKE 'dyn\_%';
  IF v_rest > 0 THEN
    RAISE NOTICE 'DYN-LIMPIEZA FAIL: quedan % objeto(s) dyn_*', v_rest;
  ELSE
    RAISE NOTICE 'DYN-LIMPIEZA OK: cero residuos (ni señuelo ni sonda ni seguros)';
  END IF;
END $$;
