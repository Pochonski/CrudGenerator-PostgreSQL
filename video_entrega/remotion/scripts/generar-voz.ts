// Genera la narración de cada escena con ElevenLabs y la guarda en public/voz/.
//
// Uso (desde video_entrega/remotion; la llave se lee de .env, que está en .gitignore):
//   node --env-file=.env scripts/generar-voz.ts --voces      lista voces disponibles
//   node --env-file=.env scripts/generar-voz.ts              genera los mp3 faltantes
//   node --env-file=.env scripts/generar-voz.ts --forzar     regenera todos
//
// Nunca imprime la llave. Los mp3 existentes se omiten para no gastar créditos.

import {existsSync, mkdirSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {NARRACION} from '../src/datos/narracion.ts';

// Voz premade multilingüe; se puede cambiar con ELEVENLABS_VOICE_ID.
const VOZ_POR_DEFECTO = 'cjVigY5qzO86Huf0OWal'; // Eric (premade); habla español con eleven_multilingual_v2
const MODELO = 'eleven_multilingual_v2';

const listarVoces = async (llave: string) => {
  const r = await fetch('https://api.elevenlabs.io/v1/voices', {headers: {'xi-api-key': llave}});
  if (!r.ok) throw new Error(`Error ${r.status} al listar voces: ${await r.text()}`);
  const {voices} = (await r.json()) as {voices: {voice_id: string; name: string; category: string; labels?: Record<string, string>}[]};
  for (const v of voices) {
    console.log(`${v.voice_id}  ${v.name.padEnd(28)} ${v.category.padEnd(10)} ${JSON.stringify(v.labels ?? {})}`);
  }
};

const generar = async (llave: string, forzar: boolean) => {
  const voz = process.env.ELEVENLABS_VOICE_ID ?? VOZ_POR_DEFECTO;
  for (const escena of NARRACION) {
    const destino = join('public', escena.archivo);
    if (existsSync(destino) && !forzar) {
      console.log(`= ${escena.archivo} (ya existe)`);
      continue;
    }
    const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voz}?output_format=mp3_44100_128`, {
      method: 'POST',
      headers: {'xi-api-key': llave, 'Content-Type': 'application/json', Accept: 'audio/mpeg'},
      body: JSON.stringify({
        text: escena.texto,
        model_id: MODELO,
        voice_settings: {stability: 0.5, similarity_boost: 0.75, style: 0.2, use_speaker_boost: true},
      }),
    });
    if (!r.ok) throw new Error(`Error ${r.status} en ${escena.id}: ${await r.text()}`);
    mkdirSync(dirname(destino), {recursive: true});
    writeFileSync(destino, Buffer.from(await r.arrayBuffer()));
    console.log(`+ ${escena.archivo}`);
  }
};

const main = async () => {
  const llave = process.env.ELEVENLABS_API_KEY;
  if (!llave) throw new Error('Falta ELEVENLABS_API_KEY: cree el archivo .env (ver comentario del script).');
  const args = new Set(process.argv.slice(2));
  if (args.has('--voces')) await listarVoces(llave);
  else await generar(llave, args.has('--forzar'));
};

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.message : e);
  process.exitCode = 1;
});
