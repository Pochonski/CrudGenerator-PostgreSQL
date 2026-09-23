# Instituto Tecnológico de Costa Rica
## Campus Tecnológico San Carlos
### Unidad de Computación — Ingeniería en Computación
**Curso:** Bases de Datos II  
**Profesor:** Msc. Leonardo Víquez Acuña  
**Evaluación:** Primer Proyecto Programado  
**Nombre del Proyecto:** Generador automático de procedimientos CRUD para PostgreSQL  
**Fecha de Inicio:** Viernes 11 de setiembre 2026, 8:00 am  
**Fecha de Entrega:** Jueves 30 de setiembre 2021, 8:00 am *(Nota: Mantiene la fecha indicada en el enunciado original)*  

---

## 1. Descripción General

El proyecto consiste en desarrollar una solución para PostgreSQL que permita autogenerar procedimientos almacenados de mantenimiento (CRUD) a partir de las tablas existentes en una base de datos.

La solución estará compuesta por dos elementos integrados:

1. **Una extensión de PostgreSQL:** Contendrá las funciones necesarias para analizar el catálogo de la base de datos y generar dinámicamente los procedimientos almacenados correspondientes a las tablas seleccionadas.
2. **Una aplicación desarrollada en Python:** Permitirá al administrador conectarse a una base de datos PostgreSQL, verificar la disponibilidad de la extensión, seleccionar los esquemas y tablas sobre los cuales desea generar los procedimientos y establecer los privilegios que tendrán diferentes usuarios sobre los procedimientos generados.

El proyecto deberá demostrar el uso de las capacidades de PostgreSQL para realizar metaprogramación sobre el catálogo del sistema, generación dinámica de SQL, administración de procedimientos y gestión de privilegios.

---

## 2. Problema

En una base de datos es frecuente que cada tabla requiera procedimientos almacenados para realizar operaciones de mantenimiento tales como:

* Insertar registros.
* Consultar registros.
* Actualizar registros.
* Eliminar registros.

La implementación manual de estos procedimientos puede generar código repetitivo y aumentar la posibilidad de inconsistencias entre tablas.

Se requiere desarrollar un mecanismo que permita automatizar la generación de estos procedimientos, utilizando la información estructural que PostgreSQL mantiene en sus catálogos.

La solución deberá ser suficientemente genérica para trabajar con diferentes tablas sin que sea necesario programar manualmente un procedimiento específico para cada una.

---

## 3. Objetivos

### Objetivo General
Desarrollar una solución integrada para PostgreSQL y Python que permita generar automáticamente procedimientos almacenados de mantenimiento CRUD a partir de la estructura de las tablas de una base de datos PostgreSQL, incluyendo la administración de los privilegios de los usuarios sobre los procedimientos generados.

### Objetivos Específicos
1. Desarrollar una extensión para PostgreSQL que permita analizar dinámicamente la estructura de esquemas y tablas mediante los catálogos del sistema y generar automáticamente procedimientos almacenados para las operaciones de mantenimiento CRUD.
2. Desarrollar una aplicación en Python que permita conectarse a una base de datos PostgreSQL, verificar la disponibilidad de la extensión y seleccionar los esquemas, tablas y operaciones CRUD que se desean generar.
3. Implementar un mecanismo de administración de privilegios que permita, desde la aplicación Python, asignar a diferentes usuarios o roles los permisos de ejecución sobre los procedimientos CRUD generados y verificar su correcto funcionamiento.

---

## 4. Alcance Funcional

### 4.1. Conexión a la base de datos
La aplicación Python deberá permitir introducir o configurar previamente los datos necesarios para establecer una conexión con PostgreSQL:
* Servidor.
* Puerto.
* Base de datos.
* Usuario.
* Contraseña.

*La aplicación deberá validar que la conexión sea exitosa antes de continuar con el proceso.*

### 4.2. Verificación de la extensión
Una vez establecida la conexión, la aplicación deberá verificar si la extensión requerida se encuentra instalada en la base de datos.

La aplicación deberá informar claramente situaciones como:
* Extensión instalada.
* Extensión no instalada.
* Extensión instalada pero no disponible para el usuario conectado.
* Error al consultar la extensión.

*No se deberá asumir que la extensión existe simplemente porque el archivo correspondiente se encuentra disponible en el equipo cliente.*

### 4.3. Selección del esquema
La aplicación deberá consultar los esquemas disponibles en la base de datos y permitir al usuario seleccionar uno de ellos.

