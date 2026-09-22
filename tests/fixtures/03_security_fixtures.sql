-- tests/fixtures/03_security_fixtures.sql
-- Fase 0 — SECURITY FIXTURES (Joseph).
-- ⚠️  ESTOS PROCEDURES NO SON LA SOLUCIÓN DEL PROYECTO.
-- Son fixtures manuales SOLO para validar GRANT/REVOKE/EXECUTE sobre lab.producto
-- sin esperar al generador de Joyce. El generador real los reemplazará.
-- Requiere: 02_schema.sql. Ejecutar como crud_admin (owner).

SET ROLE crud_admin;

-- Limpieza previa (firmas fijas del fixture)
DROP PROCEDURE IF EXISTS lab.producto_insertar(integer, text, numeric);
DROP PROCEDURE IF EXISTS lab.producto_consultar(integer, text, numeric);
DROP PROCEDURE IF EXISTS lab.producto_actualizar(integer, text, numeric);
DROP PROCEDURE IF EXISTS lab.producto_eliminar(integer);

-- INSERT fixture
CREATE PROCEDURE lab.producto_insertar(p_id integer, p_nombre text, p_precio numeric)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  INSERT INTO lab.producto(id_producto, nombre, precio)
  VALUES (p_id, p_nombre, p_precio);
END;
$$;

-- READ fixture (limitación documentada):
-- PROCEDURE no puede devolver result-set con CALL; este fixture devuelve UNA fila
-- por PK vía parámetros INOUT. El READ genérico multi-fila es CR-JOYCE-001.
CREATE PROCEDURE lab.producto_consultar(
  IN p_id integer, INOUT p_nombre text DEFAULT NULL, INOUT p_precio numeric DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  SELECT p.nombre, p.precio INTO p_nombre, p_precio
  FROM lab.producto AS p WHERE p.id_producto = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'producto % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- UPDATE fixture (por PK simple)
CREATE PROCEDURE lab.producto_actualizar(p_id integer, p_nombre text, p_precio numeric)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  UPDATE lab.producto AS p
     SET nombre = p_nombre, precio = p_precio
   WHERE p.id_producto = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'producto % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- DELETE fixture (por PK simple)
CREATE PROCEDURE lab.producto_eliminar(p_id integer)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  DELETE FROM lab.producto AS p WHERE p.id_producto = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'producto % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

COMMENT ON PROCEDURE lab.producto_insertar(integer, text, numeric) IS
  'SECURITY FIXTURE Fase 0 — reemplazar por generador de Joyce.';
COMMENT ON PROCEDURE lab.producto_consultar(integer, text, numeric) IS
  'SECURITY FIXTURE Fase 0 — READ por PK vía INOUT; READ genérico pendiente (CR-JOYCE-001).';

RESET ROLE;
