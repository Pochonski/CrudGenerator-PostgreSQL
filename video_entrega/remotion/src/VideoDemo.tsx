import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {useVideoConfig} from 'remotion';
import {Arquitectura} from './escenas/Arquitectura.tsx';
import {Cierre} from './escenas/Cierre.tsx';
import {Decision} from './escenas/Decision.tsx';
import {Paso10Creacion} from './escenas/Paso10Creacion.tsx';
import {Paso10Generacion} from './escenas/Paso10Generacion.tsx';
import {Paso10Uso} from './escenas/Paso10Uso.tsx';
import {Paso1Instalacion} from './escenas/Paso1Instalacion.tsx';
import {Paso23Conexion} from './escenas/Paso23Conexion.tsx';
import {Paso45Seleccion} from './escenas/Paso45Seleccion.tsx';
import {Paso6Especiales} from './escenas/Paso6Especiales.tsx';
import {Paso6Generacion} from './escenas/Paso6Generacion.tsx';
import {Paso7Ejecucion} from './escenas/Paso7Ejecucion.tsx';
import {Paso8Privilegios} from './escenas/Paso8Privilegios.tsx';
import {Paso8Verificacion} from './escenas/Paso8Verificacion.tsx';
import {Paso9Validacion} from './escenas/Paso9Validacion.tsx';
import {Portada} from './escenas/Portada.tsx';
import {Pruebas} from './escenas/Pruebas.tsx';

export type VideoDemoProps = {
  // Duración en cuadros de cada escena, en orden: la de su narración + 0,5 s.
  // La calcula calcularDuracionesDeVoz (Root.tsx) midiendo los mp3 de public/voz/.
  readonly duraciones: readonly number[];
};

export const VideoDemo: React.FC<VideoDemoProps> = ({duraciones}) => {
  const {fps} = useVideoConfig();

  return (
    <TransitionSeries>
      <TransitionSeries.Sequence name="Portada" durationInFrames={duraciones[0]} premountFor={fps}>
        <Portada />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Arquitectura" durationInFrames={duraciones[1]} premountFor={fps}>
        <Arquitectura />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="1 · Instalación" durationInFrames={duraciones[2]} premountFor={fps}>
        <Paso1Instalacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="2-3 · Conexión" durationInFrames={duraciones[3]} premountFor={fps}>
        <Paso23Conexion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="4-5 · Selección" durationInFrames={duraciones[4]} premountFor={fps}>
        <Paso45Seleccion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="6 · Generación" durationInFrames={duraciones[5]} premountFor={fps}>
        <Paso6Generacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="6 · PK compuesta e IDENTITY" durationInFrames={duraciones[6]} premountFor={fps}>
        <Paso6Especiales />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="7 · Ejecución" durationInFrames={duraciones[7]} premountFor={fps}>
        <Paso7Ejecucion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="8 · Privilegios" durationInFrames={duraciones[8]} premountFor={fps}>
        <Paso8Privilegios />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="8 · Verificación" durationInFrames={duraciones[9]} premountFor={fps}>
        <Paso8Verificacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="9 · Validación por rol" durationInFrames={duraciones[10]} premountFor={fps}>
        <Paso9Validacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="10 · Tabla nueva: creación" durationInFrames={duraciones[11]} premountFor={fps}>
        <Paso10Creacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="10 · Tabla nueva: generación" durationInFrames={duraciones[12]} premountFor={fps}>
        <Paso10Generacion />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="10 · Tabla nueva: uso" durationInFrames={duraciones[13]} premountFor={fps}>
        <Paso10Uso />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Pruebas" durationInFrames={duraciones[14]} premountFor={fps}>
        <Pruebas />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Decisión 1" durationInFrames={duraciones[15]} premountFor={fps}>
        <Decision
          titulo="SECURITY INVOKER + doble llave"
          texto="El rol necesita EXECUTE sobre el procedure y el permiso sobre la tabla. Con DEFINER el procedure se ejecutaría con los privilegios del dueño; lo comprobamos en un experimento y lo descartamos."
          codigo="CREATE PROCEDURE … SECURITY INVOKER SET search_path = lab, pg_temp"
          color="#4ea8ff"
          pagina="1 / 5"
          voz="voz/voz_decision_1.mp3"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Decisión 2" durationInFrames={duraciones[16]} premountFor={fps}>
        <Decision
          titulo="Sin EXECUTE para PUBLIC"
          texto="PostgreSQL otorga EXECUTE a PUBLIC al crear un procedure. La extensión lo revoca en el mismo momento; solo la matriz decide quién ejecuta."
          codigo="REVOKE EXECUTE ON PROCEDURE … FROM PUBLIC"
          color="#3ddc84"
          pagina="2 / 5"
          voz="voz/voz_decision_2.mp3"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Decisión 3" durationInFrames={duraciones[17]} premountFor={fps}>
        <Decision
          titulo="SQL dinámico sin concatenar valores"
          texto="Identificadores con %I / quote_ident y valores con %L / quote_nullable. Los parámetros se llaman p_<posición>, así funcionan columnas con espacios o palabras reservadas."
          codigo="format('INSERT INTO %I.%I (%s) VALUES (%s)', …)"
          color="#ffc845"
          pagina="3 / 5"
          voz="voz/voz_decision_3.mp3"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Decisión 4" durationInFrames={duraciones[18]} premountFor={fps}>
        <Decision
          titulo="INSERT que respeta IDENTITY y DEFAULT"
          texto="Las columnas GENERATED ALWAYS se omiten; las que tienen DEFAULT son opcionales: si llegan en NULL, PostgreSQL aplica su propio valor."
          codigo="CALL lab.ticket_insertar();   -- id y fecha los pone PostgreSQL"
          color="#8b7bff"
          pagina="4 / 5"
          voz="voz/voz_decision_4.mp3"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Decisión 5" durationInFrames={duraciones[19]} premountFor={fps}>
        <Decision
          titulo="Regeneración controlada y READ por PK"
          texto="Si el procedure ya existe se informa procedure_conflict y solo se reemplaza con do_replace explícito. READ busca por la PK completa y, si no hay fila, responde P0002."
          codigo="generate_crud(esquema, tabla, operaciones, do_replace => false)"
          color="#ff5d6c"
          pagina="5 / 5"
          voz="voz/voz_decision_5.mp3"
        />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 12})} />
      <TransitionSeries.Sequence name="Cierre" durationInFrames={duraciones[20]} premountFor={fps}>
        <Cierre />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
