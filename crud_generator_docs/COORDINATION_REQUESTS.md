# Coordination Requests — Seguridad + Integración + Pruebas (Joseph)

Documento de Fase 0 para Joyce y Armando. Cada solicitud indica qué necesitamos,
por qué, qué componente afecta, qué decisión está pendiente, alternativas
evaluadas y si bloquea o solo requiere coordinación. Ninguna decisión listada
aquí se asume aceptada por Joyce o Armando.

---

## Joyce — Extensión PostgreSQL

> **Actualización 2026-10-01 (Joyce):** las 5 solicitudes de esta sección quedan
> **RESUELTAS**. Decisiones registradas en `DECISIONS.md` (ADR-007, ADR-009,
> ADR-010, ADR-011, ADR-015) y contrato formal en `CONTRACTS.md` §3-4. Se deja
> el texto original de cada solicitud como registro histórico, con la
> resolución anotada debajo de cada una.

### CR-JOYCE-001 — Diseño de READ
Estado: **RESUELTA** — ADR-015 adoptado tal cual propuesto. Ver `CONTRACTS.md` §3.2/§4.

Contexto: el enunciado §4.5 permite "recuperar información de la tabla de acuerdo con los
criterios definidos por el equipo", por lo que READ ya no es un bloqueo técnico: es una
decisión de equipo. El área Seguridad adoptó ADR-015.

Decisión propuesta (ya especificada en DECISIONS.md ADR-015):
- `consultar` = consulta por **PK completa**, devuelve **una fila vía INOUT**.
- Firma base en ADR-015 con ejemplos para `lab.producto` y `lab.detalle_factura`.
- Fila inexistente → error con SQLSTATE descriptivo (propuesta `P0002`).
- Tabla sin PK → se deriva a CR-JOYCE-003 (no se decide aquí).

Necesitamos de Joyce:
- Confirmar que la extensión emitirá esta firma (o ajustarla), y el SQLSTATE exacto de
  fila no encontrada que Python tendrá que mostrar.

Alternativas evaluadas y descartadas por ahora:
- Refcursor OUT para multi-fila: documentado como opción, NO requerido para la entrega.

### CR-JOYCE-002 — Naming, esquema y firmas de procedures generados
Estado: **RESUELTA** — esquema destino = esquema de la tabla; tipos vía
`format_type`; sin anti-colisión especial (ver ADR-007 y `CONTRACTS.md` §3.2).

Resuelto (ADR-007, adoptado): convención del propio enunciado §4.10.

```text
<tabla>_insertar | <tabla>_consultar | <tabla>_actualizar | <tabla>_eliminar
```

Pendiente que defina Joyce:
- Esquema destino de los procedures generados (recomendación base: mismo esquema de la tabla).
- Tipos exactos y orden de parámetros (el fixture usa `integer,text,numeric` para `producto`).
- Regla anti-colisión con nombres que requieren quoting (opción base: los 4 nombres son
  únicos por construcción; confirmar cómo calificar si el esquema no califica).

Por qué afecta nuestra área:
- Cada `GRANT EXECUTE ON PROCEDURE ... (tipos exactos)` depende de la firma.
  La plantilla parametrizada (`tests/fixtures/05_grants_template.sql`) ya está lista para
  recibir los nombres reales sin rehacer trabajo.

### CR-JOYCE-003 — Tablas sin PK
Estado: **RESUELTA** — INSERT normal; READ pasa a listado completo (`refcursor
OUT`); UPDATE/DELETE devuelven `status='not_applicable'`, no se generan. Ver ADR-009.

Necesitamos definir:
- ¿Se generan solo INSERT/READ y UPDATE/DELETE se reportan "no aplicables"?
- ¿Qué código/resultado devuelve la extensión en ese caso?

Por qué afecta nuestra área:
- Define las pruebas NEG-05 y el contrato de errores "operación no aplicable".

Alternativas que proponemos al equipo:
- Generar lo aplicable + resultado estructurado `not_applicable` por operación.

### CR-JOYCE-004 — Procedures existentes
Estado: **RESUELTA** — error (`status='procedure_conflict'`) por defecto;
reemplazo solo con `do_replace=true` usando `CREATE OR REPLACE PROCEDURE`
(preserva GRANTs existentes, nunca `DROP+CREATE`). Ver ADR-010.

