import type React from 'react';
import {Easing, Interactive, interpolate, useCurrentFrame, type InteractivitySchema} from 'remotion';
import {COLOR, FUENTE, LAYOUT} from '../tema.ts';

type EncabezadoPasoProps = {
  readonly etiqueta: string;
  readonly titulo: string;
  readonly subtitulo: string;
  readonly style?: React.CSSProperties;
};

// Etiqueta en versalitas + título serif + regla que se dibuja.
const EncabezadoPasoInner: React.FC<EncabezadoPasoProps> = ({etiqueta, titulo, subtitulo, style}) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Encabezado"
      style={{
        position: 'absolute', left: LAYOUT.contenidoX, top: 84, width: LAYOUT.contenidoAncho,
        opacity: interpolate(frame, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        ...style,
      }}
    >
      <div style={{fontSize: 20, letterSpacing: 4, textTransform: 'uppercase', color: COLOR.azul, fontWeight: 700}}>{etiqueta}</div>
      <div style={{display: 'flex', alignItems: 'baseline', gap: 28, marginTop: 6}}>
        <span style={{fontFamily: FUENTE.serif, fontSize: 54, color: COLOR.tinta}}>{titulo}</span>
        <span style={{fontSize: 24, color: COLOR.gris, fontStyle: 'italic'}}>{subtitulo}</span>
      </div>
      <div
        style={{
          height: 2, background: COLOR.tinta, marginTop: 14,
          width: interpolate(frame, [4, 30], ['0%', '100%'], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.bezier(0.65, 0, 0.35, 1),
          }),
        }}
      />
    </Interactive.Div>
  );
};

const encabezadoSchema = {
  etiqueta: {type: 'text-content', default: 'Paso 1', description: 'Etiqueta (p. ej. "Paso 6")'},
  titulo: {type: 'text-content', default: '', description: 'Título'},
  subtitulo: {type: 'text-content', default: '', description: 'Subtítulo'},
} as const satisfies InteractivitySchema;

export const EncabezadoPaso = Interactive.withSchema({
  Component: EncabezadoPasoInner,
  componentName: '<EncabezadoPaso>',
  schema: encabezadoSchema,
  wrapInSequence: true,
});