### 4.4. Selección de tablas
Después de seleccionar el esquema, la aplicación deberá mostrar las tablas disponibles y permitir seleccionar cuáles serán procesadas. Como mínimo deberá ser posible:
* Seleccionar una tabla.
* Seleccionar varias tablas.
* Seleccionar todas las tablas disponibles.

La aplicación deberá identificar las características estructurales necesarias para generar los procedimientos.

### 4.5. Generación de procedimientos CRUD
La extensión deberá proporcionar funciones que permitan generar procedimientos almacenados a partir de una tabla determinada. Como mínimo deberán contemplarse las operaciones:

* **CREATE:** Procedimiento para insertar un nuevo registro. *(Ejemplo conceptual: `sp_cliente_insertar(...)`)*.
* **READ:** Procedimiento para consultar registros. La implementación deberá permitir recuperar información de la tabla de acuerdo con los criterios definidos por el equipo.
* **UPDATE:** Procedimiento para modificar un registro existente. La identificación del registro deberá realizarse utilizando la clave primaria cuando la tabla disponga de ella.
* **DELETE:** Procedimiento para eliminar un registro existente. La identificación del registro deberá realizarse utilizando la clave primaria cuando la tabla disponga de ella.

### 4.6. Análisis automático de la estructura
La extensión deberá obtener la información estructural directamente de los catálogos de PostgreSQL. Como mínimo deberá analizar:
* Esquema.
* Nombre de la tabla.
* Nombre de las columnas.
* Tipo de datos.
* Orden de las columnas.
* Claves primarias.
* Columnas con valores generados automáticamente.
* Valores predeterminados.
* Posiblemente restricciones relevantes para las operaciones CRUD.

### 4.7. Generación dinámica de SQL
La extensión deberá utilizar las capacidades de PostgreSQL para generar dinámicamente las sentencias SQL necesarias. El estudiante deberá considerar correctamente aspectos como:
* Identificación segura de esquemas.
* Identificación segura de tablas.
* Identificación segura de columnas.
* Uso apropiado de identificadores entrecomillados cuando corresponda.
* Tipos de datos.
* Parámetros de los procedimientos.
* Manejo de nombres reservados.
* Existencia previa de procedimientos.

*No se permitirá resolver el problema mediante una colección de procedimientos previamente escritos para un conjunto fijo de tablas.*

### 4.8. Manejo de claves primarias
La generación deberá identificar automáticamente las columnas que conforman la clave primaria. El diseño deberá contemplar tanto:
* Claves primarias simples.
* Claves primarias compuestas.

En el caso de una clave primaria compuesta, el procedimiento generado deberá utilizar todos los atributos que conforman dicha clave.

### 4.9. Manejo de columnas autogeneradas
La solución deberá reconocer columnas cuyo valor es generado automáticamente por PostgreSQL, por ejemplo mediante:
* Secuencias asociadas.
* Valores `DEFAULT`.
* Otros mecanismos que el equipo considere pertinentes.

*Estas columnas deberán ser tratadas adecuadamente durante la generación del procedimiento `INSERT`.*

### 4.10. Administración de privilegios
La aplicación Python deberá permitir seleccionar usuarios o roles de PostgreSQL y definir qué operaciones podrán ejecutar sobre los procedimientos generados.

Como mínimo deberá contemplarse:
* Ejecución del procedimiento de insertar.
* Ejecución del procedimiento de consultar.
* Ejecución del procedimiento de actualizar.
* Ejecución del procedimiento de eliminar.

**Ejemplo conceptual de procedimiento y matriz:**

Para una tabla `cliente` podrían existir los procedimientos:
* `cliente_insertar`
* `cliente_consultar`
* `cliente_actualizar`
* `cliente_eliminar`

Matriz de privilegios a configurar:

| Usuario / Rol | Insertar | Consultar | Actualizar | Eliminar |
| :--- | :---: | :---: | :---: | :---: |
| **vendedor** | ✓ | ✓ | X | X |
| **supervisor** | ✓ | ✓ | ✓ | X |
| **administrador** | ✓ | ✓ | ✓ | ✓ |

La aplicación deberá traducir esta configuración a los mecanismos de autorización de PostgreSQL (`GRANT` y `REVOKE`).

---

## 5. Consideraciones de Seguridad

El proyecto deberá prestar especial atención a la seguridad. Los estudiantes deberán considerar, entre otros aspectos:
* Privilegios necesarios para crear procedimientos.
* Privilegios necesarios para modificar objetos.
* Propietario de los procedimientos.
* Modos de ejecución: `SECURITY INVOKER` vs `SECURITY DEFINER`.
* Uso apropiado de `GRANT` y `REVOKE`.

