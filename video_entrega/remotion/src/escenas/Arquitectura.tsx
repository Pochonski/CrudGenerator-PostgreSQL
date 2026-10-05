import {Audio} from '@remotion/media';
import {Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EncabezadoPaso} from '../componentes/EncabezadoPaso.tsx';
import {Fondo} from '../componentes/Fondo.tsx';

// Diagrama: Python -> extension -> catalogos / procedures -> roles.
// Cada caja aparece en orden, siguiendo el flujo real de la solucion.
export const Arquitectura: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <Fondo>
      <Audio name="Voz" src={staticFile('voz/voz_arquitectura.mp3')} premountFor={fps} />
      <EncabezadoPaso name="Encabezado" premountFor={fps} insignia="▶" titulo="Arquitectura de la solución" subtitulo="La lógica de generación vive en PostgreSQL; Python orquesta" />
      <Interactive.Div
        name="Caja Python"
        style={{
          position: 'absolute', left: 60, top: 330, width: 470, border: '2px solid #4ea8ff', borderRadius: 18, padding: '22px 26px', background: '#0b1226',
          opacity: interpolate(frame, [12, 27], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [12, 27], ['0px 24px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{fontSize: 32, fontWeight: 700, color: '#4ea8ff', marginBottom: 12}}>Aplicación Python · crudgen</div>
        <div style={{fontFamily: 'Consolas, monospace', fontSize: 21, lineHeight: '32px', color: '#cdd6ea'}}>
          Conecta y asume crud_admin<br />Detecta la extensión<br />Elige esquema, tablas y operaciones<br />Aplica la matriz GRANT / REVOKE<br />Verifica permisos por rol
        </div>
      </Interactive.Div>
      <Interactive.Div
        name="Flecha SELECT"
        style={{
          position: 'absolute', left: 540, top: 440, fontFamily: 'Consolas, monospace', fontSize: 20, color: '#8a96b3',
          opacity: interpolate(frame, [48, 60], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        SELECT ─────▶
      </Interactive.Div>
      <Interactive.Div
        name="Caja extensión"
        style={{
          position: 'absolute', left: 690, top: 360, width: 440, border: '2px solid #8b7bff', borderRadius: 18, padding: '22px 26px', background: '#0b1226',
          opacity: interpolate(frame, [54, 69], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [54, 69], ['0px 24px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{fontSize: 32, fontWeight: 700, color: '#8b7bff', marginBottom: 12}}>Extensión crud_generator 1.0</div>
        <div style={{fontFamily: 'Consolas, monospace', fontSize: 21, lineHeight: '32px', color: '#cdd6ea'}}>
          analyze_table(esquema, tabla)<br />generate_crud(esquema, tabla,<br />&nbsp;&nbsp;operaciones, do_replace)<br />SQL + PL/pgSQL
        </div>
      </Interactive.Div>
      <Interactive.Div
        name="Caja catálogos"
        style={{
          position: 'absolute', left: 1260, top: 190, width: 600, border: '2px solid #ffc845', borderRadius: 18, padding: '22px 26px', background: '#0b1226',
          opacity: interpolate(frame, [96, 111], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [96, 111], ['24px 0px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{fontSize: 32, fontWeight: 700, color: '#ffc845', marginBottom: 12}}>Catálogos de PostgreSQL</div>
        <div style={{fontFamily: 'Consolas, monospace', fontSize: 21, lineHeight: '32px', color: '#cdd6ea'}}>
          pg_namespace · pg_class · pg_attribute<br />pg_attrdef · pg_index
        </div>
      </Interactive.Div>
      <Interactive.Div
        name="Flecha lee"
        style={{
          position: 'absolute', left: 1150, top: 290, fontFamily: 'Consolas, monospace', fontSize: 20, color: '#8a96b3',
          opacity: interpolate(frame, [96, 108], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        lee ──▶
      </Interactive.Div>
      <Interactive.Div
        name="Caja procedures"
        style={{
          position: 'absolute', left: 1260, top: 470, width: 600, border: '2px solid #3ddc84', borderRadius: 18, padding: '22px 26px', background: '#0b1226',
          opacity: interpolate(frame, [138, 153], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [138, 153], ['24px 0px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <div style={{fontSize: 32, fontWeight: 700, color: '#3ddc84', marginBottom: 12}}>Procedures generados</div>
        <div style={{fontFamily: 'Consolas, monospace', fontSize: 21, lineHeight: '32px', color: '#cdd6ea'}}>
          lab.&lt;tabla&gt;_insertar / _consultar<br />lab.&lt;tabla&gt;_actualizar / _eliminar<br />SECURITY INVOKER · sin EXECUTE a PUBLIC
        </div>
      </Interactive.Div>
      <Interactive.Div
        name="Flecha crea"
        style={{
          position: 'absolute', left: 1150, top: 560, fontFamily: 'Consolas, monospace', fontSize: 20, color: '#8a96b3',
          opacity: interpolate(frame, [138, 150], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        crea ─▶
      </Interactive.Div>
      <Interactive.Div
        name="Flecha GRANT"
        style={{
          position: 'absolute', left: 290, top: 690, fontFamily: 'Consolas, monospace', fontSize: 20, lineHeight: '28px', color: '#8a96b3',
          opacity: interpolate(frame, [180, 192], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        │<br />│ GRANT / REVOKE<br />▼
      </Interactive.Div>
      <Interactive.Div
        name="Caja roles"
        style={{
          position: 'absolute', left: 60, top: 820, width: 1800, border: '2px solid #ff5d6c', borderRadius: 18, padding: '18px 26px', background: '#0b1226',
          opacity: interpolate(frame, [186, 201], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [186, 201], ['0px 24px', '0px 0px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}),
        }}
      >
        <span style={{fontSize: 32, fontWeight: 700, color: '#ff5d6c'}}>Roles de PostgreSQL</span>
        <span style={{fontFamily: 'Consolas, monospace', fontSize: 21, color: '#cdd6ea', marginLeft: 30}}>
          crud_administrador · crud_supervisor · crud_vendedor — EXECUTE + permiso de tabla + USAGE del esquema
        </span>
      </Interactive.Div>
    </Fondo>
  );
};
