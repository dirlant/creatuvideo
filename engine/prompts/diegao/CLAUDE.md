# Diegao — videos de mentor para dueñas de salón

Videos de 30 s con la voz/guion de Diegao (mentor de negocios), hechos con cortes aleatorios de 3 s de los videos del evento La Receta. Cada video toca un dolor del salón, trae una objeción de redes, la resuelve en 3–4 pasos y cierra con "Sígueme". Sin hook: solo narración + animación ligada a ella; cortes cada ~3 s con soplido suave, sonido "bueno" en palabras positivas y "malo" en negativas (ver prompt/AJUSTES.md).

## Carpetas
- `prompt/` — `diegao_mentor.md` (reglas del prompt) + `AJUSTES.md` (lo que el usuario fue pidiendo; **se aplica siempre**) + `LEEME_que_prompt_usar.md`.
- `entrada/` — `evento-receta/` (videos del evento; sube aquí material nuevo).
- `resultado/` — videos terminados.
- `_operacion/` — `recursos/` (proxies 540p, cortes de 3 s por video, tarjetas del collage), `lote/` (configs .json por video), `hf/` (proyectos hyperframes), `_trabajo/`, `rev/` (cuadros de revisión). Regenerable.

## Cómo se genera
`scripts/diegao_lote.py <ffmpeg> preparar|render [slug…]`; la lista `V` (dolor, gancho, guion, objeción, pasos) está dentro del script. Salida: `diegao/resultado`. Motor: `scripts/generar_dianchi.py` con `"operacion": "diegao/_operacion"`.

## Regla de mantenimiento (importante)
Cuando el usuario pida un cambio que deba valer para videos futuros (tono, estructura, CTA, sonidos, duración, tipo de gancho…):
1. Agrégalo a `prompt/AJUSTES.md` (fecha + regla + motivo).
2. Si afecta al código, cámbialo en `scripts/` para que quede por defecto.
3. Si contradice una regla anterior, reemplázala.
Antes de escribir guiones nuevos lee `prompt/diegao_mentor.md` y `prompt/AJUSTES.md`.
