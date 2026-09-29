-- tests/security/06_revoke_public_audit.sql
-- T4 — Higiene PUBLIC + regresión de REVOKE (Joseph).
-- Demuestra sobre los 8 fixtures que EXECUTE no fuga por PUBLIC, que cada rol
-- tiene exactamente los EXECUTE de la matriz, y que un ciclo REVOKE→GRANT deja
-- el entorno idéntico (T1 detectó una fuga PUBLIC oculta tras la capa de tabla).
-- Dos niveles complementarios (no equivalentes):
--   has_function_privilege(...) → privilegio ACL real (detecta fugas aunque el
--                                  CALL falle después por la capa de tabla);
--   SET ROLE + CALL             → comportamiento efectivo (42501 real).
-- Solo crea/destruye un señuelo temporal lab.pub_leak_decoy (nunca tabla_virgen).
-- Todo GRANT/REVOKE del ciclo REV-01 se restaura; datos de prueba se limpian.
-- Idempotente y re-ejecutable contra los procedures reales de Joyce.
-- Requiere: fixtures/04_grants.sql + 06_composite_pk_fixtures.sql.

-- PUB-01 | PUBLIC sin EXECUTE en los 8 fixtures (ACL real, no comportamiento).
-- proacl NULL significa ACL por defecto → filtra EXECUTE a PUBLIC → FAIL.
DO $$
DECLARE
  r RECORD;
  v_fail integer := 0;
  v_pub boolean;
  v_acl text;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig,
           ('lab.' || e.proc_name || '(' || replace(e.sig, ' ', '') || ')') AS reg,
           p.proacl
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
  LOOP
    -- PUBLIC en el ACL aparece como entrada sin grantee ({...,=X/...}).
    -- proacl NULL es el ACL por defecto, que también filtra EXECUTE a PUBLIC.
    v_pub := (r.proacl IS NULL OR r.proacl::text LIKE '{=X/%'
           OR r.proacl::text LIKE '%,=X/%');
    v_acl := COALESCE(r.proacl::text, '(ACL por defecto)');
    IF v_pub THEN
      v_fail := v_fail + 1;
      RAISE NOTICE 'PUB-01 FAIL: % PUBLIC con EXECUTE (ACL=[%]). Fuga como la de T1.',
        r.reg, v_acl;
    ELSE
      RAISE NOTICE 'PUB-01 OK: % PUBLIC sin EXECUTE', r.reg;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'PUB-01 RESULTADO: % procedure(s) con fuga a PUBLIC', v_fail;
  ELSE
    RAISE NOTICE 'PUB-01 RESULTADO: 8/8 sin EXECUTE para PUBLIC';
  END IF;
END $$;

-- PUB-02 | matriz EXECUTE exacta por rol (24 checks ACL, sin depender del CALL).
DO $$
DECLARE
  r RECORD;
  v_tiene boolean;
  v_fail integer := 0;
  v_ok integer := 0;
BEGIN
  FOR r IN
    SELECT e.proc_name, e.sig, e.rol, e.esperado,
           ('lab.' || e.proc_name || '(' || replace(e.sig, ' ', '') || ')') AS reg
    FROM (VALUES
      ('producto_insertar', 'integer, text, numeric', 'crud_vendedor', true),
      ('producto_insertar', 'integer, text, numeric', 'crud_supervisor', true),
      ('producto_insertar', 'integer, text, numeric', 'crud_administrador', true),
      ('producto_consultar', 'integer, text, numeric', 'crud_vendedor', true),
      ('producto_consultar', 'integer, text, numeric', 'crud_supervisor', true),
      ('producto_consultar', 'integer, text, numeric', 'crud_administrador', true),
      ('producto_actualizar', 'integer, text, numeric', 'crud_vendedor', false),
      ('producto_actualizar', 'integer, text, numeric', 'crud_supervisor', true),
      ('producto_actualizar', 'integer, text, numeric', 'crud_administrador', true),
      ('producto_eliminar', 'integer', 'crud_vendedor', false),
      ('producto_eliminar', 'integer', 'crud_supervisor', false),
      ('producto_eliminar', 'integer', 'crud_administrador', true),
      ('detalle_factura_insertar', 'integer, integer, integer', 'crud_vendedor', true),
      ('detalle_factura_insertar', 'integer, integer, integer', 'crud_supervisor', true),
      ('detalle_factura_insertar', 'integer, integer, integer', 'crud_administrador', true),
      ('detalle_factura_consultar', 'integer, integer, integer', 'crud_vendedor', true),
      ('detalle_factura_consultar', 'integer, integer, integer', 'crud_supervisor', true),
      ('detalle_factura_consultar', 'integer, integer, integer', 'crud_administrador', true),
      ('detalle_factura_actualizar', 'integer, integer, integer', 'crud_vendedor', false),
      ('detalle_factura_actualizar', 'integer, integer, integer', 'crud_supervisor', true),
      ('detalle_factura_actualizar', 'integer, integer, integer', 'crud_administrador', true),
      ('detalle_factura_eliminar', 'integer, integer', 'crud_vendedor', false),
      ('detalle_factura_eliminar', 'integer, integer', 'crud_supervisor', false),
      ('detalle_factura_eliminar', 'integer, integer', 'crud_administrador', true)
    ) AS e(proc_name, sig, rol, esperado)
  LOOP
    v_tiene := has_function_privilege(r.rol, r.reg, 'EXECUTE');
    IF v_tiene = r.esperado THEN
      v_ok := v_ok + 1;
    ELSE
      v_fail := v_fail + 1;
      RAISE NOTICE 'PUB-02 FAIL: % rol=% EXECUTE=% (esperado %)',
        r.reg, r.rol, v_tiene, r.esperado;
    END IF;
  END LOOP;
  IF v_fail > 0 THEN
    RAISE NOTICE 'PUB-02 RESULTADO: %/% celdas correctas, % divergencias', v_ok, v_ok + v_fail, v_fail;
  ELSE
    RAISE NOTICE 'PUB-02 RESULTADO: 24/24 celdas EXECUTE exactas';
  END IF;
