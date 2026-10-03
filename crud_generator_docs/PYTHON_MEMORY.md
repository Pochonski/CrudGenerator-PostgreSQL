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

## Estado actual (03-10-2026, integración productiva + E2E real completados)

- [x] Arquitectura de módulos (base: `config` + `db/connection`)
- [x] Biblioteca PostgreSQL confirmada (`psycopg>=3.2`, ADR-005)
- [x] Conexión (`ConnectionManager`: abrir/reutilizar/cerrar/context manager)
- [x] Detección de extensión (`ExtensionService.check_extension` → `ExtensionStatus`, 4 estados §4.2)
- [x] Esquemas (`CatalogService.list_schemas`)
- [x] Tablas (`CatalogService.list_tables`, solo listado; sin columnas/PK — `analyze_table` es de la extensión)
- [x] Selección de tablas (CLI: una/varias/todas + `CrudSelection`)
- [x] Análisis de tabla (capa servicio: `ExtensionService.analyze_table` → `tuple[ColumnMetadata, ...]`; `CONTRACTS.md` §3.1; conectado a `ApplicationFlow`)
- [x] Selección CRUD (CLI + `CrudOperation`; genera vía `ApplicationFlow` → `generate_crud` real)
- [x] Generación (capa servicio: `ExtensionService.generate_crud` → `tuple[GenerationResult, ...]`; `CONTRACTS.md` §3.2–3.3; conectado a `ApplicationFlow`)
- [x] Roles (`CatalogService.list_roles`: listado; la aplicación de permisos vive en `PrivilegeService.apply_matrix` ya conectado al flujo)
- [x] Privilegios (capa servicio: `PrivilegeService.apply_matrix` con GRANT/REVOKE
  directos de dos llaves INVOKER; `PrivilegeMatrix` sigue siendo solo intención;
  conectado a `ApplicationFlow`)
- [x] Prueba efectiva (`PermissionProbeService.probe`: SET LOCAL ROLE + CALL
  real con `transaction(force_rollback=True)`; ALLOWED vs DENIED 42501;
  `RoleAssumptionError` separado; unit tests con fakes + integración real
  opcional; validado contra PostgreSQL real, aún no integrado al flujo
  interactivo)
- [x] Flujo integrado (`ApplicationFlow`: conexión → extensión → esquema →
  tablas → operaciones → `analyze_table`/`generate_crud` por tabla con
  `do_replace` preguntado → metadata y resultados mostrados → roles reales →
  `PrivilegeMatrix` construida por tabla (solo `SUCCESS` preguntados) →
  `apply_matrix` por tabla con `CONFLICT`/`VALIDATION_ERROR` excluyendo
  privilegios de esa tabla; `PermissionProbeService` no forma parte del flujo
  interactivo normal (solo validación/E2E); integración real validada E2E
  03-10-2026 contra `armando_e2e`)
- [x] Manejo de errores (base de conexión: jerarquía propia + SQLSTATE preservado)
- [x] Integración completa (`ApplicationFlow` conecta analyze → generate → roles → matrix → grants; probado con fakes y contra PostgreSQL real)
- [x] Prueba con tabla nueva técnica completada 03-10-2026 con
  `armando_e2e.sorpresa_final` (4 `success` sin cambio de código);
  `lab.tabla_virgen` permanece intacta/reservada para demo final

## Evidencia E2E 03-10-2026 (compacta)

PG 16.15, extensión 1.0, 3 roles, 16 procedures incluyendo `sorpresa_final`,
owner `crud_admin`, INVOKER, `ALLOWED`/`DENIED 42501`, `42P01` tabla
inexistente, PK compuesta + generated verificados, `lab.tabla_virgen` 0/0
antes y después. Detalle completo en transcript fuera del repo
(`/tmp/armando_e2e_final.txt`); no se pega aquí.

## Decisiones locales

- `ConnectionManager` usa `autocommit=True` por defecto para no dejar
  transacciones abiertas en validaciones de solo lectura; con
  `autocommit=False` hace `rollback` explícito tras validar. Las operaciones
  administrativas futuras usarán transacciones explícitas.
