import {Audio} from '@remotion/media';
import {Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Fondo} from '../componentes/Fondo.tsx';
import {COLOR, FUENTE} from '../tema.ts';

// Los 10 puntos del Entregable 3 (§10 del enunciado), marcados uno por uno.
const Punto: React.FC<{readonly n: number; readonly texto: string; readonly desde: number}> = ({n, texto, desde}) => {
  const frame = useCurrentFrame();
  const marcado = frame >= desde + 6;

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: 22, padding: '13px 0', borderTop: `1px solid ${COLOR.linea}`,
        opacity: interpolate(frame, [desde, desde + 10], [0.25, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
      }}
    >
      <span
        style={{
          width: 34, height: 34, borderRadius: 4, border: `2px solid ${marcado ? COLOR.azul : COLOR.grisClaro}`, background: marcado ? COLOR.azul : 'transparent',
          color: COLOR.blanco, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 700,
        }}
      >
        {marcado ? '✓' : ''}
      </span>
      <span style={{fontFamily: FUENTE.serif, fontSize: 24, color: COLOR.gris, width: 36}}>{n}</span>
      <span style={{fontSize: 28}}>{texto}</span>
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
        name="Título de cierre"
        style={{
          position: 'absolute', left: 120, top: 150, width: 620,
          opacity: interpolate(frame, [4, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <div style={{fontSize: 20, letterSpacing: 5, textTransform: 'uppercase', color: COLOR.azul, fontWeight: 700}}>Balance</div>
        <div style={{fontFamily: FUENTE.serif, fontSize: 76, lineHeight: 1.08, marginTop: 14}}>Los diez puntos del enunciado, cumplidos</div>
        <div style={{fontSize: 28, color: COLOR.gris, fontStyle: 'italic', marginTop: 30, lineHeight: 1.4}}>
          311 pruebas en Python · 153 verificaciones SQL · 16 procedures generados en la demo · PostgreSQL 18
        </div>
        <div style={{fontSize: 24, color: COLOR.tinta, marginTop: 60}}>Armando · Joyce · Joseph</div>
      </Interactive.Div>
      <Interactive.Div name="Lista de verificación" style={{position: 'absolute', left: 860, top: 150, width: 1000}}>
        <Punto n={1} texto="Instalación de la extensión" desde={14} />
        <Punto n={2} texto="Conexión mediante Python" desde={22} />
        <Punto n={3} texto="Detección de la extensión" desde={30} />
        <Punto n={4} texto="Selección del esquema" desde={38} />
        <Punto n={5} texto="Selección de tablas" desde={46} />
        <Punto n={6} texto="Generación de procedimientos" desde={54} />
        <Punto n={7} texto="Ejecución de los procedimientos" desde={62} />
        <Punto n={8} texto="Asignación de privilegios" desde={70} />
        <Punto n={9} texto="Validación con distintos usuarios" desde={78} />
        <Punto n={10} texto="Tablas no usadas durante el desarrollo" desde={86} />
      </Interactive.Div>
    </Fondo>
  );
};