Necesitamos definir:
- ¿Error / reemplazo / drop+create / tratamiento según firma?

Por qué afecta nuestra área:
- Define la prueba NEG-06 y evita que la demo falle por re-ejecución.

Alternativa propuesta:
- Por defecto error explícito `conflicto con procedimiento existente`; reemplazo
  solo con flag explícito del administrador.

### CR-JOYCE-005 — Owner y cláusula SECURITY que emitirá la extensión
Estado: **RESUELTA** — INVOKER adoptado tal cual la recomendación de Joseph;
owner confirmado `crud_admin` (el mismo rol ya definido en `01_roles.sql`,
sin introducir un rol nuevo). Ver ADR-011.

Contexto: el área Seguridad adoptó una **recomendación formal** en ADR-011: `SECURITY
INVOKER` por defecto, con evidencia del experimento (EXP-01/02). La decisión global se
cierra con voto del equipo + tu confirmación.

Necesitamos que la extensión emita en cada procedure generado:
- Cláusula `SECURITY INVOKER` explícita (no depender del default).
- `SET search_path = <esquema_destino>, pg_temp`.
- Nombres calificados `<esquema>.<tabla>` dentro del cuerpo.
- SQL dinámico solo con `%I`/`USING` (ADR-013).

Y que confirmes:
- Rol owner de los procedures generados (recomendación: `crud_admin`-equivalente, nunca
  superusuario personal).

Por qué afecta nuestra área:
- Con INVOKER nuestra estrategia GRANT es doble (EXECUTE + tabla). Si la extensión
  pudiera emitir DEFINER, la matriz cambiaría (solo EXECUTE). Nuestro
  `tests/security/02_invoker_vs_definer.sql` demuestra la diferencia.

---

## Armando — Python + Interfaz

### CR-ARMANDO-001 — Vía de aplicación de privilegios
Estado: **RESUELTA** (03-10-2026).

Resolución real: Python usa `PrivilegeService.apply_matrix` con
`GRANT`/`REVOKE` directos (dos llaves INVOKER: `EXECUTE` sobre procedure +
permiso de tabla + `USAGE ON SCHEMA`). `ApplicationFlow` asume `crud_admin`
mediante `ConnectionManager.assume_role`. No se usa una función privilegiada
de la extensión para grants. Probado realmente el 03-10-2026 (E2E
`armando_e2e`, 3 roles, 12+4 procedures, owner `crud_admin`).

Texto histórico (requerimiento original, conservado como registro):

Necesitamos definir:
- ¿Python ejecuta `GRANT/REVOKE` directo con credencial alta, o llama a una
  función privilegiada de la extensión?

Por qué afecta nuestra área:
- Define qué rol usa Python, qué auditar y el principio de mínimo privilegio
  (ningún rol de negocio genera; solo `crud_admin`-equivalente aplica grants).

Información que necesitamos de Armando:
- Rol/credencial que usará Python y punto del flujo donde aplica privilegios.

### CR-ARMANDO-002 — Resultado de `generate_crud`
Estado: **RESUELTA** (03-10-2026).

Resolución: la CLI presenta todos los `GenerationResult`:
`success`, `not_applicable`, `procedure_conflict`, `validation_error`.
Errores reales PostgreSQL siguen siendo excepciones mapeadas y conservan
`SQLSTATE`; no se convierten falsamente en esos status.

Texto histórico (requerimiento original, conservado como registro):

Necesitamos definir:
- Formato que Python mostrará para: éxito, no aplicable, validación, inexistente,
  conflicto, permiso insuficiente, error interno (CONTRACTS §3.3).

Por qué afecta nuestra área:
- Nuestras pruebas de integración verifican que Python no oculte errores de PG
  (SQLSTATE visibles: 42501, 42883, 42P01, etc.).

### CR-ARMANDO-003 — Validación real de permisos desde Python
Estado: **RESUELTA** (03-10-2026).

Resolución: `PermissionProbeService` usa `SET LOCAL ROLE` + `CALL` real en
transacción `force_rollback`. `42501` durante `CALL` = `DENIED`. `SET ROLE`
no posible = `RoleAssumptionError` (no se confunde con `DENIED`).
Certificación E2E real 03-10-2026 confirmó
vendedor/supervisor/administrador (`ALLOWED`/`DENIED 42501`, `42P01`,
PK compuesta, generated).

