import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO45_SELECCION} from '../datos/capturas.ts';

export const Paso45Seleccion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_4_5.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="4-5" titulo="Selección de esquema y tablas" subtitulo="Una, varias o todas — leídas del catálogo" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — esquema, tablas y operaciones"
        tamanoFuente={23}
        pasos={PASO45_SELECCION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        Nada está fijo en Python: esquemas y tablas salen de PostgreSQL
      </Leyenda>
    </Fondo>
  );
};