- `ConnectionManager.assume_role(rol)` (context manager session-level):
  valida `str` no vacío, compone `SET ROLE` con `sql.Identifier` (nunca
  interpolado), verifica `SELECT current_user, session_user` (mismatch →
  error), no-op seguro si ya es el rol, `RESET ROLE` siempre en `finally`
  (también ante excepción del cuerpo), errores `psycopg.Error` mapeados con
  `SQLSTATE` (ej. `42501` sin capacidad `SET`). `ApplicationFlow` lo usa con
  `admin_role="crud_admin"` (ADR-011, inyectable) envolviendo todo el flujo
  post-conexión para que los procedures queden owned por `crud_admin` aunque
  la sesión sea `postgres`; si `SET ROLE` falla → error mostrado y
  `EXIT_STOPPED`, sin conceder memberships.
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
- `ExtensionService.analyze_table(schema, table)` (03-10, capa servicio):
  `SELECT * FROM crud_generator.analyze_table(%s, %s)` parametrizado; retorna
  `tuple[ColumnMetadata, ...]` (dataclass frozen de 12 campos, §3.1;
  `data_type` preservado como texto de `format_type()`; orden de filas
  preservado). Lectura: `autocommit=True` sin commit/rollback; `autocommit=False`
  + `IDLE` → `rollback` al final (éxito o error); `INTRANS` → no toca la
  transacción del caller. Errores `psycopg.Error` → `translate_error()` con
  `SQLSTATE` (ej. `42P01` tabla inexistente); bugs no-PG → rollback si propia
  + relanzan originales.
- `ExtensionService.generate_crud(schema, table, operations, *, do_replace=False)`
  (03-10, capa servicio): `SELECT * FROM crud_generator.generate_crud(%s, %s, %s, %s)`
  parametrizado con `operations` como `[op.value, ...]` (lista psycopg→`text[]`);
  retorna `tuple[GenerationResult, ...]` (`operation: CrudOperation`,
  `status: GenerationStatus`, resto preservado; `identity_arguments` sin parsear).
  Un `operation` NULL devuelto por PostgreSQL a través de esta API se trata
  como violación de contrato (`ValueError`), porque el servicio no permite
  enviar `operations` NULL/vacío/`None`.
  Validaciones: `schema`/`table` str no vacíos (si no: `TypeError`/`ValueError`,
  valor preservado exacto); `operations` iterable de `CrudOperation` no vacío,
  sin strings silenciosos, sin duplicados (`TypeError`/`ValueError`), orden
  preservado; `do_replace` estrictamente `bool` (`TypeError` si no). DDL real:
  `autocommit=True` sin commit/rollback manual; `autocommit=False` + `IDLE` →
  éxito `commit` una vez / error `rollback` una vez; `INTRANS` → nunca commit
  ni rollback (ni siquiera ante error). `status` desconocido u `operation`
  desconocida desde PG → `ValueError` (violación de contrato, sin fallback).
  Tests unitarios con fakes (`fetchall`/`commit`/`rollback`) en
  `tests/test_extension_service.py`; `ApplicationFlow`/CLI llaman a este
  método en el flujo normal (generación real validada E2E 03-10-2026).
- Nombre de extensión CONFIRMADO 01-10 (Joyce): `crud_generator` (`extension/crud_generator.control`,
  `schema = crud_generator`). `DEFAULT_EXTENSION_NAME` deja de ser provisional; coincide con
  `CONTRACTS.md` §3. API `analyze_table`/`generate_crud` cerrada — ver `ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md`
  para llamada desde psycopg (FUNCTION vs PROCEDURE, READ con/sin PK vía refcursor, GRANT doble llave).
- CLI + orquestador (`ui/cli.py` + `application.py`, `main.py` mínimo):
  `Cli` con I/O inyectable (password con `getpass`, defaults host/puerto,
  reintentos); `ApplicationFlow` (factorías inyectables) orquesta
  conexión → extensión → esquema → tablas → operaciones → `CrudSelection`
  inmutable (`schema`, `tables`, `operations`) y generación real
  (`analyze_table`/`generate_crud` por tabla, validada E2E 03-10-2026). `NOT_INSTALLED`/`NOT_ACCESSIBLE`/`ERROR` detienen el flujo sin
  intentar CRUD; errores muestran mensaje sin traceback.
- Matriz de privilegios (`privileges/matrix.py`, solo modelos sin SQL):
  `PrivilegeAssignment` (frozen: `role` + `CrudOperation`) y `PrivilegeMatrix`
  mutable controlada. La matriz conserva por separado el universo de roles
  configurados y los pares habilitados, por lo que un rol totalmente denegado
  permanece representado para la futura fase de REVOKE sin privilegios
  residuales. `add_role`, `enable` y `disable` registran roles; consultas y
  listados son deterministas. Representa intención del usuario, NO permisos
  efectivos de PostgreSQL; sin `GRANT`, `REVOKE` ni `SET ROLE`.
