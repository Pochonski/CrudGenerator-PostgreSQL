# Tests — Seguridad + Integración + Pruebas (Joseph)

Harness **SQL puro**. No hay cliente Python aquí a propósito (área de Armando).

## Orden de ejecución

```text
1. fixtures/01_roles.sql       → roles + schema lab
2. fixtures/02_schema.sql       → 6 tablas del laboratorio
3. fixtures/03_security_fixtures.sql → procedures FIXTURE (no son la solución)
4. fixtures/04_grants.sql       → matriz GRANT/REVOKE hipótesis INVOKER
5. security/01_matrix.sql       → permitido vs denegado (SET ROLE + CALL)
6. security/02_invoker_vs_definer.sql → experimento comparativo ADR-011
7. security/03_negative.sql     → casos negativos NEG-01..NEG-11
8. integration/01_checklist.sql → checklist pre-integración con Joyce/Armando
9. integration/02_demo_script.sql → guion E2E (se ejecuta al final)
```

Ejecución ejemplo contra el contenedor `postgres-dev`:

```bash
export PGHOST=localhost PGUSER=postgres PGDATABASE=devdb
export PGPASSWORD=postgres
for f in tests/fixtures/*.sql tests/security/*.sql tests/integration/*.sql; do
  echo "== $f"; psql -v ON_ERROR_STOP=1 -f "$f"
done
```

Cada archivo es re-ejecutable (`DROP ... IF EXISTS` / bloques `DO` idempotentes).

## Reglas

- `lab.tabla_virgen` **NO se usa** en ningún test Fase 0. Está reservada para la
  prueba final de "tabla desconocida del profesor". Usarla invalida la prueba.
- Los procedures `lab.producto_*` son **security fixtures**: sirven solo para
  validar GRANT/REVOKE/EXECUTE. No son el generador CRUD de Joyce.
- Resultado esperado de denegado: `SQLSTATE 42501 insufficient_privilege`.
- `SET ROLE` + `RESET ROLE` en cada bloque; nunca dejar la sesión con rol cambiado.
