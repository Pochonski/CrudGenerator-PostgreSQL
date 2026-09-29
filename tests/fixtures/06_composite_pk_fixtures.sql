-- tests/fixtures/06_composite_pk_fixtures.sql
-- Fase 0 — SECURITY FIXTURES PK compuesta (Joseph).
-- ⚠️  ESTOS PROCEDURES NO SON LA SOLUCIÓN DEL PROYECTO.
-- Son fixtures manuales SOLO para validar GRANT/REVOKE/EXECUTE sobre
-- lab.detalle_factura sin esperar al generador de Joyce. El generador
-- real los reemplazará (misma convención de nombres ADR-007).
-- Requiere: 02_schema.sql + 04_grants.sql (USAGE base; si se re-ejecuta
-- 04_grants.sql, re-ejecutar este archivo para restaurar sus GRANTs).
-- Ejecutar como crud_admin (owner). Idempotente. NO toca lab.tabla_virgen.

SET ROLE crud_admin;

-- Limpieza previa (firmas fijas del fixture)
DROP PROCEDURE IF EXISTS lab.detalle_factura_insertar(integer, integer, integer);
DROP PROCEDURE IF EXISTS lab.detalle_factura_consultar(integer, integer, integer);
DROP PROCEDURE IF EXISTS lab.detalle_factura_actualizar(integer, integer, integer);
DROP PROCEDURE IF EXISTS lab.detalle_factura_eliminar(integer, integer);

-- INSERT fixture (PK compuesta completa como entrada)
CREATE PROCEDURE lab.detalle_factura_insertar(
  p_id_factura integer, p_id_producto integer, p_cantidad integer
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  INSERT INTO lab.detalle_factura(id_factura, id_producto, cantidad)
  VALUES (p_id_factura, p_id_producto, p_cantidad);
END;
$$;

-- READ fixture (limitación documentada, misma que producto_consultar):
-- PROCEDURE no puede devolver result-set con CALL; este fixture devuelve UNA fila
-- por PK COMPLETA vía parámetros INOUT. El READ genérico multi-fila es CR-JOYCE-001.
-- Ambas columnas de la PK son criterio obligatorio (AND); nunca una sola.
CREATE PROCEDURE lab.detalle_factura_consultar(
  IN p_id_factura integer, IN p_id_producto integer,
  INOUT p_cantidad integer DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  SELECT d.cantidad INTO p_cantidad
  FROM lab.detalle_factura AS d
  WHERE d.id_factura = p_id_factura
    AND d.id_producto = p_id_producto;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'detalle_factura (%, %) no existe', p_id_factura, p_id_producto
      USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- UPDATE fixture (por PK compuesta completa)
CREATE PROCEDURE lab.detalle_factura_actualizar(
  p_id_factura integer, p_id_producto integer, p_cantidad integer
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  UPDATE lab.detalle_factura AS d
     SET cantidad = p_cantidad
   WHERE d.id_factura = p_id_factura
     AND d.id_producto = p_id_producto;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'detalle_factura (%, %) no existe', p_id_factura, p_id_producto
      USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- DELETE fixture (por PK compuesta completa)
CREATE PROCEDURE lab.detalle_factura_eliminar(
  p_id_factura integer, p_id_producto integer
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  DELETE FROM lab.detalle_factura AS d
   WHERE d.id_factura = p_id_factura
     AND d.id_producto = p_id_producto;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'detalle_factura (%, %) no existe', p_id_factura, p_id_producto
      USING ERRCODE = 'P0002';
  END IF;
END;
$$;

COMMENT ON PROCEDURE lab.detalle_factura_insertar(integer, integer, integer) IS
  'SECURITY FIXTURE Fase 0 (PK compuesta) — reemplazar por generador de Joyce.';
COMMENT ON PROCEDURE lab.detalle_factura_consultar(integer, integer, integer) IS
  'SECURITY FIXTURE Fase 0 (PK compuesta) — READ por PK completa vía INOUT; READ genérico pendiente (CR-JOYCE-001).';

-- Higiene PUBLIC: los procedures recién creados traen EXECUTE para PUBLIC por
-- defecto. Como este archivo se ejecuta DESPUÉS de 04_grants.sql, hay que
-- revocarlos aquí explícitamente (si no, INT-08 detecta EXECUTE filtrado a
-- vendedor vía PUBLIC aunque la capa de tabla siga bloqueando bajo INVOKER).
REVOKE ALL ON PROCEDURE lab.detalle_factura_insertar(integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.detalle_factura_consultar(integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.detalle_factura_actualizar(integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.detalle_factura_eliminar(integer, integer) FROM PUBLIC;

-- Matriz GRANT hipótesis SECURITY INVOKER (doble llave, igual que 04_grants.sql).
-- USAGE (idempotente; ya otorgado en 04_grants.sql, se reafirma por autonomía del archivo)
GRANT USAGE ON SCHEMA lab TO crud_vendedor, crud_supervisor, crud_administrador;

-- EXECUTE selectivo sobre fixtures de lab.detalle_factura
GRANT EXECUTE ON PROCEDURE lab.detalle_factura_insertar(integer, integer, integer)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.detalle_factura_consultar(integer, integer, integer)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.detalle_factura_actualizar(integer, integer, integer)
  TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.detalle_factura_eliminar(integer, integer)
  TO crud_administrador;

-- Permisos de tabla (llave 2 bajo INVOKER)
GRANT SELECT, INSERT                 ON lab.detalle_factura TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON lab.detalle_factura TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.detalle_factura TO crud_administrador;

-- lab.tabla_virgen queda sin grants de negocio a propósito (reservada).

RESET ROLE;
