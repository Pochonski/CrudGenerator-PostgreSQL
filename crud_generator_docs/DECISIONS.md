# Decisiones del Equipo

Este documento contiene decisiones globales. Si una decisión cambia, debe discutirse entre los tres integrantes y actualizarse explícitamente.

## 0. Responsables del proyecto

- **Joseph:** Seguridad + Integración + Pruebas.
- **Joyce:** Extensión PostgreSQL.
- **Armando:** Python + Interfaz.

Las decisiones globales requieren coordinación entre los tres. Las decisiones locales pueden tomarse dentro del área responsable siempre que no rompan contratos ni arquitectura.

## ADR-001 — Separación de responsabilidades

**Estado:** Adoptada

**Decisión:** La solución se divide en extensión PostgreSQL, aplicación Python y seguridad/integración/pruebas.

**Razón:** Reduce acoplamiento y refleja el alcance del enunciado.

---

## ADR-002 — Generación en PostgreSQL

**Estado:** Adoptada

**Decisión:** La lógica principal de análisis estructural y generación CRUD residirá en la extensión PostgreSQL.

**Razón:** Es un requisito explícito y demuestra metaprogramación sobre los catálogos.

---

## ADR-003 — Uso de procedimientos

**Estado:** Adoptada inicialmente

**Decisión:** Se utilizará `CREATE PROCEDURE` como mecanismo base para los CRUD generados.

**Razón:** El enunciado solicita procedimientos almacenados. La forma exacta de exponer READ debe definirse de acuerdo con las características de PostgreSQL.

---

## ADR-004 — Lenguaje inicial de la extensión

**Estado:** Propuesta inicial

**Decisión:** Partir de PL/pgSQL, salvo restricción del docente o necesidad técnica que justifique otro lenguaje.

**Razón:** Simplifica distribución/instalación y permite demostrar SQL dinámico y metaprogramación directamente en PostgreSQL.

---

## ADR-005 — Cliente Python

**Estado:** Propuesta inicial

**Decisión:** Utilizar `psycopg`.

**Razón:** Biblioteca moderna para PostgreSQL y adecuada para una aplicación académica de este alcance.

---

## ADR-006 — Interfaz

**Estado:** Propuesta inicial

**Decisión:** Priorizar CLI por simplicidad, rapidez de implementación y facilidad de demostración.

**Razón:** El valor principal del proyecto está en la integración y generación, no en una interfaz visual compleja.

---

## ADR-007 — Convención de procedimientos

**Estado:** Adoptada — convención del enunciado (§4.10)

**Decisión:** Los procedimientos generados se nombran como `<tabla>_<operacion>` con los
verbos del ejemplo oficial del enunciado:

```text
<tabla>_insertar      → INSERT
<tabla>_consultar     → READ
<tabla>_actualizar    → UPDATE
<tabla>_eliminar      → DELETE
```

**Ejemplo (del enunciado):**

```text
cliente_insertar
cliente_consultar
cliente_actualizar
cliente_eliminar
```

**Justificación:** es la convención que usa el propio profesor en §4.10, por lo que no
queda a criterio del equipo.

**Especificación para implementación (Joyce) — CR-JOYCE-002 cerrada:**
- El nombre textual (sin quotear) se compone como `<tabla>_<operacion>`; se
  quotea como una unidad con `quote_ident`/`%I` al momento de emitir el DDL
  (los identificadores NO son valores ordinarios, ADR-013).
- **Esquema destino (adoptado):** el mismo esquema de la tabla de origen.
  `lab.producto` → procedures en `lab`. Evita pedir `CREATE` sobre un esquema
  arbitrario y mantiene `SET search_path` simple (ADR-011).
