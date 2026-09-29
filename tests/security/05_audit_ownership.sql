-- tests/security/05_audit_ownership.sql
-- T3 — Auditoría owner + search_path + SECURITY (Joseph).
-- Verifica en catálogos que los procedures fixture cumplen las propiedades que
-- deberán conservar los procedures reales de Joyce (CR-JOYCE-005, ADR-011):
-- owner crud_admin, SECURITY INVOKER, SET search_path = lab, pg_temp,
-- esquema lab y referencias calificadas.
-- Solo LEE pg_proc/pg_namespace/pg_roles (+ pg_get_functiondef). No modifica
-- nada, no usa SET ROLE, no otorga GRANTs, no toca tabla_virgen.
-- Idempotente y re-ejecutable: cuando Joyce reemplace los fixtures por los
-- procedures generados, esta misma auditoría debe volver a ejecutarse. La lista
-- esperada es explícita por firma a propósito: si una firma cambia, la
-- auditoría falla en voz alta en lugar de pasar en silencio.
-- Requiere: fixtures/03_security_fixtures.sql + 06_composite_pk_fixtures.sql.

-- AUD-01 | owner = crud_admin (falla ante cualquier otro, incl. roles de negocio)
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, rol.rolname AS ownername
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
    LEFT JOIN pg_namespace n ON n.nspname = 'lab'
    LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '')
           = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
    LEFT JOIN pg_roles rol ON rol.oid = p.proowner
  LOOP
    IF r.ownername IS NULL THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-01 FAIL: lab.%(%) no existe (esperado owner crud_admin)',
        r.proc_name, r.sig;
    ELSIF r.ownername <> 'crud_admin' THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-01 FAIL: lab.%(%) owner=% (esperado crud_admin)',
        r.proc_name, r.sig, r.ownername;
    ELSE
      RAISE NOTICE 'AUD-01 OK: lab.%(%) owner=crud_admin', r.proc_name, r.sig;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'AUD-01 RESULTADO: % procedure(s) con owner incorrecto o ausente', v_fail;
  ELSE
    RAISE NOTICE 'AUD-01 RESULTADO: 8/8 owners correctos';
  END IF;
END $$;

-- AUD-02 | SECURITY INVOKER (prosecdef = false; DEFINER nunca se acepta en silencio)
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, p.prosecdef, (p.oid IS NOT NULL) AS existe
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
    LEFT JOIN pg_namespace n ON n.nspname = 'lab'
    LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '')
           = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
  LOOP
    IF NOT r.existe THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-02 FAIL: lab.%(%) no existe (esperado SECURITY INVOKER)',
        r.proc_name, r.sig;
    ELSIF r.prosecdef THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-02 FAIL: lab.%(%) es SECURITY DEFINER (esperado SECURITY INVOKER)',
        r.proc_name, r.sig;
    ELSE
      RAISE NOTICE 'AUD-02 OK: lab.%(%) SECURITY INVOKER', r.proc_name, r.sig;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'AUD-02 RESULTADO: % procedure(s) fuera de INVOKER o ausentes', v_fail;
  ELSE
    RAISE NOTICE 'AUD-02 RESULTADO: 8/8 SECURITY INVOKER';
  END IF;
END $$;

-- AUD-03 | search_path = lab, pg_temp en proconfig (ausente o distinto = FAIL;
-- un procedure sin search_path propio depende del de la sesión y NO pasa)
DO $$
DECLARE
  r RECORD;
  v_entry text;
  v_val text;
  v_parts text[];
  v_found text;
  v_ok boolean;
  v_fail integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, p.proconfig, (p.oid IS NOT NULL) AS existe
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
    LEFT JOIN pg_namespace n ON n.nspname = 'lab'
    LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '')
           = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
  LOOP
    v_ok := FALSE;
    v_found := COALESCE(array_to_string(r.proconfig, ' | '), '(sin proconfig)');
    IF r.existe AND r.proconfig IS NOT NULL THEN
      FOREACH v_entry IN ARRAY r.proconfig LOOP
        IF split_part(v_entry, '=', 1) ~* '^\s*search_path\s*$' THEN
          v_val := split_part(v_entry, '=', 2);
          SELECT array_agg(trim(b)) INTO v_parts
          FROM unnest(string_to_array(v_val, ',')) AS b;
          IF v_parts = ARRAY['lab', 'pg_temp'] THEN
            v_ok := TRUE;
          END IF;
        END IF;
      END LOOP;
    END IF;
    IF NOT r.existe THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-03 FAIL: lab.%(%) no existe (esperado search_path=lab, pg_temp)',
        r.proc_name, r.sig;
    ELSIF v_ok THEN
      RAISE NOTICE 'AUD-03 OK: lab.%(%) search_path=lab, pg_temp', r.proc_name, r.sig;
    ELSE
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-03 FAIL: lab.%(%) proconfig=[%] (esperado search_path=lab, pg_temp)',
        r.proc_name, r.sig, v_found;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'AUD-03 RESULTADO: % procedure(s) con search_path ausente o distinto', v_fail;
  ELSE
    RAISE NOTICE 'AUD-03 RESULTADO: 8/8 search_path=lab, pg_temp';
  END IF;
