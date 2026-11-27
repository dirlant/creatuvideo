r"""PERSONALIZADOS: espacio para ediciones de video a medida con 4 carpetas:
  Videos sin edicion (originales) · Referencias (videos de inspiracion + que le gusta a la persona de cada uno) · Exportados (resultado final) · Temporales (trabajo intermedio).
Uso: python scripts\personalizados_lote.py <ffmpeg.exe> <modo>
Modos:  listar    -> imprime (una linea JSON) el contenido de las 4 carpetas y las descripciones de las referencias
        agregar   -> copia a la carpeta indicada los videos de presets.personalizados.pendiente = {destino: "sinEdicion"|"referencias", archivos: [{ruta, descripcion}]}
        describir -> guarda las descripciones de presets.personalizados.descripciones = {nombre_del_video: texto} en la carpeta de referencias
Las carpetas son las elegidas en la app (dirs.personalizados*); si no se eligieron, van dentro de la carpeta de trabajo: personalizados\<carpeta>."""
import json, os, re, shutil, sys, time

MODO = sys.argv[2] if len(sys.argv) > 2 else "listar"
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def _ajustes():
    try: return json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: return {}
AJ = _ajustes(); DIRS = AJ.get("dirs", {}) or {}; P = (AJ.get("presets", {}) or {}).get("personalizados", {}) or {}
WS = AJ.get("workspace") or AG
CARPETAS = {"sinEdicion": ("personalizadosSinEdicion", "videos-sin-edicion"), "referencias": ("personalizadosReferencias", "referencias"),
            "exportados": ("personalizadosExportados", "exportados"), "temporales": ("personalizadosTemporales", "temporales")}
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
REF_JSON = "referencias.json"

CLAUDE_MD = """# Personalizados — ediciones de video a medida

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
"""
AJUSTES_MD = "# Ajustes acumulados — Personalizados\n\nReglas que la persona fue pidiendo y que valen por defecto. Se agregan al final con fecha; si una nueva contradice una anterior, se reemplaza.\n\n- (Aún sin ajustes registrados.)\n"

# Cortar y silencios usa el mismo mecanismo para copiar varios videos a su carpeta de entrada y listar la entrada y los resultados
CARPETAS.update({"cortar": ("cortarEntrada", os.path.join("..", "por-cortar", "entrada")), "cortarResultado": ("cortarResultado", os.path.join("..", "por-cortar", "resultado"))})

def ruta(k):
    clave, sub = CARPETAS[k]; r = DIRS.get(clave) or os.path.normpath(os.path.join(WS, "personalizados", sub)); os.makedirs(r, exist_ok=True); return r
def preparar_prompt():
    d = os.path.join(WS, "personalizados"); os.makedirs(os.path.join(d, "prompt"), exist_ok=True)
    for f, txt in ((os.path.join(d, "CLAUDE.md"), CLAUDE_MD), (os.path.join(d, "prompt", "AJUSTES.md"), AJUSTES_MD)):
        if not os.path.exists(f): open(f, "w", encoding="utf-8").write(txt)
def leer_refs():
    try: return json.load(open(os.path.join(ruta("referencias"), REF_JSON), encoding="utf-8"))
    except Exception: return {}