- **Tipos y orden de parámetros (adoptado):** se derivan en tiempo real con
  `format_type(atttypid, atttypmod)` sobre `pg_attribute` (nunca un mapeo de
  tipos escrito a mano), preservando precisión/escala/longitud reales
  (`numeric(10,2)`, `varchar(50)`, etc.):
  - `insertar`/`actualizar`: columnas insertables/actualizables en
    `ordinal_position` (ver reglas de DEFAULT/IDENTITY más abajo en esta
    sección y en `CONTRACTS.md` §3.2).
  - `consultar`: PK primero, resto después (orden ya fijado en ADR-015).
  - `eliminar`: solo columnas PK, en su orden ordinal entre ellas.
- **Regla anti-colisión (adoptada):** no se necesita lógica especial. El
  nombre es único por construcción dentro de un esquema (una tabla no puede
  tener dos nombres) y no se soportan overloads: cada procedure generado
  tiene siempre una única firma. El único conflicto real posible es que ya
  exista un objeto con ese nombre, cubierto por ADR-010 (CR-JOYCE-004).

**Ejemplos de firma conceptual (base para ADR-015 y CR-JOYCE-002):**

Tabla PK simple `lab.producto(id_producto integer PK, nombre text, precio numeric)`:

```text
lab.producto_insertar(IN id_producto integer, IN nombre text, IN precio numeric)
lab.producto_consultar(INOUT id_producto integer, INOUT nombre text, INOUT precio numeric)
lab.producto_actualizar(IN id_producto integer, IN nombre text, IN precio numeric)
lab.producto_eliminar(IN id_producto integer)
```

Tabla PK compuesta `lab.detalle_factura(id_factura integer, id_producto integer, cantidad integer)`:

```text
lab.detalle_factura_insertar(IN id_factura integer, IN id_producto integer, IN cantidad integer)
lab.detalle_factura_consultar(INOUT id_factura integer, INOUT id_producto integer, INOUT cantidad integer)
lab.detalle_factura_actualizar(IN id_factura integer, IN id_producto integer, IN cantidad integer)
lab.detalle_factura_eliminar(IN id_factura integer, IN id_producto integer)
```

Los tipos exactos y el orden los confirma Joyce según los catálogos (CR-JOYCE-002).

---

## ADR-008 — Claves primarias compuestas

**Estado:** Adoptada

**Decisión:** La PK se modelará internamente como una lista ordenada de columnas.

**Razón:** Permite tratar PK simple y compuesta con el mismo modelo.

---

## ADR-009 — Tablas sin PK

**Estado:** Adoptada (Joyce, cierra CR-JOYCE-003)

**Decisión:** No se inventa una PK (ni `ctid` ni sustitutos). Por tabla sin PK:

- `INSERT` (`<tabla>_insertar`): se genera normal, no depende de PK.
- `READ` (`<tabla>_consultar`): no existe forma de buscar "una fila" sin PK, así
  que se genera una variante de **listado completo** vía `PROCEDURE` con
  parámetro `OUT refcursor` (abre un cursor con `SELECT *` de toda la tabla).
  Es la alternativa multi-fila que ya estaba documentada como opción válida en
  ADR-015, aplicada aquí porque sí es necesaria (no hay PK para el modo de una
  fila).
- `UPDATE` / `DELETE`: **no se generan**. `generate_crud` devuelve para esas
  operaciones una fila de resultado con `status = 'not_applicable'` y mensaje
  explicando que la tabla no tiene clave primaria. No se crea ningún procedure
  para ellas.

**Razón:** el enunciado liga identificación de fila a la PK explícitamente
("cuando la tabla disponga de ella"); usar `ctid` sería inventar una
pseudo-clave inestable (cambia con `VACUUM FULL`/reescritura de fila), lo que
viola el principio ya adoptado de no inventar PK.

---

## ADR-010 — Procedimientos existentes

**Estado:** Adoptada (Joyce, cierra CR-JOYCE-004)

**Decisión:** Por defecto, si ya existe un procedure con la firma exacta que la
extensión va a generar, `generate_crud` devuelve `status = 'procedure_conflict'`
para esa operación y no modifica nada.

