import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Fondo} from '../componentes/Fondo.tsx';
import {COLOR, FUENTE} from '../tema.ts';

const Integrante: React.FC<{readonly nombre: string; readonly rol: string}> = ({nombre, rol}) => (
  <div style={{borderTop: `1px solid ${COLOR.linea}`, padding: '22px 0'}}>
    <div style={{fontFamily: FUENTE.serif, fontSize: 40}}>{nombre}</div>
    <div style={{fontSize: 22, color: COLOR.gris, marginTop: 4}}>{rol}</div>
  </div>
);

export const Portada: React.FC = () => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_portada.mp3')} premountFor={fps} />
      <Interactive.Div
        name="Etiqueta"
        style={{
          position: 'absolute', left: 120, top: 330, fontSize: 22, letterSpacing: 5, textTransform: 'uppercase', color: COLOR.azul, fontWeight: 700,
          opacity: interpolate(frame, [4, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Primer proyecto · Octubre 2026
      </Interactive.Div>
      <Interactive.Div
        name="Título"
        style={{
          position: 'absolute', left: 120, top: 380, width: 1050, fontFamily: FUENTE.serif, fontSize: 96, lineHeight: 1.05,
          opacity: interpolate(frame, [10, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [10, 28], ['0px 20px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        Procedimientos CRUD que se escriben solos
      </Interactive.Div>
      <Interactive.Div
        name="Bajada"
        style={{
          position: 'absolute', left: 120, top: 720, width: 1000, fontSize: 32, lineHeight: 1.4, color: COLOR.gris, fontStyle: 'italic',
          opacity: interpolate(frame, [24, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Una extensión de PostgreSQL que lee el catálogo y genera el CRUD de cualquier tabla, administrada desde Python.
      </Interactive.Div>
      <Interactive.Div
        name="Equipo"
        style={{
          position: 'absolute', left: 1320, top: 330, width: 480,
          opacity: interpolate(frame, [36, 52], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <div style={{fontSize: 18, letterSpacing: 4, textTransform: 'uppercase', color: COLOR.gris, marginBottom: 10}}>Equipo</div>
        <Integrante nombre="Armando" rol="Aplicación Python e interfaz" />
        <Integrante nombre="Joyce" rol="Extensión PostgreSQL" />
        <Integrante nombre="Joseph" rol="Seguridad, integración y pruebas" />
      </Interactive.Div>
    </Fondo>
  );
};
