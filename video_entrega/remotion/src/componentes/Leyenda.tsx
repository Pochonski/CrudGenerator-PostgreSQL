import type React from 'react';
import {Easing, Interactive, interpolate, useCurrentFrame, type InteractivitySchema} from 'remotion';

type LeyendaProps = {
  readonly children: string;
  readonly color: string;
  readonly style?: React.CSSProperties;
};

// Pastilla con la idea clave de la escena (el video no tiene narración).
const LeyendaInner: React.FC<LeyendaProps> = ({children, color, style}) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Leyenda"
      style={{
        position: 'absolute',
        left: '50%',
        bottom: 34,
        padding: '12px 34px',
        borderRadius: 40,
        background: color,
        color: '#06182a',
        fontWeight: 700,
        fontSize: 30,
        whiteSpace: 'nowrap',
        boxShadow: '0 10px 30px #0006',
        opacity: interpolate(frame, [0, 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        translate: interpolate(frame, [0, 15], ['-50% 24px', '-50% 0px'], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        ...style,
      }}
    >
      {children}
    </Interactive.Div>
  );
};

const leyendaSchema = {
  children: {type: 'text-content', default: '', description: 'Texto'},
  color: {type: 'color', default: '#3ddc84', description: 'Color de fondo'},
} as const satisfies InteractivitySchema;

export const Leyenda = Interactive.withSchema({
  Component: LeyendaInner,
  componentName: '<Leyenda>',
  schema: leyendaSchema,
  wrapInSequence: true,
});