def guardar_refs(d):
    r = ruta("referencias"); json.dump(d, open(os.path.join(r, REF_JSON), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lineas = ["# Referencias: qué le gusta a la persona de cada video", ""] + ["## %s\n%s\n" % (n, t or "(sin descripción)") for n, t in sorted(d.items())]
    open(os.path.join(r, "LEEME_referencias.md"), "w", encoding="utf-8").write("\n".join(lineas))
def archivos(k):
    r = ruta(k); out = []
    for n in sorted(os.listdir(r), key=str.lower):
        p = os.path.join(r, n)
        if not os.path.isfile(p) or n.startswith((".", "~")) or n in (REF_JSON, "LEEME_referencias.md"): continue
        out.append({"nombre": n, "mb": round(os.path.getsize(p) / 1048576, 1), "video": n.lower().endswith(VIDEO_EXT)})
    return out
def nombre_libre(carpeta, nombre):
    base, ext = os.path.splitext(nombre); n = nombre; i = 2
    while os.path.exists(os.path.join(carpeta, n)): n = "%s (%d)%s" % (base, i, ext); i += 1
    return n

def progreso_cortes():
    """Avance de los cortes enviados a Claude Code: por cada carpeta de destino de presets.cortar.tandas, cada subcarpeta (un video)
    con sus clips, la ultima linea de _progreso.txt y si ya termino (archivo _LISTO.txt)."""
    tandas = ((AJ.get("presets", {}) or {}).get("cortar", {}) or {}).get("tandas") or []
    out = {}
    for dst in {t.get("dst") for t in tandas if t.get("dst")}:
        subs = {}
        if os.path.isdir(dst):
            for n in os.listdir(dst):
                d = os.path.join(dst, n)
                if not os.path.isdir(d): continue
                clips = []; prog = ""
                for f in os.listdir(d):   # solo los clips terminados (el trabajo intermedio va en otra carpeta)
                    p = os.path.join(d, f)
                    if os.path.isfile(p) and f.lower().endswith(VIDEO_EXT) and not f.startswith((".", "~", "_")):
                        clips.append({"ruta": p, "nombre": f, "mb": round(os.path.getsize(p) / 1048576, 1)})
                try: prog = [l.strip() for l in open(os.path.join(d, "_progreso.txt"), encoding="utf-8", errors="replace").read().splitlines() if l.strip()][-1][:200]
                except Exception: pass
                mod = os.path.getmtime(d)   # ultimo cambio (carpeta, _progreso.txt o clips): sirve para avisar si Claude Code se quedo esperando
                for f in os.listdir(d):
                    try: mod = max(mod, os.path.getmtime(os.path.join(d, f)))
                    except Exception: pass
                subs[n] = {"clips": sorted(clips, key=lambda c: c["nombre"].lower()), "progreso": prog, "listo": os.path.exists(os.path.join(d, "_LISTO.txt")), "mod": int(mod * 1000)}
        out[dst] = subs
    return out

def listar():
    refs = leer_refs(); data = {k: {"ruta": ruta(k), "archivos": archivos(k)} for k in CARPETAS}
    for a in data["referencias"]["archivos"]: a["descripcion"] = refs.get(a["nombre"], "")
    try: data["cortarProgreso"] = progreso_cortes()
    except Exception as e: data["cortarProgreso"] = {}; print("Aviso progreso: %s" % e, file=sys.stderr)
    print(json.dumps(data, ensure_ascii=True))
def agregar():
    pend = P.get("pendiente") or {}; destino = pend.get("destino"); lista = pend.get("archivos") or []
    if destino not in ("sinEdicion", "referencias", "cortar"): sys.exit("Destino no válido.")
    dst = ruta(destino); refs = leer_refs(); n = 0
    for a in lista:
        src = a.get("ruta") or ""
        if not os.path.isfile(src): print("No se encontró el archivo: " + src, flush=True); continue
        if os.path.normcase(os.path.dirname(os.path.abspath(src))) == os.path.normcase(os.path.abspath(dst)): print("Ya está en la carpeta: " + os.path.basename(src), flush=True); n += 1; continue
        nom = nombre_libre(dst, os.path.basename(src)); print("Copiando %s …" % nom, flush=True); shutil.copy2(src, os.path.join(dst, nom)); n += 1
        if destino == "referencias": refs[nom] = (a.get("descripcion") or "").strip()
    if destino == "referencias": guardar_refs(refs)
    print("OK copiados: %d en %s" % (n, dst), flush=True)
    if n == 0: sys.exit(1)
def describir():
    refs = leer_refs(); cambios = P.get("descripciones") or {}
    for nom, txt in cambios.items():
        if os.path.exists(os.path.join(ruta("referencias"), nom)): refs[nom] = str(txt).strip()
    guardar_refs(refs); print("OK descripciones guardadas: %d" % len(cambios), flush=True)

if __name__ == "__main__":
    preparar_prompt()
    {"listar": listar, "agregar": agregar, "describir": describir}.get(MODO, lambda: sys.exit("Modo desconocido: " + MODO))()
