import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_CREACION} from '../datos/capturas.ts';

export const Paso10Creacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_creacion.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="10" titulo="Una tabla que no existía durante el desarrollo" subtitulo="Se crea ahora, sin tocar Python ni la extensión" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        tamanoFuente={23}
        pasos={PASO10_CREACION}
        style={{left: 60, top: 180, width: 1800, height: 520}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        Tabla nueva: PK simple + DEFAULT now()
      </Leyenda>
    </Fondo>
  );
};
