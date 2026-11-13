# Ads — anuncios

Carpeta para los videos de anuncios (p. ej. "La Receta"). Está lista pero todavía sin flujo definido; el único anuncio anterior se hizo con `scripts/generar_lote_mentor_objeciones.py` (slug `anuncio-receta`).

## Carpetas
- `prompt/` — `PROMPT_ads.md` (definir aquí el brief: oferta, público, CTA, duración) + `AJUSTES.md`.
- `entrada/` — material para el anuncio (videos, fotos, logos, textos).
- `resultado/` — anuncios terminados.
- `_operacion/` — recursos y trabajo de esta línea (clips descargados, configs, proyectos hyperframes, temporales).

## Regla de mantenimiento
Cada petición del usuario que deba valer para futuros anuncios se agrega a `prompt/AJUSTES.md` (fecha + regla + motivo) y, si cambia el código, también en `scripts/`. Antes de crear un anuncio, lee `prompt/PROMPT_ads.md` y `prompt/AJUSTES.md`.
