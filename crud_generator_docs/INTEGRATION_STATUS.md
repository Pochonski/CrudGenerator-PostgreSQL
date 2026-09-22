# Estado de Integración del Proyecto

## Responsables

- **Joyce:** Extensión PostgreSQL
- **Armando:** Python + Interfaz
- **Joseph:** Seguridad + Integración + Pruebas

El estado es compartido: cualquier integrante puede reportar bloqueos o dependencias, pero el responsable principal lidera su resolución.

## Reglas de coordinación

1. Los tres agentes deben leer `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, `CONTRACTS.md` y `DECISIONS.md` antes de hacer cambios relevantes.
2. Los cambios de contratos o arquitectura no se hacen unilateralmente.
3. El responsable de cada área actualiza su memoria específica después de avances importantes.
4. Un cambio que afecte a otro componente debe quedar registrado en `CONTRACTS.md` o `DECISIONS.md`.

## Leyenda

- 🟢 Completo / validado
- 🟡 En progreso / pendiente de validar
- 🔴 No iniciado
- Fase 0 seguridad distingue además: Diseñado / Implementado / Probado / Integrado.

## Extensión PostgreSQL

- 🟡 Diseño de arquitectura
- 🔴 API pública
- 🔴 Catálogos
- 🔴 Generación CRUD
- 🔴 Casos límite

## Python

- 🟡 Diseño de arquitectura
- 🔴 Conexión
- 🔴 Detección de extensión
- 🔴 Selección de esquema/tablas
- 🔴 Generación
- 🔴 Privilegios

## Seguridad (Joseph — Fase 0)

- 🟢 Matriz de privilegios (diseñada; probada con fixtures en PG18: MAT-01..07 OK)
- 🟢 GRANT/REVOKE (diseñados; harness `tests/fixtures/04_grants.sql` probado)
- 🟡 SECURITY INVOKER/DEFINER (análisis en ADR-011; experimento
  `tests/security/02_invoker_vs_definer.sql` probado; decisión PENDIENTE DE CIERRE)
- 🟡 Pruebas por roles (matriz + NEG-01..11 probadas con fixtures; pendiente
  procedures reales de Joyce y tabla virgen final)

## Integración

- 🔴 Python → extensión
- 🔴 Generación → procedures
- 🔴 Python → roles/permisos
- 🔴 Prueba E2E
- 🔴 Tabla nueva

## Riesgos actuales

1. Definir correctamente la interfaz de READ (CR-JOYCE-001, BLOQUEADO).
2. Cerrar el comportamiento de tablas sin PK (CR-JOYCE-003).
3. Cerrar la política para procedures existentes (CR-JOYCE-004).
4. Definir estrategia de SECURITY INVOKER/DEFINER (ADR-011 pendiente; CR-JOYCE-005).
5. Confirmar la fecha de entrega del enunciado (ADR-014, con docente).
6. Definir vía de aplicación de privilegios desde Python (CR-ARMANDO-001) y
   validación real con SET ROLE + CALL (CR-ARMANDO-003).

## Últimas decisiones

Consultar `DECISIONS.md` y `COORDINATION_REQUESTS.md` (Fase 0: CR-JOYCE-001..005,
CR-ARMANDO-001..003). ADR-011 ampliado con análisis, sigue PENDIENTE DE CIERRE.
`CONTRACTS.md` sin cambios en Fase 0 (no se inventaron firmas).

## Próximos hitos

1. Congelar contratos.
2. Crear prototipo mínimo de extensión.
3. Crear conexión Python.
4. Integrar análisis de una tabla.
5. Generar INSERT.
6. Completar CRUD.
7. Integrar privilegios.
8. Ejecutar matriz de pruebas.
9. Probar tabla nunca utilizada.
10. Preparar demostración.
