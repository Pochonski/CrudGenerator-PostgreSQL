# Coordination Requests — Seguridad + Integración + Pruebas (Joseph)

Documento de Fase 0 para Joyce y Armando. Cada solicitud indica qué necesitamos,
por qué, qué componente afecta, qué decisión está pendiente, alternativas
evaluadas y si bloquea o solo requiere coordinación. Ninguna decisión listada
aquí se asume aceptada por Joyce o Armando.

---

## Joyce — Extensión PostgreSQL

### CR-JOYCE-001 — Diseño de READ
Estado: **DECISIÓN EN CAMINO** — propuesta formal lista (ADR-015), falta que Joyce la confirme/ajuste

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
Estado: **PARCIALMENTE RESUELTO** — naming adoptado; pendiente firmas/esquema/anti-colisión

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
Estado: **REQUIERE COORDINACIÓN** (no bloquea el lab, sí la matriz final)

Necesitamos definir:
- ¿Se generan solo INSERT/READ y UPDATE/DELETE se reportan "no aplicables"?
- ¿Qué código/resultado devuelve la extensión en ese caso?

Por qué afecta nuestra área:
- Define las pruebas NEG-05 y el contrato de errores "operación no aplicable".

Alternativas que proponemos al equipo:
- Generar lo aplicable + resultado estructurado `not_applicable` por operación.

### CR-JOYCE-004 — Procedures existentes
Estado: **REQUIERE COORDINACIÓN**

Necesitamos definir:
- ¿Error / reemplazo / drop+create / tratamiento según firma?

Por qué afecta nuestra área:
- Define la prueba NEG-06 y evita que la demo falle por re-ejecución.

Alternativa propuesta:
- Por defecto error explícito `conflicto con procedimiento existente`; reemplazo
  solo con flag explícito del administrador.

### CR-JOYCE-005 — Owner y cláusula SECURITY que emitirá la extensión
Estado: **REQUIERE COORDINACIÓN** (condiciona ADR-011 que ya tiene recomendación formal)

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
Estado: **REQUIERE COORDINACIÓN**

Necesitamos definir:
- ¿Python ejecuta `GRANT/REVOKE` directo con credencial alta, o llama a una
  función privilegiada de la extensión?

Por qué afecta nuestra área:
- Define qué rol usa Python, qué auditar y el principio de mínimo privilegio
  (ningún rol de negocio genera; solo `crud_admin`-equivalente aplica grants).

Información que necesitamos de Armando:
- Rol/credencial que usará Python y punto del flujo donde aplica privilegios.

### CR-ARMANDO-002 — Resultado de `generate_crud`
Estado: **REQUIERE COORDINACIÓN**

Necesitamos definir:
- Formato que Python mostrará para: éxito, no aplicable, validación, inexistente,
  conflicto, permiso insuficiente, error interno (CONTRACTS §3.3).

Por qué afecta nuestra área:
- Nuestras pruebas de integración verifican que Python no oculte errores de PG
  (SQLSTATE visibles: 42501, 42883, 42P01, etc.).

### CR-ARMANDO-003 — Validación real de permisos desde Python
Estado: **REQUIERE COORDINACIÓN**

Necesitamos definir:
- ¿Python verificará permisos con `SET ROLE` + `CALL` real (exigido para la demo),
  o solo consultando `information_schema` / `has_*_privilege`?

Por qué afecta nuestra área:
- Solo la ejecución real demuestra "operación permitida vs rechazada" ante el
  profesor. Nuestro `tests/integration/02_demo_script.sql` es la referencia del
  flujo esperado; Python debe poder reproducirlo.

---

## Notas compartidas

- Fecha de entrega (ADR-014): **PENDIENTE DE CONFIRMACIÓN CON DOCENTE**
  (2021 vs 2026 en el enunciado). No asumimos ninguna.
- `CONTRACTS.md` no se modificó en Fase 0: no inventamos firmas de Joyce.
- Fase A: se adoptaron ADR-007 (naming oficial §4.10) y ADR-015 (READ por PK vía INOUT);
  ADR-011 tiene recomendación formal (INVOKER). Todo documentado en `DECISIONS.md`
  como especificación para implementación de Joyce/Armando.
- Harness verificable por Joyce/Armando: `tests/README.md` + scripts SQL puros,
  probados en PostgreSQL 18 (matriz 7/7, negativas 11/11, demo E2E OK con fixtures).
