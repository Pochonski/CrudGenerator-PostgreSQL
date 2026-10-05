import type React from 'react';
import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig, type InteractivitySchema} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {COLOR, FUENTE} from '../tema.ts';

type DecisionProps = {
  readonly numero: string;
  readonly titulo: string;
  readonly texto: string;
  readonly codigo: string;
  readonly voz: string; // relativo a public/
  readonly style?: React.CSSProperties;
};

// Un criterio de diseño: numeral serif grande, explicación y fragmento de código.
const DecisionInner: React.FC<DecisionProps> = ({numero, titulo, texto, codigo, voz, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <Interactive.Div name="Criterio de diseño" style={{position: 'absolute', inset: 0, ...style}}>
      <Fondo>
        <Audio name="Voz" src={staticFile(voz)} premountFor={fps} />
        <RielProgreso name="Riel" actual="criterios" />
        <EncabezadoPaso name="Encabezado" etiqueta="Criterios de diseño" titulo="Decisiones que sostienen la seguridad" subtitulo="y la generalidad" />
        <div
          style={{
            position: 'absolute', left: 340, top: 300, width: 300, fontFamily: FUENTE.serif, fontSize: 220, lineHeight: 1, color: COLOR.azul,
            opacity: interpolate(frame, [4, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          }}
        >
          {numero}
        </div>
        <div style={{position: 'absolute', left: 700, top: 310, width: 1160}}>
          <div
            style={{
              fontFamily: FUENTE.serif, fontSize: 60, lineHeight: 1.12,
              opacity: interpolate(frame, [8, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
              translate: interpolate(frame, [8, 22], ['0px 18px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
            }}
          >
            {titulo}
          </div>
          <div
            style={{
              fontSize: 32, color: COLOR.tinta, marginTop: 30, lineHeight: 1.5,
              opacity: interpolate(frame, [20, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}
          >
            {texto}
          </div>
          <div
            style={{
              marginTop: 40, fontFamily: FUENTE.mono, fontSize: 26, background: COLOR.codigoFondo, borderRadius: 6, padding: '20px 26px', color: COLOR.tinta,
              opacity: interpolate(frame, [32, 46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}
          >
            {codigo}
          </div>
        </div>
      </Fondo>
    </Interactive.Div>
  );
};

const decisionSchema = {
  numero: {type: 'text-content', default: '01', description: 'Numeral'},
  titulo: {type: 'text-content', default: '', description: 'Título'},
  texto: {type: 'text-content', default: '', description: 'Explicación'},
  codigo: {type: 'text-content', default: '', description: 'Fragmento de código'},
} as const satisfies InteractivitySchema;

export const Decision = Interactive.withSchema({
  Component: DecisionInner,
  componentName: '<Decision>',
  schema: decisionSchema,
  wrapInSequence: true,
});
