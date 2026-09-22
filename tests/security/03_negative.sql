-- tests/security/03_negative.sql
-- Fase 0 — Pruebas negativas NEG-01..NEG-11 (Joseph).
-- Formato por prueba: ID / Objetivo / Preparación / Acción / Esperado.
-- El "Resultado real" se anota al ejecutar (ver NOTICE). Requiere fixtures completos.

-- NEG-01 | Rol sin EXECUTE → 42501
-- Prep: vendedor no tiene EXECUTE sobre producto_eliminar (04_grants.sql).
-- Acción: SET ROLE crud_vendedor; CALL lab.producto_eliminar(999).
-- Esperado: 42501 insufficient_privilege.
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_eliminar(999);
  RAISE NOTICE 'NEG-01 FALLO: debió rechazar por falta de EXECUTE';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'NEG-01 OK: 42501 sin EXECUTE';
WHEN OTHERS THEN RAISE NOTICE 'NEG-01 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-02 | Rol sin USAGE sobre esquema → 42501
-- Prep: revocar USAGE temporalmente a vendedor.
-- Acción: CALL calificado lab.producto_insertar. Esperado: 42501.
SET ROLE crud_admin;
REVOKE USAGE ON SCHEMA lab FROM crud_vendedor;
RESET ROLE;
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_insertar(301, 'SinUsage', 1.00);
  RAISE NOTICE 'NEG-02 FALLO: debió rechazar por falta de USAGE';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'NEG-02 OK: 42501 sin USAGE';
WHEN OTHERS THEN RAISE NOTICE 'NEG-02 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;
SET ROLE crud_admin;
GRANT USAGE ON SCHEMA lab TO crud_vendedor;
RESET ROLE;

-- NEG-03 | Procedure inexistente → 42883
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.no_existe(1);
  RAISE NOTICE 'NEG-03 FALLO: debió dar 42883';
EXCEPTION WHEN undefined_function THEN RAISE NOTICE 'NEG-03 OK: 42883 rutina inexistente';
WHEN OTHERS THEN RAISE NOTICE 'NEG-03 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-04 | Tabla inexistente (vía fixture dinámico mínimo, sin invadir a Joyce)
-- Acción: INSERT directo a lab.no_existe. Esperado: 42P01 undefined_table.
SET ROLE crud_admin;
DO $$
BEGIN
  EXECUTE 'INSERT INTO lab.no_existe(id) VALUES (1)';
  RAISE NOTICE 'NEG-04 FALLO: debió dar 42P01';
EXCEPTION WHEN undefined_table THEN RAISE NOTICE 'NEG-04 OK: 42P01 tabla inexistente';
WHEN OTHERS THEN RAISE NOTICE 'NEG-04 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-05 | Tabla sin PK → documentar que UPDATE/DELETE por PK no aplican (ADR-009)
-- Acción: verificar que lab.bitacora no tiene PK en catálogos.
-- Esperado: cero filas en pg_constraint para bitacora; fixtures no ofrecen UPDATE/DELETE.
DO $$
DECLARE v_n integer;
BEGIN
  SELECT count(*) INTO v_n FROM pg_constraint
   WHERE conrelid = 'lab.bitacora'::regclass AND contype = 'p';
  IF v_n = 0 THEN RAISE NOTICE 'NEG-05 OK: bitacora sin PK confirmada en catálogos';
  ELSE RAISE NOTICE 'NEG-05 FALLO: bitacora tiene PK inesperada'; END IF;
END $$;

-- NEG-06 | Procedimiento existente → pendiente Joyce (CR-JOYCE-004)
-- Acción manual cuando Joyce defina policy: re-ejecutar generate sobre producto_insertar.
-- Esperado TBD: error / reemplazo / firma. Se registra, no se inventa policy.
DO $$ BEGIN RAISE NOTICE 'NEG-06 PENDIENTE Joyce: policy de procedures existentes (CR-JOYCE-004)'; END $$;

-- NEG-07 | PK compuesta → constraint existe y es de 2 columnas
DO $$
DECLARE v_n integer;
BEGIN
  SELECT count(*) INTO v_n FROM pg_constraint
   WHERE conrelid = 'lab.detalle_factura'::regclass AND contype = 'p';
  RAISE NOTICE 'NEG-07: detalle_factura tiene % restricción(es) PK (esperado 1)', v_n;
  SELECT count(*) INTO v_n FROM pg_attribute a JOIN pg_index i
    ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
   WHERE i.indrelid = 'lab.detalle_factura'::regclass AND i.indisprimary;
  RAISE NOTICE 'NEG-07: columnas en PK compuesta = % (esperado 2)', v_n;
END $$;

-- NEG-08 | Acceso directo a tabla denegado (vendedor intenta DELETE directo)
SET ROLE crud_vendedor;
DO $$
BEGIN
  DELETE FROM lab.producto WHERE id_producto = -1;
  RAISE NOTICE 'NEG-08: DELETE directo no bloqueado a nivel tabla (revisar matriz INVOKER)';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'NEG-08 OK: DELETE directo bloqueado 42501';
WHEN OTHERS THEN RAISE NOTICE 'NEG-08 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-09 | Acceso autorizado control (admin INSERT+DELETE redondo)
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.producto_insertar(302, 'NegOK', 5.00);
  CALL lab.producto_eliminar(302);
  RAISE NOTICE 'NEG-09 OK: admin redondo INSERT+DELETE funciona';
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'NEG-09 FALLO: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-10 | Acceso no autorizado control (vendedor UPDATE) → 42501
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_actualizar(302, 'X', 1.00);
  RAISE NOTICE 'NEG-10 FALLO: debió rechazar';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'NEG-10 OK: 42501 no autorizado';
WHEN OTHERS THEN RAISE NOTICE 'NEG-10 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- NEG-11 | Quoting con nombres especiales (ADR-013) → INSERT/SELECT vía %I mental
-- Acción: INSERT directo con identificadores quotados en catalogo_especial.
SET ROLE crud_admin;
DO $$
BEGIN
  GRANT ALL ON lab.catalogo_especial TO crud_admin;
  INSERT INTO lab."catalogo_especial"("Nombre Ítem", "precio$") VALUES ('Ítem "X"', 9.99);
  RAISE NOTICE 'NEG-11 OK: quoting de "Nombre Ítem"/"precio$" funciona';
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'NEG-11 FALLO: % %', SQLSTATE, SQLERRM;
END $$;
DELETE FROM lab.catalogo_especial WHERE "Nombre Ítem" = 'Ítem "X"';
RESET ROLE;