Si el llamador pasa explícitamente `replace => true`, la extensión usa
`CREATE OR REPLACE PROCEDURE` — **nunca** `DROP` seguido de `CREATE`. Motivo
técnico: `CREATE OR REPLACE` conserva el OID del objeto y por lo tanto
conserva los `GRANT EXECUTE` ya otorgados; un `DROP + CREATE` crea un objeto
nuevo y destruye silenciosamente toda la matriz de privilegios ya aplicada
por Joseph/Armando. Dado que el proyecto depende de una matriz de privilegios
estable, perder los GRANTs en cada regeneración sería un defecto grave.

Si el objeto existente con ese nombre **no** es un procedure (función, tabla,
vista, etc.), no se puede usar `CREATE OR REPLACE` entre tipos de objeto
distintos → también se reporta `procedure_conflict`, con mensaje que aclara
que requiere intervención manual del administrador.

---

## ADR-011 — SECURITY INVOKER / SECURITY DEFINER

**Estado:** Pendiente de cierre — Fase 0 (análisis técnico registrado, decisión NO adoptada)

**Responsable principal de análisis:** Joseph (Seguridad + Integración + Pruebas).

**Requisito:** la decisión debe justificarse considerando propietario, search_path, privilegios y riesgos.

### Análisis técnico Fase 0 (Joseph, sin cerrar decisión)

1. **Semántica base PostgreSQL:**
   - `SECURITY INVOKER` (default en FUNCTION/PROCEDURE): el cuerpo se ejecuta con los
     privilegios del rol que invoca (`CALL`/`SELECT`). El acceso a tablas se chequea
     contra el invocador. Si el invocador no tiene `SELECT/INSERT/UPDATE/DELETE`
     sobre la tabla, la operación falla aunque tenga `EXECUTE` sobre el procedure.
   - `SECURITY DEFINER`: el cuerpo se ejecuta con los privilegios del propietario
     (`OWNER`) del procedure. El chequeo sobre tablas se hace contra el owner, no
     contra el invocador. El invocador solo necesita `EXECUTE` (+ `USAGE` sobre el
     esquema) para operar con privilegios elevados.

2. **Efecto sobre propietario:**
   - INVOKER: el owner importa poco en ejecución; importa quién llama. Owner
     recomendado: rol administrador de despliegue (ej. `crud_admin`), nunca un
     superusuario personal.
   - DEFINER: el owner es el vector de privilegio. Si el owner es superuser o tiene
     acceso amplio, cualquier poseedor de `EXECUTE` hereda ese poder dentro del
     procedure. Obliga a auditar owner + `REVOKE ALL` por defecto + `search_path` fijo.

3. **Efecto sobre permisos de tablas vs EXECUTE:**
   - INVOKER: modelo de dos llaves — `EXECUTE` sobre cada procedure + permisos
     directos sobre tablas (`GRANT SELECT/INSERT/... ON TABLE`). Revocar el permiso
     de tabla bloquea la vía procedure y la vía directa a la vez. Es más verboso
     pero respeta mínimo privilegio y hace la demo "acceso rechazado" trivial
     (`42501 insufficient_privilege`).
   - DEFINER: `EXECUTE` se vuelve la única llave. Permite ocultar la tabla
     (`REVOKE ALL ON TABLE` + `GRANT EXECUTE ON PROCEDURE`), útil si se quiere
     exponer solo la API. Riesgo: escalada si el procedure tiene SQL dinámico
     inyectable o `search_path` manipulable.

4. **GRANT / REVOKE:**
   - INVOKER exige matriz doble: `GRANT EXECUTE ON PROCEDURE ... TO rol` más
     `GRANT <op> ON TABLE ... TO rol`. `REVOKE` debe aplicarse en ambos niveles.
   - DEFINER exige disciplina inversa: `GRANT EXECUTE` selectivo + `REVOKE ALL ON
     TABLE FROM PUBLIC` y de roles no autorizados. Un `GRANT EXECUTE` olvidado
     equivale a acceso total a la lógica encapsulada.

