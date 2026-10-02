# Plan de vídeo (§10) y demo en vivo (§11) — evidencia de funcionamiento

**Fuente:** `documento_completo.md` §10 (vídeo, 10 pasos) y §11 (demo en vivo, 10 pasos).
**Estado:** guion validado contra PG18 local 02-10 (transcripts reales). La grabación
es manual. Duración objetivo: 8–12 min.

> Brecha conocida: `app/` (Armando) aún no llama `generate_crud` (hitos 3-4).
> El guion muestra Python para conexión/selección (§4.1–4.4) y la extensión vía
> `psql` para generación/privilegios (§4.5–4.10). Cuando Armando integre el tramo,
> los pasos 6-8 se re-graban desde la CLI sin cambiar el resto.

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
# Servidor [localhost] / Puerto / Base devdb / Usuario crud_admin / Contraseña
# → "Conexión exitosa / Base de datos: devdb / Usuario: crud_admin"
```

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

Vía extensión (hasta integración Python):

```sql
SET ROLE crud_admin;
SELECT operation, status FROM crud_generator.generate_crud('lab','producto',
  ARRAY['INSERT','READ','UPDATE','DELETE']);
-- 4 × success. Repetir con detalle_factura (PK compuesta) y ticket (identity).
RESET ROLE;
```

## Paso 7 — Ejecución de los procedimientos (§10.7)

```sql
SET ROLE crud_vendedor;
CALL lab.producto_insertar(101, 'Teclado', 25.50);
-- READ por PK (INOUT ⇒ variable en DO, literal en cliente):
--   psql: CALL lab.producto_consultar(101, NULL, NULL); → (101,'Teclado',25.50)
RESET ROLE;
-- Evidencia guardada: MAT-01..07 7/7, MAT-C1..C9 9/9, TIXR, S-AUDR.
```

## Paso 8 — Asignación de privilegios (§10.8)

```sql
-- Doble llave INVOKER (ADR-011): EXECUTE + permiso de tabla.
GRANT EXECUTE ON PROCEDURE lab.producto_insertar(integer,text,numeric) TO crud_vendedor;
GRANT SELECT, INSERT ON lab.producto TO crud_vendedor;
-- Matriz completa: vendedor I+R / supervisor I+R+U / administrador I+R+U+D
-- (04_grants.sql + grants reales del handoff §2.4).
```

## Paso 9 — Validación con diferentes usuarios (§10.9)

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
- [ ] `app/` corriendo con `crud_admin` (pasos 2-5 sin cortes).
- [ ] `psql` listo con los bloques 6-9 (copiar/pegar, sin typos en vivo).
- [ ] Transcript virgen a mano por si piden la tabla desconocida.
- [ ] Confirmar con el docente formato de entrega del vídeo (ADR-014: fecha 04-10-2026).
