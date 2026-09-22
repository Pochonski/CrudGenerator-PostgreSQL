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

- [ ] Arquitectura interna definida
- [ ] API pública definida
- [ ] Catálogos definidos
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

Registrar aquí decisiones que no cambien contratos globales.

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar aquí cualquier cambio que afecte a Python o seguridad.
