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


## Harness fail-fast

Para ejecutar todo el laboratorio con una salida confiable para CI:

```bash
export PGHOST=localhost PGPORT=5432 PGUSER=postgres PGDATABASE=devdb
export PGPASSWORD=postgres
./tests/run_harness.sh
```

El harness usa `psql -v ON_ERROR_STOP=1` y además inspecciona los `RAISE NOTICE`
de las pruebas. Un `FAIL`/ `FALLO` inesperado convierte el resultado del script
en fallo real (exit code 1), aunque PostgreSQL haya terminado con código 0.

Los casos negativos intencionales siguen siendo válidos cuando la propia prueba
captura el SQLSTATE esperado y reporta `OK`. El caso `DYN-04` que detecta
deliberadamente el señuelo inseguro está etiquetado como `OK-detección` y no
se considera un fallo del harness.

Esto permite usar el mismo comando localmente y posteriormente en CI, sin
depender de interpretar manualmente cientos de líneas de `NOTICE`.



## 10. Discovery genérico de procedures

`security/10_generated_routine_discovery.sql` inspecciona `pg_proc` sin
suponer las firmas de Joyce. Por defecto descubre procedures de `lab`.

Para filtrar:

```sql
SET crudgen.discovery_schema = 'lab';
SET crudgen.discovery_prefix = 'producto_';
\i tests/security/10_generated_routine_discovery.sql
```

La salida incluye firma de identidad, owner, SECURITY INVOKER/DEFINER,
`search_path`, argumentos, retorno y si PUBLIC conserva EXECUTE. El resumen
final permite detectar rápidamente rutinas descubiertas, DEFINER e
EXECUTE público.

Este discovery es deliberadamente independiente de T1-T6: no sustituye todavía
las matrices ni decide qué procedure corresponde a INSERT/READ/UPDATE/DELETE.
Cuando Joyce publique el contrato real, esa asociación se hará sobre este
resultado y no mediante firmas hardcodeadas.

## 11. Modo reales (procedures generados por la extensión)

`security/11_ticket_real_matrix.sql` (T2R, Caso 3 §9) y
`security/12_special_real_matrix.sql` (T6R, tipos especiales + sin PK)
prueban los procedures REALES de `crud_generator.generate_crud`, no los
fixtures. 07/09 quedan intactos para el modo fixtures (CI).

Orden en una base con la extensión instalada (ver `handoff §2.3`):

```text
1. fixtures/01_roles.sql + 02_schema.sql
2. generate_crud('lab','ticket'|'catalogo_especial'|'bitacora', 4 ops) como crud_admin
3. grants reales (plantilla 05 con firmas del handoff §2.4)
4. security/11_ticket_real_matrix.sql  → TIXR-00, MAT-T1R..T9R, TIXR-AUD 4/4
5. security/12_special_real_matrix.sql → S-00R, MAT-S1R..S8R, MAT-B1R..B3R
   (refcursor), B-POL (not_applicable ADR-009), N-P1R..P4R, S-AUDR 7/7
```

Marcadores disjuntos de 07/09: `TIXR-%`, `SPCR-%`, `LOGR-%`.
Validado 02-10 en PG18 local: 11/11 + 19/19 OK, doble pasada idéntica,
cero residuos, `tabla_virgen` intacta. Detalle de firmas y decisiones en
`crud_generator_docs/ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md` §2.

`security/13_conflict_real_matrix.sql` (NEG-06R, ADR-010) prueba la política
de procedures existentes contra reales: sin flag → 4×`procedure_conflict`
sin tocar nada; con `do_replace=true` → 4×success con GRANTs preservados
(CONF-00..05 OK en PG18 02-10, idempotente).

> 11/12/13 son modo reales y NO forman parte de `run_harness.sh` ni del CI
> (que valida el modo fixtures). Requieren extensión instalada + grants reales.
