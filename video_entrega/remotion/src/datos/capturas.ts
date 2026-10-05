// Salidas copiadas literalmente de una corrida real de crudgen y psql contra
// PostgreSQL 18 local (base devdb, esquema lab) del 04-10-2026.
// Unica adaptacion: los errores de psql se muestran sin el prefijo
// "psql:archivo.sql:N:" porque en pantalla se presentan como sesion interactiva.

import {PROMPT_DB_CONT, PROMPT_PS, type Linea, type Paso} from './linea-de-tiempo.ts';

const generacion = (tabla: string): Linea[] =>
  (['INSERT', 'READ', 'UPDATE', 'DELETE'] as const).flatMap((op, i) => {
    const rutina = tabla + ['_insertar', '_consultar', '_actualizar', '_eliminar'][i];
    return [
      `- ${op}: success`,
      `  rutina: ${rutina}`,
      {t: `  mensaje: Procedure lab.${rutina} creado correctamente (EXECUTE revocado de PUBLIC por defecto).`, cls: 'dim'},
    ];
  });

export const PASO1_INSTALACION: Paso[] = [
  {c: 'CREATE EXTENSION crud_generator;'},
  {o: ['CREATE EXTENSION']},
  {c: 'GRANT USAGE ON SCHEMA crud_generator TO crud_admin;'},
  {o: ['GRANT']},
  {c: "SELECT extname, extversion, extnamespace::regnamespace AS esquema FROM pg_extension WHERE extname = 'crud_generator';"},
  {o: ['    extname     | extversion |    esquema     ', '----------------+------------+----------------', ' crud_generator | 1.0        | crud_generator', '(1 fila)']},
];

export const PASO23_CONEXION: Paso[] = [
  {c: 'crudgen', pr: PROMPT_PS},
  {o: ['CRUD Generator PostgreSQL'], hold: 0.3},
  {p: 'Servidor [localhost]: ', a: ''},
  {p: 'Puerto [5432]: ', a: ''},
  {p: 'Base de datos: ', a: 'devdb'},
  {p: 'Usuario: ', a: 'postgres'},
  {p: 'Contraseña: ', a: '', hold: 0.6},
  {o: ['Conexión exitosa', 'Base de datos: devdb', 'Usuario: postgres', 'Verificando extensión...'], hold: 0.5},
  {o: [{t: "La extensión 'crud_generator' está instalada (versión 1.0, esquema crud_generator) y el usuario actual tiene permiso USAGE sobre su esquema. La verificación de EXECUTE sobre la API pública está pendiente.", cls: 'hl'}]},
];

export const PASO45_SELECCION: Paso[] = [
  {o: ['Seleccionar esquema:', '1. crud_generator', '2. lab', '3. public']},
  {p: 'Esquema [número]: ', a: '2', hold: 0.5},
  {o: ["Seleccionar tablas (ej. 1,3,5 o 'a' para todas):", '1. bitacora', '2. catalogo_especial', '3. detalle_factura', '4. producto', '5. tabla_virgen', '6. ticket']},
  {p: 'Tablas: ', a: '4', hold: 0.5},
  {o: ["Seleccionar operaciones (ej. 1,2 o 'a' para todas):", '1. INSERT', '2. READ', '3. UPDATE', '4. DELETE']},
  {p: 'Operaciones: ', a: 'a', hold: 0.5},
  {o: ['Resumen:', 'Esquema: lab', 'Tablas:', '- producto', 'Operaciones:', '- INSERT', '- READ', '- UPDATE', '- DELETE']},
];

export const PASO6_GENERACION: Paso[] = [
  {o: ['¿Reemplazar procedures existentes? [s/n] (default: n):']},
  {p: 'Reemplazar: ', a: 'n', hold: 0.6},
  {o: ['Estructura de lab.producto:', {t: '- id_producto: integer, PK, NOT NULL', cls: 'hl'}, '- nombre: text, no PK, NOT NULL', '- precio: numeric(10,2), no PK, NOT NULL'], hold: 1.4},
  {o: ['Generación para producto:', ...generacion('producto')]},
];

