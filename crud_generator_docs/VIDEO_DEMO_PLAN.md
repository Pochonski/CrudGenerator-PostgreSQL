# Plan de vídeo (§10) y demo en vivo (§11) — evidencia de funcionamiento

**Fuente:** `documento_completo.md` §10 (vídeo, 10 pasos) y §11 (demo en vivo, 10 pasos).
**Estado:** guion actualizado al flujo Python integrado 03-10-2026 (E2E
`armando_e2e` validado: `ApplicationFlow` real genera y aplica privilegios;
la ejecución efectiva se demuestra con `CALL`/`PermissionProbeService`).
La grabación es manual. Duración objetivo: 8–12 min.

## Escena 0 — Base limpia (30 s, off-camera preferible)

```sql
-- 01_roles.sql + 02_schema.sql → roles crud_* + 6 tablas lab (virgen incluida).
-- Extensión instalada: CREATE EXTENSION crud_generator; (ver extension/README.md)
```

## Paso 1 — Instalación de la extensión (§10.1)

```bash
cd extension && make install   # o copia manual al dir de extensiones (README)
psql -c "CREATE EXTENSION crud_generator;"
psql -c "SELECT extname, extversion FROM pg_extension WHERE extname='crud_generator';"
```
Esperado: `crud_generator | 1.0`.

## Paso 2 — Conexión mediante Python (§10.2)

```bash
cd app && python -m crud_generator.main
# Servidor [localhost] / Puerto / Base devdb / Usuario postgres / Contraseña ********
```

Flujo REAL implementado (`application.py` + `db/connection.py`):

1. La aplicación se autentica con una cuenta PostgreSQL con `LOGIN`
   (`crud_admin` es `NOLOGIN` en el laboratorio real, por lo que NO puede
   usarse como usuario de autenticación directa).
2. Esa cuenta debe poder ejecutar `SET ROLE crud_admin`. En el contenedor
   local de desarrollo/demo se usó `postgres` (solo laboratorio/demo local;
   NO se recomienda superusuario como modelo productivo; en otro entorno
   puede utilizarse cualquier usuario `LOGIN` autorizado a `SET ROLE
   crud_admin`). No se escribe ningún password en el guion.
3. Tras conectarse, `ApplicationFlow` entra en
   `ConnectionManager.assume_role("crud_admin")`.
4. Bajo ese rol administrativo se ejecutan la detección/uso administrativo de
   la extensión según el flujo, la generación CRUD y la aplicación de
   privilegios.
5. Al salir, `ConnectionManager` hace `RESET ROLE`.

Ejemplo documental correcto:

```text
Servidor: localhost
Puerto: <puerto de demo>
Base: devdb
Usuario: postgres   # solo laboratorio/demo local
Contraseña: ********

→ Conexión autenticada como postgres
→ ApplicationFlow asume crud_admin internamente
→ generación y administración continúan como crud_admin
```

Nota: `validate()` ocurre antes del `SET ROLE`, por lo que el mensaje de
conexión muestra el usuario autenticado (ej. `postgres`), no se afirma que
muestre `current_user=crud_admin`.

## Paso 3 — Detección de la extensión (§10.3)

En la misma sesión Python: `Verificando extensión...` →
`instalada (versión 1.0, esquema crud_generator)`.
Contrapunto (un take de 10 s): contra una base sin extensión muestra
`no está instalada en la base de datos actual` (estado NOT_INSTALLED).

## Paso 4 — Selección del esquema (§10.4)

CLI lista esquemas (`CatalogService.list_schemas`, sin `pg_catalog` ni
`information_schema`) → elegir `lab`.

## Paso 5 — Selección de tablas (§10.5)

CLI lista tablas (`relkind r/p`) → mostrar una / varias / todas (`a`).

## Paso 6 — Generación de procedimientos (§10.6)

Desde la CLI Python real (`ApplicationFlow`):

