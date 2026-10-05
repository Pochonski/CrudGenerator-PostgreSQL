import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_CREACION} from '../datos/capturas.ts';

export const Paso10Creacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_creacion.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="10" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 10" titulo="Prueba de generalidad" subtitulo="una tabla creada después de terminar el código" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        otraPestana="PowerShell"
        tamanoFuente={23}
        pasos={PASO10_CREACION}
        style={{left: 340, top: 220, width: 1520, height: 520}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        La tabla nace ahora; ni Python ni la extensión se modifican.
      </NotaAlPie>
    </Fondo>
  );
};
