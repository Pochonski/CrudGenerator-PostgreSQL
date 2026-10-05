import type React from 'react';
import {useMemo} from 'react';
import {Interactive, useCurrentFrame, useVideoConfig, type InteractivitySchema} from 'remotion';
import {construirLineaDeTiempo, type Linea, type Paso} from '../datos/linea-de-tiempo.ts';
import {COLOR, FUENTE} from '../tema.ts';

type TerminalProps = {
  readonly titulo: string; // pestaña activa
  readonly otraPestana?: string; // pestaña inactiva opcional, como en Windows Terminal
  readonly tamanoFuente: number;
  readonly pasos: readonly Paso[];
  readonly cursor?: boolean;
  readonly style?: React.CSSProperties;
};

const escapar = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Colorea la salida real sin alterar su texto.
const colorear = (s: string) => {
  const h = escapar(s);
  if (/^ERROR/.test(s)) return `<span style="color:${COLOR.error};font-weight:600">${h}</span>`;
  if (/^(CONTEXTO|DETALLE)/.test(s)) return `<span style="color:${COLOR.grisClaro}">${h}</span>`;
  return h
    .replace(/: success/g, `: <span style="color:${COLOR.exito};font-weight:700">success</span>`)
    .replace(/^- OK /, `- <span style="color:${COLOR.exito};font-weight:700">OK</span> `)
    .replace(/denegado \(42501\)/g, `<span style="color:${COLOR.error};font-weight:700">denegado (42501)</span>`)
    .replace(/deshabilitado/g, `<span style="color:${COLOR.error};font-weight:700">deshabilitado</span>`)
    .replace(/(?<!des)habilitado/g, `<span style="color:${COLOR.exito};font-weight:700">habilitado</span>`)
    .replace(/^(Conexión exitosa)$/, `<span style="color:${COLOR.exito};font-weight:700">$1</span>`)
    .replace(/(\d+ passed)/, `<span style="color:${COLOR.exito};font-weight:700">$1</span>`)
    .replace(/(0 FAIL\/FALLO)/, `<span style="color:${COLOR.exito};font-weight:700">$1</span>`);
};

const ESTILO_RESALTE: Record<string, React.CSSProperties> = {
  hl: {background: '#E3ECF5', boxShadow: `inset 4px 0 0 ${COLOR.azul}`, margin: '0 -24px', padding: '0 20px'},
  hly: {background: COLOR.resaltado, boxShadow: `inset 4px 0 0 ${COLOR.tinta}`, margin: '0 -24px', padding: '0 20px'},
  dim: {color: COLOR.grisClaro},
};

const Cursor = () => (
  <span style={{display: 'inline-block', width: '0.52em', height: '1.1em', background: COLOR.tinta, verticalAlign: '-0.18em', marginLeft: 2}} />
);

const TerminalInner: React.FC<TerminalProps> = ({titulo, otraPestana, tamanoFuente, pasos, cursor = true, style}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const {eventos, duracion} = useMemo(() => construirLineaDeTiempo(pasos), [pasos]);
  // La escena dura lo que dura su narración: si el tecleo no cabe, se acelera
  // para terminar 1 s antes del corte.
  const disponible = durationInFrames / fps - 1;
  const escala = disponible > 0 && duracion > disponible ? disponible / duracion : 1;
  const t = frame / fps / escala;

  type Fila = {prompt?: string; promptPs?: boolean; texto?: string; html?: string; tecleando?: boolean; cls?: string};
  const filas: Fila[] = [];
  for (const e of eventos) {
    if (e.t0 > t) break;
    if (e.k === 'o') {
      const L: Exclude<Linea, string> = typeof e.line === 'string' ? {t: e.line} : e.line;
      filas.push({html: colorear(L.t), cls: L.cls});
    } else if (e.k === 'c') {
      const n = Math.floor(Math.min(1, (t - e.t0) / (e.t1 - e.t0)) * e.text.length);
      filas.push({prompt: e.pr, promptPs: e.pr.startsWith('PS'), texto: e.text.slice(0, n), tecleando: t < e.t1});
    } else if (e.k === 'p') {
      filas.push({html: escapar(e.pr)});
    } else {
      const n = e.t1 > e.t0 ? Math.floor(Math.min(1, (t - e.t0) / (e.t1 - e.t0)) * e.text.length) : e.text.length;
      filas[filas.length - 1] = {...filas[filas.length - 1], texto: e.text.slice(0, n)};
    }
  }
  const parpadeo = cursor && Math.floor(t * 2) % 2 === 0;

  return (
    <Interactive.Div
      name="Ventana de terminal"
      style={{
        position: 'absolute',
        background: COLOR.blanco,
        border: `1px solid ${COLOR.linea}`,
        borderRadius: 6,
        overflow: 'hidden',
        boxShadow: '0 2px 0 #00000008',
        ...style,
      }}
    >
      <div style={{height: 44, display: 'flex', alignItems: 'flex-end', gap: 4, padding: '0 12px', background: COLOR.codigoFondo, borderBottom: `1px solid ${COLOR.linea}`, fontSize: 18}}>
        <span style={{background: COLOR.blanco, border: `1px solid ${COLOR.linea}`, borderBottom: 'none', borderRadius: '6px 6px 0 0', padding: '8px 18px', color: COLOR.tinta, fontWeight: 600, marginBottom: -1, boxShadow: `inset 0 3px 0 ${COLOR.azul}`}}>
          {titulo}
        </span>
        {otraPestana ? <span style={{padding: '8px 18px', color: COLOR.gris}}>{otraPestana}</span> : null}
        <span style={{padding: '8px 12px', color: COLOR.grisClaro}}>+</span>
      </div>
      <div
        style={{
          position: 'absolute', top: 44, left: 0, right: 0, bottom: 0, padding: '16px 24px',
          display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden',
          fontFamily: FUENTE.mono, fontSize: tamanoFuente,
          lineHeight: 1.45, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: COLOR.tinta,
        }}
      >
        {filas.map((f, i) => {
          const ultima = i === filas.length - 1;
          return (
            <div key={i} style={{minHeight: '1lh', flexShrink: 0, ...(f.cls ? ESTILO_RESALTE[f.cls] : {})}}>
              {f.prompt !== undefined ? <span style={{color: f.promptPs ? COLOR.gris : COLOR.azul, fontWeight: 600}}>{f.prompt}</span> : null}
              {f.html !== undefined ? <span dangerouslySetInnerHTML={{__html: f.html}} /> : null}
              {f.texto !== undefined ? (
                <span style={f.prompt !== undefined ? {color: COLOR.tinta, fontWeight: 600} : {color: COLOR.azul, fontWeight: 700}}>{f.texto}</span>
              ) : null}
              {ultima && (f.tecleando || parpadeo) ? <Cursor /> : null}
            </div>
          );
        })}
      </div>
    </Interactive.Div>
  );
};

const terminalSchema = {
  titulo: {type: 'text-content', default: 'psql — devdb', description: 'Pestaña activa'},
  tamanoFuente: {type: 'number', default: 23, min: 14, max: 40, step: 1, description: 'Tamaño de letra', hiddenFromList: false},
} as const satisfies InteractivitySchema;

export const Terminal = Interactive.withSchema({
  Component: TerminalInner,
  componentName: '<Terminal>',
  schema: terminalSchema,
  wrapInSequence: true,
});
