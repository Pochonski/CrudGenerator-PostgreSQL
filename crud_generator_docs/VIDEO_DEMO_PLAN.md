# Video de evidencia (§10) y demo en vivo (§11)

Documento único sobre el video del proyecto: qué se entrega, cómo se produjo,
qué muestra cada escena, cómo regenerarlo y qué tener en cuenta en la demo en
vivo. Reemplaza a los guiones de grabación anteriores (`GUION_JOSEPH_VIDEO.md`,
`GUIN_VIDEO.md`), que se retiraron: el video ya no se graba a mano.

## 1. Entregable

| Qué | Dónde |
|---|---|
| Video final (Entregable 3) | `video_entrega/CrudGenerator_PostgreSQL_voz.mp4` — 1920×1080, 30 fps, H.264 + AAC, ≈5:20, narrado en español |
| Proyecto que lo genera | `video_entrega/remotion/` (Remotion 4.0.532, React + TypeScript) |
| Reset del laboratorio | `crud_generator_docs/reset_video_windows.ps1` |

Los `.mp4` no se versionan (están en `.gitignore`): se regeneran con el proyecto
Remotion y se entregan aparte.

## 2. Cómo se produjo

El video no es una grabación de pantalla: es una presentación animada generada
por código, con el mismo estilo que el ejemplo de referencia del curso (portada,
arquitectura, un bloque por paso del enunciado, pruebas, decisiones técnicas y
cierre). Aun así, **todo lo que aparece en las terminales es real**:

1. Se reseteó `devdb` (PostgreSQL 18 local, `127.0.0.1:5432`) con
   `reset_video_windows.ps1`.
2. Se ejecutó el flujo completo con `crudgen` y `psql` (04-10-2026) y se
   capturó la salida exacta de cada paso.
3. Esas salidas están copiadas literalmente en
   `video_entrega/remotion/src/datos/capturas.ts`. Única adaptación: los errores
   de `psql` se muestran sin el prefijo `psql:archivo.sql:N:` porque en pantalla
   se presentan como sesión interactiva.
4. La base se dejó reseteada al terminar.

Las cifras del video también son reales: `pytest` → **311 passed, 5 skipped**
(los 5 de integración requieren `CRUDGEN_TEST_POSTGRES=1`); harness SQL →
**153 OK, 0 FAIL** (`tests/evidence/fase2_reales.log`); 16 procedures generados
en la corrida (4 tablas × 4).

La narración se generó con ElevenLabs (modelo `eleven_multilingual_v2`, voz
premade "Eric") a partir del guion en `src/datos/narracion.ts`.

## 3. Escenas (orden del video)

| # | Escena | Paso §10 | Qué muestra |
|---|---|---|---|
| 1 | Portada | — | Título, curso, integrantes (Armando: Python + interfaz; Joyce: extensión; Joseph: seguridad, integración y pruebas) |
| 2 | Arquitectura | — | crudgen → extensión `crud_generator` (`analyze_table`, `generate_crud`) → catálogos (`pg_namespace`, `pg_class`, `pg_attribute`, `pg_attrdef`, `pg_index`) → procedures `lab.<tabla>_insertar/_consultar/_actualizar/_eliminar` → roles con GRANT/REVOKE |
| 3 | Instalación | 1 | `CREATE EXTENSION crud_generator;`, `GRANT USAGE … TO crud_admin`, versión 1.0 en esquema `crud_generator` |
| 4 | Conexión y detección | 2–3 | `crudgen` se conecta a `devdb`, asume `crud_admin` y verifica extensión, versión, esquema y USAGE |
| 5 | Esquema y tablas | 4–5 | Listados leídos del catálogo; se elige `lab`, `producto` y las 4 operaciones |
| 6 | Generación | 6 | Estructura de `lab.producto` (PK, tipos, NOT NULL) y 4 × `success` con EXECUTE revocado de PUBLIC |
| 7 | Casos especiales | 6 | `detalle_factura` (PK compuesta) y `ticket` (IDENTITY ALWAYS + DEFAULT) |
| 8 | Ejecución | 7 | `CALL` reales: INSERT, READ por PK, PK compuesta, ticket con id generado |
| 9 | Privilegios | 8 | Matriz administrador I+R+U+D / supervisor I+R+U / vendedor I+R, aplicada con GRANT/REVOKE reales |
| 10 | Verificación | 8 | La app ejecuta cada procedure con cada rol: 12/12 OK |
| 11 | Validación por rol | 9 | Vendedor sin UPDATE (42501), supervisor sin DELETE (42501), administrador elimina y el READ posterior da fila inexistente (P0002) |
| 12–14 | Tabla nueva | 10 | `lab.tabla_video_nueva` creada después del desarrollo: crudgen la descubre, genera su CRUD y sus procedures funcionan (INSERT con 2 argumentos, DEFAULT `now()`), vendedor sin READ → 42501 |
| 15 | Pruebas | — | pytest 311 passed + extracto del harness SQL (153 OK) |
| 16–20 | Decisiones técnicas | — | SECURITY INVOKER + doble llave; REVOKE EXECUTE de PUBLIC; SQL dinámico con `%I`/`%L`; INSERT que respeta IDENTITY/DEFAULT; regeneración controlada (`procedure_conflict`, `do_replace`) y READ por PK (P0002) |
| 21 | Cierre | — | Cifras: 311 pruebas, 153 verificaciones, 16 procedures, PostgreSQL 18 |

