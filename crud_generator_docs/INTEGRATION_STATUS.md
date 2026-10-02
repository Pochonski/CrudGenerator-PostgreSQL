# Estado de Integración del Proyecto

**Fecha de auditoría:** 02-10-2026 (Joseph, post-merge `joyce/extension-foundation` → `main`).
**Enunciado de referencia:** `documento_completo.md` (transcripción fiel del PDF).

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

## Auditoría entregables del enunciado (02-10-2026, post-merge)

| Entregable (§10) | Responsable | Estado | Bloqueado por |
|---|---|---|---|
| Extensión instalable (`.control`, scripts, fuente) | Joyce | 🟢 Implementada y mergeada a `main` (`extension/crud_generator.control`, `extension/sql/crud_generator--1.0.sql`, probada PG16) — pendiente push a `origin/main` | Push + integración Python |
| Aplicación Python (código + documentación de uso) | Armando | 🟡 ~60% andamiaje (conexión, detección 4 estados, catálogo, CLI, orquestador; falta `analyze_table`/`generate_crud`/privilegios) | CR-ARMANDO-001..003 |
| VÍDEO de evidencia (10 pasos §10) | Equipo | 🔴 | Tramo Python + demo E2E |
| Demo en vivo (10 pasos §11 + tabla del docente) | Equipo | 🔴 | Tramo Python + tabla virgen |

Pruebas obligatorias (§9): casos 1-2-3 y 3 roles cubiertos por el laboratorio de
`tests/` con fixtures (CI PASS); validados contra procedures reales en PG18 local
02-10 (ver abajo). `lab.tabla_virgen` intacta (0 filas, 0 rutinas).

## Extensión PostgreSQL

- 🟢 Diseño de arquitectura (contrato cerrado, `CONTRACTS.md` §3-4)
- 🟢 API pública (naming, esquema, tipos y resultado cerrados — ADR-007/009/010/011/015)
- 🟢 Catálogos (`analyze_table` implementado y probado: PK simple/compuesta, identity, default, tipos/nombres especiales)
- 🟢 Generación CRUD (`generate_crud` implementado: INSERT/READ/UPDATE/DELETE probados con ejecución real en las 5 tablas del lab)
- 🟢 Casos límite (sin PK, conflicto+`do_replace`, autogenerado — implementados y probados contra Postgres 16)

## Python

- 🟢 Diseño de arquitectura (capas `ui/cli` → `application` → `services` → `db/connection`)
- 🟢 Conexión (`ConnectionManager` + `validate()`, errores con SQLSTATE, `main.py` mínimo)
- 🟢 Detección de extensión (requisito §4.2: 4 estados `INSTALLED/NOT_INSTALLED/NOT_ACCESSIBLE/ERROR` en `ExtensionService.check_extension`)
- 🟢 Selección de esquema/tablas (requisito §4.4: una/varias/todas vía `CatalogService` + `Cli.select_schema/select_tables`)
- 🟢 Selección CRUD + roles listado (`CrudOperation`, `CrudSelection`, `list_roles`; sin GRANT/REVOKE aún)
- 🔴 Generación (`ApplicationFlow` se detiene en `show_generation_pending()`; no llama `analyze_table`/`generate_crud`)
- 🔴 Privilegios (sin `GRANT/REVOKE`, sin validación `SET ROLE + CALL`)

## Seguridad (Joseph)

- 🟢 Matriz de privilegios (idéntica a §4.10 del enunciado; probada con fixtures MAT-01..07)
- 🟢 GRANT/REVOKE (04_grants probado + plantilla parametrizada 05_grants_template)
- 🟢 SECURITY INVOKER/DEFINER (ADR-011 adoptada 01-10: INVOKER + owner `crud_admin` + `search_path` fijo; EXP-01/02 + discovery 18/18 contra reales)
- 🟢 Pruebas por roles (NEG-01..11 OK con fixtures y reales; MAT-01..07 7/7 y MAT-C1..C9 9/9
  OK contra reales PG18 02-10 tras fix variables INOUT — CI fixtures PASS)
- 🟢 Caso 3 §9 + T6 contra reales (archivos nuevos 11/12 modo reales, validados PG18 02-10:
  TIXR 11/11 incl. AUD 4/4; SPC/LOG 19/19 incl. B-POL not_applicable + S-AUDR 7/7;
  07/09 intactos para modo fixtures; tabla virgen final pendiente)
- 🟢 READ adoptado y confirmado (ADR-015 + Joyce: PK vía INOUT + P0002; sin PK vía `refcursor OUT`)

