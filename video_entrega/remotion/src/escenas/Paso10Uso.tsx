import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_USO} from '../datos/capturas.ts';

export const Paso10Uso: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_uso.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="10" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 10" titulo="Prueba de generalidad" subtitulo="sus procedures en acción" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        otraPestana="PowerShell"
        tamanoFuente={23}
        pasos={PASO10_USO}
        style={{left: 340, top: 220, width: 1520, height: 680}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Solo dos argumentos: la fecha la pone el DEFAULT. El vendedor no puede consultar.
      </NotaAlPie>
    </Fondo>
  );
};
