import type React from 'react';
import {Easing, Interactive, interpolate, useCurrentFrame, type InteractivitySchema} from 'remotion';

type EncabezadoPasoProps = {
  readonly insignia: string;
  readonly titulo: string;
  readonly subtitulo: string;
  readonly style?: React.CSSProperties;
};

const EncabezadoPasoInner: React.FC<EncabezadoPasoProps> = ({insignia, titulo, subtitulo, style}) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Encabezado"
      style={{
        position: 'absolute',
        left: 60,
        top: 48,
        display: 'flex',
        alignItems: 'center',
        gap: 26,
        opacity: interpolate(frame, [0, 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        translate: interpolate(frame, [0, 15], ['-30px 0px', '0px 0px'], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        ...style,
      }}
    >
      <div
        style={{
          minWidth: 92, height: 92, padding: '0 18px', borderRadius: 20, display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: 'linear-gradient(135deg, #3aa0ff, #8b6bff)', fontWeight: 800,
          fontSize: 44, color: '#fff', boxShadow: '0 10px 30px #3a7bff44',
          scale: interpolate(frame, [0, 18], [0.6, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.spring({damping: 12}),
            output: 'perceptual-scale',
          }),
        }}
      >
        {insignia}
      </div>
      <div>
        <div style={{fontSize: 56, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.05, color: '#e6ebf5'}}>{titulo}</div>
        <div style={{fontSize: 28, color: '#8a96b3', marginTop: 6}}>{subtitulo}</div>
      </div>
    </Interactive.Div>
  );
};

const encabezadoSchema = {
  insignia: {type: 'text-content', default: '1', description: 'Número de paso'},
  titulo: {type: 'text-content', default: '', description: 'Título'},
  subtitulo: {type: 'text-content', default: '', description: 'Subtítulo'},
} as const satisfies InteractivitySchema;

export const EncabezadoPaso = Interactive.withSchema({
  Component: EncabezadoPasoInner,
  componentName: '<EncabezadoPaso>',
  schema: encabezadoSchema,
  wrapInSequence: true,
});