export const PASO6_ESPECIALES: Paso[] = [
  {p: 'Tablas: ', a: '3,6'},
  {p: 'Operaciones: ', a: 'a'},
  {p: 'Reemplazar: ', a: 'n', hold: 0.6},
  {o: ['Estructura de lab.detalle_factura:', {t: '- id_factura: integer, PK, NOT NULL', cls: 'hly'}, {t: '- id_producto: integer, PK, NOT NULL', cls: 'hly'}, '- cantidad: integer, no PK, NOT NULL'], hold: 1.6},
  {o: ['Generación para detalle_factura:', ...generacion('detalle_factura')], hold: 0.6},
  {skip: true},
  {o: ['Estructura de lab.ticket:', {t: '- id_ticket: integer, PK, NOT NULL, DEFAULT, identity ALWAYS', cls: 'hly'}, {t: "- codigo: text, no PK, NOT NULL, DEFAULT 'SIN-CODIGO'::text", cls: 'hl'}, {t: '- creado_en: timestamp with time zone, no PK, NOT NULL, DEFAULT now()', cls: 'hl'}], hold: 1.6},
  {o: ['Generación para ticket:', ...generacion('ticket')]},
];

export const PASO7_EJECUCION: Paso[] = [
  {c: 'SET ROLE crud_administrador;'}, {o: ['SET'], hold: 0.2},
  {c: "CALL lab.producto_insertar(101, 'Teclado', 25.50);"}, {o: ['CALL'], hold: 0.2},
  {c: "CALL lab.producto_insertar(102, 'Mouse', 12.00);"}, {o: ['CALL'], hold: 0.2},
  {c: 'CALL lab.producto_consultar(101);'}, {o: [' p_1 |   p_2   |  p_3  ', '-----+---------+-------', ' 101 | Teclado | 25.50', '(1 fila)'], hold: 0.9},
  {c: 'CALL lab.detalle_factura_insertar(10, 102, 3);'}, {o: ['CALL'], hold: 0.2},
  {c: 'CALL lab.detalle_factura_consultar(10, 102);'}, {o: [' p_1 | p_2 | p_3 ', '-----+-----+-----', '  10 | 102 |   3', '(1 fila)'], hold: 0.9},
  {c: 'CALL lab.ticket_insertar();'}, {o: ['CALL'], hold: 0.2},
  {c: "CALL lab.ticket_insertar('T-002');"}, {o: ['CALL'], hold: 0.2},
  {c: 'SELECT id_ticket, codigo FROM lab.ticket ORDER BY id_ticket;'},
  {o: [' id_ticket |   codigo   ', '-----------+------------', '         2 | SIN-CODIGO', '         3 | T-002', '(2 filas)']},
];

const ROLES3 = ['crud_administrador', 'crud_supervisor', 'crud_vendedor'] as const;
// crudgen pregunta la matriz POR OPERACION: INSERT para los tres roles, luego READ...
const MATRIZ = [['INSERT', 's', 's', 's'], ['READ', 's', 's', 's'], ['UPDATE', 's', 's', 'n'], ['DELETE', 's', 'n', 'n']] as const;

export const PASO8_PRIVILEGIOS: Paso[] = [
  {o: ["Seleccionar roles (ej. 1,3 o 'a' para todos):", '1. crud_admin [NOLOGIN]', '2. crud_administrador [NOLOGIN]', '3. crud_supervisor [NOLOGIN]', '4. crud_vendedor [NOLOGIN]', '5. postgres (superusuario)',
    {t: '  Aviso: es superusuario; las comprobaciones normales de privilegios no lo restringen efectivamente y otorgarle EXECUTE es innecesario (ya puede hacerlo todo).', cls: 'dim'}]},
  {p: 'Roles: ', a: '2,3,4', hold: 0.5},
  ...MATRIZ.flatMap(([op, ...v]) => v.flatMap((a, i): Paso[] => [{o: ['Rol: ' + ROLES3[i]], hold: 0.05}, {p: `Permitir ${op}? [s/n]: `, a, hold: 0.12}])),
  {w: 0.4},
  {o: ['Privilegios aplicados para producto:',
    '- crud_administrador INSERT: habilitado (privilegios directos aplicados) (producto_insertar)',
    '- crud_administrador READ: habilitado (privilegios directos aplicados) (producto_consultar)',
    '- crud_administrador UPDATE: habilitado (privilegios directos aplicados) (producto_actualizar)',
    '- crud_administrador DELETE: habilitado (privilegios directos aplicados) (producto_eliminar)',
    '- crud_supervisor INSERT: habilitado (privilegios directos aplicados) (producto_insertar)',
    '- crud_supervisor READ: habilitado (privilegios directos aplicados) (producto_consultar)',
    '- crud_supervisor UPDATE: habilitado (privilegios directos aplicados) (producto_actualizar)',
    '- crud_supervisor DELETE: deshabilitado (privilegios directos revocados) (producto_eliminar)',
    '- crud_vendedor INSERT: habilitado (privilegios directos aplicados) (producto_insertar)',
    '- crud_vendedor READ: habilitado (privilegios directos aplicados) (producto_consultar)',
    '- crud_vendedor UPDATE: deshabilitado (privilegios directos revocados) (producto_actualizar)',
    '- crud_vendedor DELETE: deshabilitado (privilegios directos revocados) (producto_eliminar)']},
];

