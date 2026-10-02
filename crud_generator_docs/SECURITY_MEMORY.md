# Memoria — Agente Seguridad, Integración y Pruebas

**Owner:** Joseph  
**Área:** Seguridad + Integración + Pruebas

## Rol

Responsable de seguridad PostgreSQL, roles/privilegios, integración, auditoría de decisiones y pruebas end-to-end.

## Equipo

- **Joseph:** Seguridad + Integración + Pruebas.
- **Joyce:** Extensión PostgreSQL.
- **Armando:** Python + Interfaz.

El owner lidera su área, pero cualquier cambio que afecte arquitectura o contratos debe coordinarse con los otros dos.

## Documentos que debe leer primero

1. `PROJECT_CONTEXT.md`
2. `ARCHITECTURE.md`
3. `CONTRACTS.md`
4. `DECISIONS.md`

## Objetivo técnico

Asegurar que el sistema funcione correctamente con distintos roles y que los privilegios sobre los procedimientos sean reales, verificables y justificables.

## Responsabilidades

- Diseño de roles de prueba.
- GRANT/REVOKE.
- EXECUTE.
- Propietarios.
- SECURITY INVOKER/DEFINER.
- Análisis de search_path cuando corresponda.
- Auditoría de SQL dinámico.
- Casos negativos.
- Pruebas CRUD.
- Integración Python ↔ extensión.
- Integración CRUD ↔ privilegios.
- Guion de demostración.

## Matriz mínima de referencia

| Rol | INSERT | READ | UPDATE | DELETE |
|---|---:|---:|---:|---:|
| vendedor | ✅ | ✅ | ❌ | ❌ |
| supervisor | ✅ | ✅ | ✅ | ❌ |
| administrador | ✅ | ✅ | ✅ | ✅ |

Los nombres son ejemplos iniciales; el equipo puede cambiarlos siempre que conserve tres niveles diferenciados.

## Modelo de roles Fase 0 (Joseph) — probado en PG18 (MAT-01..07, EXP-01/02, NEG-01..11 OK)

Roles de negocio (inalterables, `NOLOGIN` para forzar `SET ROLE` en pruebas):

```text
crud_vendedor      → INSERT + READ
crud_supervisor    → INSERT + READ + UPDATE
crud_administrador → INSERT + READ + UPDATE + DELETE
```

Roles de sistema (propuesta, REQUIERE COORDINACIÓN con Joyce/Armando):

```text
crud_admin   → owner de esquemas/tablas/procedures de prueba, único que GENERA.
               Equivale al "administrador del sistema" que opera Python con credencial alta.
crud_owner   → alternativa si Joyce decide que la extensión fije otro owner.
               Por defecto crud_owner = crud_admin hasta que Joyce responda (CR-JOYCE-005).
```

Principio clave (ADR-012): la matriz NO es simulación Python. Cada celda ✅/❌ debe
corresponder a `GRANT` reales en PostgreSQL y verificarse con `SET ROLE ...; CALL ...`.

### Distinción generar vs ejecutar

```text
GENERAR/MODIFICAR procedures  → solo crud_admin (CREATE en el esquema + OWNER).
                                Requiere además CREATE USAGE sobre esquema de destino.
EJECUTAR procedures            → roles de negocio vía GRANT EXECUTE selectivo.
                                 Con INVOKER (hipótesis) se suma GRANT sobre tablas.
```

Ningún rol de negocio recibe `CREATEDB/CREATEROLE/SUPERUSER`, ni `ALL ON SCHEMA`,
ni `ALL ON TABLE`. Mínimo privilegio estricto.

### Estrategia GRANT (hipótesis INVOKER, pendiente de cierre ADR-011)

Por cada tabla `app.t` y sus 4 procedures `app.t_insertar|consultar|actualizar|eliminar`:

```sql
-- Base: revocar default público
REVOKE ALL ON SCHEMA app FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA app FROM PUBLIC;
REVOKE ALL ON ALL ROUTINES IN SCHEMA app FROM PUBLIC;

-- Descubrimiento: todos necesitan USAGE para calificar objetos
GRANT USAGE ON SCHEMA app TO crud_vendedor, crud_supervisor, crud_administrador;

-- EXECUTE selectivo (llave 1)
GRANT EXECUTE ON PROCEDURE app.t_insertar(...)   TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE app.t_consultar(...)  TO crud_vendedor, crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE app.t_actualizar(...) TO crud_supervisor, crud_administrador;
GRANT EXECUTE ON PROCEDURE app.t_eliminar(...)   TO crud_administrador;

-- Permisos de tabla (llave 2, solo bajo INVOKER)
GRANT SELECT, INSERT                      ON app.t TO crud_vendedor;
GRANT SELECT, INSERT, UPDATE              ON app.t TO crud_supervisor;
GRANT SELECT, INSERT, UPDATE, DELETE      ON app.t TO crud_administrador;
```

