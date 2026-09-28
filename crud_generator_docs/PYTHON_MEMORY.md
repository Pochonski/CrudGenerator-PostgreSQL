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
- [ ] Detección de extensión
- [ ] Esquemas
- [ ] Tablas
- [ ] Selección de tablas
- [ ] Análisis de tabla
- [ ] Selección CRUD
- [ ] Generación
- [ ] Roles
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
- No se tocó ningún contrato global (`CONTRACTS.md`/`DECISIONS.md` sin cambios).

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar cualquier cambio en firmas, nombres, parámetros o resultados que afecte a la extensión o seguridad.
