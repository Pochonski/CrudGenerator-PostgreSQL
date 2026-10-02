# Integración con la extensión real — de Joyce para Armando y Joseph

## Propósito

La extensión `crud_generator` (PR #8, rama `joyce/extension-foundation`) ya
está implementada y probada contra PostgreSQL 16. Este documento es la guía
concreta para que Armando conecte `app/` contra la API real y para que
Joseph re-apunte su harness de pruebas contra los procedures reales en vez
de los fixtures manuales.

**Fuentes relacionadas:** `CONTRACTS.md` (contrato formal), `DECISIONS.md`
(ADR-007/009/010/011/015), `EXTENSION_MEMORY.md`, `COORDINATION_REQUESTS.md`,
`extension/README.md`.

No hay más decisiones pendientes de mi lado (CR-JOYCE-001..005 resueltas).
Lo que queda documentado aquí es **cómo consumir** lo que ya existe.

---

## 1. Para Armando (Python)

### 1.1 Nombre y esquema de la extensión — confirmado

- Nombre: `crud_generator` (coincide con tu `DEFAULT_EXTENSION_NAME` en
  `extension_service.py`; no hace falta cambiar nada ahí).
- La extensión vive en su propio esquema `crud_generator` (fijado en el
  `.control`). Tu consulta de `check_extension` ya hace join con
  `pg_namespace` vía `extnamespace`, así que detecta el esquema real
  automáticamente — tampoco requiere cambios.

### 1.2 Distinción clave: FUNCTIONS vs PROCEDURES

- `crud_generator.analyze_table` y `crud_generator.generate_crud` son
  **FUNCTIONS** (devuelven filas). Se llaman con `SELECT`, igual que tus
  consultas de catálogo actuales:

  ```python
  cur.execute(
      "SELECT * FROM crud_generator.analyze_table(%s, %s)",
      (schema_name, table_name),
  )
  columns = cur.fetchall()
  ```

  ```python
  cur.execute(
      "SELECT * FROM crud_generator.generate_crud(%s, %s, %s, %s)",
      (schema_name, table_name, operations, do_replace),
  )
  results = cur.fetchall()  # una fila por operación, ver CONTRACTS.md §3.3
  ```

  `operations` es un `text[]` de Postgres: en psycopg3 basta pasar una lista
  de Python de strings (`["INSERT", "READ"]`), psycopg la adapta sola.

- Los procedures generados (`<tabla>_insertar`, `_consultar`, `_actualizar`,
  `_eliminar`) son **PROCEDURES reales** (`CREATE PROCEDURE`, requisito del
  enunciado). Se ejecutan con `CALL`, no con `SELECT`:

  ```python
  cur.execute("CALL lab.producto_insertar(%s, %s, %s)", (1, "Teclado", 100.00))
  ```

  El nombre de esquema/rutina viene de `routine_name`/`schema_name` en el
  resultado de `generate_crud` — son **identificadores**, no valores. Si los
  insertás en el texto del `CALL`, usá `psycopg.sql.Identifier`/`psycopg.sql.SQL`
  para componer la sentencia de forma segura (no f-strings con el nombre a
  pelo), igual que el enunciado exige para la propia extensión:

  ```python
  from psycopg import sql
  stmt = sql.SQL("CALL {}.{}({})").format(
      sql.Identifier(schema_name),
      sql.Identifier(routine_name),
      sql.SQL(", ").join(sql.Placeholder() * len(values)),
  )
  cur.execute(stmt, values)
  ```

### 1.3 Cómo leer el resultado de `generate_crud`

Cada fila trae `operation, status, schema_name, routine_name,
identity_arguments, message, sqlstate` (ver `CONTRACTS.md` §3.3). Lógica
esperada en Python:

```python
for row in results:
    if row.status == "success":
        ...  # guardar routine_name + identity_arguments para GRANTs (ver 1.5)
    elif row.status == "not_applicable":
        ...  # mostrar al usuario que esa operación no aplica (tabla sin PK)
    elif row.status == "procedure_conflict":
        ...  # ofrecer reintentar con do_replace=True
    elif row.status == "validation_error":
        ...  # error de la propia llamada (ej. operación desconocida)
```

Cualquier otro problema (tabla inexistente `42P01`, permiso insuficiente
`42501`, o cualquier error interno de PostgreSQL) **no** aparece como fila:
sale como excepción real de `psycopg.errors.*`. No la conviertas en un
`status` — mostrala tal cual con su `sqlstate` (regla de `CONTRACTS.md` §5,
"no ocultar errores de PostgreSQL").

### 1.4 Ejecutar los procedures generados, caso por caso

- **INSERT/UPDATE/DELETE:** `CALL schema.routine(%s, %s, ...)` con los
  valores en el mismo orden que `identity_arguments`. Fila inexistente en
  UPDATE/DELETE → excepción con `SQLSTATE P0002` (no una fila de resultado).
- **READ con PK:** todos los parámetros son `INOUT`. Un `CALL` emitido
  directamente desde Python/psycopg (no desde otro bloque PL/pgSQL) acepta
  literales/parámetros normales sin restricción — ya probado contra
  `lab.producto_consultar`:

  ```python
  cur.execute("CALL lab.producto_consultar(%s, %s, %s)", (102, None, None))
  row = cur.fetchone()  # (102, 'Mouse', 10.00) si existe; P0002 si no
  ```

- **READ sin PK (tabla sin clave primaria):** el procedure tiene un único
  parámetro `OUT resultado refcursor`. Hace falta una transacción explícita
  (sin autocommit) para que el cursor siga vivo entre el `CALL` y el `FETCH`:

  ```python
  with conn.transaction():  # o autocommit=False + commit() manual
      cur.execute("CALL lab.bitacora_consultar(%s)", (None,))
      cursor_name = cur.fetchone()[0]
      cur.execute(sql.SQL("FETCH ALL FROM {}").format(sql.Identifier(cursor_name)))
      rows = cur.fetchall()
  ```

### 1.5 Privilegios — CR-ARMANDO-001 (pendiente de tu lado)

Mi extensión **revoca `EXECUTE` de `PUBLIC`** automáticamente en cada
procedure que genera (ADR-011): ningún rol de negocio tiene acceso hasta que
Python lo otorgue explícitamente. Para habilitar un rol tenés que otorgar
**dos permisos** (modelo de dos llaves bajo `SECURITY INVOKER`, ver
`SECURITY_MEMORY.md` de Joseph):

```sql
GRANT USAGE ON SCHEMA lab TO crud_vendedor;
GRANT EXECUTE ON PROCEDURE lab.producto_insertar(integer, text, numeric) TO crud_vendedor;
GRANT INSERT ON lab.producto TO crud_vendedor;  -- permiso de tabla, también necesario
```

Usá el `identity_arguments` real devuelto por `generate_crud` para construir
la firma del `GRANT EXECUTE ON PROCEDURE` — no la adivines ni la
hardcodees, puede variar según las columnas de la tabla (ver tabla de
firmas reales en la sección 2.3 para referencia, pero son ejemplos del
laboratorio, no una lista fija de producción).

Quién ejecuta estos `GRANT`: el mismo rol que generó los procedures (ej.
`crud_admin`), porque es su owner. Esto cierra CR-ARMANDO-001 de tu lado
(definir si Python ejecuta GRANT/REVOKE directo — la respuesta, según
ADR-012, es sí, directo, con el rol administrador, no simulado en memoria).

### 1.6 Rol de conexión para generar

El rol con el que Python se conecta al llamar `generate_crud` necesita
`CREATE` sobre el esquema destino (ej. `crud_admin`). Si no lo tiene, la
llamada falla con un error real de PostgreSQL (`42501`) — no hace falta
lógica especial, solo no ocultarlo.

---

## 2. Para Joseph (Seguridad/Integración/Pruebas)

### 2.1 Ya aplicado

- Fix de `has_function_privilege('PUBLIC', ...)` → `'public'` en
  `tests/security/10_generated_routine_discovery.sql` (commiteado en PR #8).

### 2.2 Pendiente de tu lado: ajuste en `01_matrix.sql` MAT-07

Al apuntar MAT-07 a `lab.producto_consultar` **real** (no tu fixture), la
PK también es `INOUT` (ADR-015), a diferencia de tu fixture donde era `IN`.
Dentro de un bloque `DO $$ ... $$` eso exige pasar una **variable** en las
tres posiciones, no un literal en la primera:

```sql
-- Antes (fixture, PK como IN):
CALL lab.producto_consultar(102, v_nombre, v_precio);

-- Con el procedure real (PK también INOUT):
DECLARE
  v_id integer := 102;
BEGIN
  CALL lab.producto_consultar(v_id, v_nombre, v_precio);
```

Confirmado que funciona así contra el procedure real.

### 2.3 Cómo generar los procedures reales para tu harness

En vez de `03_security_fixtures.sql` / `06_composite_pk_fixtures.sql` /
`07_ticket_fixtures.sql` / `08_special_nopk_fixtures.sql` (que crean
procedures manuales), después de `01_roles.sql` + `02_schema.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS crud_generator;
GRANT USAGE ON SCHEMA crud_generator TO crud_admin;
SET ROLE crud_admin;
SELECT * FROM crud_generator.generate_crud('lab','producto',           ARRAY['INSERT','READ','UPDATE','DELETE']);
SELECT * FROM crud_generator.generate_crud('lab','detalle_factura',    ARRAY['INSERT','READ','UPDATE','DELETE']);
SELECT * FROM crud_generator.generate_crud('lab','ticket',             ARRAY['INSERT','READ','UPDATE','DELETE']);
SELECT * FROM crud_generator.generate_crud('lab','bitacora',           ARRAY['INSERT','READ','UPDATE','DELETE']);
SELECT * FROM crud_generator.generate_crud('lab','catalogo_especial',  ARRAY['INSERT','READ','UPDATE','DELETE']);
RESET ROLE;
```

`04_grants.sql` (firma `lab.producto_*(integer, text, numeric)`) funciona
**sin cambios** contra los procedures reales de `lab.producto` — ya lo
verifiqué corriendo `04_grants.sql` + `01_matrix.sql` (MAT-01..06 OK,
MAT-07 con el ajuste de la sección 2.2). `05_grants_template.sql` queda
lista para llenarse con las firmas reales de las demás tablas (tabla de
referencia abajo).

### 2.4 Firmas reales confirmadas (referencia, no una lista congelada)

Obtenidas corriendo tu propio `10_generated_routine_discovery.sql` contra
las 18 rutinas generadas. Son el resultado de generar sobre las 5 tablas
del laboratorio tal como están definidas hoy en `02_schema.sql` — si
cambian las columnas de una tabla, las firmas cambian con ellas (por diseño,
no están hardcodeadas en ningún lado).

| Rutina | Identity arguments |
|---|---|
| `producto_insertar` | `IN p_1 integer, IN p_2 text, IN p_3 numeric` |
| `producto_consultar` | `INOUT p_1 integer, INOUT p_2 text, INOUT p_3 numeric` |
| `producto_actualizar` | `IN p_1 integer, IN p_2 text, IN p_3 numeric` |
| `producto_eliminar` | `IN p_1 integer` |
| `detalle_factura_insertar` | `IN p_1 integer, IN p_2 integer, IN p_3 integer` |
| `detalle_factura_consultar` | `INOUT p_1 integer, INOUT p_2 integer, INOUT p_3 integer` |
| `detalle_factura_actualizar` | `IN p_1 integer, IN p_2 integer, IN p_3 integer` |
| `detalle_factura_eliminar` | `IN p_1 integer, IN p_2 integer` |
| `ticket_insertar` | `IN p_2 text, IN p_3 timestamp with time zone` (sin `p_1`: `id_ticket` es IDENTITY ALWAYS) |
| `ticket_consultar` | `INOUT p_1 integer, INOUT p_2 text, INOUT p_3 timestamp with time zone` |
| `ticket_actualizar` | `IN p_1 integer, IN p_2 text, IN p_3 timestamp with time zone` |
| `ticket_eliminar` | `IN p_1 integer` |
| `bitacora_insertar` | `IN p_1 integer, IN p_2 text, IN p_3 timestamp with time zone` |
| `bitacora_consultar` | `OUT resultado refcursor` (sin PK → listado completo, ADR-009) |
| `bitacora_actualizar` / `bitacora_eliminar` | no se generan (`not_applicable`, sin PK) |
| `catalogo_especial_insertar` | `IN p_2 text, IN p_1 integer, IN p_3 numeric, IN p_4 boolean, IN p_5 jsonb, IN p_6 date` (orden: obligatorios antes que opcionales, ver `CONTRACTS.md` §3.2) |
| `catalogo_especial_consultar` | `INOUT p_1 integer, INOUT p_2 text, INOUT p_3 numeric, INOUT p_4 boolean, INOUT p_5 jsonb, INOUT p_6 date` |
| `catalogo_especial_actualizar` | `IN p_1 integer, IN p_2 text, IN p_3 numeric, IN p_4 boolean, IN p_5 jsonb, IN p_6 date` |
| `catalogo_especial_eliminar` | `IN p_1 integer` |

Verificado en esta misma corrida: 18/18 owner `crud_admin`, 18/18
`SECURITY INVOKER`, 18/18 `search_path=lab, pg_temp`, 0 fugas de `EXECUTE`
a `PUBLIC`.

### 2.5 Tabla virgen (desconocida)

`lab.tabla_virgen` (`id integer PRIMARY KEY, nota text`) es una tabla con PK
simple común y corriente — no necesita ningún caso especial en la
extensión. Cuando el equipo decida "activarla" para la prueba final, alcanza
con `SELECT * FROM crud_generator.generate_crud('lab','tabla_virgen',
ARRAY['INSERT','READ','UPDATE','DELETE']);` igual que cualquier otra tabla
con PK simple (ej. `lab.producto`). No lo corrí yo para no invalidar la
regla de "no tocar `tabla_virgen` antes de la prueba final" (`tests/README.md`).

---

## 3. Qué NO cambió (para evitar releer todo `CONTRACTS.md`)

- Naming: `<tabla>_insertar/consultar/actualizar/eliminar` (ADR-007), sin cambios.
- Modelo de privilegios de dos llaves bajo INVOKER: sin cambios (Joseph ya lo
  diseñó y probó; la extensión solo garantiza que `EXECUTE` arranca en cero).
- Matriz de roles `crud_vendedor/crud_supervisor/crud_administrador`: sin cambios.
