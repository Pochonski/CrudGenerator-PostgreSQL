# Joyce — Implementation Handoff

## Propósito

Guía de integración entre la extensión PostgreSQL de Joyce y Seguridad/Integración (Joseph) y Python/Interfaz (Armando).

La meta es que la implementación de Joyce pueda conectarse con el trabajo existente sin obligar a las otras áreas a adivinar nombres, firmas, permisos o comportamiento.

**Fuentes relacionadas:** CONTRACTS.md, DECISIONS.md, COORDINATION_REQUESTS.md, SECURITY_MEMORY.md y tests/security/10_generated_routine_discovery.sql.

## 1. Entrega esperada

La extensión debe permitir conceptualmente:

1. Analizar una tabla existente.
2. Obtener metadata estructural suficiente para decidir qué CRUD aplica.
3. Generar los procedures CRUD correspondientes.
4. Devolver resultados estructurados que Python pueda interpretar.
5. Mantener las propiedades de seguridad acordadas.

La generación SQL CRUD pertenece a PostgreSQL. Python no debe reconstruir los procedures.

## 2. Naming adoptado

La convención adoptada en ADR-007 / enunciado §4.10 es:

~~~text
<tabla>_insertar
<tabla>_consultar
<tabla>_actualizar
<tabla>_eliminar
~~~

Ejemplo:

~~~text
lab.producto_insertar
lab.producto_consultar
lab.producto_actualizar
lab.producto_eliminar
~~~

El naming está adoptado, pero tipos, orden de parámetros, retorno y esquema destino deben quedar documentados por Joyce antes de que Python dependa de ellos.

## 3. Contrato mínimo por routine

| Campo | Requerido |
|---|---|
| nombre completo | Sí |
| schema | Sí |
| nombre | Sí |
| tipo de objeto | Sí, procedure |
| identity arguments | Sí |
| parámetros y orden | Sí |
| tipos de parámetros | Sí |
| OUT/INOUT, si existen | Sí |
| retorno/resultado | Sí |
| fila inexistente | Sí |
| SQLSTATE propio, si aplica | Sí |
| owner | Sí |
| SECURITY INVOKER/DEFINER | Sí |
| search_path | Sí |
| política sin PK | Sí |
| política de conflicto | Sí |

La firma debe poder obtenerse sin ambigüedad mediante pg_get_function_identity_arguments(p.oid) y p.oid::regprocedure.

## 4. Seguridad de procedures generados

La recomendación de Seguridad es SECURITY INVOKER, salvo decisión posterior del equipo.

Cada procedure generado debería usar:

~~~sql
SECURITY INVOKER
SET search_path = <schema_destino>, pg_temp
~~~

Dentro del cuerpo:

- usar nombres de tabla/esquema calificados;
- no depender del search_path de la sesión;
- no utilizar SQL dinámico inseguro;
- si existe SQL dinámico, usar quoting seguro de identificadores (%I o equivalente) y parámetros mediante USING;
- no otorgar EXECUTE a PUBLIC por defecto.

## 5. Owner

La propuesta de Seguridad es un rol administrador/owner dedicado:

~~~text
crud_admin
~~~

No se debe depender del usuario personal que ejecute la generación. Si Joyce necesita otro nombre, debe documentarlo antes de conectar las auditorías T3/T4.

## 6. INSERT, DEFAULT e identity

No asumir que todas las columnas reciben parámetros de INSERT.

La generación debe analizar DEFAULT, GENERATED, IDENTITY, columnas obligatorias, PK simple y PK compuesta.

En particular, definir explícitamente cómo se manejan las columnas autogeneradas y si se omiten o aceptan valores explícitos.

## 7. PK simple y compuesta

Con PK simple:

~~~text
WHERE pk = parámetro
~~~

Con PK compuesta:

~~~text
WHERE pk_1 = parámetro_1
  AND pk_2 = parámetro_2
  ...
~~~

Nunca asumir que existe una única columna PK. T1 ya prueba PK compuesta.

## 8. READ

ADR-015 propone consultar por PK completa y devolver una fila mediante INOUT.

La fila inexistente usa actualmente P0002 en los fixtures.

Joyce debe confirmar la firma final, tipos, orden de parámetros y SQLSTATE antes de congelar el contrato.

## 9. Tabla sin PK

No inventar una PK.

La propuesta actual es:

- generar las operaciones aplicables;
- reportar las no aplicables estructuradamente;
- no usar ctid como sustituto de PK para UPDATE/DELETE;
- permitir que Python distinga not_applicable de un error real.

La decisión final debe quedar en CONTRACTS.md y DECISIONS.md.

## 10. Procedures existentes

Debe existir una política explícita para conflictos.

Propuesta:

~~~text
error explícito → conflicto con procedure existente
~~~

No hacer DROP+CREATE silencioso durante una ejecución normal.

## 11. Resultado de generate_crud

Python necesita distinguir como mínimo:

~~~text
success
not_applicable
validation_error
object_not_found
procedure_conflict
permission_denied
internal_error
~~~

El formato puede ser record/composite/JSON/etc., pero debe ser estable y documentado.

Idealmente cada operación devuelve:

~~~text
operation
status
schema
routine_name
identity_arguments
message
sqlstate
~~~

## 12. Discovery y auditoría

Se incorporó:

~~~text
tests/security/10_generated_routine_discovery.sql
~~~

Descubre procedures reales desde pg_proc y reporta schema, nombre, firma, owner, SECURITY INVOKER/DEFINER, search_path, argumentos, retorno y PUBLIC EXECUTE.

Es deliberadamente independiente de las firmas de los fixtures.

Cuando Joyce tenga una implementación funcional, el siguiente paso será ejecutar este discovery sobre las routines reales y conectar T3/T4/T5/T6 con ellas.

## 13. Checklist de entrega

### Extensión

- [ ] .control definido.
- [ ] Instalación limpia.
- [ ] API pública documentada.
- [ ] Análisis de metadata.
- [ ] INSERT.
- [ ] READ.
- [ ] UPDATE.
- [ ] DELETE.
- [ ] PK compuesta.
- [ ] DEFAULT/identity.
- [ ] Tabla sin PK con política explícita.
- [ ] Conflicto de procedure con política explícita.

### Seguridad

- [ ] Owner documentado.
- [ ] SECURITY INVOKER/DEFINER documentado.
- [ ] search_path documentado.
- [ ] Referencias calificadas.
- [ ] SQL dinámico seguro, si existe.
- [ ] PUBLIC EXECUTE revisado.
- [ ] Sin privilegios excesivos concedidos automáticamente.

### Integración

- [ ] Nombres reales documentados.
- [ ] Firmas reales documentadas.
- [ ] Resultados/errores documentados.
- [ ] SQLSTATE documentados cuando formen parte del contrato.
- [ ] Discovery 10 ejecutado sobre routines reales.
- [ ] T3/T4/T5/T6 adaptados a routines reales.
- [ ] Python consume la API sin generar SQL CRUD por su cuenta.

## 14. Regla para cerrar contratos

Cuando Joyce cierre una decisión que afecte a Python o Seguridad:

1. actualizar CONTRACTS.md;
2. registrar la decisión en DECISIONS.md;
3. actualizar EXTENSION_MEMORY.md;
4. indicar las firmas reales de las APIs públicas;
5. indicar qué pruebas existentes pasan a ser aplicables.

Una implementación experimental no debe tratarse como contrato final hasta quedar documentada.
