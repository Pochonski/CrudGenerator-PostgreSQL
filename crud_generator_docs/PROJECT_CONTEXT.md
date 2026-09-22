# Proyecto — Generador Automático de Procedimientos CRUD para PostgreSQL

## 1. Identificación

- Institución: Instituto Tecnológico de Costa Rica — Campus Tecnológico San Carlos
- Unidad: Unidad de Computación
- Carrera: Ingeniería en Computación
- Curso: Bases de Datos II
- Proyecto: Primer Proyecto
- Tema: Generador automático de procedimientos CRUD para PostgreSQL
- Inicio indicado en el enunciado: viernes 11 de setiembre de 2026, 8:00 a. m.
- Fecha de entrega indicada en el enunciado: jueves 30 de setiembre de 2021, 8:00 a. m.
- **Nota:** la fecha de entrega presenta una inconsistencia de año en el enunciado y debe confirmarse con el docente. El equipo no debe asumir 2021 ni 2026 sin confirmación.

## 2. Objetivo del proyecto

Construir una solución integrada que permita analizar tablas existentes en PostgreSQL y generar automáticamente procedimientos almacenados CRUD, junto con una aplicación Python para administrar el proceso y configurar privilegios de ejecución para distintos usuarios/roles.

La solución debe demostrar metaprogramación sobre los catálogos de PostgreSQL, generación dinámica de SQL, creación/administración de procedimientos y gestión de privilegios.

## 3. Arquitectura acordada

La solución se divide en tres áreas:

1. **Extensión PostgreSQL**
   - Analiza los catálogos de PostgreSQL.
   - Descubre estructura de tablas.
   - Detecta PK simples y compuestas.
   - Detecta columnas con DEFAULT y mecanismos de generación automática.
   - Genera dinámicamente los procedimientos CRUD.

2. **Aplicación Python**
   - Es la interfaz/orquestador.
   - Se conecta a PostgreSQL.
   - Verifica conexión y disponibilidad de la extensión.
   - Permite seleccionar esquema, tablas y operaciones.
   - Solicita la generación a la extensión.
   - Permite seleccionar roles y configurar privilegios.
   - Reporta resultados y errores.

3. **Seguridad, integración y pruebas**
   - Diseña/valida GRANT, REVOKE y EXECUTE.
   - Analiza SECURITY INVOKER/DEFINER.
   - Valida propietarios y permisos.
   - Diseña las pruebas integrales.
   - Coordina los contratos entre componentes.
   - Prepara la demostración final.

## 4. Equipo y responsables

El proyecto será desarrollado por tres integrantes. Cada área tiene un responsable principal, pero las decisiones que afecten la integración son decisiones de equipo.

| Integrante | Rol principal | Responsabilidad |
|---|---|---|
| **Joseph** | Seguridad + Integración + Pruebas | Seguridad PostgreSQL, roles, GRANT/REVOKE, EXECUTE, análisis SECURITY INVOKER/DEFINER, integración, pruebas y demostración final. |
| **Joyce** | Extensión PostgreSQL | Extensión instalable, catálogos, análisis estructural, PK simples/compuestas, valores autogenerados y generación dinámica de procedimientos CRUD. |
| **Armando** | Python + Interfaz | Conexión, detección de extensión, selección de esquemas/tablas/operaciones, orquestación y configuración de privilegios desde Python. |

**Regla del equipo:** ser responsable principal de un área no significa trabajar de forma aislada. Cualquier cambio que afecte contratos, arquitectura, seguridad o comportamiento compartido debe quedar documentado y coordinarse con los otros integrantes.

## 5. Principio arquitectónico fundamental

**Python NO contiene la lógica específica de generación CRUD.**

Python solicita operaciones a PostgreSQL.
La extensión PostgreSQL analiza la estructura real de las tablas y genera los procedimientos.

No se permitirá una implementación basada en una lista fija de tablas o procedimientos escritos manualmente para tablas concretas.

## 6. Flujo principal