5. **search_path:**
   - Con DEFINER, un `search_path` mutable permite *trojan-horse*: si el procedure
     referencia `mi_tabla` sin calificar y el atacante crea `mi_tabla` en un esquema
     anterior del path, el código DEFINER opera sobre el objeto del atacante con
     privilegios del owner. Mitigación obligatoria: `SET search_path = <esquema_app>,
     pg_temp` en la definición + nombres calificados + `pg_temp` al final o fuera.
   - Con INVOKER el riesgo persiste para confusión de objetos, pero no hay elevación
     de privilegio: el atacante solo se afecta a sí mismo.

6. **SQL dinámico (`EXECUTE format(...)` en PL/pgSQL):**
   - Regla ADR-013 aplica en ambos modelos: identificadores con `%I`/`quote_ident`,
     literales con `%L`/`quote_literal` o `USING`. Con DEFINER, una inyección equivale
     a ejecución como owner → impacto máximo. Nuestra auditoría (harness Fase 0)
     debe probar quoting con nombres especiales (`"Mi Tabla"`, `"precio$"`, etc.).

7. **Mínimo privilegio:**
   - INVOKER lo implementa de forma natural (cada rol solo recibe lo que necesita
     en tabla + procedure).
   - DEFINER lo viola por diseño salvo que cada procedure re-chequee
     `session_user`/`current_user` manualmente (ej. `IF NOT pg_has_role(...) THEN
     RAISE EXCEPTION ...`), lo que duplica lógica de permisos dentro del código.

8. **Experiencia de demostración:**
   - INVOKER: demo directa — `SET ROLE vendedor; CALL ...` → OK en permitido,
     `ERROR 42501` en denegado. El profesor ve el enforcement real de PG.
   - DEFINER: la demo requiere mostrar que el `REVOKE` de `EXECUTE` bloquea, y que
     sin `EXECUTE` no hay acceso aunque la tabla sea inaccesible. Menos intuitivo
     para explicar "tres niveles de acceso" si todo pasa por una sola llave.

### Decisión final (Joyce, cierra CR-JOYCE-005 — votada por el equipo)

**Estado:** Adoptada. El equipo adopta la recomendación formal de Joseph tal cual.

**Recomendación adoptada:** `SECURITY INVOKER` por defecto para los CRUD generados, reservando
`SECURITY DEFINER` solo para casos justificados (ej. API que deba ocultar la tabla base
o auditoría centralizada, ninguno usado en el alcance actual).

**Owner confirmado:** `crud_admin` (el mismo rol ya definido en
`tests/fixtures/01_roles.sql`: `NOLOGIN`, dueño de `lab` con `USAGE, CREATE`).
Las funciones de generación de la extensión deben ejecutarse autenticadas como
`crud_admin` (o un rol equivalente con `CREATE` sobre el esquema destino) para
que `crud_admin` quede como owner real de los procedures generados — igual que
en los fixtures de seguridad ya probados por Joseph. No se introduce un rol
nuevo.

**Evidencia del experimento (ejecutado en PostgreSQL 18):**
- `EXP-01` — procedure INVOKER ejecutado por rol sin permiso de tabla → **error 42501**
  (mínimo privilegio natural).
- `EXP-02` — procedure DEFINER idéntico ejecutado por el mismo rol → **permitido**
  (elevación de privilegio vía owner). VERDI: el riesgo de DEFINER es real y medible.
- Referencia: `tests/security/02_invoker_vs_definer.sql`.

**Especificación que la extensión debe emitir (para implementación de Joyce):**
1. Cláusula `SECURITY INVOKER` explícita en cada procedure generado (no depender del
   default implícito).
2. `SET search_path = <esquema_destino>, pg_temp` en la definición del procedure.
3. Cuerpo con nombres calificados (`<esquema>.<tabla>`) — nunca referencias de tabla
   sin calificar.
