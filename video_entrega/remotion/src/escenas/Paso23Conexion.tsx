import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO23_CONEXION} from '../datos/capturas.ts';

export const Paso23Conexion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_2_3.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="2-3" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Pasos 2 y 3" titulo="Conectar y detectar" subtitulo="desde la CLI en Python" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO23_CONEXION}
        style={{left: 340, top: 220, width: 1520, height: 620}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Antes de generar, crudgen comprueba versión, esquema y permiso de uso de la extensión.
      </NotaAlPie>
    </Fondo>
  );
};
