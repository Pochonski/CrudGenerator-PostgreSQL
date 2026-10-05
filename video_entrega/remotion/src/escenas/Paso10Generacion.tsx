import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_GENERACION} from '../datos/capturas.ts';

export const Paso10Generacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_generacion.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="10" titulo="Una tabla que no existía durante el desarrollo" subtitulo="crudgen la descubre en el catálogo y genera su CRUD" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — lab.tabla_video_nueva"
        tamanoFuente={23}
        pasos={PASO10_GENERACION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        Sin cambiar una línea de código: 4 × success y matriz aplicada
      </Leyenda>
    </Fondo>
  );
};