## Integración

- 🟢 Contratos resueltos (ADR-007/009/010/011/015)
- 🔴 Python → extensión (pendiente de Armando: `app/` aún no llama `analyze_table`/`generate_crud`)
- 🟢 Generación → procedures (18 rutinas generadas y verificadas contra PG18 local 02-10;
  firmas exactas según handoff §2.4, incl. `not_applicable` sin PK y reorden p_2,p_1 en especial)
- 🟢 Discovery/matriz/auditorías contra reales PG18 02-10: discovery 18/0/18/0, T3 40/40,
  T4 PUB-01 8/8 + PUB-02 24/24 + REV-01 completo, T5 OK, EXP-01/02 OK, demo E2E OK
  (MAT-07/DEMO-04/MAT-C/T4-3b fix variables INOUT, CI fixtures PASS)
- 🔴 Python → roles/permisos
- 🟡 Prueba E2E (falta el tramo Python; la parte PostgreSQL del flujo ya está probada)
- 🔴 Tabla nueva (tabla_virgen reservada, intacta)

## Riesgos actuales

1. **TIEMPO:** entrega confirmada **domingo 4 de octubre de 2026** (ADR-014). Desde
   el 2026-10-02 quedan ~2 días. Merge Joyce→main hecho local (FF a `a1381fa`);
   pendiente `push` a `origin/main` + priorizar flujo E2E Python sobre pulir exóticos.
2. ~~Definir firmas/esquema finales de la extensión (CR-JOYCE-002).~~ Resuelto 2026-10-01.
3. ~~Decidir READ multi-fila / sin PK (CR-JOYCE-003) y policy de procedures existentes (CR-JOYCE-004).~~ Resuelto 2026-10-01.
4. ~~Cerrar voto ADR-011 (INVOKER) + confirmar owner/cláusula que emitirá la extensión (CR-JOYCE-005).~~ Resuelto 2026-10-01.
5. Definir vía de aplicación de privilegios desde Python (CR-ARMANDO-001) y validación real
   con SET ROLE + CALL (CR-ARMANDO-003). Pendiente de Armando.
6. ~~Confirmar la fecha de entrega del enunciado (ADR-014)~~ Confirmada. Falta confirmar
   formato exacto del vídeo (§10) con el docente si hiciera falta.
7. ~~Implementación real de la extensión (código)~~ Completa y probada 2026-10-02
   (`extension/`, ver EXTENSION_MEMORY.md). Pendiente: que Armando integre `app/`
   contra la API real en vez de detenerse antes de generar.

## Últimas decisiones

- **ADR-007 (Adoptada):** convención `<tabla>_{insertar,consultar,actualizar,eliminar}` (§4.10),
  esquema destino = esquema de la tabla, tipos vía `format_type`.
- **ADR-015 (Adoptada y confirmada por Joyce):** READ por PK completa vía INOUT; sin PK, listado vía `refcursor OUT`.
- **ADR-011 (Adoptada):** INVOKER por defecto, owner `crud_admin`; verificado 18/18 en discovery real.
- **ADR-009/010 (Adoptadas):** política de tabla sin PK y de conflicto de procedures (`do_replace` con `CREATE OR REPLACE`).
- **ADR-014 (Confirmada):** entrega domingo 4 de octubre de 2026.
- Ver `DECISIONS.md` (ADR-001..015) y `COORDINATION_REQUESTS.md` (CR-JOYCE-001..005 resueltas, CR-ARMANDO-001..003 pendientes).
- `CONTRACTS.md` actualizado 2026-10-01/02 con la API real de la extensión (ya no es propuesta).

## Próximos hitos

1. ~~Congelar contratos~~ Hecho (CR-JOYCE-001..005 resueltas 2026-10-01).
2. ~~Implementar la extensión~~ Hecho y probada 2026-10-02 (ver EXTENSION_MEMORY.md).
3. Armando: integrar `app/` para llamar `crud_generator.analyze_table`/`generate_crud` (ya no mock).
4. Armando: resolver CR-ARMANDO-001..003 (vía de privilegios, formato de resultado, validación real con SET ROLE).
5. Joseph: aplicar los dos ajustes reportados en COORDINATION_REQUESTS.md (fix de discovery ya aplicado por Joyce; MAT-07 pendiente de su ajuste) y re-ejecutar MAT/NEG completos contra procedures reales.
6. Probar tabla_virgen (tabla desconocida) end-to-end desde Python.
7. Preparar vídeo de evidencia y demo en vivo (10 pasos §10/§11) antes del 2026-10-04.
