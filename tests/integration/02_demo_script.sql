-- tests/integration/02_demo_script.sql
-- Fase 0 — Guion E2E de demostración (Joseph). Se ejecuta AL FINAL, con todo integrado.
-- Hoy deja constancia de cada paso como NOTICE; cuando Joyce+Armando entreguen,
-- cada paso se sustituye por la llamada real sin cambiar el orden.
-- Flujo: Python → PG → extensión → procedures → GRANT/REVOKE → autorizado OK / denegado 42501.

-- DEMO-01: Python verifica extensión (Armando) → hoy: chequeo manual
DO $$ BEGIN RAISE NOTICE 'DEMO-01: verificar extensión crud_generator (pendiente Joyce+Armando)'; END $$;

-- DEMO-02: generar CRUD de lab.producto vía extensión (Joyce)
DO $$ BEGIN RAISE NOTICE 'DEMO-02: generate_crud(lab, producto) — pendiente CR-JOYCE-002'; END $$;

-- DEMO-03: aplicar matriz de privilegios (este harness ya lo hace en 04_grants.sql)
DO $$ BEGIN RAISE NOTICE 'DEMO-03: matriz vendedor/supervisor/administrador aplicada (fixtures)'; END $$;

-- DEMO-04: usuario autorizado — vendedor INSERT + READ
SET ROLE crud_vendedor;
DO $$
DECLARE v_n text; v_p numeric;
BEGIN
  CALL lab.producto_insertar(901, 'DemoOK', 15.00);
  CALL lab.producto_consultar(901, v_n, v_p);
  RAISE NOTICE 'DEMO-04 OK autorizado: vendedor INSERT+READ nombre=% precio=%', v_n, v_p;
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'DEMO-04 FALLO: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DEMO-05: usuario no autorizado — vendedor DELETE → 42501 delante del profesor
SET ROLE crud_vendedor;
DO $$
BEGIN
  CALL lab.producto_eliminar(901);
  RAISE NOTICE 'DEMO-05 FALLO: debió rechazar';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'DEMO-05 OK no autorizado: 42501 delante del profesor';
WHEN OTHERS THEN RAISE NOTICE 'DEMO-05 distinto: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DEMO-06: administrador cierra el ciclo (DELETE permitido) + limpieza
SET ROLE crud_administrador;
DO $$
BEGIN
  CALL lab.producto_eliminar(901);
  RAISE NOTICE 'DEMO-06 OK: administrador DELETE cierra el ciclo';
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'DEMO-06 FALLO: % %', SQLSTATE, SQLERRM;
END $$;
RESET ROLE;

-- DEMO-07: tabla desconocida del profesor (lab.tabla_virgen) — NO ejecutar hasta la demo final
DO $$ BEGIN RAISE NOTICE 'DEMO-07 RESERVADO: tabla_virgen intacta, no tocar hasta demo final'; END $$;
