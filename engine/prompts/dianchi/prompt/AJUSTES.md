# Ajustes acumulados — Dianchi

Reglas que el usuario fue pidiendo y que valen por defecto para todos los videos nuevos. Se agregan al final con fecha; si una nueva contradice una anterior, se reemplaza.

## Formato y estructura
- 2026-11-11 · Sin hook al inicio: el video arranca con el título y el gancho (el guion de Dianchi), no con un video de mentor.
- 2026-11-11 · Máximo 30 s de video (≈ 23–28 s de voz). Guion de ~55–70 palabras + gancho + CTA.
- 2026-11-12 · Cada video plantea una objeción/miedo frecuente de la clienta (globo con la frase entre comillas) y la resuelve en 3 pasos con píldoras, sin prometer resultados ni inventar cifras.
- 2026-11-12 · CTA siempre "Guarda este audio para recordarlo antes de …"; la cinta fija dice "Guarda este audio y esta idea / para tu negocio"; tarjeta final con ícono de guardar.
- 2026-11-12 · Cada guion incluye una cautela real (avisar alergias, embarazo, condición médica, piel sensible…) cuando el servicio la requiere.

## Voz, sonido y animación
- Voz es-MX-JorgeNeural a 1.3x en todos los videos.
- 2026-11-11 · Nada de ASMR que suene a viento: sin whoosh en los cortes (`sin_whoosh`). Los sonidos van ligados al texto: pop al aparecer título/píldora/globo, ticks en las pausas (`sfx_texto`), ding en el CTA.
- Texto de cada píldora: máximo ~24 caracteres (si no, se corta en el borde).
- Las animaciones no se pisan: píldoras, globo y collage en intervalos distintos (`dianchi_lote.py verificar` avisa los CHOQUE y las escenas de menos de ~2 s).
- Cada escena dura ≥ ~2,5 s; las imágenes deben corresponder a lo que se dice (revisar la hoja de contacto antes de renderizar y reemplazar clips que no encajen).

## Salida
- Hyperframes entrega HEVC 10 bits: re-codificar a H.264 yuv420p (`dianchi_lote.py render` ya lo hace).
- Los videos van a `dianchi/resultado/` con nombre TÍTULO + fecha-hora.
- Al terminar un lote: revisar cuadros de cada video, `ffprobe` (códec/duración) y volumen máximo; no dar por listo solo porque exista el archivo.

## Cambios del 2026-11-13 (lote 3)
- 2026-11-13 · **Efectos tendencia por defecto** (`"efectos": true` en la config; `dianchi_lote.py` ya lo pone): zoom-punch + destello suave en cada cambio de toma, barra de progreso fucsia arriba, palabra activa del subtítulo con "pop", píldoras que entran con rebote y brillo, collage que flota con estrella pegatina. Sin sonidos nuevos (siguen las reglas de sonido de arriba). Implementado en `scripts/generar_dianchi.py` y `scripts/hf_collage.py`.
- 2026-11-13 · **No repetir rubros**: antes de proponer un lote, leer `prompt/rubros_hechos.md` y agregar al final los nuevos slugs.
- 2026-11-13 · Imágenes siempre nuevas: clips de Pexels sin repetir lo ya usado; revisar la hoja de contacto (`dianchi_lote.py hoja`) y cambiar con `reemplazar` los que no encajen (cara pintada, personas de espaldas con celular, otro oficio…).
- 2026-11-13 · Cambios de toma más frecuentes: añadir escenas extra en palabras del guion para que ningún tramo pase de ~4 s (antes llegaban a 5–6 s).
