# Guion de Joseph — del Paso 9 al cierre (Terminal A + Terminal B)

**Ámbito:** Paso 9 (5:40–7:00) → casos especiales (7:00–8:10) → Paso 10 (8:10–9:40)
→ probar tabla nueva (9:40–10:10) → cierre (10:10–10:40).
**Máquina:** Windows + PostgreSQL 18 local (sin Docker: no usar `docker exec`;
`psql` directo contra `127.0.0.1:5432`, base `devdb`).
**Estado previo verificado:** fila 101 presente, matriz aplicada, 4 routines de
producto, sin restos de `tabla_video_nueva`.

---

## 0. Antes de grabar (fuera de cámara)

- Cerrar notificaciones. PowerShell con letra grande (`Ctrl` + rueda).
- Grabación con `Win + G` (Xbox Game Bar).
- La clave (`postgres`) se escribe a ciegas en el prompt de `psql`: nunca en
  una variable visible ni en texto.
- Si algo sale distinto a lo esperado: detener, avisar, regrabar el bloque
  (no improvisar).

---

## 5:40–7:00 · Paso 9 — Validación de seguridad con diferentes roles

En Terminal B (PowerShell). Primero conectarse (`psql` no está en el PATH por
defecto; la primera línea lo habilita solo en esa ventana). La clave se escribe
a ciegas y no se muestra:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
psql -h 127.0.0.1 -U postgres -d devdb
```

Probar primero el vendedor:

```sql
SET ROLE crud_vendedor;
CALL lab.producto_consultar(101, NULL, NULL);
CALL lab.producto_actualizar(101, 'Teclado Gamer', 30.00);
RESET ROLE;
```

Lo que se dice: “El vendedor tiene READ, por lo que la consulta está permitida.
Sin embargo, UPDATE fue revocado; PostgreSQL rechaza realmente esa operación y
devuelve un error de privilegios.”

Luego el supervisor:

```sql
SET ROLE crud_supervisor;
CALL lab.producto_actualizar(101, 'Teclado Gamer', 30.00);
CALL lab.producto_consultar(101, NULL, NULL);
CALL lab.producto_eliminar(101);
RESET ROLE;
```

Lo que se dice: “El supervisor sí posee UPDATE, por lo que exactamente la misma
actualización funciona. Sin embargo, DELETE continúa prohibido para este rol.”

Finalmente el administrador:

```sql
SET ROLE crud_administrador;
CALL lab.producto_eliminar(101);
CALL lab.producto_consultar(101, NULL, NULL);
RESET ROLE;
```

Lo que se dice: “Finalmente, el administrador sí puede eliminar. La consulta
posterior confirma que el registro ya no existe.”

Nota: después del DELETE, el READ por PK produce el error de fila no encontrada
P0002. Los errores de permisos corresponden a 42501. Al terminar este bloque la
fila 101 queda eliminada y la base limpia.

---

## 7:00–8:10 · Casos especiales — PK compuesta e IDENTITY/DEFAULT

Salir de psql con `\q`. En Terminal A (PowerShell) ejecutar `crudgen` (el
comando ya está instalado). Es interactivo: escribís lo indicado y el programa
responde; si algo sale mal, vuelve a preguntar. Comandos exactos, en orden:

```powershell
crudgen
```

```text
Servidor [localhost]: 127.0.0.1
Puerto [5432]:
Base de datos: devdb
Usuario: postgres
Contraseña: (escribirla a ciegas, no se muestra)
Esquema [número]: 2
Tablas: 3,6
Operaciones: a
Reemplazar: s
Roles: 2
Permitir INSERT? [s/n]: s
Permitir READ? [s/n]: s
Permitir UPDATE? [s/n]: s
Permitir DELETE? [s/n]: s
Permitir INSERT? [s/n]: s
Permitir READ? [s/n]: s
Permitir UPDATE? [s/n]: s
Permitir DELETE? [s/n]: s
Verificar: s
Ejecutar: n
```

Detalle de respuestas:

```text
Esquema: 2 (lab; el listado muestra crud_generator=1, lab=2, public=3)
Tablas: 3,6 (detalle_factura y ticket; bitacora=1, catalogo_especial=2,
  producto=4, tabla_virgen=5)
Operaciones: a (las cuatro)
Reemplazar: s
```

Nota: se responde `s` en Reemplazar porque este laboratorio ya tiene las
rutinas generadas (en una base limpia del video general sería `n`).

```text
Roles: 2 (únicamente crud_administrador; el listado muestra
  crud_admin=1, crud_administrador=2, crud_supervisor=3, crud_vendedor=4,
  postgres=5)