- `PrivilegeService.apply_matrix(schema, table, matrix, generation_results)`
  (capa servicio, `privileges/service.py` + `PrivilegeChange` frozen
  `role/operation/allowed/schema_name/table_name/routine_name`): reconcilia UNA
  tabla con GRANT/REVOKE directos de dos llaves INVOKER (`EXECUTE` sobre
  procedure + `INSERT`/`SELECT`/`UPDATE`/`DELETE` sobre tabla según operación;
  `GRANT USAGE ON SCHEMA` una vez por rol con ≥1 habilitada; USAGE nunca se
  revoca por tabla). Preflight sin mutar (valida `schema_name` exacto en todo
  resultado, inputs/matriz/statuses/naming
  `<tabla>_insertar|consultar|actualizar|eliminar`, exige GenerationResult para
  toda operación habilitada por algún rol —ausente+denegada por todos es válida
  fuera de scope—, resuelve cada SUCCESS en
  `pg_catalog` exigiendo 1 fila `prokind='p'` y firma
  `pg_get_function_identity_arguments()` idéntica a `GenerationResult`;
  `identity_arguments` del caller jamás se inyecta como SQL: solo se usa el
  string recuperado del catálogo; `""` válido, `None` rechazado;
  `NOT_APPLICABLE` (solo válido para UPDATE/DELETE: INSERT/READ con ese
  status es violación de contrato) habilitada / `PROCEDURE_CONFLICT` /
  `VALIDATION_ERROR` →
  `ValueError` antes de mutar; `NOT_APPLICABLE` denegada por todos limpia el
  permiso directo de tabla por rol —`REVOKE <priv> ON TABLE`, sin `EXECUTE`,
  sin `USAGE`, sin `PrivilegeChange` porque no hay procedure aplicable—). Atomicidad: `IDLE` → `with conn.transaction()`
  (vale con `autocommit=True/False`); `INTRANS` → dentro de la transacción del
  caller sin commit/rollback. Errores `psycopg.Error` → `translate_error()` con
  `SQLSTATE`; `TypeError`/`ValueError` nunca se convierten. Limitación: REVOKE
  directo no garantiza denegación efectiva ante herencia/PUBLIC/superuser/owner
  (validación real con SET ROLE + CALL vía `PermissionProbeService`, validada E2E 03-10-2026). Sin `GRANT USAGE ON SEQUENCE`.
- `PermissionProbeService.probe(role, generation_result, arguments=())`
  (`privileges/probe.py` + `PermissionProbeStatus` ALLOWED/DENIED +
  `PermissionProbeResult` frozen + `RoleAssumptionError` que extiende
  `InsufficientPrivilegeError` con `sqlstate`/`original`): prueba UN procedure
  SUCCESS como UN rol real. `SET LOCAL ROLE` con `Identifier` + verificación
  `SELECT current_user, session_user` (mismatch → `ValueError`); `CALL`
  compuesto con `Identifier` + `Placeholder` por argumento (cero args →
  `CALL s.r()`); output vía `cursor.description`/`fetchone` preservado tal
  cual (refcursor solo conserva el nombre, sin `FETCH` todavía). `42501` en
  SET → `RoleAssumptionError` (no DENIED); `42501` en CALL → DENIED con
  `sqlstate`; `P0002`/otros → `translate_error()` preservando `SQLSTATE`.
  Aislamiento: exige conexión `IDLE` (`INTRANS` → `RuntimeError` antes de
  cualquier SQL) y todo ocurre en `with conn.transaction(force_rollback=True)`
  (vale con `autocommit=True/False`); DML del probe nunca persiste y no hay
  `commit`/`rollback` manual ni `RESET ROLE` obligatorio. Unit tests con fakes
  en `tests/test_permission_probe.py`; integración real opcional en
  `tests/test_permission_probe_integration.py` (marcada `integration`, sin
  tocar `lab.tabla_virgen`, con `pytest.skip` defensivo).
- No se tocó ningún contrato global desde Python (`CONTRACTS.md`/`DECISIONS.md` los cerró Joyce 01-10).

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar cualquier cambio en firmas, nombres, parámetros o resultados que afecte a la extensión o seguridad.

- [x] ~~JOYCE (nombre de la extensión)~~ RESUELTO 01-10: `crud_generator` confirmado (`.control` + `CONTRACTS.md` §3).
- [x] ~~JOYCE (EXECUTE sobre funciones públicas)~~ RESUELTO 01-10: firmas cerradas (CR-JOYCE-001/002); pendiente solo que Python implemente verificación fina si aplica.
- [x] ~~ARMANDO: CR-ARMANDO-001/002/003~~ RESUELTOS 03-10-2026 (E2E `armando_e2e`; ver `COORDINATION_REQUESTS.md`).
