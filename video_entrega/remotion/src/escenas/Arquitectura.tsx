import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';
import {RielProgreso} from '../componentes/RielProgreso.tsx';
import {COLOR, FUENTE} from '../tema.ts';

type CapaProps = {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly color: string;
  readonly rotulo: string;
  readonly titulo: string;
  readonly texto: string;
  readonly desde: number;
};

// Una capa del diagrama: tarjeta blanca con franja de color a la izquierda.
const Capa: React.FC<CapaProps> = ({x, y, w, h, color, rotulo, titulo, texto, desde}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: 'absolute', left: x, top: y, width: w, height: h, background: COLOR.blanco, border: `1px solid ${COLOR.linea}`,
        borderLeft: `8px solid ${color}`, borderRadius: 6, padding: '18px 26px', display: 'flex', flexDirection: 'column', justifyContent: 'center',
        opacity: interpolate(frame, [desde, desde + 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        translate: interpolate(frame, [desde, desde + 14], ['0px 16px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
      }}
    >
      <div style={{fontSize: 15, letterSpacing: 3, textTransform: 'uppercase', color, fontWeight: 700}}>{rotulo}</div>
      <div style={{fontFamily: FUENTE.serif, fontSize: 34, marginTop: 4}}>{titulo}</div>
      <div style={{fontFamily: FUENTE.mono, fontSize: 19, color: COLOR.gris, marginTop: 8}}>{texto}</div>
    </div>
  );
};

// Trazo SVG que se dibuja entre dos cuadros.
const progresoTrazo = (frame: number, desde: number) =>
  interpolate(frame, [desde, desde + 18], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.65, 0, 0.35, 1)});

export const Arquitectura: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_arquitectura.mp3')} premountFor={fps} />
      <RielProgreso name="Riel" premountFor={fps} actual="intro" />
      <EncabezadoPaso name="Encabezado" premountFor={fps} etiqueta="Panorama" titulo="Cómo está construido" subtitulo="la generación vive en la base de datos" />
      <Interactive.Svg name="Conectores" width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        <g stroke={COLOR.tinta} strokeWidth={2} fill="none">
          <path d="M 1100 365 L 1100 425" pathLength={1} strokeDasharray="1" strokeDashoffset={progresoTrazo(frame, 40)} />
          <path d="M 900 565 L 900 600 L 710 600 L 710 625" pathLength={1} strokeDasharray="1" strokeDashoffset={progresoTrazo(frame, 80)} />
          <path d="M 1300 565 L 1300 600 L 1490 600 L 1490 625" pathLength={1} strokeDasharray="1" strokeDashoffset={progresoTrazo(frame, 110)} />
          <path d="M 1490 775 L 1490 835" pathLength={1} strokeDasharray="1" strokeDashoffset={progresoTrazo(frame, 150)} />
        </g>
        <g fill={COLOR.gris} fontFamily={FUENTE.mono} fontSize={18} style={{opacity: interpolate(frame, [40, 56], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          <text x={1118} y={402}>SELECT crud_generator.generate_crud(…)</text>
        </g>
        <g fill={COLOR.gris} fontFamily={FUENTE.mono} fontSize={18} style={{opacity: interpolate(frame, [80, 96], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          <text x={724} y={593}>lee</text>
          <text x={1314} y={593}>crea</text>
        </g>
        <g fill={COLOR.gris} fontFamily={FUENTE.mono} fontSize={18} style={{opacity: interpolate(frame, [150, 166], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          <text x={1508} y={812}>EXECUTE según la matriz</text>
        </g>
      </Interactive.Svg>
      <Capa x={340} y={235} w={1520} h={130} color={COLOR.azul} rotulo="Interfaz y orquestación" titulo="Aplicación Python · crudgen" texto="conecta · asume crud_admin · elige esquema, tablas y operaciones · aplica GRANT / REVOKE · verifica" desde={8} />
      <Capa x={340} y={425} w={1520} h={140} color={COLOR.tinta} rotulo="Lógica de generación" titulo="Extensión crud_generator 1.0 (SQL + PL/pgSQL)" texto="analyze_table(esquema, tabla) · generate_crud(esquema, tabla, operaciones, do_replace)" desde={52} />
      <Capa x={340} y={625} w={740} h={150} color={COLOR.gris} rotulo="Metadatos" titulo="Catálogos del sistema" texto="pg_namespace · pg_class · pg_attribute · pg_attrdef · pg_index" desde={90} />
      <Capa x={1120} y={625} w={740} h={150} color={COLOR.exito} rotulo="Resultado" titulo="Procedures generados" texto="lab.<tabla>_insertar / _consultar / _actualizar / _eliminar" desde={120} />
      <Capa x={340} y={835} w={1520} h={120} color={COLOR.error} rotulo="Control de acceso" titulo="Roles de PostgreSQL" texto="crud_administrador · crud_supervisor · crud_vendedor — SECURITY INVOKER, sin EXECUTE para PUBLIC" desde={160} />
    </Fondo>
  );
};
