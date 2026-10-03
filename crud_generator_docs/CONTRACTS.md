# Contratos de Integración

Este documento es la fuente de verdad para las interfaces entre los componentes. Un agente no debe cambiar un contrato sin actualizar este archivo y registrar la decisión.

## 1. Responsables de los contratos

- **Joyce:** contrato y API de la extensión PostgreSQL.
- **Armando:** consumo de la API desde Python y flujo de aplicación.
- **Joseph:** contratos de seguridad, integración y validación.

Ningún integrante debe cambiar unilateralmente una interfaz que consuma otro componente.

## 2. Contrato Python ↔ PostgreSQL

Python debe ser capaz de:

1. Abrir conexión.
2. Consultar disponibilidad de la extensión.
3. Consultar esquemas.
4. Consultar tablas de un esquema.
5. Solicitar análisis de una tabla.
6. Solicitar generación de una o varias operaciones CRUD.
7. Consultar roles/usuarios.
8. Aplicar o solicitar la aplicación de privilegios.
9. Mostrar errores y resultados.

## 3. API pública de la extensión — CERRADA (Joyce, 2026-10-01)

> Esta sección deja de ser propuesta: es el contrato que Python debe consumir.
> Cierra CR-JOYCE-001 y CR-JOYCE-002. Las firmas exactas (tipos reales) se
> confirman contra PostgreSQL cuando la implementación esté instalada, pero la
> forma de la API (nombres de función, parámetros, forma del resultado) ya no
> cambia sin pasar otra vez por este documento.

Todo vive en el esquema de la extensión `crud_generator` (el mismo que
`CREATE EXTENSION crud_generator` registra en `pg_extension`; es lo que
`ExtensionService.check_extension` de Armando ya verifica vía
`has_schema_privilege`).

### 3.1 Analizar tabla

```sql
crud_generator.analyze_table(schema_name text, table_name text)
RETURNS TABLE (
  column_name          text,
  data_type             text,   -- format_type(atttypid, atttypmod), tipo real con precisión/escala
  ordinal_position      integer,
  is_primary_key        boolean,
  pk_position           integer,  -- posición dentro de la PK (1..N), NULL si no es PK
  is_nullable            boolean,
  has_default            boolean,
  default_expression     text,    -- pg_get_expr(adbin, adrelid), NULL si no aplica
  is_identity            boolean,
  identity_generation    text,    -- 'ALWAYS' | 'BY DEFAULT' | NULL
  is_generated           boolean, -- columna GENERATED ... STORED
  generated_expression   text
)
```

- Una fila por columna, ordenada por `ordinal_position`.
- Tabla sin PK: todas las filas tienen `is_primary_key = false`, `pk_position = NULL`.
- Objeto inexistente (`schema_name`/`table_name` no son una tabla real) →
  error real de PostgreSQL (`SQLSTATE 42P01`), no una fila de resultado. Ver §5.

### 3.2 Generar CRUD

```sql
crud_generator.generate_crud(
  schema_name text,
  table_name  text,
  operations  text[],          -- subconjunto de {'INSERT','READ','UPDATE','DELETE'}
  do_replace  boolean DEFAULT false
)
RETURNS TABLE (
  operation           text,    -- 'INSERT' | 'READ' | 'UPDATE' | 'DELETE'
  status              text,    -- ver §3.3
  schema_name         text,
  routine_name        text,
  identity_arguments  text,    -- pg_get_function_identity_arguments(oid); NULL si no se creó
  message             text,
  sqlstate            text     -- solo relevante si status indica error propio (no usado hoy)
)
```

**Nombres de parámetro:** cada parámetro generado se llama `p_<ordinal_position>`
(ej. `p_1`, `p_2`, ...), **no** `p_<nombre_columna>`. Esto es deliberado: nombres
de columna con espacios, acentos o palabras reservadas (ver `lab.catalogo_especial`,
columna `"Nombre Ítem"`) no producirían identificadores PL/pgSQL válidos si se
usaran para nombrar parámetros. Los nombres reales de columna sí se usan
(correctamente quoteados) dentro del cuerpo del procedure para las sentencias
SQL reales. Python/Joseph deben referirse a los parámetros por posición, no
por nombre, y pueden leer `identity_arguments` (vía `generate_crud` o el
discovery de Joseph) para conocer tipos y modos exactos de cada procedure real.

Una fila por operación solicitada. Reglas de generación por operación:

- **INSERT (`<tabla>_insertar`):** un parámetro `IN` por columna insertable.
  **Orden real de parámetros (confirmado contra PostgreSQL 16):** primero las
  columnas **obligatorias** (`NOT NULL` sin `DEFAULT`), en `ordinal_position`
  entre ellas; después las columnas **opcionales** (con `DEFAULT NULL` en el
  parámetro), también en `ordinal_position` entre ellas. Esto **no** siempre
  coincide con el `ordinal_position` global de la tabla: PostgreSQL exige que
  todo parámetro con `DEFAULT` aparezca después de todos los que no lo tienen,
  y una columna con `DEFAULT`/identity puede estar antes que una `NOT NULL`
  sin `DEFAULT` en la tabla (ej. `lab.catalogo_especial`, donde `id` con
  identity precede a `"Nombre Ítem"` obligatoria). El `INSERT` interno
  siempre nombra las columnas explícitamente, así que el reordenamiento no
  afecta el resultado.
  - Columna `GENERATED ALWAYS AS IDENTITY` o `GENERATED ... STORED`: **se
    omite del parámetro** (no se puede pedir ni setear).
  - Columna `GENERATED BY DEFAULT AS IDENTITY`: parámetro opcional
    (`DEFAULT NULL`); si llega `NULL` se omite del `INSERT` (se deja generar);
    si llega un valor se inserta con `OVERRIDING SYSTEM VALUE`.
  - Columna con `DEFAULT` (no identity): parámetro opcional (`DEFAULT NULL`);
    `NULL` ⇒ columna omitida del `INSERT` (aplica el `DEFAULT` de la tabla).
    Limitación documentada: no hay forma de insertar explícitamente `NULL`
    literal en una columna con `DEFAULT` a través de este procedure.
  - Columna `NOT NULL` sin `DEFAULT` ni generada: parámetro obligatorio.
  - Columna nullable sin `DEFAULT`: parámetro opcional (`DEFAULT NULL`); la
    columna siempre se incluye en el `INSERT` (no hay `DEFAULT` de tabla al
    que recurrir), por lo que `NULL` se inserta tal cual.
