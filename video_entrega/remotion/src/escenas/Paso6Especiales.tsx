import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO6_ESPECIALES} from '../datos/capturas.ts';

export const Paso6Especiales: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_6_especiales.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="6" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 6" titulo="Estructuras más complejas" subtitulo="PK compuesta, IDENTITY y DEFAULT" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO6_ESPECIALES}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Las columnas generadas o con DEFAULT dejan de ser obligatorias al insertar.
      </NotaAlPie>
    </Fondo>
  );
};
