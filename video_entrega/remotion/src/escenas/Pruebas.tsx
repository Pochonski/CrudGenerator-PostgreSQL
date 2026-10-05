import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {Leyenda} from '../componentes/Leyenda.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PRUEBAS_HARNESS, PRUEBAS_PYTEST} from '../datos/capturas.ts';

export const Pruebas: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_pruebas.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="✓" titulo="Pruebas automáticas" subtitulo="Unitarias en Python y matriz de seguridad en SQL" />
      <Terminal
        name="Terminal pytest"
        premountFor={fps}
        titulo="pytest — aplicación Python"
        tamanoFuente={18}
        pasos={PRUEBAS_PYTEST}
        style={{left: 60, top: 180, width: 1020, height: 560}}
      />
      <Terminal
        name="Log del harness SQL"
        from={52}
        premountFor={fps}
        titulo="tests/evidence/fase2_reales.log (extracto)"
        tamanoFuente={18}
        cursor={false}
        pasos={PRUEBAS_HARNESS}
        style={{left: 1110, top: 180, width: 750, height: 560}}
      />
      <Leyenda name="Leyenda" from={30} premountFor={fps} color="#3ddc84">
        311 pruebas unitarias · 153 verificaciones SQL · 0 fallos
      </Leyenda>
    </Fondo>
  );
};
