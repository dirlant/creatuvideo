# Prompt — por cortar

Eres mi agente de edición. Te dejo un video largo en `por-cortar/entrada/`. Lo conviertes en clips verticales (1080x1920) para Reels/TikTok y los dejas en `por-cortar/resultado/`.

## Qué hacer
1. **Transcribir** con Whisper (español, tiempos por palabra) y elegir los mejores momentos: ideas completas de 30–90 s que se entiendan solas.
2. **Cortar**: quitar silencios y muletillas, cambio de plano cada ~4 s, encuadre vertical con seguimiento de la persona (YOLO). Para clase con alumnas usar la versión 2 (presentador al fondo, alumnas en primer plano); para presentador de pie, la versión 1.
3. **Patrón de interrupción**: al inicio de cada clip va el hook (`por-cortar/hook/`, p. ej. "Si yo fuera tu mentor, te diría lo siguiente"), con el título gancho encima y sonidos en los cambios de plano.
4. **Título**: 3 líneas, 40–50 caracteres en total, sin emojis, palabra clave entre *asteriscos* (se dibuja en Billabong, sin tildes ni ñ); no repetir la frase del hook. Etiqueta de categoría arriba, dentro de la zona segura de TikTok.
5. Registrar lo hecho en `_operacion/procesados.txt` y `_operacion/titulos_usados.txt` (no repetir títulos).

## Verificación
Mirar cuadros reales de cada clip, duración y volumen antes de darlo por listo.

## Ajustes
Aplica además todo lo que está en `AJUSTES.md` (reglas que el usuario fue pidiendo).
