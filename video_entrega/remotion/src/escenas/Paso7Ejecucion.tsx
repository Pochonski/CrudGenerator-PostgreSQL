import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO7_EJECUCION} from '../datos/capturas.ts';

export const Paso7Ejecucion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_7.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="7" titulo="Ejecución de los procedimientos" subtitulo="Los procedures generados son objetos reales de PostgreSQL" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        tamanoFuente={23}
        pasos={PASO7_EJECUCION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        INSERT · READ por PK · PK compuesta · IDENTITY y DEFAULT automáticos
      </Leyenda>
    </Fondo>
  );
};
