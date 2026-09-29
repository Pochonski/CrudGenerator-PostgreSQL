-- tests/fixtures/08_special_nopk_fixtures.sql
-- T6 — SECURITY FIXTURES tipos especiales + tabla sin PK (Joseph).
-- ⚠️  ESTOS PROCEDURES NO SON LA SOLUCIÓN DEL PROYECTO.
-- Son fixtures manuales SOLO para validar GRANT/REVOKE/EXECUTE sin esperar al
-- generador de Joyce. El generador real los reemplazará (ADR-007).
--
-- Parte A — lab.catalogo_especial (quoting + jsonb/boolean/date/numeric/identity):
--   insertar exige los 5 valores (los DEFAULT del esquema se verifican por
--   separado en la matriz); id BY DEFAULT se omite y RETURNING lo devuelve.
--   Fila inexistente → P0002 (convención fixtures).
--
-- Parte B — lab.bitacora (SIN PK). POLÍTICA PROVISIONAL, NO definitiva
-- (ADR-009 pendiente, CR-JOYCE-003 sin respuesta de Joyce/equipo):
--   * SÍ se fixturea: insertar (sin RETURNING de identidad: no hay PK) y
--     contar_por_sesion (agregado por criterio, no READ por fila).
--   * NO se fixturea: actualizar/eliminar por fila ni READ multi-fila vía CALL
--     (un PROCEDURE con CALL no devuelve result-set; ctid es físico e inestable
--     y NO se usa como identidad). La matriz verifica su AUSENCIA (42883).
--   * Cuando Joyce/equipo decidan (solo aplicables / not_applicable / listar),
--     este fixture se reemplaza SIN cambiar la matriz de roles.
-- Requiere: 02_schema.sql + 04_grants.sql (si se re-ejecuta 04, re-ejecutar este).
-- Ejecutar como crud_admin (owner). Idempotente. NO toca lab.tabla_virgen.

SET ROLE crud_admin;

-- Limpieza previa (firmas fijas del fixture)
DROP PROCEDURE IF EXISTS lab.catalogo_especial_insertar(integer, text, numeric, boolean, jsonb, date);
DROP PROCEDURE IF EXISTS lab.catalogo_especial_consultar(integer, text, numeric, boolean, jsonb, date);
DROP PROCEDURE IF EXISTS lab.catalogo_especial_actualizar(integer, text, numeric, boolean, jsonb, date);
DROP PROCEDURE IF EXISTS lab.catalogo_especial_eliminar(integer);
DROP PROCEDURE IF EXISTS lab.bitacora_insertar(integer, text);
DROP PROCEDURE IF EXISTS lab.bitacora_contar(integer, integer);

