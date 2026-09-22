# Contratos de Integración

Este documento es la fuente de verdad para las interfaces entre los componentes. Un agente no debe cambiar un contrato sin actualizar este archivo y registrar la decisión.

## 1. Responsables de los contratos

- **Joyce:** contrato y API de la extensión PostgreSQL.
- **Armando:** consumo de la API desde Python y flujo de aplicación.
- **Joseph:** contratos de seguridad, integración y validación.

Ningún integrante debe cambiar unilateralmente una interfaz que consuma otro componente.

## 2. Contrato Python ↔ PostgreSQL

Python debe ser capaz de:

1. Abrir conexión.
2. Consultar disponibilidad de la extensión.
3. Consultar esquemas.
4. Consultar tablas de un esquema.
5. Solicitar análisis de una tabla.
6. Solicitar generación de una o varias operaciones CRUD.
7. Consultar roles/usuarios.
8. Aplicar o solicitar la aplicación de privilegios.
9. Mostrar errores y resultados.

## 3. API pública de la extensión — propuesta inicial

> Esta sección es una propuesta de diseño. Debe cerrarse antes de que Python dependa de ella.

### 3.1 Analizar tabla

Conceptualmente:

```text
analyze_table(schema_name, table_name)
```

Debe entregar información suficiente para que Python pueda mostrar al administrador las características relevantes de la tabla.

Debe contemplar:

- esquema
- tabla
- columnas
- tipos
- orden
- PK
- PK compuesta
- DEFAULT
- generated/identity cuando aplique

### 3.2 Generar CRUD

Conceptualmente:

```text
generate_crud(schema_name, table_name, operations)
```

Donde `operations` representa la selección de operaciones, por ejemplo INSERT/READ/UPDATE/DELETE.

La firma definitiva y los tipos exactos deben documentarse antes de congelar la integración.

### 3.3 Resultado

El resultado debe permitir que Python distinga como mínimo entre:

- éxito
- operación no aplicable
- error de validación
- objeto inexistente
- conflicto con procedimiento existente
- permiso insuficiente
- error interno de PostgreSQL

El formato definitivo queda pendiente de decisión.

## 4. Contrato para READ

**Decisión pendiente y crítica.**

Debe definirse:

- firma del procedure de consulta
- criterio de consulta
- qué sucede con tablas con PK
- qué sucede con tablas sin PK
- cómo devuelve los registros

La solución debe seguir siendo genérica.

## 5. Contrato de errores

No ocultar errores de PostgreSQL.

Python debe mostrar mensajes comprensibles, conservando una distinción entre:

- error de conexión
- error de extensión
- error de objeto
- error de permisos
- error de generación
- error inesperado

## 6. Contrato de privilegios

Python debe poder expresar una matriz lógica equivalente a:

```text
role → operation → allowed/denied
```

PostgreSQL es la autoridad real sobre los permisos.

Python no debe simular permisos únicamente en memoria.

## 7. Regla de cambios

Una modificación de contrato requiere:

- actualizar este documento
- registrar una entrada en `DECISIONS.md`
- actualizar memoria del agente correspondiente
- advertir al resto del equipo

## 8. Revisión de integración

Antes de considerar integrado el proyecto, deben probarse al menos:

```text
Python → detectar extensión
Python → analizar tabla
Python → generar INSERT
Python → generar READ
Python → generar UPDATE
Python → generar DELETE
Python → configurar privilegios
PostgreSQL → negar acceso no autorizado
```