END $$;

-- AUD-04 | esquema = lab y nombre no ambiguo en otros esquemas
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
  v_otros integer;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, n.nspname, (p.oid IS NOT NULL) AS existe
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
    LEFT JOIN pg_namespace n ON n.nspname = 'lab'
    LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '')
           = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
  LOOP
    IF NOT r.existe THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-04 FAIL: lab.%(%) no existe (esperado esquema lab)',
        r.proc_name, r.sig;
      CONTINUE;
    END IF;
    SELECT count(DISTINCT nn.nspname) INTO v_otros
    FROM pg_proc pp JOIN pg_namespace nn ON nn.oid = pp.pronamespace
    WHERE pp.proname = r.proc_name AND nn.nspname <> 'lab';
    IF v_otros > 0 THEN
      RAISE NOTICE 'AUD-04 WARNING: % existe también en otro(s) esquema(s); la resolución calificada lab.% evita ambigüedad',
        r.proc_name, r.proc_name;
    END IF;
    RAISE NOTICE 'AUD-04 OK: lab.%(%) esquema=lab', r.proc_name, r.sig;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'AUD-04 RESULTADO: % procedure(s) ausentes en lab', v_fail;
  ELSE
    RAISE NOTICE 'AUD-04 RESULTADO: 8/8 en esquema lab';
  END IF;
END $$;

-- AUD-05 | referencias calificadas lab.<tabla> en el cuerpo + sin SQL dinámico.
-- Limpia comentarios y literales antes de buscar, para no marcar parámetros
-- (p_id, p_nombre…), alias (p, d) ni mensajes como falsos positivos.
-- Referencia no calificada tras palabra DML = FAIL; EXECUTE dinámico = WARNING.
DO $$
DECLARE
  r RECORD;
  v_def text;
  v_clean text;
  v_pat text := '((?:insert\s+into|update|delete\s+from|from|join)\s+"?(?:producto|detalle_factura|ticket|bitacora|catalogo_especial|tabla_virgen)"?(?:\s|;|,|\)|$))';
  v_hit text;
  v_fail integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, e.tabla, p.oid, (p.oid IS NOT NULL) AS existe
    FROM (VALUES
      ('producto_insertar', 'integer, text, numeric', 'producto'),
      ('producto_consultar', 'integer, text, numeric', 'producto'),
      ('producto_actualizar', 'integer, text, numeric', 'producto'),
      ('producto_eliminar', 'integer', 'producto'),
      ('detalle_factura_insertar', 'integer, integer, integer', 'detalle_factura'),
      ('detalle_factura_consultar', 'integer, integer, integer', 'detalle_factura'),
      ('detalle_factura_actualizar', 'integer, integer, integer', 'detalle_factura'),
      ('detalle_factura_eliminar', 'integer, integer', 'detalle_factura')
    ) AS e(proc_name, sig, tabla)
    LEFT JOIN pg_namespace n ON n.nspname = 'lab'
    LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = e.proc_name
         AND replace(p.oid::regprocedure::text, ' ', '')
           = replace(('lab.' || e.proc_name || '(' || e.sig || ')'), ' ', '')
  LOOP
    IF NOT r.existe THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-05 FAIL: lab.%(%) no existe (sin cuerpo que auditar)',
        r.proc_name, r.sig;
      CONTINUE;
    END IF;
    v_def := pg_get_functiondef(r.oid);
    IF position('lab.' || r.tabla IN v_def) = 0 THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-05 FAIL: lab.%(%) no referencia lab.% calificada en su definición',
        r.proc_name, r.sig, r.tabla;
      CONTINUE;
    END IF;
    v_clean := regexp_replace(v_def, '/\*.*?\*/', ' ', 'gs');
    v_clean := regexp_replace(v_clean, '--[^\n]*', ' ', 'g');
    v_clean := regexp_replace(v_clean, '''(''''|[^''])*''', ' ', 'g');
    -- Minúsculas para que la detección sea insensible a mayúsculas
    -- (substring-from es case-sensitive; los fixtures usan DML en mayúsculas).
    v_clean := lower(v_clean);
    v_hit := substring(v_clean from v_pat);
    IF v_hit IS NOT NULL THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'AUD-05 FAIL: lab.%(%) referencia no calificada dependiente de search_path: «%»',
        r.proc_name, r.sig, trim(v_hit);
      CONTINUE;
    END IF;
    IF v_clean ~* '\mexecute\s' THEN
      RAISE NOTICE 'AUD-05 WARNING: lab.%(%) usa EXECUTE dinámico; auditar quoting %%I/USING (ADR-013)',
        r.proc_name, r.sig;
    END IF;
    RAISE NOTICE 'AUD-05 OK: lab.%(%) referencias calificadas, sin SQL dinámico',
      r.proc_name, r.sig;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'AUD-05 RESULTADO: % procedure(s) con referencias sin calificar o ausentes', v_fail;
  ELSE
    RAISE NOTICE 'AUD-05 RESULTADO: 8/8 referencias calificadas';
  END IF;
END $$;