*La aplicación no deberá construir SQL concatenando directamente valores proporcionados por el usuario cuando exista un mecanismo seguro para parametrizarlos o identificar correctamente los objetos.*

---

## 6. Flujo de Trabajo de la Aplicación Python

La aplicación deberá proporcionar una interfaz (gráfica o de línea de comandos) que permita realizar, como mínimo, el siguiente flujo ordenado:

1. Conectar a PostgreSQL
2. Verificar conexión
3. Verificar extensión
4. Seleccionar esquema
5. Seleccionar tablas
6. Analizar estructura
7. Seleccionar operaciones CRUD
8. Generar procedimientos
9. Seleccionar usuarios/roles
10. Asignar privilegios
11. Aplicar configuración
12. Mostrar resultado

---

## 7. Requisitos Técnicos Mínimos

### Extensión PostgreSQL
La solución deberá:
* Ser instalable como una extensión de PostgreSQL.
* Contener el archivo `.control` correspondiente.
* Contener los objetos SQL necesarios.
* Implementar las funciones requeridas para analizar las tablas.
* Generar dinámicamente los procedimientos CRUD.
* Utilizar información obtenida de los catálogos de PostgreSQL.

### Aplicación Python
La aplicación deberá:
* Utilizar una biblioteca de conexión a PostgreSQL.
* Establecer conexiones correctamente.
* Detectar la existencia de la extensión.
* Consultar esquemas y tablas.
* Permitir seleccionar objetos.
* Solicitar o utilizar los parámetros de generación.
* Configurar privilegios.
* Reportar errores y resultados.

---

## 8. Restricciones

1. Los procedimientos CRUD deberán ser generados dinámicamente.
2. No se permitirá crear procedimientos específicos para cada tabla y presentarlos como solución general.
3. La solución deberá funcionar con tablas diferentes a las utilizadas durante el desarrollo.
4. La aplicación Python no deberá contener la lógica específica de generación de cada tabla.
5. La lógica relacionada con la estructura de la base de datos deberá residir, principalmente, en la extensión PostgreSQL.
6. Los nombres de esquemas, tablas y columnas no deberán considerarse valores fijos dentro del código.
7. La solución deberá manejar adecuadamente errores derivados de tablas sin clave primaria, tablas con claves compuestas, columnas autogeneradas y objetos previamente existentes.

---

## 9. Pruebas Obligatorias

Cada equipo deberá realizar pruebas utilizando al menos tres estructuras de tablas diferentes, incluyendo obligatoriamente:

* **Caso 1 - Clave primaria simple:** Una tabla cuya clave primaria esté constituida por una sola columna.
* **Caso 2 - Clave primaria compuesta:** Una tabla cuya clave primaria esté constituida por dos o más columnas.
* **Caso 3 - Generación automática de valores:** Una tabla que contenga al menos una columna cuyo valor sea generado automáticamente.

*Adicionalmente deberá realizarse una prueba de privilegios utilizando al menos tres roles con diferentes niveles de acceso.*

---

## 10. Entregables

### Entregable 1: Extensión PostgreSQL
Deberá incluir:
* Archivo `.control`.
* Scripts SQL.
* Código fuente utilizado para implementar las funciones.

### Entregable 2: Aplicación Python
Deberá incluir:
* Código fuente.
* Documentación de uso.

### Entregable 3: Evidencia de funcionamiento (Vídeo)
Deberá demostrarse mediante un vídeo corto:
1. Instalación de la extensión.
2. Conexión mediante Python.
3. Detección de la extensión.
4. Selección del esquema.
5. Selección de tablas.
6. Generación de procedimientos.
7. Ejecución de los procedimientos.
8. Asignación de privilegios.
9. Validación de los privilegios utilizando diferentes usuarios.
10. Funcionamiento sobre tablas no utilizadas durante el desarrollo.

---

## 11. Demostración en Vivo

Cada equipo deberá realizar una demostración en la cual se partirá de una base de datos que contenga tablas previamente definidas. El equipo deberá demostrar que, utilizando únicamente la aplicación Python, es posible:

1. Conectarse a la base de datos.
2. Detectar la extensión.
3. Seleccionar un esquema.
4. Seleccionar tablas.
5. Generar los procedimientos CRUD.
6. Mostrar los procedimientos creados.
7. Seleccionar usuarios o roles.
8. Asignar diferentes privilegios.
9. Comprobar que los privilegios funcionan correctamente.
10. Realizar operaciones utilizando los procedimientos generados.

*El docente podrá utilizar tablas adicionales no proporcionadas previamente a los estudiantes para comprobar que la solución realmente es genérica.*