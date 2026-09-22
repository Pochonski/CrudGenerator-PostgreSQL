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

- [ ] Arquitectura de módulos
- [ ] Biblioteca PostgreSQL confirmada
- [ ] Conexión
- [ ] Detección de extensión
- [ ] Esquemas
- [ ] Tablas
- [ ] Selección de tablas
- [ ] Análisis de tabla
- [ ] Selección CRUD
- [ ] Generación
- [ ] Roles
- [ ] Privilegios
- [ ] Manejo de errores
- [ ] Integración completa
- [ ] Prueba con tabla nueva

## Decisiones locales

Registrar aquí decisiones que no afecten los contratos globales.

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar cualquier cambio en firmas, nombres, parámetros o resultados que afecte a la extensión o seguridad.
