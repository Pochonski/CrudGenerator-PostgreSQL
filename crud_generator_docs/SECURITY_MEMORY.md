# Memoria — Agente Seguridad, Integración y Pruebas

**Owner:** Joseph  
**Área:** Seguridad + Integración + Pruebas

## Rol

Responsable de seguridad PostgreSQL, roles/privilegios, integración, auditoría de decisiones y pruebas end-to-end.

## Equipo

- **Joseph:** Seguridad + Integración + Pruebas.
- **Joyce:** Extensión PostgreSQL.
- **Armando:** Python + Interfaz.

El owner lidera su área, pero cualquier cambio que afecte arquitectura o contratos debe coordinarse con los otros dos.

## Documentos que debe leer primero

1. `PROJECT_CONTEXT.md`
2. `ARCHITECTURE.md`
3. `CONTRACTS.md`
4. `DECISIONS.md`

## Objetivo técnico

Asegurar que el sistema funcione correctamente con distintos roles y que los privilegios sobre los procedimientos sean reales, verificables y justificables.

## Responsabilidades

- Diseño de roles de prueba.
- GRANT/REVOKE.
- EXECUTE.
- Propietarios.
- SECURITY INVOKER/DEFINER.
- Análisis de search_path cuando corresponda.
- Auditoría de SQL dinámico.
- Casos negativos.
- Pruebas CRUD.
- Integración Python ↔ extensión.
- Integración CRUD ↔ privilegios.
- Guion de demostración.

## Matriz mínima de referencia

| Rol | INSERT | READ | UPDATE | DELETE |
|---|---:|---:|---:|---:|
| vendedor | ✅ | ✅ | ❌ | ❌ |
| supervisor | ✅ | ✅ | ✅ | ❌ |
| administrador | ✅ | ✅ | ✅ | ✅ |

Los nombres son ejemplos iniciales; el equipo puede cambiarlos siempre que conserve tres niveles diferenciados.

## Estado actual

- [ ] Roles definidos
- [ ] Propietarios definidos
- [ ] Estrategia GRANT
- [ ] Estrategia REVOKE
- [ ] EXECUTE validado
- [ ] SECURITY INVOKER/DEFINER analizado
- [ ] Riesgos SQL dinámico revisados
- [ ] PK simple probado
- [ ] PK compuesta probada
- [ ] Autogenerado probado
- [ ] Sin PK probado
- [ ] Procedimiento existente probado
- [ ] Usuario autorizado probado
- [ ] Usuario no autorizado probado
- [ ] Tabla no conocida probada
- [ ] Demo E2E preparada

## Problemas / descubrimientos

- Ninguno registrado todavía.

## Requiere coordinación

Registrar aquí cualquier hallazgo que requiera cambiar la API, arquitectura, privilegios o comportamiento de generación.
