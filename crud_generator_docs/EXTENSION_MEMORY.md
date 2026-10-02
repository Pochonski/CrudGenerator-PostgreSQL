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
- [ ] Catálogos definidos (implementación pendiente)
- [ ] `.control`
- [ ] Análisis de tablas
- [ ] INSERT
- [ ] READ
- [ ] UPDATE
- [ ] DELETE
- [ ] PK compuesta
- [ ] Autogenerados/identity/default
- [ ] Tabla sin PK
- [ ] Conflicto de procedimientos
- [ ] Pruebas aisladas
- [ ] Integración con Python

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

- Ninguno registrado todavía.

## Requiere coordinación

- Ninguna pendiente por ahora. Cuando la implementación arroje firmas reales
  (tipos exactos vistos por PostgreSQL), se documentarán aquí y en
  `CONTRACTS.md` siguiendo la regla de `JOYCE_IMPLEMENTATION_HANDOFF.md` §14.
