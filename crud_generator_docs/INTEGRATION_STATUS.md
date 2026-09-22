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

## Seguridad

- 🟡 Matriz de privilegios
- 🔴 GRANT/REVOKE
- 🔴 SECURITY INVOKER/DEFINER
- 🔴 Pruebas por roles

## Integración

- 🔴 Python → extensión
- 🔴 Generación → procedures
- 🔴 Python → roles/permisos
- 🔴 Prueba E2E
- 🔴 Tabla nueva

## Riesgos actuales

1. Definir correctamente la interfaz de READ.
2. Cerrar el comportamiento de tablas sin PK.
3. Cerrar la política para procedures existentes.
4. Definir estrategia de SECURITY INVOKER/DEFINER.
5. Confirmar la fecha de entrega del enunciado.

## Últimas decisiones

Consultar `DECISIONS.md`.

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
