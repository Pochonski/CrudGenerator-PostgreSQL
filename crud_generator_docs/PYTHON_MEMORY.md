# Memoria — Agente Python

**Owner:** Armando  
**Área:** Python + Interfaz

## Rol

Responsable principal de la aplicación Python, interfaz, conexión y orquestación del flujo.

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

Construir una aplicación Python que permita al administrador conectarse a PostgreSQL, detectar la extensión, seleccionar esquema/tablas/operaciones, solicitar generación y configurar privilegios.

## Responsabilidades

- Configuración de conexión.
- Conexión PostgreSQL.
- Detección de extensión.
- Consulta de esquemas.
- Consulta de tablas.
- Selección múltiple.
- Análisis y presentación de metadata.
- Selección de CRUD.
- Llamadas a la extensión.
- Consulta de roles.
- Configuración de privilegios.
- Reporte de errores.
- Flujo de demostración.

## Reglas

- No contener lógica específica de una tabla.
- No generar CRUD manualmente.
- No simular privilegios solamente en Python.
- Usar los contratos definidos en `CONTRACTS.md`.
- La UI debe estar separada de la lógica de acceso a datos tanto como sea razonable.

## Estado actual

- [x] Arquitectura de módulos (base: `config` + `db/connection`)
- [x] Biblioteca PostgreSQL confirmada (`psycopg>=3.2`, ADR-005)
- [x] Conexión (`ConnectionManager`: abrir/reutilizar/cerrar/context manager)
- [x] Detección de extensión (`ExtensionService.check_extension` → `ExtensionStatus`)
- [x] Esquemas (`CatalogService.list_schemas`)
- [x] Tablas (`CatalogService.list_tables`, solo listado; sin columnas/PK)
- [x] Selección de tablas (CLI: una/varias/todas + `CrudSelection`)
- [ ] Análisis de tabla
- [x] Selección CRUD (CLI + `CrudOperation`, sin generar)
- [ ] Generación
- [x] Roles (`CatalogService.list_roles`, solo listado; sin GRANT/REVOKE)
- [ ] Privilegios
- [x] Manejo de errores (base de conexión: jerarquía propia + SQLSTATE preservado)
- [ ] Integración completa
- [ ] Prueba con tabla nueva

## Decisiones locales

- `ConnectionManager` usa `autocommit=True` por defecto para no dejar
  transacciones abiertas en validaciones de solo lectura; con
  `autocommit=False` hace `rollback` explícito tras validar. Las operaciones
  administrativas futuras usarán transacciones explícitas.
- Jerarquía propia de errores (`AuthenticationError`, `DatabaseNotFoundError`,
  `ServerUnavailableError`, `InsufficientPrivilegeError`,
  `UnexpectedDatabaseError`, base `DatabaseConnectionError` con `sqlstate` y
  `original`) mapeada desde `psycopg`/SQLSTATE; nunca expone la contraseña
  (`repr` propio + saneado de mensajes). `commit()`/`rollback()` son estrictos:
  sin conexión abierta lanzan `DatabaseConnectionError`.
- `validate()` retorna `ConnectionInfo(database, current_user, server_version)`
  con una sola consulta (`current_database()`, `current_user`, `version()`),
  sin `print` y sin tocar catálogos. La UI decidirá cómo mostrarlo.
- Prueba de integración real aislada en
  `tests/test_connection_integration.py`, omitida sin `CRUDGEN_TEST_POSTGRES=1`.
- `CatalogService(manager)` (fase catálogo): lee `pg_namespace`, `pg_class` +
  `pg_namespace` y `pg_roles`; retorna `SchemaInfo`/`TableInfo`/`RoleInfo`
  (dataclasses frozen en `models.py`). Esquemas de sistema excluidos por
  política genérica (`pg_catalog`, `information_schema`, `pg_temp_*`,
  `pg_toast*`); tablas solo `relkind IN ('r','p')`; roles sin filtrar nombres.
  Filtros como valores con `%s` (nunca interpolación); `list_tables("")`
  lanza `ValueError`; errores PG se mapean con `translate_error()`. Ownership de
  transacciones: con `autocommit=False` solo revierte la transacción que su
  lectura inició (estado inicial `IDLE`); nunca toca una transacción
  preexistente del caller (`INTRANS`).
- `ConnectionManager.translate_error()` (aditivo, sin cambio de
  comportamiento) para que los servicios reutilicen `_map_error` sin importar
  privados entre módulos.
- `ExtensionService(manager)` (fase extensión §4.2): `check_extension(nombre)`
  consulta `pg_extension` + `has_schema_privilege(oid, 'USAGE')` y retorna
  `ExtensionStatus(name, state, version, schema, message, sqlstate)` con
  `ExtensionState`: `INSTALLED` (fila + USAGE; el mensaje aclara que la
  verificación de EXECUTE sobre la API pública está pendiente),
  `NOT_INSTALLED` (sin fila, nunca por excepción), `NOT_ACCESSIBLE`
  (detección parcial basada actualmente en falta de USAGE), `ERROR` (fallo de
  la consulta con SQLSTATE; el fallo de conexión lanza en vez de retornarse).
  Nombre parametrizado con `%s`; `""` → `ValueError`; ownership de
  transacciones igual que `CatalogService`; solo `psycopg.Error` se convierte
  en `ERROR` (un bug ajeno a PG se propaga).
- Nombre de extensión NO congelado: la lógica recibe el nombre por parámetro;
  `DEFAULT_EXTENSION_NAME = "crud_generator"` es provisional (del diagrama de
  `ARCHITECTURE.md`) hasta que Joyce confirme el `.control`.
- CLI + orquestador (`ui/cli.py` + `application.py`, `main.py` mínimo):
  `Cli` con I/O inyectable (password con `getpass`, defaults host/puerto,
  reintentos); `ApplicationFlow` (factorías inyectables) orquesta
  conexión → extensión → esquema → tablas → operaciones → `CrudSelection`
  inmutable (`schema`, `tables`, `operations`) y mensaje final de generación
  pendiente. `NOT_INSTALLED`/`NOT_ACCESSIBLE`/`ERROR` detienen el flujo sin
  intentar CRUD; errores muestran mensaje sin traceback.
- No se tocó ningún contrato global (`CONTRACTS.md`/`DECISIONS.md` sin cambios).

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar cualquier cambio en firmas, nombres, parámetros o resultados que afecte a la extensión o seguridad.

- **REQUIERE COORDINACIÓN — JOYCE (nombre de la extensión):** `DEFAULT_EXTENSION_NAME`
  es provisional; falta el nombre definitivo del `.control`/API para congelarlo.
- **REQUIERE COORDINACIÓN — JOYCE (EXECUTE sobre funciones públicas):** el estado
  `NOT_ACCESSIBLE` hoy solo detecta falta de `USAGE` sobre el esquema instalado;
  la verificación fina de `EXECUTE` sobre cada función pública queda pendiente de
  que existan firmas definitivas (CR-JOYCE-001/002). No se inventó ninguna firma.
