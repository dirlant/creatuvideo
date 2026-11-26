# Personalizados — ediciones de video a medida

Aquí se hacen ediciones personalizadas a partir de los videos de la persona, tomando como guía los videos de referencia que ella eligió.

## Las 4 carpetas (las rutas exactas vienen en cada instrucción de la app)
- **Videos sin edición**: los originales. **Nunca los modifiques ni los borres**; trabaja sobre copias o leyéndolos.
- **Referencias**: videos de inspiración. Junto a ellos está `referencias.json` con **qué le gusta a la persona de cada video** (ritmo, tipografía, transiciones, color, sonido, estructura…). Léelo ANTES de editar y reproduce ese estilo.
- **Exportados**: aquí se entrega el resultado final. Nombre claro y fecha; H.264 yuv420p, AAC.
- **Temporales**: tu zona de trabajo (cortes, audios, proyectos HyperFrames, cuadros de revisión). Se puede borrar después; nunca guardes aquí lo final.

## Motor de edición
- **HyperFrames** (HTML → video, cuadro a cuadro) se usa con `npx --yes hyperframes@0.9.96 …` (Node y npm ya están disponibles; esa versión se descargó y respondió bien).
- **No hace falta instalar Remotion**: HyperFrames cubre lo mismo. Si la persona trae un proyecto Remotion existente, hay un conversor a HyperFrames.
- Para cortes, mezcla de audio y codificación usa ffmpeg (la app lo localiza; la ruta está en Ajustes).

## Cómo trabajar
1. Lee `referencias.json` y mira cuadros reales de cada referencia para entender el estilo.
2. Propón brevemente el plan (qué videos, qué estilo, duración) y luego ejecútalo.
3. Trabaja en Temporales; entrega en Exportados.
4. Antes de dar algo por listo, revisa cuadros, duración, audio y que no haya cortes ni texto montado.
5. Si la persona pide una regla que deba valer a futuro, anótala en `prompt/AJUSTES.md` (fecha + regla + motivo).
