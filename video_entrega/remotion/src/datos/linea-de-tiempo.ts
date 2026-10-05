// Motor de "terminal animada": convierte un guion de comandos, prompts y
// salidas en eventos con tiempo (segundos). Sin dependencias de React para
// poder calcular duraciones de escena desde Node.

export type Linea = string | {readonly t: string; readonly cls?: Resalte};
export type Resalte = 'hl' | 'hly' | 'dim';

export type Paso =
  | {readonly c: string; readonly pr?: string} // comando tecleado
  | {readonly o: readonly Linea[]; readonly hold?: number} // salida
  | {readonly p: string; readonly a: string; readonly hold?: number} // prompt + respuesta
  | {readonly w: number} // espera
  | {readonly skip: true}; // linea "⋮" de salida omitida

export type Evento =
  | {readonly k: 'c'; readonly pr: string; readonly text: string; readonly t0: number; readonly t1: number}
  | {readonly k: 'o'; readonly line: Linea; readonly t0: number}
  | {readonly k: 'p'; readonly pr: string; readonly t0: number}
  | {readonly k: 'a'; readonly text: string; readonly t0: number; readonly t1: number};

export const PROMPT_PS = 'PS C:\\CrudGenerator> ';
export const PROMPT_DB = 'devdb=# ';
export const PROMPT_DB_CONT = 'devdb(# ';

// Ritmo: comandos a 55 caracteres/s, respuestas a 12 caracteres/s,
// salida a 0,045 s por linea.
export const construirLineaDeTiempo = (pasos: readonly Paso[]) => {
  let t = 0;
  const eventos: Evento[] = [];
  for (const p of pasos) {
    if ('c' in p) {
      const d = Math.max(0.4, p.c.length / 55);
      eventos.push({k: 'c', pr: p.pr ?? PROMPT_DB, text: p.c, t0: t, t1: t + d});
      t += d + 0.35;
    } else if ('o' in p) {
      p.o.forEach((line, i) => eventos.push({k: 'o', line, t0: t + i * 0.045}));
      t += p.o.length * 0.045 + (p.hold ?? 0.7);
    } else if ('p' in p) {
      eventos.push({k: 'p', pr: p.p, t0: t});
      t += 0.3;
      const d = p.a ? Math.max(0.18, p.a.length / 12) : 0;
      eventos.push({k: 'a', text: p.a, t0: t, t1: t + d});
      t += d + (p.hold ?? 0.3);
    } else if ('w' in p) {
      t += p.w;
    } else {
      eventos.push({k: 'o', line: {t: '  ⋮', cls: 'dim'}, t0: t});
      t += 0.2;
    }
  }
  return {eventos, duracion: t};
};
