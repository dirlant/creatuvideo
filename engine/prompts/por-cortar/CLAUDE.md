# Por cortar — cortar un video largo, quitar silencios y poner el patrón de interrupción

Aquí entra un video largo (clase, charla, presentador) y salen clips verticales listos: sin silencios, con cambios de plano, título gancho y el patrón de interrupción (hook de mentor + sonidos) al inicio.

## Carpetas
- `prompt/` — `PROMPT_cortar.md` (cómo se corta y qué se espera) + `AJUSTES.md` (lo que el usuario fue pidiendo; **se aplica siempre**).
- `entrada/` — **sube aquí el video largo** (y videos hablados por animar).
- `resultado/` — clips terminados.
- `hook/` — videos del patrón de interrupción (`mentor.mp4`, `mentor_recorte.webm`, hooks por rubro) y `LEEME_HOOKS.md`.
- `_operacion/` — recursos y trabajo: `clips_trabajo/` (modelo YOLO, transcripciones, definiciones de clips), `clips_trabajo2/`, `animar_trabajo/`, `procesados.txt`, `titulos_usados.txt`. Regenerable.

## Flujo (comandos en `instalacion\agente\herramientas.ps1`)
1. `Transcribir` (Whisper, tiempos por palabra) → 2. `Cortar-Clips` (`crear_clips_v2.py` para clase con alumnas; `crear_clips.py` para presentador de pie): quita silencios, cambia de plano cada ~4 s con seguimiento YOLO → 3. `Unir-HookAsmr` (hook + título + sonidos en cada cambio de plano) → 4. `Animar-Video` / `Agregar-Imagenes` si el video hablado necesita animación.

## Regla de mantenimiento (importante)
Cuando el usuario pida un cambio que deba valer para futuros cortes (duración de clips, criterio de silencios, estilo del título, hook, sonidos, subtítulos…):
1. Agrégalo a `prompt/AJUSTES.md` (fecha + regla + motivo).
2. Si afecta al código, cámbialo en `scripts/` para que quede por defecto.
3. Si contradice una regla anterior, reemplázala.
Antes de cortar, lee `prompt/PROMPT_cortar.md` y `prompt/AJUSTES.md`.