-- A.INSERT: columnas quotadas ("Nombre Ítem", "precio$") con %I mental vía
-- identificadores estáticos calificados; id BY DEFAULT omitido a propósito.
CREATE PROCEDURE lab.catalogo_especial_insertar(
  INOUT p_id integer DEFAULT NULL,
  IN p_nombre text DEFAULT NULL,
  IN p_precio numeric DEFAULT NULL,
  IN p_activo boolean DEFAULT NULL,
  IN p_datos jsonb DEFAULT NULL,
  IN p_fecha date DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  INSERT INTO lab.catalogo_especial("Nombre Ítem", "precio$", activo, datos, fecha)
  VALUES (p_nombre, p_precio, p_activo, p_datos, p_fecha)
  RETURNING lab.catalogo_especial.id INTO p_id;
END;
$$;

-- A.READ por PK vía INOUT (limitación CALL documentada, CR-JOYCE-001).
CREATE PROCEDURE lab.catalogo_especial_consultar(
  IN p_id integer,
  INOUT p_nombre text DEFAULT NULL,
  INOUT p_precio numeric DEFAULT NULL,
  INOUT p_activo boolean DEFAULT NULL,
  INOUT p_datos jsonb DEFAULT NULL,
  INOUT p_fecha date DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  SELECT c."Nombre Ítem", c."precio$", c.activo, c.datos, c.fecha
    INTO p_nombre, p_precio, p_activo, p_datos, p_fecha
  FROM lab.catalogo_especial AS c WHERE c.id = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'catalogo_especial % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- A.UPDATE por PK (todos los valores suministrados).
CREATE PROCEDURE lab.catalogo_especial_actualizar(
  IN p_id integer,
  IN p_nombre text DEFAULT NULL,
  IN p_precio numeric DEFAULT NULL,
  IN p_activo boolean DEFAULT NULL,
  IN p_datos jsonb DEFAULT NULL,
  IN p_fecha date DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  UPDATE lab.catalogo_especial AS c
     SET "Nombre Ítem" = p_nombre, "precio$" = p_precio, activo = p_activo,
         datos = p_datos, fecha = p_fecha
   WHERE c.id = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'catalogo_especial % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- A.DELETE por PK.
CREATE PROCEDURE lab.catalogo_especial_eliminar(p_id integer)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  DELETE FROM lab.catalogo_especial AS c WHERE c.id = p_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'catalogo_especial % no existe', p_id USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- B.INSERT sin PK: sin RETURNING de identidad (no existe); creado_en usa DEFAULT.
CREATE PROCEDURE lab.bitacora_insertar(
  IN p_id_sesion integer DEFAULT NULL,
  IN p_mensaje text DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  INSERT INTO lab.bitacora(id_sesion, mensaje) VALUES (p_id_sesion, p_mensaje);
END;
$$;

-- B.COUNT por criterio (provisional): agregado, no READ por fila.
-- Cuando el equipo decida el READ sin PK, este fixture se reemplaza.
CREATE PROCEDURE lab.bitacora_contar(
  IN p_id_sesion integer DEFAULT NULL,
  INOUT p_n integer DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  SELECT count(*) INTO p_n FROM lab.bitacora AS b WHERE b.id_sesion = p_id_sesion;
END;
$$;

COMMENT ON PROCEDURE lab.catalogo_especial_insertar(integer, text, numeric, boolean, jsonb, date) IS
  'SECURITY FIXTURE T6 (tipos especiales/quoting) — reemplazar por generador de Joyce.';
COMMENT ON PROCEDURE lab.bitacora_insertar(integer, text) IS
  'SECURITY FIXTURE T6 (sin PK, POLÍTICA PROVISIONAL) — reemplaza al decidirse CR-JOYCE-003.';
COMMENT ON PROCEDURE lab.bitacora_contar(integer, integer) IS
  'SECURITY FIXTURE T6 (sin PK, agregado provisional, no es READ por fila).';

-- Higiene PUBLIC (lección T4): revocar lo que los nuevos procedures traen por defecto.
REVOKE ALL ON PROCEDURE lab.catalogo_especial_insertar(integer, text, numeric, boolean, jsonb, date) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.catalogo_especial_consultar(integer, text, numeric, boolean, jsonb, date) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.catalogo_especial_actualizar(integer, text, numeric, boolean, jsonb, date) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.catalogo_especial_eliminar(integer) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.bitacora_insertar(integer, text) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.bitacora_contar(integer, integer) FROM PUBLIC;

-- Matriz GRANT hipótesis SECURITY INVOKER (doble llave).
GRANT USAGE ON SCHEMA lab TO crud_vendedor, crud_supervisor, crud_administrador;

GRANT EXECUTE ON PROCEDURE lab.catalogo_especial_insertar(integer, text, numeric, boolean, jsonb, date)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.catalogo_especial_consultar(integer, text, numeric, boolean, jsonb, date)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.catalogo_especial_actualizar(integer, text, numeric, boolean, jsonb, date)
  TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.catalogo_especial_eliminar(integer)
  TO crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.bitacora_insertar(integer, text)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.bitacora_contar(integer, integer)
  TO crud_vendedor, crud_supervisor, crud_administrador;

GRANT SELECT, INSERT                 ON lab.catalogo_especial TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON lab.catalogo_especial TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.catalogo_especial TO crud_administrador;
GRANT SELECT, INSERT                 ON lab.bitacora TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON lab.bitacora TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.bitacora TO crud_administrador;

-- lab.tabla_virgen queda sin grants de negocio a propósito (reservada).

RESET ROLE;
