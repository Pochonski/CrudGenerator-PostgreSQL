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

**Estado:** Pendiente de cierre

**Propuesta:** `<tabla>_<operacion>`.

**Ejemplo:**

```text
cliente_insertar
cliente_consultar
cliente_actualizar
cliente_eliminar
```

Debe definirse además cómo evitar colisiones cuando existan overloads o nombres especiales.

---

## ADR-008 — Claves primarias compuestas

**Estado:** Adoptada

**Decisión:** La PK se modelará internamente como una lista ordenada de columnas.

**Razón:** Permite tratar PK simple y compuesta con el mismo modelo.

---

## ADR-009 — Tablas sin PK

**Estado:** Pendiente de cierre

**Principio:** No inventar una PK.

**Pregunta a cerrar:** si se generan únicamente operaciones aplicables o se reportan determinadas operaciones como no disponibles.

---

## ADR-010 — Procedimientos existentes

**Estado:** Pendiente de cierre

**Pregunta a cerrar:** política ante procedimientos existentes: reemplazo, error, o tratamiento diferenciado según firma.

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

### Recomendación NO vinculante (pendiente de experimento)

La hipótesis de trabajo es **INVOKER por defecto** por mínimo privilegio y
demostrabilidad, reservando DEFINER solo para casos justificados (ej. auditoría
centralizada o API que deba ocultar la tabla base). NO se adopta todavía:
requiere el experimento comparativo en `tests/security/02_invoker_vs_definer.sql`
y la respuesta de Joyce (owner que emitirá la extensión) — ver `CR-JOYCE-005`.

**Pregunta a cerrar con el equipo:** ¿los procedures generados fijarán owner +
`search_path` explícito? ¿La extensión emitirá cláusula `SECURITY` explícita o
heredará el default?

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

**Estado:** Pendiente de confirmación

**Decisión:** No asumir el año de entrega hasta confirmar con el docente porque el enunciado indica 30 de setiembre de 2021 mientras el inicio indica 2026.