Si el equipo adoptara DEFINER, la llave 2 se invierte: `REVOKE ALL ON TABLE` a
negocio y solo `GRANT EXECUTE`. Ver ADR-011 y experimento
`tests/security/02_invoker_vs_definer.sql`.

### Estrategia REVOKE

- Revocación por operación: `REVOKE EXECUTE ON PROCEDURE app.t_eliminar FROM crud_supervisor;`
  (+ `REVOKE DELETE ON app.t FROM crud_supervisor;` bajo INVOKER).
- Revocación total de un rol: `REVOKE ALL ON ALL ROUTINES IN SCHEMA app FROM <rol>;`
  + `REVOKE ALL ON ALL TABLES IN SCHEMA app FROM <rol>;`.
- Tras cada `REVOKE`, re-verificar con `SET ROLE` que el `CALL` denegado devuelve
  `SQLSTATE 42501` y que operaciones vecinas siguen OK (sin regresión).
- Herencia de roles: en Fase 0 NO se usa `GRANT rol TO rol` entre negocio para
  evitar escalada transitiva; cada negocio recibe grants directos. Si el equipo
  pide jerarquía (`administrador hereda de supervisor`), documentarlo como decisión
  y probar `SET ROLE` en cada nivel.

### Owner y search_path (propuesta pendiente de Joyce)

- Owner de fixtures y tablas de prueba: `crud_admin`.
- Cada procedure fixture fija `SET search_path = app, pg_temp` (o esquema que Joyce
  defina) y cuerpo con nombres calificados `app.tabla`.
- Auditoría SQL dinámico (ADR-013): identificadores solo vía `%I`, valores vía `USING`;
  el harness incluye tabla de nombres especiales para probar quoting.

## Análisis INVOKER vs DEFINER

Ver análisis completo en `DECISIONS.md` ADR-011 (recomendación formal: INVOKER por
defecto; decisión global pendiente de voto + CR-JOYCE-005). Experimento ejecutado en
PG18: `tests/security/02_invoker_vs_definer.sql` → EXP-01 INVOKER bloquea sin permiso
de tabla (42501), EXP-02 DEFINER eleva vía owner.

## READ — decisión adoptada (ADR-015)

READ adoptado como `consultar` por PK completa, una fila vía INOUT (ADR-015 en
DECISIONS.md), respaldado por el enunciado §4.5 y el fixture probado `lab.producto_consultar`
(MAT-07). Pendiente de confirmación de Joyce (CR-JOYCE-001) y del caso sin PK (CR-JOYCE-003).

## Plantilla de grants parametrizada (Fase A)

`tests/fixtures/05_grants_template.sql` mapea la matriz completa con marcadores
`<schema>.<tabla>_<operacion>`. A la llegada de las firmas reales de Joyce, se rellena
con nombres/tipos exactos y sustituye a `04_grants.sql` sin reescribir la lógica
(CR-JOYCE-002).

## Plan de pruebas Fase 0

Laboratorio: `tests/fixtures/02_schema.sql` (6 tablas: pk simple, pk compuesta,
identity+default, sin pk, tipos/nombres especiales, virgen reservada).
Harness SQL puro: `tests/security/` + `tests/integration/` — ver `tests/README.md`.
Formato por prueba: ID / Objetivo / Preparación / Acción / Resultado esperado /
Resultado real / Estado. Catálogo de SQLSTATE: `42501` (permiso), `42883`
(rutina inexistente), `42P01` (tabla inexistente), `42602`/`42703` según quoting.

## Estado actual

- [x] Roles definidos (Fase 0) — probados en PG18
- [x] Propietarios definidos (propuesta: crud_admin, pendiente Joyce)
- [x] Estrategia GRANT (diseñada; probada con fixtures en 04_grants.sql) + plantilla 05
- [x] Estrategia REVOKE (diseñada; NEG-01/02/08/10 probados)
- [x] EXECUTE validado (con fixtures: MAT-01..07)
- [x] SECURITY INVOKER/DEFINER analizado + experimento ejecutado (EXP-01/02);
  decisión global pendiente de voto (ADR-011) y CR-JOYCE-005
- [x] Riesgos SQL dinámico revisados (reglas + fixtures de quoting)
- [x] PK simple probado (MAT-01..07 7/7 con fixtures y con reales PG18 02-10;
  MAT-07/DEMO-04/T4-3b con variable INOUT — vale en ambos modos, CI PASS)