Matriz: s 8 veces (4 operaciones de detalle_factura + 4 de ticket)
```

Ante lo nuevo responder:

```text
Verificar: s (muestra los OK en cámara)
Ejecutar: n
```

Lo que se dice: “La generación no está limitada a claves primarias simples. En
detalle_factura la extensión detecta automáticamente una clave primaria
compuesta por id_factura e id_producto.”

Lo que se dice: “También detectamos columnas generadas automáticamente y valores
DEFAULT. Por ejemplo, id_ticket utiliza IDENTITY y no debe ser tratado como un
parámetro obligatorio de INSERT.”

Nota: la pantalla de metadata muestra tipos reales (`numeric(10,2)`),
`identity ALWAYS` y PK por columna; los resultados salen como `success` con su
línea `rutina:`.

---

## 8:10–9:40 · Paso 10 — Tabla creada después del desarrollo

En Terminal B (`psql`, misma conexión) crear la tabla nueva:

```sql
SET ROLE crud_admin;

CREATE TABLE lab.tabla_video_nueva (
    id integer PRIMARY KEY,
    descripcion text NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);

RESET ROLE;
```

Lo que se dice: “Ahora crearemos una tabla nueva después de que la aplicación
ya fue desarrollada. No realizaremos ningún cambio en Python ni en la
extensión.”

Ejecutar `crudgen` nuevamente (Terminal A; si pide conexión, los mismos 5 datos:
`127.0.0.1`, Enter, `devdb`, `postgres`, clave a ciegas) y mostrar que
`tabla_video_nueva` aparece como **opción 7** en el listado. Responder, en orden:

```text
Esquema [número]: 2
Tablas: 7
Operaciones: a
Reemplazar: n
Roles: 2 (únicamente crud_administrador)
Permitir INSERT? [s/n]: s
Permitir READ? [s/n]: s
Permitir UPDATE? [s/n]: s
Permitir DELETE? [s/n]: s
Verificar: s
Ejecutar: n
```

Nota: acá sí `Reemplazar: n`, porque la tabla es nueva y no hay conflicto.

Lo que se dice: “La aplicación descubre inmediatamente la tabla mediante el
catálogo de PostgreSQL.”

Lo que se dice: “Sin modificar una sola línea de Python y sin crear
procedimientos manualmente, la extensión acaba de analizar una tabla desconocida
y generar sus cuatro operaciones CRUD.”

---

## 9:40–10:10 · Probar la tabla nueva

En Terminal B:

```sql
SET ROLE crud_administrador;
CALL lab.tabla_video_nueva_insertar(1, 'Creada durante la demostración');
CALL lab.tabla_video_nueva_consultar(1, NULL, NULL);
RESET ROLE;
```

Lo que se dice: “El procedure generado para la tabla recién creada funciona
exactamente igual que los anteriores, incluyendo el manejo automático del valor
DEFAULT de creado_en.”

Nota: el INSERT lleva solo 2 argumentos (el tercero, `creado_en`, lo pone el
DEFAULT); el READ devuelve la fila completa con la fecha generada.

---

## 10:10–10:40 · Cierre

Lo que se dice: “Con esta demostración verificamos el flujo completo del
proyecto. La extensión obtiene metadatos directamente desde los catálogos de
PostgreSQL, detecta claves primarias simples y compuestas, valores DEFAULT y
columnas generadas, y crea dinámicamente procedimientos INSERT, READ, UPDATE y
DELETE. La aplicación Python permite administrar el proceso de generación y
configurar los privilegios. Finalmente, PostgreSQL hace cumplir esos privilegios
mediante roles reales, GRANT, REVOKE y procedimientos SECURITY INVOKER. También
demostramos que una tabla creada posteriormente puede ser analizada y utilizada
sin modificar el código de la aplicación. Con esto se comprueba que la solución
es genérica y no depende de tablas hardcodeadas.”

---

## Después de grabar (fuera de cámara, opcional)

Dejar el laboratorio ordenado borrando la tabla de prueba y sus rutinas:

```sql
SET ROLE crud_admin;
DROP TABLE IF EXISTS lab.tabla_video_nueva;
DROP PROCEDURE IF EXISTS lab.tabla_video_nueva_insertar;
DROP PROCEDURE IF EXISTS lab.tabla_video_nueva_consultar;
DROP PROCEDURE IF EXISTS lab.tabla_video_nueva_actualizar;
DROP PROCEDURE IF EXISTS lab.tabla_video_nueva_eliminar;
RESET ROLE;
```
