import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO6_GENERACION} from '../datos/capturas.ts';

export const Paso6Generacion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_6.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="6" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 6" titulo="Generar los procedimientos" subtitulo="analyze_table + generate_crud" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="PowerShell — crudgen"
        otraPestana="psql — devdb"
        tamanoFuente={23}
        pasos={PASO6_GENERACION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Se leen PK, tipos y NOT NULL; nacen cuatro procedures sin EXECUTE para PUBLIC.
      </NotaAlPie>
    </Fondo>
  );
};
