# Tests — Seguridad + Integración + Pruebas (Joseph)

Harness **SQL puro**. No hay cliente Python aquí a propósito (área de Armando).

## Orden de ejecución

```text
1. fixtures/01_roles.sql       → roles + schema lab
2. fixtures/02_schema.sql       → 6 tablas del laboratorio
3. fixtures/03_security_fixtures.sql → procedures FIXTURE (no son la solución)
4. fixtures/04_grants.sql       → matriz GRANT/REVOKE hipótesis INVOKER
5. fixtures/05_grants_template.sql → PLANTILLA parametrizada (no se ejecuta tal cual;
                                   se rellena con las firmas reales de Joyce en integración)
5b. fixtures/06_composite_pk_fixtures.sql → fixtures PK compuesta detalle_factura_*
                                    (+ sus GRANTs; re-ejecutar si se re-ejecuta 04_grants.sql)
5c. fixtures/07_ticket_fixtures.sql → fixtures IDENTITY/DEFAULT ticket_*
                                    (+ sus GRANTs; misma regla que 06)
5d. fixtures/08_special_nopk_fixtures.sql → fixtures tipos especiales + sin PK
                                    (catalogo_especial_*, bitacora_*; misma regla)
6. security/01_matrix.sql       → permitido vs denegado (SET ROLE + CALL)
6b. security/04_composite_matrix.sql → matriz PK compuesta MAT-C1..C9
6c. security/07_ticket_matrix.sql → matriz IDENTITY/DEFAULT MAT-T1..T9, N-T1..T3, TIX-AUD
6d. security/09_special_nopk_matrix.sql → matriz especial/sin-PK MAT-S/B, N-P1..P4, S-AUD
7. security/02_invoker_vs_definer.sql → experimento comparativo ADR-011
7b. security/05_audit_ownership.sql → auditoría owner/INVOKER/search_path/refs AUD-01..05
                                   (re-ejecutable contra los procedures reales de Joyce)
8. security/03_negative.sql     → casos negativos NEG-01..NEG-11
8b. security/06_revoke_public_audit.sql → higiene PUBLIC + matriz EXECUTE + regresión
                                   REVOKE→GRANT (PUB-01/02/03, REV-01)
8c. security/08_dynamic_sql_audit.sql → SQL dinámico ADR-013 (%I+USING, ataques,
                                   señuelo controlado, scan estático DYN-00..05)
9. integration/01_checklist.sql → checklist pre-integración con Joyce/Armando
10. integration/02_demo_script.sql → guion E2E (se ejecuta al final)
```

Ejecución ejemplo contra el contenedor `postgres-dev`:

```bash
export PGHOST=localhost PGUSER=postgres PGDATABASE=devdb
export PGPASSWORD=postgres
for f in tests/fixtures/01_roles.sql tests/fixtures/02_schema.sql \
         tests/fixtures/03_security_fixtures.sql tests/fixtures/04_grants.sql \
         tests/fixtures/06_composite_pk_fixtures.sql \
         tests/fixtures/07_ticket_fixtures.sql \
         tests/fixtures/08_special_nopk_fixtures.sql \
         tests/security/*.sql tests/integration/*.sql; do
  echo "== $f"; psql -v ON_ERROR_STOP=1 -f "$f"
done
```

> `05_grants_template.sql` se excluye del loop porque es una plantilla con placeholders,
> no un script ejecutable directo (se usa cuando Joyce entregue las firmas reales).

Cada archivo es re-ejecutable (`DROP ... IF EXISTS` / bloques `DO` idempotentes).

## Reglas

- `lab.tabla_virgen` **NO se usa** en ningún test Fase 0. Está reservada para la
  prueba final de "tabla desconocida del profesor". Usarla invalida la prueba.
- Los procedures `lab.producto_*`, `lab.detalle_factura_*` y `lab.ticket_*` son
  **security fixtures**: sirven solo para validar GRANT/REVOKE/EXECUTE.
  No son el generador CRUD de Joyce.
- Resultado esperado de denegado: `SQLSTATE 42501 insufficient_privilege`.
- `SET ROLE` + `RESET ROLE` en cada bloque; nunca dejar la sesión con rol cambiado.
