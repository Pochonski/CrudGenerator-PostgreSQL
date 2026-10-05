import type React from 'react';
import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig, type InteractivitySchema} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';

type DecisionProps = {
  readonly titulo: string;
  readonly texto: string;
  readonly codigo: string;
  readonly color: string;
  readonly pagina: string;
  readonly voz: string; // relativo a public/
  readonly style?: React.CSSProperties;
};

const DecisionInner: React.FC<DecisionProps> = ({titulo, texto, codigo, color, pagina, voz, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <Interactive.Div name="Decisión técnica" style={{position: 'absolute', inset: 0, ...style}}>
      <Fondo>
        <Audio name="Voz" src={staticFile(voz)} premountFor={fps} />
        <EncabezadoPaso name="Encabezado" insignia="★" titulo="Decisiones técnicas" subtitulo="Por qué está diseñado así" />
        <div style={{position: 'absolute', left: 140, right: 140, top: 300}}>
          <div
            style={{
              fontSize: 70, fontWeight: 800, lineHeight: 1.1, borderLeft: `10px solid ${color}`, paddingLeft: 34,
              opacity: interpolate(frame, [6, 21], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
              translate: interpolate(frame, [6, 21], ['0px 24px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
            }}
          >
            {titulo}
          </div>
          <div
            style={{
              fontSize: 38, color: '#cdd6ea', margin: '34px 0 0 44px', lineHeight: 1.4,
              opacity: interpolate(frame, [18, 33], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}
          >
            {texto}
          </div>
          <div
            style={{
              display: 'inline-block', margin: '44px 0 0 44px', fontFamily: '"Cascadia Mono", Consolas, monospace', fontSize: 30,
              padding: '18px 28px', border: `2px solid ${color}`, borderRadius: 14, color,
              opacity: interpolate(frame, [33, 48], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}
          >
            {codigo}
          </div>
        </div>
        <div style={{position: 'absolute', right: 70, bottom: 50, color: '#8a96b3', fontSize: 28}}>{pagina}</div>
      </Fondo>
    </Interactive.Div>
  );
};

const decisionSchema = {
  titulo: {type: 'text-content', default: '', description: 'Título'},
  texto: {type: 'text-content', default: '', description: 'Explicación'},
  codigo: {type: 'text-content', default: '', description: 'Fragmento de código'},
  color: {type: 'color', default: '#4ea8ff', description: 'Color de acento'},
  pagina: {type: 'text-content', default: '1 / 5', description: 'Página'},
} as const satisfies InteractivitySchema;

export const Decision = Interactive.withSchema({
  Component: DecisionInner,
  componentName: '<Decision>',
  schema: decisionSchema,
  wrapInSequence: true,
});
