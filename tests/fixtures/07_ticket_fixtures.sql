-- tests/fixtures/07_ticket_fixtures.sql
-- T2 — SECURITY FIXTURES IDENTITY/DEFAULT (Joseph). Caso 3 §9 del enunciado.
-- ⚠️  ESTOS PROCEDURES NO SON LA SOLUCIÓN DEL PROYECTO.
-- Son fixtures manuales SOLO para validar GRANT/REVOKE/EXECUTE sobre lab.ticket
-- (id_ticket GENERATED ALWAYS AS IDENTITY + DEFAULTs) sin esperar al generador
-- de Joyce. El generador real los reemplazará (misma convención ADR-007).
--
-- Convención fixture (provisional; Joyce puede ajustarla con CR-JOYCE-002/003):
--   * id_ticket NUNCA se suministra: es GENERATED ALWAYS; el valor entrante de
--     p_id_ticket se IGNORA y RETURNING lo sobrescribe con el generado por PG.
--   * p_codigo NULL significa "usar el DEFAULT del esquema" vía VALUES (DEFAULT),
--     sin hardcodear 'SIN-CODIGO' en el cuerpo.
--   * actualizar solo modifica codigo (columnas generadas/automáticas inmutables).
--   * fila inexistente → P0002 (misma convención que producto_*/detalle_factura_*).
-- Requiere: 02_schema.sql + 04_grants.sql (si se re-ejecuta 04_grants.sql,
-- re-ejecutar este archivo). Ejecutar como crud_admin (owner). Idempotente.
-- NO toca lab.tabla_virgen.

SET ROLE crud_admin;

-- Limpieza previa (firmas fijas del fixture)
DROP PROCEDURE IF EXISTS lab.ticket_insertar(integer, text, timestamptz);
DROP PROCEDURE IF EXISTS lab.ticket_consultar(integer, text, timestamptz);
DROP PROCEDURE IF EXISTS lab.ticket_actualizar(integer, text);
DROP PROCEDURE IF EXISTS lab.ticket_eliminar(integer);

-- INSERT fixture: solo codigo se suministra; id y creado_en los genera PG.
CREATE PROCEDURE lab.ticket_insertar(
  INOUT p_id_ticket integer DEFAULT NULL,
  IN p_codigo text DEFAULT NULL,
  INOUT p_creado_en timestamptz DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  IF p_codigo IS NULL THEN
    INSERT INTO lab.ticket(codigo) VALUES (DEFAULT)
    RETURNING lab.ticket.id_ticket, lab.ticket.creado_en
      INTO p_id_ticket, p_creado_en;
  ELSE
    INSERT INTO lab.ticket(codigo) VALUES (p_codigo)
    RETURNING lab.ticket.id_ticket, lab.ticket.creado_en
      INTO p_id_ticket, p_creado_en;
  END IF;
END;
$$;

-- READ fixture (limitación documentada, misma que producto_consultar):
-- PROCEDURE no puede devolver result-set con CALL; devuelve UNA fila por PK
-- vía parámetros INOUT. El READ genérico multi-fila es CR-JOYCE-001.
CREATE PROCEDURE lab.ticket_consultar(
  IN p_id_ticket integer,
  INOUT p_codigo text DEFAULT NULL,
  INOUT p_creado_en timestamptz DEFAULT NULL
)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  SELECT t.codigo, t.creado_en INTO p_codigo, p_creado_en
  FROM lab.ticket AS t WHERE t.id_ticket = p_id_ticket;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ticket % no existe', p_id_ticket USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- UPDATE fixture (solo codigo; id/creado_en no se suministran ni modifican)
CREATE PROCEDURE lab.ticket_actualizar(p_id_ticket integer, p_codigo text)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  UPDATE lab.ticket AS t
     SET codigo = p_codigo
   WHERE t.id_ticket = p_id_ticket;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ticket % no existe', p_id_ticket USING ERRCODE = 'P0002';
  END IF;
END;
$$;

-- DELETE fixture (por PK)
CREATE PROCEDURE lab.ticket_eliminar(p_id_ticket integer)
  LANGUAGE plpgsql
  SECURITY INVOKER
  SET search_path = lab, pg_temp
AS $$
BEGIN
  DELETE FROM lab.ticket AS t WHERE t.id_ticket = p_id_ticket;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ticket % no existe', p_id_ticket USING ERRCODE = 'P0002';
  END IF;
END;
$$;

COMMENT ON PROCEDURE lab.ticket_insertar(integer, text, timestamptz) IS
  'SECURITY FIXTURE T2 (IDENTITY/DEFAULT) — reemplazar por generador de Joyce.';
COMMENT ON PROCEDURE lab.ticket_consultar(integer, text, timestamptz) IS
  'SECURITY FIXTURE T2 (IDENTITY/DEFAULT) — READ por PK vía INOUT; READ genérico pendiente (CR-JOYCE-001).';

-- Higiene PUBLIC (lección T4): los procedures nuevos traen EXECUTE para PUBLIC
-- por defecto y este archivo corre DESPUÉS de 04_grants.sql.
REVOKE ALL ON PROCEDURE lab.ticket_insertar(integer, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.ticket_consultar(integer, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.ticket_actualizar(integer, text) FROM PUBLIC;
REVOKE ALL ON PROCEDURE lab.ticket_eliminar(integer) FROM PUBLIC;

-- Matriz GRANT hipótesis SECURITY INVOKER (doble llave, igual que 04/06).
GRANT USAGE ON SCHEMA lab TO crud_vendedor, crud_supervisor, crud_administrador;

GRANT EXECUTE ON PROCEDURE lab.ticket_insertar(integer, text, timestamptz)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.ticket_consultar(integer, text, timestamptz)
  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.ticket_actualizar(integer, text)
  TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE lab.ticket_eliminar(integer)
  TO crud_administrador;

GRANT SELECT, INSERT                 ON lab.ticket TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE         ON lab.ticket TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab.ticket TO crud_administrador;

-- lab.tabla_virgen queda sin grants de negocio a propósito (reservada).

RESET ROLE;