## 4. Proyecto Remotion (`video_entrega/remotion/`)

```
src/
  Root.tsx                 registra el video y cada escena (carpeta "Escenas")
  VideoDemo.tsx            TransitionSeries con fundidos de 12 cuadros
  datos/capturas.ts        salidas reales de crudgen y psql
  datos/linea-de-tiempo.ts convierte comandos/prompts/salidas en eventos con tiempo
  datos/narracion.ts       guion hablado, un texto por escena
  componentes/             Terminal (tecleo animado), EncabezadoPaso, Leyenda, Fondo
  escenas/                 una escena por archivo (Portada, Paso1Instalacion, …)
scripts/generar-voz.ts     genera public/voz/*.mp3 con ElevenLabs
public/voz/                21 mp3 de narración (versionados)
```

- **Duración**: la fija la voz. `calculateMetadata` (en `Root.tsx`) mide cada
  mp3 con `getAudioDurationInSeconds` y cada escena dura su audio + 0,5 s.
  Si una terminal tarda más que su narración, `Terminal` acelera el tecleo para
  terminar 1 s antes del corte.
- **Edición**: textos, colores y tamaños de encabezados, leyendas y decisiones
  se editan desde Remotion Studio (componentes `Interactive.withSchema`).

### Regenerar

Desde `video_entrega/remotion/`:

```bash
npm install
npm run dev
```

Abre Remotion Studio (`http://localhost:3000`) para previsualizar.

Cambiar la narración: editar `src/datos/narracion.ts`, borrar el mp3 afectado
en `public/voz/` y ejecutar (requiere un archivo `.env`, ignorado por git, con
`ELEVENLABS_API_KEY=...`):

```bash
node --env-file=.env scripts/generar-voz.ts
```

Solo genera los mp3 que faltan (`--forzar` regenera todos; `--voces` lista las
voces de la cuenta; `ELEVENLABS_VOICE_ID` cambia la voz).

Renderizar el MP4 final:

```bash
npx remotion render CrudGeneratorDemo ../CrudGenerator_PostgreSQL_voz.mp4
```

Cambiar una salida de terminal exige volver a capturarla de una corrida real
(sección 2) para que el video siga mostrando solo resultados verdaderos.

## 5. Demo en vivo (§11) — lo que hay que saber

El enunciado pide hacerlo **solo con la aplicación Python**: conectar, detectar
la extensión, elegir esquema/tablas, generar, mostrar procedures, elegir roles,
asignar privilegios, comprobarlos y operar con los procedures. `crudgen` cubre
todo: los pasos `Verificar` (ejecuta cada procedure como cada rol) y `Ejecutar`
(CALL con valores) resuelven §11.9 y §11.10 sin `psql`.

Antes de empezar:

```powershell
$env:PGPASSWORD = '<clave del laboratorio>'
powershell -ExecutionPolicy Bypass -File crud_generator_docs\reset_video_windows.ps1
```

Deja `lab` con 6 tablas, sin rutinas y **sin** la extensión (instalarla es parte
de la demo: `CREATE EXTENSION crud_generator;` + `GRANT USAGE ON SCHEMA
crud_generator TO crud_admin;`).

Comportamiento real de `crudgen` (verificado en la corrida del video; los
guiones viejos lo describían mal):

- **La matriz se pregunta por operación, no por rol**: primero `Permitir
  INSERT?` para cada rol elegido, luego READ, UPDATE y DELETE. Para la matriz
  administrador/supervisor/vendedor (roles `2,3,4`) las 12 respuestas son:
  `s s s` · `s s s` · `s s n` · `s n n`.
- **Con varias tablas, todo se repite por tabla**: `Roles`, la matriz,
  `Verificar` y `Ejecutar` se preguntan una vez por cada tabla generada.
- La numeración sale del catálogo en orden alfabético: esquemas
  `crud_generator=1, lab=2, public=3`; tablas `bitacora=1, catalogo_especial=2,
  detalle_factura=3, producto=4, tabla_virgen=5, ticket=6`; roles
  `crud_admin=1, crud_administrador=2, crud_supervisor=3, crud_vendedor=4,
  postgres=5`. Una tabla nueva se intercala alfabéticamente (por ejemplo
  `tabla_video_nueva` queda como 5): **elegir siempre por nombre**.
- `Reemplazar: n` en una base recién reseteada; si un procedure ya existe la
  extensión responde `procedure_conflict` (no es un error del programa).
- Resultados esperados: permiso denegado = **42501**; READ de una fila
  inexistente = **P0002**.

Detalles que pueden sorprender:

- Si `detalle_factura` referencia un producto, el DELETE de ese producto falla
  por la llave foránea (correcto en PostgreSQL). Para mostrar el ciclo de
  borrado, usar un producto sin detalle.
- `Verificar` ejecuta las operaciones dentro de una transacción que se
  revierte, pero las secuencias IDENTITY no retroceden: el primer `ticket`
  insertado después puede recibir id 2 en vez de 1.
- La tabla del docente: crear la tabla (por ejemplo `SET ROLE crud_admin;
  CREATE TABLE lab.<nombre> (…);`), volver a `crudgen` y elegirla por nombre;
  no hace falta tocar Python ni la extensión.
