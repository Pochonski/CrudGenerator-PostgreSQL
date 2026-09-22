-- tests/security/01_matrix.sql
-- Fase 0 — Matriz permitido vs denegado (Joseph).
-- Verifica EXECUTE+tabla reales con SET ROLE + CALL. No consulta solo metadata.
-- Esperado OK → success; esperado DENEGADO → SQLSTATE 42501.
-- Requiere: fixtures/04_grants.sql. Cada bloque deja constancia en RAISE NOTICE.

-- MAT-01 | vendedor → INSERT permitido → SUCCESS
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_insertar(101, 'Teclado', 25.50);
  RAISE NOTICE 'MAT-01 OK: vendedor INSERT permitido funciona';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-01 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-02 | vendedor → UPDATE denegado → 42501
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_actualizar(101, 'Teclado X', 30.00);
  RAISE NOTICE 'MAT-02 FALLO: vendedor UPDATE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-02 OK: vendedor UPDATE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-02 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-03 | vendedor → DELETE denegado → 42501
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_eliminar(101);
  RAISE NOTICE 'MAT-03 FALLO: vendedor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-03 OK: vendedor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-03 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-04 | supervisor → UPDATE permitido → SUCCESS
SET ROLE crud_supervisor;
DO $$
BEGIN
  CALL lab.producto_actualizar(101, 'Teclado Pro', 29.99);
  RAISE NOTICE 'MAT-04 OK: supervisor UPDATE permitido funciona';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-04 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-05 | supervisor → DELETE denegado → 42501
SET ROLE crud_supervisor;
DO $$
BEGIN
  CALL lab.producto_eliminar(101);
  RAISE NOTICE 'MAT-05 FALLO: supervisor DELETE debió ser rechazado';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'MAT-05 OK: supervisor DELETE rechazado con 42501';
WHEN OTHERS THEN
  RAISE NOTICE 'MAT-05 resultado distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-06 | administrador → DELETE permitido → SUCCESS
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.producto_eliminar(101);
  RAISE NOTICE 'MAT-06 OK: administrador DELETE permitido funciona';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-06 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- MAT-07 | vendedor → READ por PK permitido → SUCCESS (INOUT)
SET ROLE crud_vendedor;
DO $$
DECLARE
  v_nombre text;
  v_precio numeric;
BEGIN
  CALL lab.producto_insertar(102, 'Mouse', 10.00);
  CALL lab.producto_consultar(102, v_nombre, v_precio);
  RAISE NOTICE 'MAT-07 OK: vendedor READ devuelve nombre=% precio=%', v_nombre, v_precio;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'MAT-07 FALLO inesperado: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- Limpieza (como admin, fuera de roles de negocio)
SET ROLE crud_admin;
DELETE FROM lab.producto WHERE id_producto IN (101, 102);
RESET ROLE;
