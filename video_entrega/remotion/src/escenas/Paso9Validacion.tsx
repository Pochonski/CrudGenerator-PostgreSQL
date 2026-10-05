import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO9_VALIDACION} from '../datos/capturas.ts';

export const Paso9Validacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_9.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="9" titulo="Validación con distintos usuarios" subtitulo="El mismo CALL, distinto rol, distinto resultado" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb, cambiando de rol"
        tamanoFuente={23}
        pasos={PASO9_VALIDACION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        Cada rol ejecuta solo lo que se le otorgó (42501 = permiso denegado)
      </Leyenda>
    </Fondo>
  );
};
