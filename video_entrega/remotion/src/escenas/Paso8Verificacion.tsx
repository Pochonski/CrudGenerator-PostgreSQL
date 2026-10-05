import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO8_VERIFICACION} from '../datos/capturas.ts';

export const Paso8Verificacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_8_verificacion.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="8" titulo="Verificación automática de la matriz" subtitulo="La aplicación ejecuta cada procedure como cada rol" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="crudgen — verificación de permisos"
        tamanoFuente={23}
        pasos={PASO8_VERIFICACION}
        style={{left: 60, top: 180, width: 1800, height: 780}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        12 / 12 OK: lo que dice la matriz es lo que PostgreSQL hace cumplir
      </Leyenda>
    </Fondo>
  );
};