```text
Conectar a PostgreSQL
        ↓
Verificar conexión
        ↓
Verificar extensión
        ↓
Seleccionar esquema
        ↓
Seleccionar tablas
        ↓
Analizar estructura
        ↓
Seleccionar operaciones CRUD
        ↓
Solicitar generación
        ↓
Verificar procedimientos/resultados
        ↓
Seleccionar usuarios/roles
        ↓
Configurar privilegios
        ↓
Aplicar GRANT/REVOKE
        ↓
Validar permisos
        ↓
Mostrar resultado
```

## 7. Casos obligatorios de prueba

El sistema debe probar como mínimo:

- Tabla con clave primaria simple.
- Tabla con clave primaria compuesta.
- Tabla con columna cuyo valor es generado automáticamente.
- Al menos tres roles con diferentes niveles de acceso.
- Una tabla no utilizada previamente durante el desarrollo.

También se deben considerar tablas sin PK, DEFAULT, procedimientos previamente existentes, nombres especiales y diferentes tipos de datos.

## 8. Decisiones globales iniciales

Estas decisiones son de equipo y no deben ser cambiadas unilateralmente por un agente.

- La lógica de metadatos y generación CRUD vive principalmente en la extensión PostgreSQL.
- Python funciona como cliente/orquestador.
- Se partirá de `CREATE PROCEDURE`, porque el enunciado solicita procedimientos almacenados.
- La extensión será una extensión instalable de PostgreSQL, con archivo `.control` y scripts/objetos requeridos.
- Se priorizará PL/pgSQL como tecnología inicial para la lógica de la extensión, salvo que el docente o una restricción técnica obligue a usar otro lenguaje.
- La aplicación Python usará una biblioteca moderna y estable de PostgreSQL; la propuesta inicial es `psycopg`.
- La interfaz inicial priorizará simplicidad y demostrabilidad; la propuesta inicial es CLI, salvo que el equipo decida justificar una GUI.
- Los nombres de procedimientos seguirán una convención consistente de tipo `<tabla>_<operacion>`, pendiente de formalizar definitivamente en `DECISIONS.md`.
- UPDATE y DELETE utilizarán la clave primaria cuando exista.
- Las PK compuestas se tratarán como un conjunto de columnas, no como una única columna.
- No se inventará una PK para tablas que no la tengan.
- Las decisiones sobre SECURITY DEFINER/INVOKER y comportamiento exacto de tablas sin PK deben justificarse antes de cerrarse.

## 9. Restricciones clave del enunciado

- No crear CRUD manuales para un conjunto fijo de tablas y presentarlos como solución genérica.
- Los nombres de esquema, tabla y columna no pueden estar hardcodeados.
- La extensión debe utilizar información de los catálogos del sistema.
- Deben manejarse PK simples y compuestas.
- Deben considerarse columnas autogeneradas y valores DEFAULT.
- Deben manejarse procedimientos previamente existentes.
- Deben cuidarse identificadores, quoting y SQL dinámico seguro.
- La aplicación debe poder trabajar sobre tablas nuevas no utilizadas durante el desarrollo.

## 9. Regla de colaboración entre agentes

No optimizar una parte de forma aislada cuando la decisión afecta otro componente.

Toda modificación que cambie una API, contrato, nombre, formato de datos o comportamiento observable debe:

1. Registrarse en `DECISIONS.md` si es una decisión global.
2. Registrarse en `CONTRACTS.md` si modifica una interfaz.
3. Registrarse en el archivo de memoria del agente correspondiente.
4. Marcarse como `REQUIERE COORDINACIÓN` cuando afecte a otro agente.

## 10. Documentos canónicos

- `PROJECT_CONTEXT.md`: contexto y reglas generales.
- `ARCHITECTURE.md`: arquitectura técnica y responsabilidades.
- `CONTRACTS.md`: interfaces entre componentes.
- `DECISIONS.md`: decisiones de arquitectura y convenciones.
- `EXTENSION_MEMORY.md`: memoria técnica del agente de extensión.
- `PYTHON_MEMORY.md`: memoria técnica del agente Python.
- `SECURITY_MEMORY.md`: memoria técnica del agente de seguridad/integración/pruebas.
- `INTEGRATION_STATUS.md`: estado general de integración, riesgos y pendientes.