- [x] PK compuesta: matriz MAT-C1..C9 9/9 con fixtures y con reales PG18 02-10
  (fix variables INOUT en C2/C5/C7/C8/C9); estructura verificada en NEG-07.
  Reales generados por Joyce (`lab.detalle_factura_*`, firmas idénticas).
- [x] Auditoría owner/search_path/SECURITY (T3: `tests/security/05_audit_ownership.sql`,
  AUD-01..05) — 40/40 OK con fixtures y 40/40 OK contra reales PG18 02-10
  (owner crud_admin, INVOKER, search_path, esquema, refs calificadas).
- [x] Higiene PUBLIC + regresión REVOKE (T4: `tests/security/06_revoke_public_audit.sql`,
  PUB-01/02/03 + REV-01) — OK con fixtures y contra reales PG18 02-10
  (PUB-01 8/8, matriz EXECUTE 24/24, ciclo REVOKE→GRANT restaurado, señuelo).
  Sin basura residual; tabla_virgen intacta.
- [x] Autogenerado IDENTITY/DEFAULT: T2 con fixtures (07, Caso 3 §9) + T2R contra
  reales (`tests/security/11_ticket_real_matrix.sql`) — TIXR-00, MAT-T1R..T9R,
  TIXR-AUD 4/4 OK en PG18 02-10, doble pasada idéntica, cero residuos.
  Convención real: insertar sin id (GENERATED ALWAYS omitido, NULL→DEFAULT).
- [x] SQL dinámico seguro (T5: `tests/security/08_dynamic_sql_audit.sql`, DYN-00..05)
  — ADR-013 verificado con pruebas, no solo documentado: %I + USING neutralizan
  8 valores hostiles (round-trip exacto) y 3 identificadores hostiles (42P01 sin
  ejecución); señuelo con || inyecta de verdad (tautología 8/8) y el scan lo marca;
  12 fixtures + 3 seguros limpios; %L innecesario (USING parametriza). Autocontenido:
  cero residuos, doble pasada idéntica en PG16.
- [x] Sin PK + tipos especiales contra reales (T6R:
  `tests/security/12_special_real_matrix.sql`) — S-00R, MAT-S1R..S8R, MAT-B1R..B3R
  (READ por `refcursor` con FETCH en-transacción), B-POL (`not_applicable`
  ADR-009 verificado vía generate_crud), N-P1R..P4R, S-AUDR 7/7 OK en PG18 02-10.
  09/08 quedan para modo fixtures. Política CR-JOYCE-003 RESUELTA e implementada.
- [x] Tipos especiales con fixtures (T6): `lab.catalogo_especial_*` con quoting/unicode/jsonb/
  boolean/date/numeric + identity BY DEFAULT; round-trip exacto y DEFAULTs del
  esquema verificados (09) y contra reales con orden de params real (12).
- [ ] Procedimiento existente probado (pendiente Joyce CR-JOYCE-004)
- [x] Usuario autorizado probado (fixtures: MAT-01/04/06/07, NEG-09)
- [x] Usuario no autorizado probado (fixtures: MAT-02/03/05, NEG-01/02/10)
- [ ] Tabla no conocida probada (tabla virgen reservada, ver estrategia abajo)
- [ ] Demo E2E preparada

### Estrategia tabla virgen (reservada)

`lab.tabla_virgen` se crea vacía en el schema y NO se usa en ningún fixture,
experimento ni prueba Fase 0. Su DDL real solo se define cuando el equipo acuerde
el protocolo "tabla desconocida del profesor" (columnas+PK desconocidas hasta la
demo). Cualquier uso accidental invalida la prueba — ver `tests/fixtures/02_schema.sql`.

## Problemas / descubrimientos

- Fase 0: READ vía `PROCEDURE` no puede devolver filas con `CALL` — bloquea matriz
  READ y demo. Registrado como CR-JOYCE-001, no implementamos workaround propio.
- Fase 0: falta respuesta de Joyce sobre owner + cláusula SECURITY que emitirá la
  extensión (CR-JOYCE-005) y sobre policy de procedures existentes (CR-JOYCE-004).
- Fase 0: falta respuesta de Armando sobre vía de aplicación de privilegios
  (directo vs función) y validación real con `SET ROLE` (CR-ARMANDO-001/003).
- PDF del enunciado es escaneado sin texto extraíble — validar requisitos solo con .md.

## Requiere coordinación

- Ver `COORDINATION_REQUESTS.md` (CR-JOYCE-001 a 005, CR-ARMANDO-001 a 003).
- Cualquier hallazgo que requiera cambiar la API, arquitectura, privilegios o
  comportamiento de generación.
