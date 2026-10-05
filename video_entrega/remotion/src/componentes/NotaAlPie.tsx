import type React from 'react';
import {Easing, Interactive, interpolate, useCurrentFrame, type InteractivitySchema} from 'remotion';
import {COLOR, LAYOUT} from '../tema.ts';

type NotaAlPieProps = {
  readonly children: string;
  readonly style?: React.CSSProperties;
};

// Nota editorial bajo el contenido: rótulo "Qué pasa" + texto, con una
// línea azul que se dibuja a la izquierda.
const NotaAlPieInner: React.FC<NotaAlPieProps> = ({children, style}) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Nota al pie"
      style={{
        position: 'absolute', left: LAYOUT.contenidoX, bottom: 44, width: LAYOUT.contenidoAncho, display: 'flex',
        alignItems: 'center', gap: 24,
        opacity: interpolate(frame, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        ...style,
      }}
    >
      <div
        style={{
          height: 3, background: COLOR.azul, flexShrink: 0,
          width: interpolate(frame, [0, 20], [0, 70], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      />
      <span style={{fontSize: 18, letterSpacing: 3, textTransform: 'uppercase', color: COLOR.azul, fontWeight: 700, flexShrink: 0}}>Qué pasa</span>
      <span style={{fontSize: 28, color: COLOR.tinta}}>{children}</span>
    </Interactive.Div>
  );
};

const notaSchema = {
  children: {type: 'text-content', default: '', description: 'Texto'},
} as const satisfies InteractivitySchema;

export const NotaAlPie = Interactive.withSchema({
  Component: NotaAlPieInner,
  componentName: '<NotaAlPie>',
  schema: notaSchema,
  wrapInSequence: true,
});
