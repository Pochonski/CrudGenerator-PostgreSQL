import {Audio} from '@remotion/media';
import {staticFile, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {NotaAlPie} from '../componentes/NotaAlPie.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {Terminal} from '../componentes/Terminal.tsx';
import {PASO7_EJECUCION} from '../datos/capturas.ts';

export const Paso7Ejecucion: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_paso_7.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="7" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Paso 7" titulo="Ejecutar lo generado" subtitulo="CALL sobre objetos reales" />
      <Terminal
        name="Terminal"
        premountFor={fps}
        titulo="psql — devdb"
        otraPestana="PowerShell"
        tamanoFuente={23}
        pasos={PASO7_EJECUCION}
        style={{left: 340, top: 220, width: 1520, height: 740}}
      />
      <NotaAlPie name="Nota" from={30} premountFor={fps}>
        Insertar, consultar por PK y dejar que PostgreSQL genere el id del ticket.
      </NotaAlPie>
    </Fondo>
  );
};
