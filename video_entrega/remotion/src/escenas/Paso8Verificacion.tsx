import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO8_VERIFICACION} from '../datos/capturas.ts';

export const Paso8Verificacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_8_verificacion.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="8" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 8" titulo="Comprobar la matriz" subtitulo="cada procedure, con cada rol" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO8_VERIFICACION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Las 12 combinaciones coinciden: lo esperado es lo que PostgreSQL permite.
      </NotaAlPie>
    </Fondo>
  );
};
