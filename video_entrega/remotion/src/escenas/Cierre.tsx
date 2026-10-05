import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Fondo} from '../componentes/Fondo.tsx';

// Cifras reales: pytest de hoy (311 passed), harness SQL fase 2 (153 OK),
// procedures generados en la corrida del video (4 tablas x 4) y PostgreSQL 18.
const Cifra: React.FC<{readonly n: string; readonly texto: string; readonly x: number; readonly desde: number}> = ({n, texto, x, desde}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: 'absolute', top: 470, left: x, width: 380, height: 300, border: '1px solid #1e2a4a', background: '#0e1630', borderRadius: 22, padding: 34,
        opacity: interpolate(frame, [desde, desde + 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        translate: interpolate(frame, [desde, desde + 15], ['0px 30px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
      }}
    >
      <div style={{fontSize: 110, fontWeight: 800, lineHeight: 1, background: 'linear-gradient(135deg, #4ea8ff, #8b7bff)', WebkitBackgroundClip: 'text', color: 'transparent'}}>{n}</div>
      <div style={{fontSize: 30, color: '#cdd6ea', marginTop: 22, lineHeight: 1.3}}>{texto}</div>
    </div>
  );
};

export const Cierre: React.FC = () => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_cierre.mp3')} premountFor={fps} />
      <Interactive.Div
        name="Lema"
        style={{
          position: 'absolute', left: 140, top: 200,
          opacity: interpolate(frame, [6, 21], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <div style={{fontSize: 88, fontWeight: 800, letterSpacing: -2}}>Una sola solución, cualquier tabla</div>
        <div style={{fontSize: 40, color: '#8a96b3', marginTop: 30}}>Extensión PostgreSQL · Aplicación Python · Privilegios por rol</div>
      </Interactive.Div>
      <Cifra n="311" texto="pruebas unitarias en Python" x={140} desde={24} />
      <Cifra n="153" texto="verificaciones SQL de seguridad, 0 fallos" x={560} desde={35} />
      <Cifra n="16" texto="procedures generados en esta demo (4 tablas)" x={980} desde={45} />
      <Cifra n="18" texto="versión de PostgreSQL probada" x={1400} desde={56} />
      <Interactive.Div
        name="Equipo"
        style={{
          position: 'absolute', left: 140, bottom: 90, fontSize: 30, color: '#8a96b3',
          opacity: interpolate(frame, [72, 87], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Armando · Joyce · Joseph — Bases de Datos II, TEC
      </Interactive.Div>
    </Fondo>
  );
};
