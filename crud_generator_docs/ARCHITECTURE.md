# Arquitectura — Generador CRUD PostgreSQL

## 1. Vista general

```text
                    ┌─────────────────────┐
                    │    Aplicación       │
                    │       Python        │
                    │ UI + Orquestación   │
                    └──────────┬──────────┘
                               │
                            psycopg
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  Extensión    │  │
                    │  │ crud_generator│  │
                    │  └───────┬───────┘  │
                    │          │          │
                    │          ▼          │
                    │   Catálogos del DB  │
                    │          │          │
                    │          ▼          │
                    │ Procedimientos CRUD │
                    │          │          │
                    │          ▼          │
                    │ Roles / Privilegios│
                    └─────────────────────┘
```

## 2. Equipo y ownership

| Integrante | Área dueña | Límites principales |
|---|---|---|
| **Joyce** | Extensión PostgreSQL | Catálogos, metadata, generación dinámica y API de la extensión. |
| **Armando** | Python + Interfaz | Conexión, UI/CLI, orquestación y consumo de la API. |
| **Joseph** | Seguridad + Integración + Pruebas | Roles, privilegios, validación de seguridad, contratos, pruebas E2E y demostración. |

El ownership indica quién lidera una parte. No autoriza cambios unilaterales en contratos o decisiones globales.

## 3. Responsabilidades

### Extensión PostgreSQL

Responsable de descubrir metadatos y generar dinámicamente procedimientos.

No depende de Python para conocer la estructura de una tabla.

### Python

Responsable de interacción con el administrador y orquestación.

No genera internamente el CRUD de tablas concretas.

### Seguridad / Integración / Pruebas

Responsable de validar permisos, analizar decisiones de seguridad, comprobar contratos y ejecutar pruebas integrales.

## 4. Capas conceptuales de Python

```text
UI / CLI
   ↓
Application Controller
   ↓
PostgreSQL Service
   ↓
Database Connection
```

La lógica de UI no debe contener SQL complejo ni reglas de generación.

## 5. Capas conceptuales de la extensión

```text
API pública
   ↓
Validación de objetos
   ↓
Lectura de metadatos
   ↓
Modelo interno de tabla
   ↓
Generador SQL
   ↓
Creación/actualización de procedimientos
   ↓
Resultado estructurado
```

## 6. Modelo conceptual de metadatos

La extensión debe representar, como mínimo, información equivalente a:

```text
TableMetadata
- schema_name
- table_name
- columns[]
- primary_key_columns[]

ColumnMetadata
- column_name
- data_type
- ordinal_position
- is_primary_key
- has_default
- default_expression
- is_generated
- generated_expression (si aplica)
- identity information (si aplica)
```

La estructura exacta podrá cambiar, pero debe soportar PK compuesta y columnas autogeneradas desde el diseño.

## 8. Flujo de generación

```text
schema + table + operations
          ↓
  validar existencia
          ↓
 leer metadatos
          ↓
 identificar PK/default/generated
          ↓
 construir definición de cada procedure
          ↓
 ejecutar SQL dinámico seguro
          ↓
 devolver resultado
```

## 9. Seguridad de objetos

Esquema, tabla, columna y nombre de procedimiento son identificadores, no valores ordinarios.

El diseño debe usar mecanismos apropiados para identificar/quotear objetos y parametrizar valores cuando corresponda.

## 10. No objetivos

No forman parte del núcleo inicial:

- ORM.
- Migraciones generales de base de datos.
- Soporte universal de todos los lenguajes de procedimientos.
- Un constructor visual complejo.
- Generación de SQL CRUD dentro de Python.

Cualquier funcionalidad adicional debe evaluarse contra el tiempo y los requisitos del enunciado.
