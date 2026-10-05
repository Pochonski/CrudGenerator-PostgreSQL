import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_GENERACION} from '../datos/capturas.ts';

export const Paso10Generacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_generacion.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="10" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 10" titulo="Prueba de generalidad" subtitulo="crudgen la encuentra en el catálogo" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO10_GENERACION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Cuatro procedures nuevos y permisos para administrador y vendedor.
      </NotaAlPie>
    </Fondo>
  );
};