export const PASO8_VERIFICACION: Paso[] = [
  {o: ['Verificar permisos ejecutando cada procedure generado como cada rol (con 42501 = denegado) [s/n] (default: s):']},
  {p: 'Verificar: ', a: 's', hold: 0.5},
  {o: ['Verificación de permisos (matriz vs PostgreSQL):',
    '- OK crud_administrador INSERT: matriz=permitido, no denegado (error 23502).',
    '- OK crud_administrador READ: matriz=permitido, no denegado (error P0002).',
    '- OK crud_administrador UPDATE: matriz=permitido, no denegado (error P0002).',
    '- OK crud_administrador DELETE: matriz=permitido, no denegado (error P0002).',
    '- OK crud_supervisor INSERT: matriz=permitido, no denegado (error 23502).',
    '- OK crud_supervisor READ: matriz=permitido, no denegado (error P0002).',
    '- OK crud_supervisor UPDATE: matriz=permitido, no denegado (error P0002).',
    '- OK crud_supervisor DELETE: matriz=denegado, denegado (42501).',
    '- OK crud_vendedor INSERT: matriz=permitido, no denegado (error 23502).',
    '- OK crud_vendedor READ: matriz=permitido, no denegado (error P0002).',
    '- OK crud_vendedor UPDATE: matriz=denegado, denegado (42501).',
    '- OK crud_vendedor DELETE: matriz=denegado, denegado (42501).'], hold: 1},
  {o: ['Ejecutar una operación CRUD con valores (vacío = NULL) [s/n] (default: n):']},
  {p: 'Ejecutar: ', a: 'n'},
];

export const PASO9_VALIDACION: Paso[] = [
  {c: 'SET ROLE crud_vendedor;'}, {o: ['SET'], hold: 0.2},
  {c: 'CALL lab.producto_consultar(101);'}, {o: [' p_1 |   p_2   |  p_3  ', '-----+---------+-------', ' 101 | Teclado | 25.50', '(1 fila)'], hold: 0.6},
  {c: "CALL lab.producto_actualizar(101, 'Teclado Gamer', 30.00);"}, {o: ['ERROR:  permiso denegado al procedimiento producto_actualizar'], hold: 1.2},
  {c: 'SET ROLE crud_supervisor;'}, {o: ['SET'], hold: 0.2},
  {c: "CALL lab.producto_actualizar(101, 'Teclado Gamer', 30.00);"}, {o: ['CALL'], hold: 0.3},
  {c: 'CALL lab.producto_consultar(101);'}, {o: [' p_1 |      p_2      |  p_3  ', '-----+---------------+-------', ' 101 | Teclado Gamer | 30.00', '(1 fila)'], hold: 0.6},
  {c: 'CALL lab.producto_eliminar(101);'}, {o: ['ERROR:  permiso denegado al procedimiento producto_eliminar'], hold: 1.2},
  {c: 'SET ROLE crud_administrador;'}, {o: ['SET'], hold: 0.2},
  {c: 'CALL lab.producto_eliminar(101);'}, {o: ['CALL'], hold: 0.3},
  {c: 'CALL lab.producto_consultar(101);'},
  {o: ['ERROR:  No existe fila en lab.producto con la clave primaria indicada', 'CONTEXTO:  función PL/pgSQL producto_consultar(integer,text,numeric) en la línea 5 en RAISE']},
];

export const PASO10_CREACION: Paso[] = [
  {c: 'SET ROLE crud_admin;'}, {o: ['SET'], hold: 0.2},
  {c: 'CREATE TABLE lab.tabla_video_nueva ('},
  {c: '  id integer PRIMARY KEY,', pr: PROMPT_DB_CONT},
  {c: '  descripcion text NOT NULL,', pr: PROMPT_DB_CONT},
  {c: '  creado_en timestamptz NOT NULL DEFAULT now()', pr: PROMPT_DB_CONT},
  {c: ');', pr: PROMPT_DB_CONT},
  {o: ['CREATE TABLE'], hold: 0.2},
  {c: 'RESET ROLE;'}, {o: ['RESET']},
];

