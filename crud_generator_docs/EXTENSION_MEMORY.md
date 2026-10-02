# Memoria — Agente Extensión PostgreSQL

**Owner:** Joyce  
**Área:** Extensión PostgreSQL

## Rol

Responsable principal de la extensión PostgreSQL, catálogos, análisis estructural y generación dinámica de procedimientos.

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

Construir una extensión instalable de PostgreSQL capaz de analizar tablas existentes y generar procedimientos CRUD genéricos a partir de sus metadatos.

## Responsabilidades

- Diseño del `.control`.
- Scripts SQL de instalación.
- Funciones de la extensión.
- Lectura de catálogos PostgreSQL.
- Modelo interno de metadata.
- Detección de columnas y tipos.
- Detección de PK simple/compuesta.
- Detección de DEFAULT.
- Detección de columnas generadas/identity/otros mecanismos soportados.
- Generación dinámica de SQL.
- Creación de procedures CRUD.
- Manejo de objetos existentes.
- Errores y validaciones.
- Documentación de API pública.

## Reglas

- No hardcodear tablas.
- No asumir una sola PK.
- No asumir que todas las columnas reciben valores en INSERT.
- No inventar una PK si no existe.
- Proteger identificadores.
- Mantener la API documentada en `CONTRACTS.md`.

## Estado actual

- [x] Arquitectura interna definida (API en `CONTRACTS.md` §3, cerrada 2026-10-01)
- [x] API pública definida
- [x] Catálogos definidos (`crud_generator._table_columns`, `pg_attribute`/`pg_attrdef`/`pg_index`)
- [x] `.control` (`extension/crud_generator.control`, `schema = crud_generator`, `default_version = '1.0'`)
- [x] Análisis de tablas (`crud_generator.analyze_table`, probado en las 5 tablas del lab)
- [x] INSERT (DEFAULT/IDENTITY BY DEFAULT con `OVERRIDING SYSTEM VALUE`, mandatorios reordenados antes que opcionales)
- [x] READ (PK vía INOUT + P0002; sin PK vía `refcursor OUT`)
- [x] UPDATE (por PK, excluye columnas GENERATED)
- [x] DELETE (por PK)
- [x] PK compuesta (`lab.detalle_factura`, probado INSERT/READ/UPDATE/DELETE reales)
- [x] Autogenerados/identity/default (`lab.ticket`, `lab.catalogo_especial`, probado)
- [x] Tabla sin PK (`lab.bitacora`: INSERT + READ listado, UPDATE/DELETE `not_applicable`)
- [x] Conflicto de procedimientos (`procedure_conflict` por defecto; `do_replace=true` con `CREATE OR REPLACE`, GRANTs preservados — verificado)
- [x] Pruebas aisladas (manuales contra Postgres 16 en Docker, ver sección siguiente)
- [x] Integración con Python (signatures documentadas en `CONTRACTS.md`; nombre de extensión `crud_generator` confirma el `DEFAULT_EXTENSION_NAME` de Armando)
- [ ] Integración formal con `app/` (Armando aún no consume `generate_crud`/`analyze_table` desde Python)

## Decisiones locales

- **2026-10-01 — Nombre de extensión:** `crud_generator`, confirmando el
  `DEFAULT_EXTENSION_NAME` provisional de Armando. El `.control` fija
  `schema = crud_generator` para que `has_schema_privilege` (usado por
  `ExtensionService.check_extension`) tenga significado real (si fuera
  `public`, casi cualquier rol tendría USAGE y el estado `NOT_ACCESSIBLE`
  nunca se daría).
- **2026-10-01 — Lenguaje:** extensión 100% SQL/PL-pgSQL (sin C), instalable
  con `CREATE EXTENSION` desde un único script versionado
  (`extension/sql/crud_generator--1.0.sql`) + `.control`. Confirma ADR-004.
