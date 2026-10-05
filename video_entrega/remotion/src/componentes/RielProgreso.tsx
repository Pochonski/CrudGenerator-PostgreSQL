import type React from 'react';
import {Interactive, type InteractivitySchema} from 'remotion';
import {COLOR, FUENTE, LAYOUT} from '../tema.ts';

// Índice lateral: dónde estamos dentro del recorrido del enunciado.
const ETAPAS = [
  {id: 'intro', n: '·', texto: 'Arquitectura'},
  {id: '1', n: '1', texto: 'Instalación'},
  {id: '2-3', n: '2·3', texto: 'Conexión'},
  {id: '4-5', n: '4·5', texto: 'Selección'},
  {id: '6', n: '6', texto: 'Generación'},
  {id: '7', n: '7', texto: 'Ejecución'},
  {id: '8', n: '8', texto: 'Privilegios'},
  {id: '9', n: '9', texto: 'Validación'},
  {id: '10', n: '10', texto: 'Tabla nueva'},
  {id: 'pruebas', n: '✓', texto: 'Pruebas'},
  {id: 'criterios', n: '§', texto: 'Criterios'},
] as const;

type RielProgresoProps = {
  readonly actual: string;
  readonly style?: React.CSSProperties;
};

const RielProgresoInner: React.FC<RielProgresoProps> = ({actual, style}) => {
  const indice = ETAPAS.findIndex((e) => e.id === actual);

  return (
    <Interactive.Div
      name="Riel de progreso"
      style={{
        position: 'absolute', left: LAYOUT.rielX, top: 110, width: LAYOUT.rielAncho, bottom: 60,
        borderRight: `1px solid ${COLOR.linea}`, display: 'flex', flexDirection: 'column', gap: 22, paddingTop: 10,
        ...style,
      }}
    >
      <div style={{fontSize: 16, letterSpacing: 3, color: COLOR.gris, textTransform: 'uppercase', marginBottom: 6}}>Recorrido</div>
      {ETAPAS.map((e, i) => {
        const esActual = i === indice;
        const pasado = i < indice;
        return (
          <div key={e.id} style={{display: 'flex', alignItems: 'center', gap: 14, color: esActual ? COLOR.azul : pasado ? COLOR.tinta : COLOR.grisClaro}}>
            <span
              style={{
                width: 14, height: 14, borderRadius: 7, flexShrink: 0,
                border: `2px solid ${esActual ? COLOR.azul : pasado ? COLOR.tinta : COLOR.grisClaro}`,
                background: esActual ? COLOR.azul : pasado ? COLOR.tinta : 'transparent',
              }}
            />
            <span style={{fontFamily: FUENTE.serif, fontSize: 22, width: 38}}>{e.n}</span>
            <span style={{fontSize: 21, fontWeight: esActual ? 700 : 400}}>{e.texto}</span>
          </div>
        );
      })}
    </Interactive.Div>
  );
};

const rielSchema = {
  actual: {type: 'text-content', default: '1', description: 'Etapa actual (intro, 1, 2-3, …, pruebas, criterios)'},
} as const satisfies InteractivitySchema;

export const RielProgreso = Interactive.withSchema({
  Component: RielProgresoInner,
  componentName: '<RielProgreso>',
  schema: rielSchema,
  wrapInSequence: true,
});
