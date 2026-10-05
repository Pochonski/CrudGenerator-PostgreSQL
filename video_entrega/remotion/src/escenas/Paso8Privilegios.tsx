import {Audio} from '@remotion/media';
import {Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO8_PRIVILEGIOS} from '../datos/capturas.ts';
import {construirLineaDeTiempo} from '../datos/linea-de-tiempo.ts';
import {COLOR, FUENTE} from '../tema.ts';

// Duración natural del tecleo; Terminal la comprime si la voz es más corta.
const FIN_TERMINAL = construirLineaDeTiempo(PASO8_PRIVILEGIOS).duracion;

const Celda: React.FC<{readonly si: boolean}> = ({si}) => (
  <td style={{textAlign: 'center', padding: '14px 4px', borderTop: `1px solid ${COLOR.linea}`, color: si ? COLOR.azul : COLOR.grisClaro, fontSize: 30}}>{si ? '●' : '○'}</td>
);

const Fila: React.FC<{readonly rol: string; readonly v: readonly boolean[]}> = ({rol, v}) => (
  <tr>
    <td style={{padding: '14px 4px', borderTop: `1px solid ${COLOR.linea}`, fontFamily: FUENTE.serif, fontSize: 26}}>{rol}</td>
    {v.map((si, i) => <Celda key={i} si={si} />)}
  </tr>
);

export const Paso8Privilegios: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  // La tabla aparece 0,3 s después de que la terminal termina de escribir.
  const inicioTabla = Math.round((Math.min(FIN_TERMINAL, durationInFrames / fps - 1) + 0.3) * fps);

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_8_privilegios.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="8" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 8" titulo="Repartir privilegios" subtitulo="por operación, para cada rol" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={21}
        pasos={PASO8_PRIVILEGIOS}
        style={{left: 340, top: 220, width: 1000, height: 740}}
      />
      <Interactive.Div
        name="Tabla de privilegios"
        style={{
          position: 'absolute', left: 1380, top: 220, width: 480, background: COLOR.blanco, border: `1px solid ${COLOR.linea}`, borderRadius: 6, padding: '26px 28px',
          opacity: interpolate(frame, [inicioTabla, inicioTabla + 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <div style={{fontSize: 16, letterSpacing: 3, textTransform: 'uppercase', color: COLOR.azul, fontWeight: 700}}>Resultado en PostgreSQL</div>
        <div style={{fontFamily: FUENTE.serif, fontSize: 32, margin: '8px 0 16px'}}>lab.producto</div>
        <table style={{width: '100%', borderCollapse: 'collapse'}}>
          <thead>
            <tr style={{color: COLOR.gris, fontSize: 17, letterSpacing: 1}}>
              <th />
              <th>INS</th>
              <th>READ</th>
              <th>UPD</th>
              <th>DEL</th>
            </tr>
          </thead>
          <tbody>
            <Fila rol="administrador" v={[true, true, true, true]} />
            <Fila rol="supervisor" v={[true, true, true, false]} />
            <Fila rol="vendedor" v={[true, true, false, false]} />
          </tbody>
        </table>
        <div style={{fontSize: 20, color: COLOR.gris, marginTop: 20, lineHeight: 1.45}}>
          ● GRANT de EXECUTE + permiso de tabla + USAGE<br />○ REVOKE
        </div>
      </Interactive.Div>
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Cada respuesta es un GRANT o un REVOKE real; quien hace cumplir los permisos es PostgreSQL.
      </NotaAlPie>
    </Fondo>
  );
};