END $$;

-- REV-01 | regresión controlada REVOKE→GRANT sobre producto_actualizar/supervisor.
-- ACL (has_function_privilege) + comportamiento (SET ROLE + CALL, 42501 real).
-- Al final restaura el GRANT y verifica matriz vecina + PUBLIC + limpieza.
-- Fila de prueba 701 reservada para este archivo.
SET ROLE crud_admin;
DELETE FROM lab.producto WHERE id_producto = 701;
INSERT INTO lab.producto(id_producto, nombre, precio) VALUES (701, 'RevT4', 9.99);
RESET ROLE;

-- Paso 1: estado inicial correcto (ACL + comportamiento)
DO $$
BEGIN
  IF NOT has_function_privilege('crud_supervisor',
      'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE') THEN
    RAISE NOTICE 'REV-01 FAIL paso 1: supervisor debería tener EXECUTE inicial';
  ELSE
    RAISE NOTICE 'REV-01 OK paso 1: EXECUTE inicial presente (ACL)';
  END IF;
END $$;
SET ROLE crud_supervisor;
DO $$
BEGIN
  CALL lab.producto_actualizar(701, 'RevT4b', 10.99);
  RAISE NOTICE 'REV-01 OK paso 1b: CALL inicial funciona (comportamiento)';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'REV-01 FAIL paso 1b: CALL inicial falló: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Paso 2: REVOKE + verificación de desaparición (ACL + comportamiento 42501)
REVOKE EXECUTE ON PROCEDURE lab.producto_actualizar(integer, text, numeric)
  FROM crud_supervisor;
DO $$
DECLARE
  v_pub boolean;
BEGIN
  IF has_function_privilege('crud_supervisor',
      'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE') THEN
    RAISE NOTICE 'REV-01 FAIL paso 2: EXECUTE sobrevivió al REVOKE';
  ELSE
    RAISE NOTICE 'REV-01 OK paso 2: EXECUTE desaparece tras REVOKE (ACL)';
  END IF;
  SELECT (p.proacl IS NULL OR p.proacl::text LIKE '{=X/%'
       OR p.proacl::text LIKE '%,=X/%') INTO v_pub
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname = 'producto_actualizar'
    AND p.oid::regprocedure::text = 'lab.producto_actualizar(integer,text,numeric)';
  IF v_pub THEN
    RAISE NOTICE 'REV-01 FAIL paso 2b: PUBLIC ganó EXECUTE con el REVOKE';
  ELSE
    RAISE NOTICE 'REV-01 OK paso 2b: PUBLIC sigue sin EXECUTE';
  END IF;
END $$;
SET ROLE crud_supervisor;
DO $$
BEGIN
  CALL lab.producto_actualizar(701, 'RevT4c', 11.99);
  RAISE NOTICE 'REV-01 FAIL paso 2c: CALL debió ser rechazado tras REVOKE';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'REV-01 OK paso 2c: CALL rechazado con 42501 real tras REVOKE';
WHEN OTHERS THEN
  RAISE NOTICE 'REV-01 FAIL paso 2c: SQLSTATE distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Paso 3: restauración exacta del GRANT original + verificación de retorno
GRANT EXECUTE ON PROCEDURE lab.producto_actualizar(integer, text, numeric)
  TO crud_supervisor;
