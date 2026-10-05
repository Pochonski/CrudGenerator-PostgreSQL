import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {Composition, Folder, staticFile, type CalculateMetadataFunction} from 'remotion';
import {EncabezadoPaso} from './componentes/EncabezadoPaso.tsx';
import {Leyenda} from './componentes/Leyenda.tsx';
import {NARRACION} from './datos/narracion.ts';
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
import {VideoDemo, type VideoDemoProps} from './VideoDemo.tsx';

const FPS = 30;
const FUNDIDO = 12; // cuadros de cada transición en VideoDemo
// 0,5 s de aire tras cada frase: cubre el fundido para que dos voces no se pisen.
const cuadrosDeVoz = async (archivo: string) => Math.ceil(((await getAudioDurationInSeconds(staticFile(archivo))) + 0.5) * FPS);

const calcularDuracionesDeVoz: CalculateMetadataFunction<VideoDemoProps> = async () => {
  const duraciones = await Promise.all(NARRACION.map((n) => cuadrosDeVoz(n.archivo)));
  return {
    durationInFrames: duraciones.reduce((a, b) => a + b, 0) - FUNDIDO * (duraciones.length - 1),
    props: {duraciones},
  };
};

// Cada escena suelta dura lo mismo que su narración.
const duracionDe =
  <T extends Record<string, unknown>>(archivo: string): CalculateMetadataFunction<T> =>
  async () => ({durationInFrames: await cuadrosDeVoz(archivo)});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CrudGeneratorDemo"
        component={VideoDemo}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={5903}
        defaultProps={{duraciones: []}}
        calculateMetadata={calcularDuracionesDeVoz}
      />
      <Folder name="Escenas">
        <Composition id="Portada" component={Portada} width={1920} height={1080} fps={30} durationInFrames={210} calculateMetadata={duracionDe('voz/voz_portada.mp3')} />
        <Composition id="Arquitectura" component={Arquitectura} width={1920} height={1080} fps={30} durationInFrames={390} calculateMetadata={duracionDe('voz/voz_arquitectura.mp3')} />
        <Composition id="Paso1-Instalacion" component={Paso1Instalacion} width={1920} height={1080} fps={30} durationInFrames={278} calculateMetadata={duracionDe('voz/voz_paso_1.mp3')} />
        <Composition id="Paso23-Conexion" component={Paso23Conexion} width={1920} height={1080} fps={30} durationInFrames={274} calculateMetadata={duracionDe('voz/voz_paso_2_3.mp3')} />
        <Composition id="Paso45-Seleccion" component={Paso45Seleccion} width={1920} height={1080} fps={30} durationInFrames={272} calculateMetadata={duracionDe('voz/voz_paso_4_5.mp3')} />
        <Composition id="Paso6-Generacion" component={Paso6Generacion} width={1920} height={1080} fps={30} durationInFrames={207} calculateMetadata={duracionDe('voz/voz_paso_6.mp3')} />
        <Composition id="Paso6-Especiales" component={Paso6Especiales} width={1920} height={1080} fps={30} durationInFrames={335} calculateMetadata={duracionDe('voz/voz_paso_6_especiales.mp3')} />
        <Composition id="Paso7-Ejecucion" component={Paso7Ejecucion} width={1920} height={1080} fps={30} durationInFrames={499} calculateMetadata={duracionDe('voz/voz_paso_7.mp3')} />
        <Composition id="Paso8-Privilegios" component={Paso8Privilegios} width={1920} height={1080} fps={30} durationInFrames={527} calculateMetadata={duracionDe('voz/voz_paso_8_privilegios.mp3')} />
        <Composition id="Paso8-Verificacion" component={Paso8Verificacion} width={1920} height={1080} fps={30} durationInFrames={212} calculateMetadata={duracionDe('voz/voz_paso_8_verificacion.mp3')} />
        <Composition id="Paso9-Validacion" component={Paso9Validacion} width={1920} height={1080} fps={30} durationInFrames={553} calculateMetadata={duracionDe('voz/voz_paso_9.mp3')} />
        <Composition id="Paso10-Creacion" component={Paso10Creacion} width={1920} height={1080} fps={30} durationInFrames={287} calculateMetadata={duracionDe('voz/voz_paso_10_creacion.mp3')} />
        <Composition id="Paso10-Generacion" component={Paso10Generacion} width={1920} height={1080} fps={30} durationInFrames={331} calculateMetadata={duracionDe('voz/voz_paso_10_generacion.mp3')} />
        <Composition id="Paso10-Uso" component={Paso10Uso} width={1920} height={1080} fps={30} durationInFrames={313} calculateMetadata={duracionDe('voz/voz_paso_10_uso.mp3')} />
        <Composition id="Pruebas" component={Pruebas} width={1920} height={1080} fps={30} durationInFrames={210} calculateMetadata={duracionDe('voz/voz_pruebas.mp3')} />
        <Composition
          id="Decision"
          component={Decision}
          width={1920}
          height={1080}
          fps={30}
          durationInFrames={195}
          calculateMetadata={async ({props}) => ({durationInFrames: await cuadrosDeVoz(props.voz)})}
          defaultProps={{
            titulo: 'SECURITY INVOKER + doble llave',
            texto: 'El rol necesita EXECUTE sobre el procedure y el permiso sobre la tabla. Con DEFINER el procedure se ejecutaría con los privilegios del dueño; lo comprobamos en un experimento y lo descartamos.',
            codigo: 'CREATE PROCEDURE … SECURITY INVOKER SET search_path = lab, pg_temp',
            color: '#4ea8ff',
            pagina: '1 / 5',
            voz: 'voz/voz_decision_1.mp3',
          }}
        />
        <Composition id="Cierre" component={Cierre} width={1920} height={1080} fps={30} durationInFrames={270} calculateMetadata={duracionDe('voz/voz_cierre.mp3')} />
      </Folder>
      <Folder name="Elementos">
        <Composition
          id="EncabezadoPaso"
          component={EncabezadoPaso}
          width={1920}
          height={1080}
          fps={30}
          durationInFrames={60}
          defaultProps={{insignia: '1', titulo: 'Instalación de la extensión', subtitulo: 'CREATE EXTENSION en PostgreSQL 18'}}
        />
        <Composition
          id="Leyenda"
          component={Leyenda}
          width={1920}
          height={1080}
          fps={30}
          durationInFrames={60}
          defaultProps={{children: 'crud_generator 1.0 queda registrada en su propio esquema', color: '#3ddc84'}}
        />
      </Folder>
    </>
  );
};
