import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO6_GENERACION} from '../datos/capturas.ts';

export const Paso6Generacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_6.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="6" titulo="Análisis y generación de procedimientos" subtitulo="analyze_table lee la estructura; generate_crud crea los procedures" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — lab.producto"
        tamanoFuente={23}
        pasos={PASO6_GENERACION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        PK, tipos y NOT NULL leídos del catálogo · 4 × success
      </Leyenda>
    </Fondo>
  );
};
