import {Audio} from '@remotion/media';
import {Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PRUEBAS_HARNESS, PRUEBAS_PYTEST} from '../datos/capturas.ts';
import {COLOR, FUENTE} from '../tema.ts';

export const Pruebas: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_pruebas.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="pruebas" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Respaldo" titulo="Pruebas automáticas" subtitulo="Python y SQL, sin fallos" />
      <Interactive.Div
        name="Cifra pytest"
        style={{
          position: 'absolute', left: 340, top: 230, width: 740, display: 'flex', alignItems: 'baseline', gap: 22,
          opacity: interpolate(frame, [8, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <span style={{fontFamily: FUENTE.serif, fontSize: 120, color: COLOR.azul, lineHeight: 1}}>311</span>
        <span style={{fontSize: 28, color: COLOR.tinta}}>pruebas unitarias en Python</span>
      </Interactive.Div>
      <Interactive.Div
        name="Cifra harness"
        style={{
          position: 'absolute', left: 1250, top: 230, width: 610, display: 'flex', alignItems: 'baseline', gap: 22,
          opacity: interpolate(frame, [20, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <span style={{fontFamily: FUENTE.serif, fontSize: 120, color: COLOR.azul, lineHeight: 1}}>153</span>
        <span style={{fontSize: 28, color: COLOR.tinta}}>verificaciones de seguridad en SQL</span>
      </Interactive.Div>
      <Terminal
        name="Terminal pytest"
        premountFor={fps}
        titulo="PowerShell — pytest"
        tamanoFuente={15}
        pasos={PRUEBAS_PYTEST}
        style={{left: 340, top: 400, width: 880, height: 520}}
      />
      <Terminal
        name="Log del harness SQL"
        from={52}
        premountFor={fps}
        titulo="fase2_reales.log (extracto)"
        tamanoFuente={15}
        cursor={false}
        pasos={PRUEBAS_HARNESS}
        style={{left: 1250, top: 400, width: 610, height: 520}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Las cifras salen de pytest y de los logs de evidencia del harness SQL: 0 fallos.
      </NotaAlPie>
    </Fondo>
  );
};
