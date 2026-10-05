import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO10_USO} from '../datos/capturas.ts';

export const Paso10Uso: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_10_uso.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="10" titulo="Una tabla que no existía durante el desarrollo" subtitulo="Sus procedures funcionan igual que los demás" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        tamanoFuente={23}
        pasos={PASO10_USO}
        style={{left: 60, top: 180, width: 1800, height: 700}}
      />
      <Leyenda name="Leyenda" from={36} premountFor={fps} color="#3ddc84">
        INSERT con 2 argumentos: creado_en lo pone el DEFAULT · vendedor sin READ → 42501
      </Leyenda>
    </Fondo>
  );
};
