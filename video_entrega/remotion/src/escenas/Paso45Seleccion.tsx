import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO45_SELECCION} from '../datos/capturas.ts';

export const Paso45Seleccion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_4_5.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="4-5" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Pasos 4 y 5" titulo="Elegir esquema y tablas" subtitulo="listas leídas del catálogo" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO45_SELECCION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Ningún nombre está escrito en Python: todo sale de pg_namespace y pg_class.
      </NotaAlPie>
    </Fondo>
  );
};
