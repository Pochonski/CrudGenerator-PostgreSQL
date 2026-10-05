# CRUD Generator PostgreSQL — Aplicación Python

## Requisitos

- Python >= 3.11
- PostgreSQL compatible con el proyecto
- Extensión `crud_generator` 1.0 instalada en la base de datos
- `psycopg` (`psycopg[binary]>=3.2`)
- Usuario autenticado que pueda `SET ROLE` al rol administrativo `crud_admin`
  (o ejecutar ya como ese rol/equivalente)

Aclaración: `crud_admin` es `NOLOGIN` en el laboratorio del equipo, por lo que
en ese entorno se autentica con una cuenta administrativa capaz de
`SET ROLE crud_admin`. No se publican passwords reales como recomendación
de producción.

## Instalación

Desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./app[dev]"
```

Esta es la sintaxis usada por el repo (`app/pyproject.toml`, paquete
`crud-generator-postgresql`, extra `dev` con `pytest` + `ruff`).

## Ejecución

Con el virtualenv activo (funciona desde la raíz, paquete instalado editable):

```bash
crudgen
```

Alternativa real equivalente:

```bash
python -m crud_generator.main
```

Ambos ejecutan `crud_generator.main:main` → `ApplicationFlow(Cli()).run()`.
No se requiere estar en `app/` ni ajustar `PYTHONPATH` cuando el paquete
está instalado editable.

## Flujo interactivo REAL

Orden implementado en `src/crud_generator/application.py` + `ui/cli.py`:

1. Servidor (default `localhost`)
2. Puerto (default `5432`)
3. Base de datos
4. Usuario
5. Contraseña (vía `getpass`, nunca se imprime ni registra)
6. Conexión (`ConnectionManager.connect` + `validate()` → `Conexión exitosa`,
   base y usuario)
7. `SET ROLE` administrativo a `crud_admin` (`ConnectionManager.assume_role`,
   con `RESET ROLE` al salir; si ya es ese rol es no-op)
8. Detección de extensión (`ExtensionService.check_extension`: `INSTALLED` /
   `NOT_INSTALLED` / `NOT_ACCESSIBLE` / `ERROR`; otro estado detiene el flujo)
9. Selección de esquema (`CatalogService.list_schemas`, numerada)
10. Selección de una/varias tablas (`list_tables`, `1` / `1,3,5` / `a` todas)
11. Selección de operaciones CRUD (`INSERT, READ, UPDATE, DELETE`, `1,2` / `a`)
12. Elección `do_replace` (`s/n`, default `n`)
13. `analyze_table` real por tabla
   (`SELECT * FROM crud_generator.analyze_table(%s,%s)`)
14. Presentación de metadata (`show_table_metadata`: tipo, PK, nullable,
   `DEFAULT`, `identity`, `generated`)
15. `generate_crud` real por tabla
   (`SELECT * FROM crud_generator.generate_crud(%s,%s,%s,%s)`)
16. Resultados por operación: `success` / `not_applicable` /
   `procedure_conflict` / `validation_error` (se muestran todos, sin ocultar)
17. Selección de roles PostgreSQL (`list_roles`, `1,3` / `a`; aviso si es
   superusuario)
18. Matriz de permisos (`PrivilegeMatrix`: por cada `SUCCESS` × cada rol se
   pregunta `Permitir <OP>? [s/n]`)
19. `GRANT`/`REVOKE` directos reales (`PrivilegeService.apply_matrix`, dos
    llaves INVOKER, atómico por tabla; tablas con `PROCEDURE_CONFLICT` o
    `VALIDATION_ERROR` excluyen privilegios hasta resolver generación)
20. Resumen de cambios (`show_privilege_changes` por tabla)
21. Verificación efectiva (`PermissionProbeService`: por cada rol × `SUCCESS`
    ejecuta el `CALL` real con NULLs; `42501` = denegado, otro desenlace =
    no denegado; se compara contra la matriz y se marcan `OK`/`DISCREPANCIA`,
    §11 paso 9)
22. Ejecución con valores (`ProcedureService`: elige operación `SUCCESS`,
    pide valores como texto —vacío = NULL, PostgreSQL castea; literal
    inválido → error mostrable `22P02`— y muestra retornos `INOUT` o filas
    del `refcursor` en READ sin PK, §11 paso 10)

Aclaración: `PermissionProbeService` también se usa fuera del flujo (E2E,
tests de integración); dentro del flujo solo verifica, nunca persiste
(`force_rollback`), mientras que el paso 22 sí persiste (commit).

## Modelo de seguridad

Fiel al contrato vigente:

- Procedures `SECURITY INVOKER` (explícito por la extensión).
- Owner esperado `crud_admin`.
- `PUBLIC` sin `EXECUTE` (la extensión revoca `EXECUTE ... FROM PUBLIC` por
  defecto).
- Para una operación permitida se necesita, a la vez:
  - `USAGE` sobre el schema,
  - `EXECUTE` sobre el procedure generado,
  - permiso de tabla correspondiente (`INSERT` / `SELECT` / `UPDATE` /
    `DELETE`).
- Python aplica privilegios directos (`GRANT`/`REVOKE`).
- Un `REVOKE` directo no garantiza denegación efectiva si existen permisos
  heredados (membresía en otro rol), `PUBLIC`, owner o superusuario.
- La validación efectiva se hace con `SET ROLE` + `CALL` real
  (`PermissionProbeService` o `psql`), no solo con el texto del CLI ni solo
  con `has_*_privilege`.

## do_replace

- `false`: procedure existente con la misma firma → `procedure_conflict`
  (no se reemplaza).
- `true`: `CREATE OR REPLACE` según contrato de la extensión (preserva grants).

No se afirma `DROP+CREATE`.

## Estados/errores

Estados cerrados de `generate_crud` (contrato §3.3):

- `success`
- `not_applicable` (solo válido para `UPDATE`/`DELETE` en tabla sin PK)
- `procedure_conflict`
- `validation_error`

Las excepciones PostgreSQL reales se propagan como jerarquía propia
(`DatabaseConnectionError` y subtipos) conservando `SQLSTATE`. Ejemplos de
significado (no exhaustivos, no se promete que sean los únicos posibles):

- `42501` permiso insuficiente
- `42P01` tabla inexistente
- `P0002` fila no encontrada en `READ` por PK

## Tests

Desde `app/`:

```bash
python -m pytest -q
```

Resultado actual certificado: `280 passed, 5 skipped`.

Integración real requiere explícitamente:

```bash
CRUDGEN_TEST_POSTGRES=1 \
PGHOST=<host> PGPORT=<puerto> PGDATABASE=<db> \
PGUSER=<usuario> PGPASSWORD=<password> \
python -m pytest -q
```

Comando genérico con variables, no atado a ningún puerto como requisito
productivo. El puerto `55432` corresponde únicamente al contenedor de
desarrollo usado en la certificación (`crudgen-postgres-dev`).

Resultado certificado del entorno E2E: `285 passed`.

Ruff (desde `app/`):

```bash
python -m ruff check src tests
```

Certificado limpio (`All checks passed`).

## Evidencia E2E

Resumen fecha 2026-10-03:

- PostgreSQL 16.15
- `crud_generator` 1.0

Casos reales sobre schema exclusivo `armando_e2e` (sin tocar
`lab.tabla_virgen`):

- PK simple (`cliente`)
- PK compuesta (`detalle`)
- `identity`/`default` (`cliente.id`, `creado_en`, `cantidad`)
- `generated stored` (`registro.impuesto`)
- Tres roles (`vendedor`: I+R / `supervisor`: I+R+U / `administrador`: I+R+U+D)
- Tabla nueva `sorpresa_final` generada sin cambios de Python
- `ALLOWED` y `DENIED 42501` vía `SET ROLE` + `CALL` real con rollback
- Tabla inexistente `42P01`

Sin password en la evidencia.
