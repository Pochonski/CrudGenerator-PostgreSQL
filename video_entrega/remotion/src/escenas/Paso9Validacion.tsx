import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO9_VALIDACION} from '../datos/capturas.ts';

export const Paso9Validacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_9.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="9" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 9" titulo="Probar con cada usuario" subtitulo="mismo CALL, distinto rol" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        otraPestana="PowerShell"
        tamanoFuente={23}
        pasos={PASO9_VALIDACION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        42501: PostgreSQL negó el permiso  ·  P0002: la fila ya no existe.
      </NotaAlPie>
    </Fondo>
  );
};
