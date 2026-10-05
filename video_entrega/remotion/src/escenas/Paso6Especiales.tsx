import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO6_ESPECIALES} from '../datos/capturas.ts';

export const Paso6Especiales: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_6_especiales.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="6" titulo="PK compuesta, IDENTITY y DEFAULT" subtitulo="Misma extensión, otras estructuras de tabla" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — lab.detalle_factura y lab.ticket"
        tamanoFuente={23}
        pasos={PASO6_ESPECIALES}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        PK compuesta detectada · IDENTITY ALWAYS y DEFAULT fuera del INSERT obligatorio
      </Leyenda>
    </Fondo>
  );
};
