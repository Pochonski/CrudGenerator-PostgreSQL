# Estado de Integración del Proyecto

**Fecha de auditoría:** 22-09-2026 (Joseph).
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

## Auditoría entregables del enunciado (22-09-2026)

| Entregable (§10) | Responsable | Estado | Bloqueado por |
|---|---|---|---|
| Extensión instalable (`.control`, scripts, fuente) | Joyce | 🔴 0% código | — |
| Aplicación Python (código + documentación de uso) | Armando | 🔴 0% código | — |
| VÍDEO de evidencia (10 pasos §10) | Equipo | 🔴 | Joyce + Armando + demo |
| Demo en vivo (10 pasos §11 + tabla del docente) | Equipo | 🔴 | Joyce + Armando |

Pruebas obligatorias (§9): casos 1-2-3 y 3 roles cubiertos por el laboratorio de
`tests/` con fixtures; pendiente validar contra procedures reales de Joyce.

## Extensión PostgreSQL

- 🟡 Diseño de arquitectura
- 🔴 API pública (naming adoptado ADR-007; firmas/esquema pendientes CR-JOYCE-002)
- 🔴 Catálogos
- 🔴 Generación CRUD
- 🔴 Casos límite

## Python

- 🟡 Diseño de arquitectura
- 🔴 Conexión
- 🔴 Detección de extensión (requisito §4.2: 4 estados; pendiente de incluir en contrato)
- 🔴 Selección de esquema/tablas (requisito §4.4: una/varias/todas)
- 🔴 Generación
- 🔴 Privilegios

## Seguridad (Joseph)

- 🟢 Matriz de privilegios (idéntica a §4.10 del enunciado; probada con fixtures MAT-01..07)
- 🟢 GRANT/REVOKE (04_grants probado + plantilla parametrizada 05_grants_template)
- 🟡 SECURITY INVOKER/DEFINER (recomendación formal ADR-011, experimento EXP-01/02 probado;
  decisión global pendiente de voto + CR-JOYCE-005)
- 🟡 Pruebas por roles (NEG-01..11 probados con fixtures; pendiente procedures reales + tabla virgen)
- 🟢 READ adoptado (ADR-015: por PK vía INOUT; pendiente confirmación Joyce CR-JOYCE-001)

## Integración

- 🟡 Contratos parcialmente resueltos (ADR-007 naming, ADR-015 READ)
- 🔴 Python → extensión
- 🔴 Generación → procedures
- 🔴 Python → roles/permisos
- 🔴 Prueba E2E
- 🔴 Tabla nueva (tabla_virgen reservada, intacta)

## Riesgos actuales

1. **TIEMPO:** si la entrega es 30-09-2026 (ADR-014 pendiente de confirmar), quedan ~8 días
   y las áreas de Joyce y Armando están en 0% de código. Riesgo crítico de equipo.
2. Definir firmas/esquema finales de la extensión (CR-JOYCE-002).
3. Decidir READ multi-fila / sin PK (CR-JOYCE-003) y policy de procedures existentes (CR-JOYCE-004).
4. Cerrar voto ADR-011 (INVOKER) + confirmar owner/cláusula que emitirá la extensión (CR-JOYCE-005).
5. Definir vía de aplicación de privilegios desde Python (CR-ARMANDO-001) y validación real
   con SET ROLE + CALL (CR-ARMANDO-003).
6. Confirmar la fecha de entrega del enunciado (ADR-014) y el formato del vídeo (§10) con el docente.

## Últimas decisiones

- **ADR-007 (Adoptada):** convención `<tabla>_{insertar,consultar,actualizar,eliminar}` (§4.10).
- **ADR-015 (Adoptada, pendiente Joyce):** READ por PK completa vía INOUT.
- **ADR-011 (Recomendación formal):** INVOKER por defecto, evidencia EXP-01/02; voto pendiente.
- Ver `DECISIONS.md` (ADR-001..015) y `COORDINATION_REQUESTS.md` (CR-JOYCE-001..005, CR-ARMANDO-001..003).
- `CONTRACTS.md` sin cambios en Fases 0/A (no se inventaron firmas de Joyce).

## Próximos hitos

1. Confirmar fecha de entrega y formato de vídeo con el docente.
2. Congelar contratos (firmas/esquema — Joyce responde CR-JOYCE-002; READ CR-JOYCE-001).
3. Crear prototipo mínimo de extensión (Joyce).
4. Crear conexión Python (Armando), incluidos 4 estados de detección y selección una/varias/todas.
5. Votar ADR-011 y confirmar owner (CR-JOYCE-005).
6. Sustituir fixtures por procedures reales; re-ejecutar MAT/NEG.
7. Probar tabla_virgen (tabla desconocida).
8. Preparar vídeo de evidencia y demo en vivo (10 pasos §10/§11).
