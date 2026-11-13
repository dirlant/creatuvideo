# CreaTuVideo

Panel de escritorio (Windows) para generar videos de **Dianchi**, **Diegao** y **cortes con silencios**, con Claude Code integrado.

## Qué hace la versión 0.1
- Eliges la línea (Dianchi, Diegao, Cortar y silencios, Claude Code) y los videos del lote; la app ejecuta los scripts del motor y muestra el registro.
- Eliges las carpetas: resultados (por línea), imágenes, videos de relleno, videos fuente de Diegao y video a cortar. Se enlazan sin copiar nada.
- Predeterminados: voz, efectos de tendencia y “usar mis videos de relleno en vez de Pexels”.
- **Claude Code**: abre una ventana con `claude` en la carpeta de trabajo, ya con las reglas de la línea (`CLAUDE.md` + `prompt/AJUSTES.md`). Cada petición que deba valer a futuro se anota ahí.
- **Se actualiza desde este repositorio** (ver abajo).

## Estructura del repositorio
```
main.js, preload.js, renderer/   la app (interfaz); renderer/ se actualiza sin reinstalar
engine/scripts/                  motor Python (dianchi_lote, diegao_lote, generar_dianchi, hf_collage…)
engine/assets/                   fuentes (Billabong, Poppins)
engine/prompts/<línea>/          CLAUDE.md y prompt/ (reglas, AJUSTES.md) de cada línea
```

## Carpeta de trabajo
Por defecto `Documentos\CreaTuVideo` (cambiable en Ajustes). La app copia ahí `scripts/` y `_operacion/_work`, y deja `dianchi/`, `diegao/`, `por-cortar/`, `ads/` con `prompt/`, `entrada/`, `resultado/` y `_operacion/`. Las carpetas que elijas en Ajustes se enlazan (junction) en el lugar de `resultado/` y `entrada/`.

## Actualizaciones
1. Publicas cambios en `main` de este repositorio (`engine/` y `renderer/`).
2. La app compara el último commit de `main` con el que tiene instalado (al abrir, o con “Buscar actualización”).
3. “Actualizar ahora” descarga el repositorio y reemplaza el motor y la interfaz en `%APPDATA%\creatuvideo\overlay`, luego se reinicia.
- Si el repositorio es **privado**, hace falta un token de GitHub de solo lectura (Ajustes → Claves) o tener `gh` con sesión iniciada.
- Los cambios en `main.js`, `preload.js` o `package.json` (el “caparazón”) requieren un instalador nuevo. Un instalador nuevo descarta el overlay anterior.
- Los prompts (`prompt/*.md`) no se pisan si ya los cambiaste: la versión nueva queda al lado como `*.actualizado.md`.

## Desarrollo
```
npm install
npm start          # abrir la app
npm run dist       # instalador en dist\ (NSIS)
```
Requisitos para generar videos: uv, FFmpeg y Node.js (la app ofrece instalarlos con winget), Claude Code con sesión iniciada, y una clave de Pexels si no usas tus propios videos de relleno.

## Pendiente (próximas versiones)
- Flujo “Cortar y silencios” con botones propios (hoy lo conduce Claude Code).
- Terminal de Claude Code integrada en la ventana.
- Firma del instalador y actualización del caparazón.
- Flujo de Ads.
