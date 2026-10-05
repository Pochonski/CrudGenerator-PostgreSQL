import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO1_INSTALACION} from '../datos/capturas.ts';

export const Paso1Instalacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_1.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="1" titulo="Instalación de la extensión" subtitulo="CREATE EXTENSION en PostgreSQL 18" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb (PostgreSQL 18)"
        tamanoFuente={23}
        pasos={PASO1_INSTALACION}
        style={{left: 60, top: 180, width: 1800, height: 560}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        crud_generator 1.0 queda registrada en su propio esquema
      </Leyenda>
    </Fondo>
  );
};
