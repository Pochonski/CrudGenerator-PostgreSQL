// Identidad visual "claro editorial": papel, tinta y un único acento azul
// PostgreSQL. Los estados (éxito / denegado) usan verde y naranja apagados.

export const COLOR = {
  papel: '#F6F3EC',
  blanco: '#FFFFFF',
  tinta: '#1C1B19',
  gris: '#6B6760',
  grisClaro: '#A8A39A',
  linea: '#D9D3C7',
  codigoFondo: '#EEEAE1',
  azul: '#336791',
  exito: '#2E7D4F',
  error: '#C2410C',
  resaltado: '#FFF1B8',
} as const;

export const FUENTE = {
  serif: 'Cambria, Georgia, "Times New Roman", serif',
  sans: '"Segoe UI", system-ui, sans-serif',
  mono: '"Cascadia Mono", "Cascadia Code", Consolas, monospace',
} as const;

// Geometría común: riel de progreso a la izquierda, contenido a la derecha.
export const LAYOUT = {
  rielX: 60,
  rielAncho: 230,
  contenidoX: 340,
  contenidoAncho: 1520,
  mastheadAlto: 56,
} as const;
