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

**Estado:** Pendiente de cierre

**Responsable principal de análisis:** agente de Seguridad/Integración/Pruebas.

**Requisito:** la decisión debe justificarse considerando propietario, search_path, privilegios y riesgos.

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