export const PASO10_GENERACION: Paso[] = [
  {o: ["Seleccionar tablas (ej. 1,3,5 o 'a' para todas):", '1. bitacora', '2. catalogo_especial', '3. detalle_factura', '4. producto', {t: '5. tabla_video_nueva', cls: 'hly'}, '6. tabla_virgen', '7. ticket'], hold: 1.2},
  {p: 'Tablas: ', a: '5'},
  {p: 'Operaciones: ', a: 'a'},
  {p: 'Reemplazar: ', a: 'n', hold: 0.5},
  {o: ['Estructura de lab.tabla_video_nueva:', '- id: integer, PK, NOT NULL', '- descripcion: text, no PK, NOT NULL', {t: '- creado_en: timestamp with time zone, no PK, NOT NULL, DEFAULT now()', cls: 'hl'}], hold: 1.2},
  {o: ['Generación para tabla_video_nueva:', ...generacion('tabla_video_nueva')], hold: 0.6},
  {p: 'Roles: ', a: '2,4'},
  {skip: true},
  {o: ['Privilegios aplicados para tabla_video_nueva:',
    '- crud_administrador INSERT: habilitado (privilegios directos aplicados) (tabla_video_nueva_insertar)',
    '- crud_administrador READ: habilitado (privilegios directos aplicados) (tabla_video_nueva_consultar)',
    '- crud_administrador UPDATE: habilitado (privilegios directos aplicados) (tabla_video_nueva_actualizar)',
    '- crud_administrador DELETE: habilitado (privilegios directos aplicados) (tabla_video_nueva_eliminar)',
    '- crud_vendedor INSERT: habilitado (privilegios directos aplicados) (tabla_video_nueva_insertar)',
    '- crud_vendedor READ: deshabilitado (privilegios directos revocados) (tabla_video_nueva_consultar)',
    '- crud_vendedor UPDATE: deshabilitado (privilegios directos revocados) (tabla_video_nueva_actualizar)',
    '- crud_vendedor DELETE: deshabilitado (privilegios directos revocados) (tabla_video_nueva_eliminar)']},
];

export const PASO10_USO: Paso[] = [
  {c: 'SET ROLE crud_administrador;'}, {o: ['SET'], hold: 0.2},
  {c: "CALL lab.tabla_video_nueva_insertar(1, 'Creada después del desarrollo');"}, {o: ['CALL'], hold: 0.3},
  {c: 'CALL lab.tabla_video_nueva_consultar(1);'},
  {o: [' p_1 |              p_2              |              p_3              ', '-----+-------------------------------+-------------------------------', '   1 | Creada después del desarrollo | 2026-10-04 21:29:52.940034-06', '(1 fila)'], hold: 1},
  {c: 'SET ROLE crud_vendedor;'}, {o: ['SET'], hold: 0.2},
  {c: 'CALL lab.tabla_video_nueva_consultar(1);'},
  {o: ['ERROR:  permiso denegado al procedimiento tabla_video_nueva_consultar']},
];

export const PRUEBAS_PYTEST: Paso[] = [
  {c: 'python -m pytest app/tests -q', pr: PROMPT_PS},
  {o: ['.......s................................................................ [ 91%]', '............................                                             [100%]', '311 passed, 5 skipped in 0.44s']},
];

export const PRUEBAS_HARNESS: Paso[] = [
  {o: ['MAT-01 OK: vendedor INSERT permitido funciona', 'MAT-02 OK: vendedor UPDATE rechazado con 42501', 'MAT-03 OK: vendedor DELETE rechazado con 42501',
    'MAT-04 OK: supervisor UPDATE permitido funciona', 'MAT-05 OK: supervisor DELETE rechazado con 42501', 'MAT-06 OK: administrador DELETE permitido funciona',
    'MAT-C1 OK: vendedor INSERT PK compuesta permitido funciona', 'MAT-C3 OK: vendedor UPDATE rechazado con 42501', 'MAT-C5 OK: supervisor UPDATE permitido funciona (cantidad=7)',
    {t: '  ⋮', cls: 'dim'}, {t: 'RESUMEN FASE 2: 153 OK, 0 FAIL/FALLO, 0 PSQL-EXIT!=0', cls: 'hl'}]},
];