4. SQL dinámico (si se usa): identificadores con `%I`/`quote_ident`, valores con
   `USING`/`%L` (ADR-013).

**Condición de adopción:** cumplida — voto del equipo y confirmación de Joyce
(owner `crud_admin`) resueltos el 2026-10-01. Ver CR-JOYCE-005 en
`COORDINATION_REQUESTS.md`.

**Confirmado por el experimento:** INVOKER bloquea sin permiso de tabla (42501),
DEFINER eleva vía owner (EXP-01/02).

---

## ADR-012 — Privilegios

**Estado:** Adoptada

**Decisión:** Los permisos reales se aplicarán mediante mecanismos de PostgreSQL (`GRANT`, `REVOKE`, privilegio `EXECUTE`, etc.).

**Razón:** El requisito exige validación real con distintos usuarios/roles.

---

## ADR-013 — SQL dinámico seguro

**Estado:** Adoptada

**Decisión:** Los identificadores y valores deben manejarse según los mecanismos apropiados de PostgreSQL, evitando concatenación insegura cuando exista una alternativa segura.

---

## ADR-014 — Fechas del enunciado

**Estado:** Confirmada (2026-10-01)

**Decisión:** Fecha de entrega confirmada: **domingo 4 de octubre de 2026**
(corrida desde el 30 de setiembre original). Se descarta definitivamente la
lectura "30 de setiembre de 2021": el texto del enunciado ("jueves 30 de
setiembre") era internamente consistente solo para 2021 (2021-09-30 es
jueves; 2026-09-30 es miércoles), lo que confirma que era una plantilla de un
curso anterior sin actualizar, no un typo de un solo dígito.

**Impacto:** quedan ~3 días desde la confirmación. Prioridad: tener un
generador funcional end-to-end (INSERT/READ/UPDATE/DELETE, PK simple y
compuesta, autogenerado, sin PK) antes que pulir casos exóticos adicionales.

---

## ADR-015 — Contrato de READ (consultar)

**Estado:** Adoptada — confirmada por Joyce (CR-JOYCE-001) el 2026-10-01, cierra como contrato global.

**Decisión:** `consultar` es un procedure que consulta por **clave primaria completa** y
devuelve **una fila** mediante parámetros `INOUT`. La firma replica la estructura de la tabla.

**Justificación:** el enunciado §4.5 define READ como *"recuperar información de la tabla
de acuerdo con los criterios definidos por el equipo"*. La lectura por PK completa es el
criterio más simple y soporta una PK compuesta sin ambigüedad. En PostgreSQL un
`PROCEDURE` llamado con `CALL` no retorna result-set directo; la vía `INOUT` es la mínima
demostrable y ya está validada en el fixture de la Fase 0 (`lab.producto_consultar`,
probado en MAT-07).

**Especificación para implementación (Joyce):**

Para una tabla `T` con PK `{k1..kN}` y resto de columnas `{c1..cM}`:

```text
T_consultar(INOUT k1 tipo, ..., INOUT kN tipo, INOUT c1 tipo, ..., INOUT cM tipo)
```

- Los parámetros PK van primero (INOUT), luego el resto de columnas (INOUT).
- Si la fila no existe → error con SQLSTATE descriptivo (propuesta: `P0002` con mensaje)
  para que Python lo muestre correctamente (CONTRACTS §5).
- Para PK simple el patrón es `(INOUT id_pk tipo, INOUT resto...)` — ejemplo `lab.producto_consultar`.
- Para PK compuesta todos los componentes van como parámetros — ejemplo `lab.detalle_factura_consultar`.

**Caso tabla sin PK (resuelto, ver ADR-009):** READ por PK no aplica; se genera
en su lugar un `consultar` de listado completo vía `refcursor OUT`. UPDATE y
DELETE no se generan (`not_applicable`).

**Lectura multi-fila con filtros (fuera de alcance):** no requerida para la
entrega; el único caso multi-fila implementado es el listado completo de
tablas sin PK descrito en ADR-009.