- **READ (`<tabla>_consultar`):**
  - Con PK: `(INOUT pk1 tipo, ..., INOUT pkN tipo, INOUT col1 tipo, ...)` —
    contrato de ADR-015. Fila inexistente → `SQLSTATE P0002`.
    **Nota de compatibilidad (confirmada en pruebas):** como *todos* los
    parámetros son `INOUT` (incluida la PK), invocar `CALL` **desde dentro de
    otro bloque PL/pgSQL** (ej. un `DO $$ ... $$` como en `tests/security/01_matrix.sql`
    MAT-07) requiere pasar una **variable** en cada posición, no un literal
    (`CALL t_consultar(v_id, v_col, ...)`, no `CALL t_consultar(102, v_col, ...)`) —
    es una restricción de PL/pgSQL para parámetros de salida, no un error de la
    extensión. Un `CALL` emitido directamente por un cliente (psql top-level,
    psycopg) no tiene esta restricción y acepta literales sin problema, ya
    probado contra `lab.producto_consultar`.
  - Sin PK: `(OUT resultado refcursor)` — abre un cursor con `SELECT *` de
    toda la tabla (ADR-009). El cliente debe leer el nombre de cursor devuelto
    por `CALL` y hacer `FETCH` sobre ese nombre dentro de la misma transacción
    (probado: `CALL t_consultar(NULL)` seguido de `FETCH ALL FROM <nombre_devuelto>`).
- **UPDATE (`<tabla>_actualizar`):** `(IN pk1 tipo, ..., IN pkN tipo, IN col1 tipo, ...)`
  con un parámetro por cada columna no-PK actualizable (se excluyen columnas
  `GENERATED ALWAYS`, igual criterio que INSERT). Fila inexistente → `P0002`.
  Solo se genera si la tabla tiene PK (si no, fila con `not_applicable`).
- **DELETE (`<tabla>_eliminar`):** `(IN pk1 tipo, ..., IN pkN tipo)`. Fila
  inexistente → `P0002`. Solo se genera si la tabla tiene PK.

Cada procedure generado usa `LANGUAGE plpgsql SECURITY INVOKER SET search_path
= <esquema_tabla>, pg_temp`, cuerpo con referencias calificadas, owner =
rol que ejecuta `generate_crud` (debe ser `crud_admin`, ver ADR-011).

### 3.3 Resultado — valores de `status` (cerrado)

| `status` | Significado | Se crea/toca el procedure |
|---|---|---|
| `success` | Procedure creado (o reemplazado con `do_replace=true`) | Sí |
| `not_applicable` | Operación no definida para esta tabla (UPDATE/DELETE sin PK) | No |
| `procedure_conflict` | Ya existe un procedure/objeto con ese nombre y `do_replace=false`, o el objeto existente no es un procedure | No |
| `validation_error` | Parámetros de la llamada inválidos (ej. `operations` vacío o con valor fuera del enum) | No |

`object_not_found`, `permission_denied` e `internal_error` **no** son valores
de `status`: PostgreSQL los señaliza como errores reales de la sentencia
completa (`SQLSTATE` 42P01, 42501, u otro) — ver §5. La función no los
disfraza como filas de resultado exitosas.

## 4. Contrato para READ — CERRADO

Ver §3.2 (READ) y ADR-015/ADR-009 en `DECISIONS.md`. Resumen:

- Tabla con PK → `consultar` por PK completa, una fila vía `INOUT`, `P0002` si no existe.
- Tabla sin PK → `consultar` de listado completo vía `refcursor OUT`.

## 5. Contrato de errores

No ocultar errores de PostgreSQL.

Python debe mostrar mensajes comprensibles, conservando una distinción entre:

- error de conexión
- error de extensión
- error de objeto
- error de permisos
- error de generación
- error inesperado

## 6. Contrato de privilegios

Python debe poder expresar una matriz lógica equivalente a:

```text
role → operation → allowed/denied
```

PostgreSQL es la autoridad real sobre los permisos.

Python no debe simular permisos únicamente en memoria.

## 7. Regla de cambios

Una modificación de contrato requiere:

- actualizar este documento
- registrar una entrada en `DECISIONS.md`
- actualizar memoria del agente correspondiente
- advertir al resto del equipo

## 8. Revisión de integración

Antes de considerar integrado el proyecto, deben probarse al menos:

```text
Python → detectar extensión
Python → analizar tabla
Python → generar INSERT
Python → generar READ
Python → generar UPDATE
Python → generar DELETE
Python → configurar privilegios
PostgreSQL → negar acceso no autorizado
```
