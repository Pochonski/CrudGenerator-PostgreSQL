import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Fondo} from '../componentes/Fondo.tsx';

export const Portada: React.FC = () => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_portada.mp3')} premountFor={fps} />
      <Interactive.Div
        name="Curso"
        style={{
          position: 'absolute', left: 140, top: 250, fontFamily: '"Cascadia Mono", Consolas, monospace', color: '#4ea8ff', fontSize: 30, letterSpacing: 1,
          opacity: interpolate(frame, [6, 21], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Bases de Datos II · TEC · Primer proyecto
      </Interactive.Div>
      <Interactive.Div
        name="Título"
        style={{
          position: 'absolute', left: 140, top: 310, fontSize: 104, fontWeight: 800, lineHeight: 1.02, letterSpacing: -2,
          opacity: interpolate(frame, [15, 33], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [15, 33], ['0px 30px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        Generador automático de
        <br />
        procedimientos CRUD
      </Interactive.Div>
      <Interactive.Div
        name="Subtítulo"
        style={{
          position: 'absolute', left: 140, top: 560, fontSize: 40, color: '#8a96b3',
          opacity: interpolate(frame, [27, 45], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Extensión de PostgreSQL + aplicación en Python
      </Interactive.Div>
      <Interactive.Div
        name="Integrantes"
        style={{
          position: 'absolute', left: 140, top: 700, display: 'flex', gap: 28,
          opacity: interpolate(frame, [42, 60], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [42, 60], ['0px 30px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{border: '1px solid #1e2a4a', background: '#0e1630cc', borderRadius: 18, padding: '22px 30px', minWidth: 380}}>
          <div style={{fontSize: 36, fontWeight: 700}}>Armando</div>
          <div style={{fontSize: 24, color: '#8a96b3'}}>Aplicación Python + interfaz</div>
        </div>
        <div style={{border: '1px solid #1e2a4a', background: '#0e1630cc', borderRadius: 18, padding: '22px 30px', minWidth: 380}}>
          <div style={{fontSize: 36, fontWeight: 700}}>Joyce</div>
          <div style={{fontSize: 24, color: '#8a96b3'}}>Extensión PostgreSQL</div>
        </div>
        <div style={{border: '1px solid #1e2a4a', background: '#0e1630cc', borderRadius: 18, padding: '22px 30px', minWidth: 380}}>
          <div style={{fontSize: 36, fontWeight: 700}}>Joseph</div>
          <div style={{fontSize: 24, color: '#8a96b3'}}>Seguridad, integración y pruebas</div>
        </div>
      </Interactive.Div>
    </Fondo>
  );
};
