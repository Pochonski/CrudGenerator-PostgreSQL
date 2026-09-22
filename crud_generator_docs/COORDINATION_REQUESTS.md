# Coordination Requests — Seguridad + Integración + Pruebas (Joseph)

Documento de Fase 0 para Joyce y Armando. Cada solicitud indica qué necesitamos,
por qué, qué componente afecta, qué decisión está pendiente, alternativas
evaluadas y si bloquea o solo requiere coordinación. Ninguna decisión listada
aquí se asume aceptada por Joyce o Armando.

---

## Joyce — Extensión PostgreSQL

### CR-JOYCE-001 — Diseño de READ
Estado: **BLOQUEADO**

Necesitamos definir:
- Firma exacta del procedure de lectura por tabla (nombres, nº/tipos de parámetros).
- Criterio de consulta (por PK completa / PK parcial / filtros).
- Cómo devuelve filas un `PROCEDURE` llamado con `CALL` (INOUT, OUT, refcursor,
  tabla temporal, otra vía aceptada por el docente).
- Comportamiento con tablas con PK, con PK compuesta y sin PK.

Por qué afecta nuestra área:
- Sin READ ejecutable no podemos dar `GRANT EXECUTE` real ni probar la columna
  READ de la matriz vendedor/supervisor/administrador.
- La demo exige "usuario autorizado lee / no autorizado es rechazado".

Información que necesitamos de Joyce:
- Propuesta de firma + ejemplo concreto sobre `lab.producto` y `lab.detalle_factura`.
- Confirmación del docente de que la vía elegida cuenta como "procedimiento".

Propuesta/alternativas que estamos evaluando (sin adoptar):
- READ por PK vía INOUT (una fila) como mínimo demostrable — usado solo en fixture.
- Refcursor OUT para multi-fila.
- Escalar a `FUNCTION` para lectura si el docente lo acepta (implicaría revisar ADR-003).

### CR-JOYCE-002 — Naming, esquema y firmas de procedures generados
Estado: **BLOQUEADO**

Necesitamos definir:
- Convención final (ADR-007: `<tabla>_<operacion>` vs verbos español del ejemplo).
- Esquema destino de los procedures generados.
- Firmas completas INSERT/UPDATE/DELETE (orden de params, tratamiento de
  DEFAULT/identity, PK compuesta como N params).
- Regla anti-colisión (overloads, nombres con mayúsculas/símbolos).

Por qué afecta nuestra área:
- Cada `GRANT EXECUTE ON PROCEDURE ... (tipos exactos)` depende de la firma.
  Sin firmas congeladas no podemos escribir la capa de privilegios definitiva.

Información que necesitamos de Joyce:
- Tabla de ejemplo: esquema + 4 nombres + 4 firmas para una tabla PK simple y una
  PK compuesta.

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
Estado: **REQUIERE COORDINACIÓN** (condiciona ADR-011)

Necesitamos definir:
- Rol owner de los procedures generados.
- Si la extensión emitirá `SECURITY INVOKER` / `SECURITY DEFINER` explícito o
  heredará el default, y si fijará `SET search_path`.

Por qué afecta nuestra área:
- Con DEFINER, nuestra estrategia GRANT cambia por completo (solo EXECUTE +
  `REVOKE` de tablas). Con INVOKER se exige doble llave EXECUTE+tabla.
- Nuestro experimento `tests/security/02_invoker_vs_definer.sql` demuestra la
  diferencia; la decisión final debe ser conjunta (ADR-011 sigue pendiente).

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
- Harness verificable por Joyce/Armando: `tests/README.md` + scripts SQL puros,
  probados en PostgreSQL 18 (matriz 7/7, negativas 11/11, demo E2E OK con fixtures).
