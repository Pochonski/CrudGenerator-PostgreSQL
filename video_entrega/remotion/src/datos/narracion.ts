// Guion de la narración: un audio por escena, en el mismo orden que VideoDemo.
// El texto está escrito para ser leído en voz alta: nombres técnicos en forma
// pronunciable ("crud generator", "Postgres") y códigos SQLSTATE evitados o
// dichos con palabras.

export type Narracion = {
  readonly id: string;
  readonly archivo: string; // relativo a public/
  readonly texto: string;
};

export const NARRACION: readonly Narracion[] = [
  {
    id: 'portada',
    archivo: 'voz/voz_portada.mp3',
    texto: 'Generador automático de procedimientos CRUD para Postgres. Proyecto de Bases de Datos Dos del TEC, desarrollado por Armando, Joyce y Joseph.',
  },
  {
    id: 'arquitectura',
    archivo: 'voz/voz_arquitectura.mp3',
    texto: 'La solución tiene tres piezas. Una aplicación en Python, que sirve de interfaz y orquesta el proceso. Una extensión de Postgres, que lee los catálogos del sistema para entender cada tabla y genera los procedimientos. Y los roles de la base de datos, que reciben los permisos con GRANT y REVOKE. La lógica de generación vive en la base de datos, no en Python.',
  },
  {
    id: 'paso_1',
    archivo: 'voz/voz_paso_1.mp3',
    texto: 'Paso uno: instalamos la extensión con CREATE EXTENSION. Queda registrada como crud generator, versión uno punto cero, en su propio esquema, y le damos al rol administrativo permiso para usarla.',
  },
  {
    id: 'paso_2_3',
    archivo: 'voz/voz_paso_2_3.mp3',
    texto: 'Pasos dos y tres: desde la aplicación Python nos conectamos a la base de datos. Internamente, la aplicación asume el rol administrativo y, antes de permitir generar nada, verifica que la extensión esté instalada, con su versión, su esquema y el permiso de uso.',
  },
  {
    id: 'paso_4_5',
    archivo: 'voz/voz_paso_4_5.mp3',
    texto: 'Pasos cuatro y cinco: los esquemas y las tablas no están escritos en el código; se leen del catálogo. Elegimos el esquema lab, la tabla producto y las cuatro operaciones: insertar, consultar, actualizar y eliminar.',
  },
  {
    id: 'paso_6',
    archivo: 'voz/voz_paso_6.mp3',
    texto: 'Paso seis: la extensión analiza la estructura real de producto, con sus tipos, su clave primaria y sus restricciones, y genera los cuatro procedimientos. Los cuatro se crean con éxito, y a cada uno se le quita el permiso de ejecución público.',
  },
  {
    id: 'paso_6_especiales',
    archivo: 'voz/voz_paso_6_especiales.mp3',
    texto: 'La misma extensión resuelve estructuras más complejas. En detalle de factura detecta una clave primaria compuesta por dos columnas. En ticket detecta una columna identity y valores por defecto, que dejan de ser parámetros obligatorios al insertar.',
  },
  {
    id: 'paso_7',
    archivo: 'voz/voz_paso_7.mp3',
    texto: 'Paso siete: los procedimientos generados son objetos reales de Postgres. Insertamos y consultamos productos, usamos la clave compuesta de detalle de factura, e insertamos tickets sin indicar el identificador: la base de datos lo genera sola, junto con el código por defecto.',
  },
  {
    id: 'paso_8_privilegios',
    archivo: 'voz/voz_paso_8_privilegios.mp3',
    texto: 'Paso ocho: asignamos privilegios desde la aplicación. Para cada operación elegimos qué roles la pueden usar. El administrador recibe todo; el supervisor, todo menos eliminar; y el vendedor, solo insertar y consultar. Cada sí es un GRANT real, y cada no, un REVOKE.',
  },
  {
    id: 'paso_8_verificacion',
    archivo: 'voz/voz_paso_8_verificacion.mp3',
    texto: 'Después, la aplicación verifica la matriz: ejecuta cada procedimiento con cada rol y compara lo que pasa con lo esperado. Las doce combinaciones coinciden.',
  },
  {
    id: 'paso_9',
    archivo: 'voz/voz_paso_9.mp3',
    texto: 'Paso nueve: validamos con distintos usuarios. El vendedor puede consultar, pero cuando intenta actualizar, Postgres le niega el permiso. El supervisor sí puede actualizar, pero no eliminar. Finalmente, el administrador elimina el registro, y la consulta posterior confirma que ya no existe.',
  },
  {
    id: 'paso_10_creacion',
    archivo: 'voz/voz_paso_10_creacion.mp3',
    texto: 'Paso diez: creamos una tabla nueva, que no existía mientras desarrollábamos el proyecto. No cambiamos ni una línea de Python ni de la extensión.',
  },
  {
    id: 'paso_10_generacion',
    archivo: 'voz/voz_paso_10_generacion.mp3',
    texto: 'La aplicación la encuentra de inmediato en el catálogo. La extensión analiza su estructura, genera sus cuatro procedimientos, y le asignamos permisos: todo para el administrador, y solo insertar para el vendedor.',
  },
  {
    id: 'paso_10_uso',
    archivo: 'voz/voz_paso_10_uso.mp3',
    texto: 'Sus procedimientos funcionan igual que los demás. El insertar solo pide dos valores, porque la fecha la completa el valor por defecto. Y como el vendedor no tiene permiso de consulta, la base de datos se lo niega.',
  },
  {
    id: 'pruebas',
    archivo: 'voz/voz_pruebas.mp3',
    texto: 'Todo esto está respaldado por pruebas automáticas: trescientas once pruebas unitarias en Python y ciento cincuenta y tres verificaciones de seguridad en SQL, sin ningún fallo.',
  },
  {
    id: 'decision_1',
    archivo: 'voz/voz_decision_1.mp3',
    texto: 'Primera decisión técnica: los procedimientos se ejecutan como security invoker. Cada rol necesita permiso de ejecución y, además, permiso sobre la tabla. Con security definer correrían con los privilegios del dueño; lo comprobamos con un experimento y lo descartamos.',
  },
  {
    id: 'decision_2',
    archivo: 'voz/voz_decision_2.mp3',
    texto: 'Segunda: Postgres le da permiso de ejecución público a todo procedimiento nuevo. La extensión lo revoca en ese mismo momento, para que solo la matriz de privilegios decida quién ejecuta.',
  },
  {
    id: 'decision_3',
    archivo: 'voz/voz_decision_3.mp3',
    texto: 'Tercera: el SQL dinámico nunca concatena valores. Identificadores y valores se escapan con las funciones de Postgres, y los parámetros se nombran por posición, así funcionan incluso columnas con espacios o con palabras reservadas.',
  },
  {
    id: 'decision_4',
    archivo: 'voz/voz_decision_4.mp3',
    texto: 'Cuarta: el insertar respeta las columnas generadas. Las columnas identity se omiten, y las que tienen valor por defecto son opcionales: si llegan vacías, Postgres aplica su propio valor.',
  },
  {
    id: 'decision_5',
    archivo: 'voz/voz_decision_5.mp3',
    texto: 'Quinta: la regeneración es controlada. Si un procedimiento ya existe, se informa un conflicto y solo se reemplaza si se pide de forma explícita. Y la consulta busca por la clave primaria completa; si no encuentra la fila, responde con un error claro.',
  },
  {
    id: 'cierre',
    archivo: 'voz/voz_cierre.mp3',
    texto: 'Una sola solución que funciona con cualquier tabla: una extensión de Postgres, una aplicación en Python y privilegios reales por rol. Gracias por su atención.',
  },
];
