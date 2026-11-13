# Dianchi — videos de rubros (belleza), sin hook

Videos de rubro con guion de Dianchi: escenas B-roll (Pexels) según las palabras del guion, voz Jorge 1.3x, subtítulos, píldoras de pasos, collage y tarjeta final "Guarda este audio…". 30 s máximo.

## Carpetas
- `prompt/` — `rubros_hechos.md` (lista para no repetir), `dianchi_rubros.md` (reglas del prompt) + `AJUSTES.md` (todo lo que el usuario fue pidiendo; **se aplica siempre**) + `LEEME_que_prompt_usar.md`.
- `entrada/` — material para armar los videos: `videos/` (B-roll por carpeta) e `imagenes/` (biblioteca de tarjetas y fotos).
- `resultado/` — videos terminados (H.264, 1080x1920).
- `_operacion/` — recursos y trabajo de esta línea: `recursos/<slug>/` (clips descargados, fotos del collage), `lote/` (configs .json y hojas de contacto), `hf/` (proyectos hyperframes), `_trabajo/` (temporales). Se puede regenerar; no es entrega.

## Cómo se genera
`scripts/dianchi_lote.py` (lista `RUBROS` con guion, escenas, pasos, objeción): modos `verificar` → `descargar` → `hoja` → `render`. Salida: `dianchi/resultado`. Un video suelto: `scripts/generar_dianchi.py` con un config (clave `"operacion": "dianchi/_operacion"`).

## Regla de mantenimiento (importante)
Cada vez que el usuario pida un cambio que deba valer para videos futuros (estilo, texto, sonidos, estructura del guion, CTA, duración, voz…):
1. Agrégalo a `prompt/AJUSTES.md` con fecha, la regla y el motivo (una o dos líneas).
2. Si afecta al código, cámbialo en `scripts/` para que quede por defecto.
3. Si contradice una regla anterior, reemplázala (no dejes las dos).
No dejes la regla solo en la conversación. Antes de escribir guiones nuevos, lee `prompt/dianchi_rubros.md` y `prompt/AJUSTES.md`.