- **2026-10-01 — Resolución de las 5 CR abiertas por Joseph:** ver ADR-007
  (naming/esquema/tipos), ADR-009 (sin PK), ADR-010 (conflicto), ADR-011
  (INVOKER + owner `crud_admin`), ADR-015 (READ). Detalle completo de la API
  en `CONTRACTS.md` §3-4.
- **Versión de PostgreSQL objetivo:** 16+ (misma versión que usa
  `.github/workflows/sql-harness.yml`); se evita cualquier sintaxis que no
  exista en PG16 aunque los experimentos de Joseph se hayan corrido en PG18.

## Problemas / descubrimientos

- **Orden de parámetros de `_insertar`:** PostgreSQL exige que todo parámetro
  con `DEFAULT` venga después de todos los que no tienen `DEFAULT`; el orden
  ordinal de la tabla no garantiza eso. Se corrigió reordenando: obligatorios
  primero, opcionales después (ambos grupos en orden ordinal interno). Ver
  `CONTRACTS.md` §3.2 (INSERT).
- **`OPEN cursor WITH HOLD FOR EXECUTE ...` no es sintaxis válida en PL/pgSQL**
  (el modificador `WITH HOLD` no existe en esa forma). El `consultar` sin PK
  usa `OPEN resultado FOR EXECUTE ...` simple; el cliente debe hacer `FETCH`
  en la misma transacción del `CALL` (ya reflejado en `CONTRACTS.md`).
- **Bug de un carácter en el discovery de Joseph** (`has_function_privilege('PUBLIC', ...)`
  debía ser `'public'` en minúsculas): corregido directamente en
  `tests/security/10_generated_routine_discovery.sql` por ser un error
  objetivo, no una decisión de diseño.
- **`CALL` con literales en parámetros INOUT falla dentro de bloques PL/pgSQL**
  (no al usarlo desde un cliente): confirmado que `tests/security/01_matrix.sql`
  MAT-07 necesita variables en todas las posiciones al apuntar a `consultar`
  real (PK también INOUT por ADR-015, a diferencia del fixture de Joseph).
  Registrado como nota de coordinación para Joseph en `COORDINATION_REQUESTS.md`.

## Validación realizada (2026-10-02, Postgres 16 en Docker)

- `analyze_table`: PK simple, PK compuesta, IDENTITY ALWAYS/BY DEFAULT,
  DEFAULT, tipos especiales (`numeric(12,2)`, `jsonb`, `boolean`, `date`),
  nombres con espacios/acentos (`"Nombre Ítem"`, `"precio$"`).
- `generate_crud` + ejecución real de INSERT/READ/UPDATE/DELETE en las 5
  tablas del laboratorio de Joseph, incluyendo error `P0002` en fila
  inexistente y `OVERRIDING SYSTEM VALUE` para identity BY DEFAULT.
- Política de conflicto: `procedure_conflict` (42723/42P13) por defecto;
  `do_replace=true` regenera con `CREATE OR REPLACE` y se verificó que un
  `GRANT EXECUTE` previo a `crud_vendedor` sobrevive intacto a la regeneración.
- Harness externo de Joseph ejecutado sin modificar su lógica: discovery
  (18/18 `crud_admin`/INVOKER/search_path correcto/sin EXECUTE a PUBLIC),
  `04_grants.sql` + `01_matrix.sql` (MAT-01..06 OK contra procedures reales;
  MAT-07 requiere el ajuste de variables ya reportado).

## Requiere coordinación

- Ver la sección nueva en `COORDINATION_REQUESTS.md` (hallazgos 2026-10-02
  para Joseph: fix del discovery y ajuste de MAT-07).
- Pendiente de Armando: integrar `app/` para llamar `crud_generator.analyze_table`
  y `crud_generator.generate_crud` en vez de detenerse antes de generar.
- **Guía completa de integración (paso a paso, para Armando y Joseph):**
  `ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md` — cómo llamar la API desde psycopg,
  distinción FUNCTION/PROCEDURE, manejo de READ con/sin PK, GRANT de dos
  llaves, cómo re-generar el laboratorio con procedures reales, y tabla de
  firmas reales confirmadas.
