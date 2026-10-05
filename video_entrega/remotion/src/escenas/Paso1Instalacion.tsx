import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO1_INSTALACION} from '../datos/capturas.ts';

export const Paso1Instalacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_1.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="1" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 1" titulo="Instalar la extensión" subtitulo="CREATE EXTENSION en PostgreSQL 18" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        otraPestana="PowerShell"
        tamanoFuente={23}
        pasos={PASO1_INSTALACION}
        style={{left: 340, top: 220, width: 1520, height: 560}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        La extensión queda registrada en la versión 1.0, dentro de su propio esquema.
      </NotaAlPie>
    </Fondo>
  );
};
