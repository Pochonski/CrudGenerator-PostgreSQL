# crud_generator — extensión PostgreSQL

Genera dinámicamente procedimientos CRUD de mantenimiento a partir de los
catálogos de PostgreSQL. Contrato completo y decisiones de diseño en
[`crud_generator_docs/CONTRACTS.md`](../crud_generator_docs/CONTRACTS.md) y
[`crud_generator_docs/DECISIONS.md`](../crud_generator_docs/DECISIONS.md).

## Instalación

### Con `pg_config`/PGXS (instalación estándar)

```bash
cd extension
make install
```

Esto copia `crud_generator.control` y `sql/crud_generator--1.0.sql` al
directorio de extensiones de la instalación de PostgreSQL apuntada por
`pg_config`.

### Manual (sin herramientas de build, p. ej. dentro de un contenedor oficial)

Como la extensión es 100% SQL/PL-pgSQL (sin código C), basta con copiar los
dos archivos al directorio de extensiones del servidor:

```bash
docker cp crud_generator.control <contenedor>:$(docker exec <contenedor> pg_config --sharedir)/extension/
docker cp sql/crud_generator--1.0.sql <contenedor>:$(docker exec <contenedor> pg_config --sharedir)/extension/
```

### Activar en una base de datos

```sql
CREATE EXTENSION crud_generator;
GRANT USAGE ON SCHEMA crud_generator TO <rol_que_generara>;
```

El rol que ejecute `generate_crud` debe tener `CREATE` sobre el esquema
destino de las tablas (ej. `crud_admin`, ver ADR-011): la extensión corre en
modo `SECURITY INVOKER`, así que los procedures generados quedan con ese rol
como owner.

## API pública

```sql
SELECT * FROM crud_generator.analyze_table('mi_esquema', 'mi_tabla');

SELECT * FROM crud_generator.generate_crud(
  'mi_esquema', 'mi_tabla',
  ARRAY['INSERT','READ','UPDATE','DELETE'],
  false  -- do_replace
);
```

Ver `CONTRACTS.md` §3 para el significado exacto de cada columna del
resultado y las reglas de generación (DEFAULT/IDENTITY, PK simple/compuesta,
tablas sin PK, conflicto con procedures existentes).

## Estructura

```text
extension/
├── crud_generator.control      # metadata de la extensión (schema fijo: crud_generator)
├── Makefile                    # build PGXS estándar
└── sql/
    └── crud_generator--1.0.sql # tipos + funciones (análisis de catálogo y generación)
```

## Validado contra

PostgreSQL 16 (misma versión que `.github/workflows/sql-harness.yml`), usando
el laboratorio de pruebas de `tests/fixtures/01_roles.sql` y
`tests/fixtures/02_schema.sql`: clave primaria simple (`lab.producto`),
compuesta (`lab.detalle_factura`), IDENTITY/DEFAULT (`lab.ticket`), tabla sin
PK (`lab.bitacora`) y tipos/nombres especiales (`lab.catalogo_especial`).
