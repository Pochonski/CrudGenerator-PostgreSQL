import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO23_CONEXION} from '../datos/capturas.ts';

export const Paso23Conexion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_2_3.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="2-3" titulo="Conexión y detección de la extensión" subtitulo="Desde la aplicación Python (crudgen)" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — conexión"
        tamanoFuente={23}
        pasos={PASO23_CONEXION}
        style={{left: 60, top: 180, width: 1800, height: 620}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        Python verifica versión, esquema y permiso USAGE antes de generar
      </Leyenda>
    </Fondo>
  );
};