Texto histórico (requerimiento original, conservado como registro):

Necesitamos definir:
- ¿Python verificará permisos con `SET ROLE` + `CALL` real (exigido para la demo),
  o solo consultando `information_schema` / `has_*_privilege`?

Por qué afecta nuestra área:
- Solo la ejecución real demuestra "operación permitida vs rechazada" ante el
  profesor. Nuestro `tests/integration/02_demo_script.sql` es la referencia del
  flujo esperado; Python debe poder reproducirlo.

---

## Guía completa de integración

Ver [`ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md`](ARMANDO_JOSEPH_INTEGRATION_HANDOFF.md):
cómo llamar `analyze_table`/`generate_crud` desde Python (psycopg), cómo
ejecutar los procedures generados (INSERT/READ con y sin PK/UPDATE/DELETE),
el modelo de GRANT de dos llaves, cómo re-generar el laboratorio de pruebas
con procedures reales en vez de fixtures, y la tabla de firmas reales
confirmadas para las 5 tablas del laboratorio.

## Nuevo — hallazgos de Joyce al integrar la implementación real (2026-10-02)

Implementé la extensión (`extension/`) y la probé contra el laboratorio
completo de Joseph (`lab.producto`, `detalle_factura`, `ticket`, `bitacora`,
`catalogo_especial`) más su propio harness. Dos hallazgos para Joseph:

1. **Bug de un carácter en `tests/security/10_generated_routine_discovery.sql`:**
   usaba `has_function_privilege('PUBLIC', ...)` (mayúsculas) que PostgreSQL
   rechaza con `role "PUBLIC" does not exist`; el pseudo-rol se escribe en
   minúsculas (`'public'`). Lo corregí directamente (dos ocurrencias) porque
   era un bug objetivo, no una decisión de diseño. Con el fix, el discovery
   corrió limpio contra las 18 rutinas reales: 18/18 owner `crud_admin`,
   18/18 `INVOKER`, 18/18 `search_path=lab, pg_temp`, 0 fugas de EXECUTE a
   PUBLIC.
2. **`tests/security/01_matrix.sql` MAT-07 necesita un ajuste menor contra
   routines reales:** corrí `04_grants.sql` + `01_matrix.sql` sin tocarlos
   contra mis procedures reales de `lab.producto` (firmas idénticas a tu
   fixture) — MAT-01 a MAT-06 pasaron sin cambios. MAT-07 falla con
   `42601 ... parameter "p_1" is an output parameter but corresponding
   argument is not writable` porque en el contrato real (ADR-015) **la PK
   también es INOUT** en `consultar` (tu fixture la declaraba `IN`). Llamar
   `CALL producto_consultar(102, v_nombre, v_precio)` con un literal en la
   posición de la PK falla solo cuando el `CALL` se emite **desde dentro de
   otro bloque PL/pgSQL**; necesita una variable en las tres posiciones
   (`CALL producto_consultar(v_id, v_nombre, v_precio)`), confirmado que
   funciona así. Un `CALL` directo de cliente (psql top-level, psycopg) no
   tiene esta restricción. Detalle completo en `CONTRACTS.md` §3.2 (READ).

## Notas compartidas

- Fecha de entrega (ADR-014): **CONFIRMADA — domingo 4 de octubre de 2026.**
- `CONTRACTS.md` fue actualizado por Joyce el 2026-10-01 con la API real de la
  extensión (§3-4). Ya no es una propuesta: es el contrato vigente.
- Fase A: se adoptaron ADR-007 (naming oficial §4.10) y ADR-015 (READ por PK vía INOUT);
  ADR-011 ADOPTADA 01-10 (INVOKER + owner `crud_admin`, verificada contra reales
  02-10: T3 40/40, discovery 18/0/18/0). Todo documentado en `DECISIONS.md`.
- Harness verificable por Joyce/Armando: `tests/README.md` + scripts SQL puros,
  probados en PostgreSQL 18 (matriz 7/7, negativas 11/11, demo E2E OK con fixtures).