- Selección de operaciones (`INSERT, READ, UPDATE, DELETE`, `a` todas).
- Elección `do_replace` (`n` en creación fresca).
- Por tabla: metadata real de `analyze_table` mostrada en CLI.
- `generate_crud` real → `4 × success` por tabla (ej. `lab.producto`,
  `detalle_factura` con PK compuesta, `ticket` con identity).

Nota histórica: hasta el 02-10 este paso se mostraba vía `psql` directo
(`SELECT ... generate_crud(...)` con `SET ROLE crud_admin`); desde el
03-10 se graba desde la CLI Python integrada.

## Paso 7 — Ejecución de los procedimientos (§10.7)

La aplicación interactiva NO pide valores CRUD ni ejecuta los procedures
generados (administra generación y privilegios). La ejecución efectiva se
demuestra con `CALL` real (vía `psql` o `PermissionProbeService` con
rollback):

```sql
SET ROLE crud_vendedor;
CALL lab.producto_insertar(101, 'Teclado', 25.50);
-- READ por PK (INOUT ⇒ variable en DO, literal en cliente):
--   psql: CALL lab.producto_consultar(101, NULL, NULL); → (101,'Teclado',25.50)
RESET ROLE;
-- Evidencia guardada: MAT-01..07 7/7, MAT-C1..C9 9/9, TIXR, S-AUDR.
```

## Paso 8 — Asignación de privilegios (§10.8)

Desde la CLI Python real (`ApplicationFlow` → `PrivilegeService.apply_matrix`):

- Selección de roles (ej. `crud_vendedor`, `crud_supervisor`,
  `crud_administrador`).
- Matriz por tabla (preguntas `Permitir <OP>? [s/n]` por cada `SUCCESS` × rol).
- Doble llave INVOKER aplicada (ADR-011): `EXECUTE` + permiso de tabla +
  `USAGE ON SCHEMA`.

Equivalente SQL (referencia, no grabación principal):

```sql
-- Doble llave INVOKER (ADR-011): EXECUTE + permiso de tabla.
GRANT EXECUTE ON PROCEDURE lab.producto_insertar(integer,text,numeric) TO crud_vendedor;
GRANT SELECT, INSERT ON lab.producto TO crud_vendedor;
-- Matriz completa: vendedor I+R / supervisor I+R+U / administrador I+R+U+D
-- (04_grants.sql + grants reales del handoff §2.4).
```

## Paso 9 — Validación con diferentes usuarios (§10.9)

Con `CALL` real o `PermissionProbeService` (la CLI interactiva no ejecuta
CRUD; solo administra generación y privilegios):

```sql
SET ROLE crud_vendedor;      CALL lab.producto_eliminar(101);  -- ERROR 42501
SET ROLE crud_administrador; CALL lab.producto_eliminar(101);  -- OK + P0002 al re-consultar
```
Evidencia: NEG-01..11, REV-01 (REVOKE→GRANT con vecinos intactos), PUB-01/02.

## Paso 10 — Tablas no usadas en desarrollo (§10.10 / §11 tabla del docente)

Transcript real 02-10 (VIR-00..06, PG18): `tabla_virgen(id, nota)` pasó de
0 rutinas → `generate_crud` 4×success → INSERT+READ vendedor OK → DELETE 42501
→ ciclo admin OK/P0002 → DROP + virgen restaurada (0 rutinas, 0 filas).
En vivo el docente aporta su tabla: repetir VIR-01..05 con su nombre.

## Checklist pre-grabación

- [ ] Base demo fresca (roles+schema+extensión, sin datos de prueba).
- [ ] `app/` corriendo con cuenta `LOGIN` de demo capaz de `SET ROLE
  crud_admin`; `ApplicationFlow` realiza la asunción del rol administrativo
  internamente (pasos 2-6 y 8 desde la CLI, sin `psql` para generar ni para
  grants).
- [ ] `psql` / `PermissionProbeService` listo para pasos 7 y 9 (ejecución
  efectiva con `CALL` real; la CLI no pide valores CRUD).
- [ ] Transcript virgen a mano por si piden la tabla desconocida.
- [ ] Confirmar con el docente formato de entrega del vídeo (ADR-014: fecha 04-10-2026).