DO $$
DECLARE
  v_sup boolean;
  v_adm boolean;
  v_ven boolean;
  v_pub boolean;
BEGIN
  v_sup := has_function_privilege('crud_supervisor',
    'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE');
  v_adm := has_function_privilege('crud_administrador',
    'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE');
  v_ven := has_function_privilege('crud_vendedor',
    'lab.producto_actualizar(integer,text,numeric)', 'EXECUTE');
  SELECT (p.proacl IS NULL OR p.proacl::text LIKE '{=X/%'
       OR p.proacl::text LIKE '%,=X/%') INTO v_pub
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname = 'producto_actualizar'
    AND p.oid::regprocedure::text = 'lab.producto_actualizar(integer,text,numeric)';
  IF v_sup AND v_adm AND NOT v_ven AND NOT v_pub THEN
    RAISE NOTICE 'REV-01 OK paso 3: privilegio vuelve solo a supervisor (vecinos intactos, PUBLIC bloqueado)';
  ELSE
    RAISE NOTICE 'REV-01 FAIL paso 3: sup=% adm=% ven=% pub=% (esperado t/t/f/f)',
      v_sup, v_adm, v_ven, v_pub;
  END IF;
END $$;
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_nombre text;
  v_precio numeric;
BEGIN
  CALL lab.producto_actualizar(701, 'RevT4d', 12.99);
  CALL lab.producto_consultar(701, v_nombre, v_precio);
  IF v_nombre = 'RevT4d' AND v_precio = 12.99 THEN
    RAISE NOTICE 'REV-01 OK paso 3b: CALL vuelve a funcionar tras GRANT';
  ELSE
    RAISE NOTICE 'REV-01 FAIL paso 3b: datos=% % tras restaurar', v_nombre, v_precio;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'REV-01 FAIL paso 3b: CALL falló tras restaurar: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Limpieza REV-01 (como owner; fila 701 reservada de este archivo)
SET ROLE crud_admin;
DELETE FROM lab.producto WHERE id_producto = 701;
RESET ROLE;

-- PUB-03 | señuelo con fuga PUBLIC: la auditoría debe marcar FAIL, luego OK tras
-- REVOKE, y el señuelo debe desaparecer. Nunca usa tabla_virgen.
SET ROLE crud_admin;
DROP PROCEDURE IF EXISTS lab.pub_leak_decoy(integer);
CREATE PROCEDURE lab.pub_leak_decoy(p_id integer)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  RAISE NOTICE 'decoy %', p_id;
END;
$$;
RESET ROLE;
GRANT EXECUTE ON PROCEDURE lab.pub_leak_decoy(integer) TO PUBLIC;
DO $$
DECLARE
  v_pub boolean;
BEGIN
  SELECT (p.proacl IS NULL OR p.proacl::text LIKE '{=X/%'
       OR p.proacl::text LIKE '%,=X/%') INTO v_pub
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname = 'pub_leak_decoy'
    AND p.oid::regprocedure::text = 'lab.pub_leak_decoy(integer)';
  IF v_pub THEN
    RAISE NOTICE 'PUB-03 OK-detección: fuga PUBLIC en señuelo detectada como FAIL esperado';
  ELSE
    RAISE NOTICE 'PUB-03 FAIL-detección: la auditoría NO ve la fuga PUBLIC del señuelo';
  END IF;
END $$;
REVOKE ALL ON PROCEDURE lab.pub_leak_decoy(integer) FROM PUBLIC;
DO $$
DECLARE
  v_pub boolean;
BEGIN
  SELECT (p.proacl IS NULL OR p.proacl::text LIKE '{=X/%'
       OR p.proacl::text LIKE '%,=X/%') INTO v_pub
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'lab' AND p.proname = 'pub_leak_decoy'
    AND p.oid::regprocedure::text = 'lab.pub_leak_decoy(integer)';
  IF v_pub THEN
    RAISE NOTICE 'PUB-03 FAIL-corrección: PUBLIC conserva EXECUTE tras REVOKE';
  ELSE
    RAISE NOTICE 'PUB-03 OK-corrección: tras REVOKE, PUBLIC sin EXECUTE';
  END IF;
END $$;
SET ROLE crud_admin;
DROP PROCEDURE lab.pub_leak_decoy(integer);
RESET ROLE;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'lab' AND p.proname = 'pub_leak_decoy') THEN
    RAISE NOTICE 'PUB-03 FAIL-limpieza: señuelo sobrevivió';
  ELSE
    RAISE NOTICE 'PUB-03 OK-limpieza: señuelo eliminado, sin basura';
  END IF;
END $$;
