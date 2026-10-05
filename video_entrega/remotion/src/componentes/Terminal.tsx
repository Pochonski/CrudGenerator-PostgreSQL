import type React from 'react';
import {useMemo} from 'react';
import {Interactive, useCurrentFrame, useVideoConfig, type InteractivitySchema} from 'remotion';
import {construirLineaDeTiempo, type Linea, type Paso} from '../datos/linea-de-tiempo.ts';

type TerminalProps = {
  readonly titulo: string;
  readonly tamanoFuente: number;
  readonly pasos: readonly Paso[];
  readonly cursor?: boolean;
  readonly style?: React.CSSProperties;
};

const escapar = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Colorea la salida real sin alterar su texto.
const colorear = (s: string) => {
  const h = escapar(s);
  if (/^ERROR/.test(s)) return `<span style="color:#ff5d6c">${h}</span>`;
  if (/^(CONTEXTO|DETALLE)/.test(s)) return `<span style="color:#5c6888">${h}</span>`;
  return h
    .replace(/: success/g, ': <span style="color:#3ddc84">success</span>')
    .replace(/^- OK /, '- <span style="color:#3ddc84">OK</span> ')
    .replace(/denegado \(42501\)/g, '<span style="color:#ffc845">denegado (42501)</span>')
    .replace(/deshabilitado/g, '<span style="color:#ffc845">deshabilitado</span>')
    .replace(/(?<!des)habilitado/g, '<span style="color:#3ddc84">habilitado</span>')
    .replace(/^(Conexión exitosa)$/, '<span style="color:#3ddc84">$1</span>')
    .replace(/(\d+ passed)/, '<span style="color:#3ddc84">$1</span>')
    .replace(/(0 FAIL\/FALLO)/, '<span style="color:#3ddc84">$1</span>');
};

const ESTILO_RESALTE: Record<string, React.CSSProperties> = {
  hl: {background: '#1a2a55', boxShadow: 'inset 4px 0 0 #4ea8ff', margin: '0 -24px', padding: '0 20px'},
  hly: {background: '#3a2f0e', boxShadow: 'inset 4px 0 0 #ffc845', margin: '0 -24px', padding: '0 20px'},
  dim: {color: '#5c6888'},
};

const Cursor = () => (
  <span style={{display: 'inline-block', width: '0.52em', height: '1.1em', background: '#4ea8ff', verticalAlign: '-0.18em', marginLeft: 2}} />
);

const TerminalInner: React.FC<TerminalProps> = ({titulo, tamanoFuente, pasos, cursor = true, style}) => {
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
        background: '#070b16',
        border: '1px solid #1e2a4a',
        borderRadius: 16,
        overflow: 'hidden',
        boxShadow: '0 30px 80px #0008',
        ...style,
      }}
    >
      <div style={{height: 44, display: 'flex', alignItems: 'center', gap: 10, padding: '0 18px', background: '#0c1222', borderBottom: '1px solid #1e2a4a', fontSize: 20, color: '#8a96b3'}}>
        <span style={{width: 14, height: 14, borderRadius: 7, background: '#ff5f57'}} />
        <span style={{width: 14, height: 14, borderRadius: 7, background: '#febc2e'}} />
        <span style={{width: 14, height: 14, borderRadius: 7, background: '#28c840'}} />
        <span style={{marginLeft: 12}}>{titulo}</span>
      </div>
      <div
        style={{
          position: 'absolute', top: 44, left: 0, right: 0, bottom: 0, padding: '16px 24px',
          display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden',
          fontFamily: '"Cascadia Mono", "Cascadia Code", Consolas, monospace', fontSize: tamanoFuente,
          lineHeight: 1.45, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#e6ebf5',
        }}
      >
        {filas.map((f, i) => {
          const ultima = i === filas.length - 1;
          return (
            <div key={i} style={{minHeight: '1lh', flexShrink: 0, ...(f.cls ? ESTILO_RESALTE[f.cls] : {})}}>
              {f.prompt !== undefined ? <span style={{color: f.promptPs ? '#4fd6e8' : '#8b7bff'}}>{f.prompt}</span> : null}
              {f.html !== undefined ? <span dangerouslySetInnerHTML={{__html: f.html}} /> : null}
              {f.texto !== undefined ? (
                <span style={f.prompt !== undefined ? {color: '#fff', fontWeight: 600} : {color: '#4ea8ff', fontWeight: 700}}>{f.texto}</span>
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
  titulo: {type: 'text-content', default: 'psql — devdb', description: 'Título de la ventana'},
  tamanoFuente: {type: 'number', default: 23, min: 14, max: 40, step: 1, description: 'Tamaño de letra', hiddenFromList: false},
} as const satisfies InteractivitySchema;

export const Terminal = Interactive.withSchema({
  Component: TerminalInner,
  componentName: '<Terminal>',
  schema: terminalSchema,
  wrapInSequence: true,
});
