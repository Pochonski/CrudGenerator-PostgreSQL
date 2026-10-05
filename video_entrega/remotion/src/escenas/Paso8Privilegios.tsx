import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO8_PRIVILEGIOS} from '../datos/capturas.ts';
import {construirLineaDeTiempo} from '../datos/linea-de-tiempo.ts';

// Duración natural del tecleo; Terminal la comprime si la voz es más corta.
const FIN_TERMINAL = construirLineaDeTiempo(PASO8_PRIVILEGIOS).duracion;

const Celda: React.FC<{readonly si: boolean}> = ({si}) => (
  <td style={{textAlign: 'center', padding: '12px 6px', borderTop: '1px solid #1e2a4a', color: si ? '#3ddc84' : '#ff5d6c', fontWeight: 800}}>{si ? '✓' : '✗'}</td>
);

const Fila: React.FC<{readonly rol: string; readonly v: readonly boolean[]}> = ({rol, v}) => (
  <tr>
    <td style={{padding: '12px 6px', borderTop: '1px solid #1e2a4a', fontFamily: 'Consolas, monospace', fontSize: 24}}>{rol}</td>
    {v.map((si, i) => <Celda key={i} si={si} />)}
  </tr>
);

export const Paso8Privilegios: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  // La tarjeta aparece 0,3 s después de que la terminal termina de escribir.
  const inicioTarjeta = Math.round((Math.min(FIN_TERMINAL, durationInFrames / fps - 1) + 0.3) * fps);

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_8_privilegios.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="8" titulo="Asignación de privilegios" subtitulo="Roles y operaciones, desde la aplicación" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — selección de roles y privilegios"
        tamanoFuente={23}
        pasos={PASO8_PRIVILEGIOS}
        style={{left: 60, top: 180, width: 1180, height: 780}}
      />
      <Interactive.Div
        name="Tarjeta matriz"
        style={{
          position: 'absolute', left: 1280, top: 180, width: 580, border: '1px solid #1e2a4a', background: '#0e1630', borderRadius: 18, padding: 30,
          opacity: interpolate(frame, [inicioTarjeta, inicioTarjeta + 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [inicioTarjeta, inicioTarjeta + 15], ['0px 24px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{fontSize: 30, fontWeight: 700, marginBottom: 18}}>Matriz aplicada a lab.producto</div>
        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: 28}}>
          <thead>
            <tr style={{color: '#8a96b3', fontSize: 22}}>
              <th />
              <th>INSERT</th>
              <th>READ</th>
              <th>UPDATE</th>
              <th>DELETE</th>
            </tr>
          </thead>
          <tbody>
            <Fila rol="administrador" v={[true, true, true, true]} />
            <Fila rol="supervisor" v={[true, true, true, false]} />
            <Fila rol="vendedor" v={[true, true, false, false]} />
          </tbody>
        </table>
        <div style={{fontSize: 22, color: '#8a96b3', marginTop: 24, lineHeight: 1.4}}>
          Cada ✓ es un GRANT real (EXECUTE + permiso de tabla + USAGE); cada ✗, un REVOKE.
        </div>
      </Interactive.Div>
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#4ea8ff">
        La matriz se pregunta por operación: INSERT, READ, UPDATE y DELETE para cada rol
      </Leyenda>
    </Fondo>
  );
};
