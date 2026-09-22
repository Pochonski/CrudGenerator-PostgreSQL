-- tests/security/02_invoker_vs_definer.sql
-- Fase 0 — Experimento comparativo ADR-011 (Joseph). Decisión NO cerrada.
-- Misma lógica, dos modelos. Muestra por qué INVOKER es la hipótesis de trabajo
-- y qué riesgo introduce DEFINER. Ejecutar como crud_admin; lee los NOTICE.
-- Requiere: fixtures/02_schema.sql (usa lab.producto).

SET ROLE crud_admin;

DROP PROCEDURE IF EXISTS lab.exp_invoker_insert(integer, text, numeric);
DROP PROCEDURE IF EXISTS lab.exp_definer_insert(integer, text, numeric);

CREATE PROCEDURE lab.exp_invoker_insert(p_id integer, p_nombre text, p_precio numeric)
  LANGUAGE plpgsql SECURITY INVOKER SET search_path = lab, pg_temp
AS $$ BEGIN INSERT INTO lab.producto(id_producto,nombre,precio) VALUES (p_id,p_nombre,p_precio); END; $$;

CREATE PROCEDURE lab.exp_definer_insert(p_id integer, p_nombre text, p_precio numeric)
  LANGUAGE plpgsql SECURITY DEFINER SET search_path = lab, pg_temp
AS $$ BEGIN INSERT INTO lab.producto(id_producto,nombre,precio) VALUES (p_id,p_nombre,p_precio); END; $$;

-- Ambos ejecutables por vendedor; tabla SOLO accesible para admin en este experimento
REVOKE ALL ON TABLE lab.producto FROM crud_vendedor;
GRANT USAGE ON SCHEMA lab TO crud_vendedor;
GRANT EXECUTE ON PROCEDURE lab.exp_invoker_insert(integer,text,numeric) TO crud_vendedor;
GRANT EXECUTE ON PROCEDURE lab.exp_definer_insert(integer,text,numeric) TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.producto TO crud_admin;
RESET ROLE;

-- EXP-01: INVOKER sin permiso de tabla → debe FALLAR (42501). Prueba mínimo privilegio.
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.exp_invoker_insert(201, 'ExpInv', 1.00);
  RAISE NOTICE 'EXP-01: INVOKER permitió sin permiso de tabla (NO esperado bajo hipótesis)';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'EXP-01 OK: INVOKER bloquea sin permiso de tabla (42501)';
WHEN OTHERS THEN RAISE NOTICE 'EXP-01 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- EXP-02: DEFINER sin permiso de tabla → debe PERMITIR (hereda owner). Muestra elevación.
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.exp_definer_insert(202, 'ExpDef', 2.00);
  RAISE NOTICE 'EXP-02: DEFINER permitió sin permiso de tabla (elevación vía owner)';
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'EXP-02 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Limpieza y restauración de la matriz estándar
SET ROLE crud_admin;
DELETE FROM lab.producto WHERE id_producto IN (201, 202);
DROP PROCEDURE lab.exp_invoker_insert(integer, text, numeric);
DROP PROCEDURE lab.exp_definer_insert(integer, text, numeric);
-- Restaura permisos de la matriz (duplica 04_grants.sql para lab.producto)
GRANT SELECT, INSERT ON lab.producto TO crud_vendedor;
RESET ROLE;
