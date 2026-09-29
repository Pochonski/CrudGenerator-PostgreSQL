-- tests/security/04_composite_matrix.sql
-- Fase 0 — Matriz PK compuesta permitido vs denegado (Joseph).
-- Verifica EXECUTE+tabla reales con SET ROLE + CALL sobre los fixtures de
-- lab.detalle_factura (PK de 2 columnas). No consulta solo metadata.
-- Esperado OK → success; esperado DENEGADO → SQLSTATE 42501;
-- fila inexistente → SQLSTATE P0002 (misma convención que producto_*).
-- Requiere: fixtures/06_composite_pk_fixtures.sql.
-- Cada bloque deja constancia en RAISE NOTICE. Idempotente (ids 501/502/601/602
-- reservados para este archivo; limpieza final como crud_admin). NO toca tabla_virgen.

-- Preparación (como owner): padres en producto + limpieza de claves de prueba.
-- La FK detalle_factura → producto exige padres existentes antes de cada INSERT.
SET ROLE crud_admin;
DELETE FROM lab.detalle_factura WHERE id_factura IN (601, 602);
DELETE FROM lab.producto WHERE id_producto IN (501, 502);
INSERT INTO lab.producto(id_producto, nombre, precio) VALUES
  (501, 'CompA', 100.00),
  (502, 'CompB', 200.00);
RESET ROLE;

-- MAT-C1 | vendedor → INSERT permitido → SUCCESS
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.detalle_factura_insertar(601, 501, 5);
  RAISE NOTICE 'MAT-C1 OK: vendedor INSERT PK compuesta permitido funciona';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C1 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C2 | vendedor → READ por PK completa permitido → SUCCESS (INOUT)
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_cantidad integer;
BEGIN
  CALL lab.detalle_factura_consultar(601, 501, v_cantidad);
  IF v_cantidad = 5 THEN
    RAISE NOTICE 'MAT-C2 OK: vendedor READ devuelve cantidad=%', v_cantidad;
  ELSE
    RAISE NOTICE 'MAT-C2 FALLO: cantidad inesperada=% (esperado 5)', v_cantidad;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C2 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C3 | vendedor → UPDATE denegado → 42501
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.detalle_factura_actualizar(601, 501, 9);
  RAISE NOTICE 'MAT-C3 FALLO: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-C3 OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C3 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C4 | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.detalle_factura_eliminar(601, 501);
  RAISE NOTICE 'MAT-C4 FALLO: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-C4 OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C4 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C5 | supervisor → UPDATE permitido → SUCCESS (verificado con READ)
SET ROLE crud_supervisor;
DO $$
DECLARE
  v_cantidad integer;
BEGIN
  CALL lab.detalle_factura_actualizar(601, 501, 7);
  CALL lab.detalle_factura_consultar(601, 501, v_cantidad);
  IF v_cantidad = 7 THEN
    RAISE NOTICE 'MAT-C5 OK: supervisor UPDATE permitido funciona (cantidad=%)', v_cantidad;
  ELSE
    RAISE NOTICE 'MAT-C5 FALLO: cantidad=% tras UPDATE (esperado 7)', v_cantidad;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C5 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C6 | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
BEGIN
  CALL lab.detalle_factura_eliminar(601, 501);
  RAISE NOTICE 'MAT-C6 FALLO: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-C6 OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C6 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C7 | administrador → DELETE permitido → SUCCESS (fila queda inexistente P0002)
SET ROLE crud_administrador;
DO $$
DECLARE
  v_cantidad integer;
BEGIN
  CALL lab.detalle_factura_eliminar(601, 501);
  BEGIN
    CALL lab.detalle_factura_consultar(601, 501, v_cantidad);
    RAISE NOTICE 'MAT-C7 FALLO: la fila debió desaparecer tras DELETE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = 'P0002' THEN
      RAISE NOTICE 'MAT-C7 OK: administrador DELETE cierra el ciclo (fila inexistente P0002)';
    ELSE
      RAISE NOTICE 'MAT-C7 resultado distinto al verificar: % %', SQLSTATE, SQLERRM;
    END IF;
  END;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C7 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C8 | PK compuesta REAL: dos filas comparten id_factura; cada operación
-- debe discriminar por la combinación completa (id_factura, id_producto).
-- Si el fixture usara una sola columna, estos checks fallarían.
SET ROLE crud_administrador;
DO $$
DECLARE
  v_cantidad integer;
BEGIN
  CALL lab.detalle_factura_insertar(602, 501, 1);
  CALL lab.detalle_factura_insertar(602, 502, 2);
  -- La segunda columna discrimina: (602,502) debe devolver 2, no 1.
  CALL lab.detalle_factura_consultar(602, 502, v_cantidad);
  IF v_cantidad <> 2 THEN
    RAISE NOTICE 'MAT-C8 FALLO: consultar(602,502)=% (esperado 2)', v_cantidad;
    RETURN;
  END IF;
  -- UPDATE sobre (602,501) no debe tocar (602,502).
  CALL lab.detalle_factura_actualizar(602, 501, 10);
  CALL lab.detalle_factura_consultar(602, 502, v_cantidad);
  IF v_cantidad <> 2 THEN
    RAISE NOTICE 'MAT-C8 FALLO: UPDATE(602,501) afectó a (602,502)=%', v_cantidad;
    RETURN;
  END IF;
  CALL lab.detalle_factura_consultar(602, 501, v_cantidad);
  IF v_cantidad <> 10 THEN
    RAISE NOTICE 'MAT-C8 FALLO: UPDATE(602,501) no aplicó (cantidad=%)', v_cantidad;
    RETURN;
  END IF;
  -- DELETE sobre (602,501): esa combinación desaparece (P0002) y (602,502) sobrevive.
  CALL lab.detalle_factura_eliminar(602, 501);
  BEGIN
    CALL lab.detalle_factura_consultar(602, 501, v_cantidad);
    RAISE NOTICE 'MAT-C8 FALLO: (602,501) debió desaparecer tras DELETE';
    RETURN;
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE <> 'P0002' THEN
      RAISE NOTICE 'MAT-C8 FALLO al verificar DELETE: % %', SQLSTATE, SQLERRM;
      RETURN;
    END IF;
  END;
  CALL lab.detalle_factura_consultar(602, 502, v_cantidad);
  IF v_cantidad = 2 THEN
    RAISE NOTICE 'MAT-C8 OK: PK compuesta discrimina por ambas columnas';
  ELSE
    RAISE NOTICE 'MAT-C8 FALLO: (602,502) sobreviviente con cantidad=%', v_cantidad;
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-C8 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-C9 | fila inexistente → P0002 (convención producto_*, no 42501 ni 42P01).
-- Como vendedor llega al P0002, además confirma EXECUTE+SELECT sobre consultar.
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_cantidad integer;
BEGIN
  CALL lab.detalle_factura_consultar(999, 999, v_cantidad);
  RAISE NOTICE 'MAT-C9 FALLO: debió reportar fila inexistente P0002';
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = 'P0002' THEN
    RAISE NOTICE 'MAT-C9 OK: fila inexistente reporta P0002';
  ELSE
    RAISE NOTICE 'MAT-C9 resultado distinto: % %', SQLSTATE, SQLERRM;
  END IF;
END $$;
RESET ROLE;

-- Limpieza (como owner, fuera de roles de negocio; detalle antes que producto por FK)
SET ROLE crud_admin;
DELETE FROM lab.detalle_factura WHERE id_factura IN (601, 602);
DELETE FROM lab.producto WHERE id_producto IN (501, 502);
RESET ROLE;
