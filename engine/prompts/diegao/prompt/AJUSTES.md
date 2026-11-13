# Ajustes acumulados — Diegao

Reglas que el usuario fue pidiendo y que valen por defecto. Se agregan al final con fecha; si una nueva contradice una anterior, se reemplaza.

## Contenido
- 2026-11-11 · Temas de negocio para dueñas de salón (publicidad, administración, finanzas, agenda vacía, precios, inasistencias, marketing…), siempre a partir de una **objeción frecuente en redes**, que el video resuelve.
- 2026-11-11 · Formato storytelling con imágenes y videos; guion según el prompt de Diegao (tú a tú, español neutro, gancho como afirmación sin signos de pregunta, sin descripciones visuales, sin cifras inventadas).
- 2026-11-12 · Cada video lleva un tipo de gancho distinto (Verdad, Revelación, Disruptivo, Anti-hook, Provocación, Contraintuitivo, Reencuadre…) y 3–4 pasos en píldoras.
- 2026-11-12 · **CTA: "Sígueme para más ideas para tu negocio"** (tarjeta final con ícono de seguir, cinta fija "Sígueme para más ideas / para tu negocio", ding en "Sígueme"). No usar "Guarda".

## Imagen y sonido
- 2026-11-11 · Material: solo los videos de `entrada/evento-receta`. Cortes de 3 s al azar (verticales, sin repetir mientras haya otros), un corte nuevo cada ~2–3 s en palabras del guion; collage con fotogramas de los mismos cortes.
- 2026-11-11 · Máximo 30 s (≈ 24–27 s de voz). Voz es-MX-JorgeNeural 1.3x.
- 2026-11-11 · Sin ASMR tipo viento: sin whoosh en los cortes; sonidos ligados al texto (pop en título/globo/píldoras/collage, tick en las pausas, ding en el CTA).
- Texto de píldora ≤ ~24 caracteres; sin choques entre animaciones (`diegao_lote.py preparar` reintenta collage 2,0/1,6/1,2 s o lo quita).

## Salida
- H.264 yuv420p 1080x1920 (hyperframes entrega HEVC 10 bits; el script lo re-codifica). Nombre: TÍTULO + fecha-hora en `diegao/resultado/`.
- Revisar cuadros y audio de cada video antes de darlo por terminado.

## Cambios del 2026-11-12 (reemplazan reglas anteriores de sonido/hook)
- 2026-11-12 · **Sin hook de "Si yo fuera tu mentor"**: Diegao no usa ningún video/audio de hook (ni `mentor.mp4` ni el recorte). Solo narración (Jorge 1.3x) y animación ligada a lo que se dice. El gancho es la primera frase del guion, hablada por la voz en off.
- 2026-11-12 · **Patrón de interrupción cada ~3 s**: cambio de toma (corte distinto del evento, alterna empuje de cámara in/out) cada 2.3–3.0 s, siempre en el inicio de una palabra.
- 2026-11-12 · **Sonidos sin exceso** (reemplaza "pop/tick en el texto"): (1) soplido suave (`swish`) en cada cambio de toma; (2) sonido **"bueno"** (dos notas que suben) en 2 palabras clave positivas por video; (3) sonido **"malo"** (tono grave que baja) en 1–2 palabras negativas; (4) ding en "Sígueme". Nada más: sin pop en píldoras/collage, sin clics en las pausas. Cada video define `buenas=[(palabra, n)]` y `malas=[(palabra, n)]` en `scripts/diegao_lote.py`.
- 2026-11-12 · Las palabras "buenas" y "malas" deben serlo en su contexto (no marcar como malo "pequeño" en "un salón pequeño compite…"); no poner dos sonidos a menos de ~1 s.
- 2026-11-12 · El video de publicidad también usa CTA "Sígueme" (antes llevaba "Guarda").
