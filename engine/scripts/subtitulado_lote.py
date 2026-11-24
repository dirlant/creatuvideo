r"""SUBTITULADO: narracion con voz + subtitulos animados palabra por palabra, en el centro del video, con tipografia Lato.
Uso: uv run --python 3.12 --with edge-tts --with pillow --with numpy python scripts\subtitulado_lote.py <ffmpeg.exe> <modo>
Modos:  generar -> un video subtitulado por cada video elegido (o uno sobre pantalla negra si no se elige ninguno)
        guion   -> pide el texto de la narracion a la API de ChatGPT y lo devuelve a la app en una linea «CTV_GUION {json}»
Estilo (el del video de referencia «lash-record-pantalla-negra-lato»): frases cortas centradas; las palabras aparecen una a una al ritmo de la voz
(suben 38 px, crecen de 85 % a 100 % y aparecen en 0,22 s); las palabras clave van GRANDES en Lato Black blanco y el resto chicas en Lato Regular gris claro;
letras muy juntas y un brillo suave. Lee los datos de los ajustes de la app (presets.subtitulado)."""
import asyncio, glob, hashlib, json, math, os, re, shutil, subprocess, sys, time, unicodedata
import edge_tts
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else (shutil.which(sys.argv[1]) or sys.argv[1]); MODO = sys.argv[2] if len(sys.argv) > 2 else "generar"
FP = FF.replace("ffmpeg.exe", "ffprobe.exe") if FF.lower().endswith("ffmpeg.exe") else (shutil.which("ffprobe") or "ffprobe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def _ajustes():
    try: return json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: return {}
AJ = _ajustes(); PRE = AJ.get("presets", {}); DIRS = AJ.get("dirs", {})
P = PRE.get("subtitulado", {}) or {}
SALIDA = DIRS.get("subtituladoResultado") or os.path.join(AJ.get("workspace") or AG, "subtitulado", "resultado"); os.makedirs(SALIDA, exist_ok=True)
OPS = os.path.join(AG, "subtitulado", "_operacion"); os.makedirs(OPS, exist_ok=True)
env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
INI = 0.35                                   # la voz arranca a los 0,35 s (igual que el video de referencia)
FPS = 30
IDIOMAS = {"es": "español", "en": "inglés", "pt": "portugués", "de": "alemán"}
VOCES_AUTO = {"es": "es-MX-JorgeNeural", "en": "en-US-GuyNeural", "pt": "pt-BR-AntonioNeural", "de": "de-DE-ConradNeural"}

def sh(cmd, **kw):
    kw.setdefault("env", env)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)

# ---------------------------------------------------------------- 1) redactar la narracion con la API de ChatGPT
def escribir_guion():
    import urllib.request, urllib.error
    key = (AJ.get("openaiKey") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key: sys.exit("Falta la clave de OpenAI (ChatGPT). Pégala en Ajustes → Clave de OpenAI.")
    tema = (P.get("tema") or "").strip()
    if not tema: sys.exit("Escribe primero la temática a resolver.")
    try: seg = int(P.get("narracionSeg") or 30)
    except Exception: seg = 30
    seg = max(8, min(180, seg)); palabras = int(round(seg * 2.5)); tono = (P.get("tono") or "Cercano").strip()
    idioma = IDIOMAS.get((P.get("idioma") or "es").strip(), "español"); modelo = (AJ.get("openaiModelo") or "gpt-4o-mini").strip()
    sistema = ("Eres guionista de videos cortos para redes sociales (Reels, TikTok). Escribes la narración que una voz leerá en voz alta mientras las palabras aparecen en pantalla como subtítulos animados. "
               "Respondes SOLO con el texto de la narración, en texto plano: sin título, sin numeración con símbolos, sin emojis, sin comillas alrededor, sin indicaciones de escena.")
    usuario = ("Temática a resolver: %s\nIdioma: %s\nTono: %s\nLongitud: unas %d palabras (la voz lee unas 2,5 palabras por segundo, así que la narración debe durar unos %d segundos).\n"
               "Estructura: empieza con un gancho que plantee el problema o despierte curiosidad; desarrolla 2 a 4 ideas claras y concretas; incluye una cifra o dato concreto si es natural; "
               "cierra con una frase corta y un llamado a la acción. Frases cortas y directas, fáciles de leer en voz alta, con comas y puntos bien puestos.") % (tema, idioma, tono, palabras, seg)
    def pedir(extra=""):
        cuerpo = json.dumps({"model": modelo, "temperature": 0.8, "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario + extra}]}).encode("utf-8")
        rq = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=cuerpo, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try: r = json.loads(urllib.request.urlopen(rq, timeout=120).read().decode("utf-8"))
        except urllib.error.HTTPError as ex:
            try: m = json.loads(ex.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception: m = ""
            sys.exit("La API de ChatGPT respondió con error %s: %s" % (ex.code, (m or ex.reason)[:300].replace(key, "…")))
        except Exception as ex: sys.exit("No se pudo consultar la API de ChatGPT (hace falta internet): %s" % str(ex)[:200].replace(key, "…"))
        return (r["choices"][0]["message"]["content"] or "").strip().strip('"').strip()
    print("Consultando a ChatGPT (%s): «%s», %d s (~%d palabras)…" % (modelo, tema, seg, palabras), flush=True)
    texto = pedir(); n = len(texto.split())
    if n < palabras * 0.75 or n > palabras * 1.25:
        print("El texto salió de %d palabras; se pide ajustarlo a ~%d." % (n, palabras), flush=True)
        texto = pedir("\nIMPORTANTE: la versión anterior tenía %d palabras. Ahora debe tener %d palabras (entre %d y %d)." % (n, palabras, int(palabras * .9), int(palabras * 1.1))) or texto
    if not texto: sys.exit("ChatGPT no devolvió texto.")
    print("Texto listo: %d palabras (~%d s de narración)." % (len(texto.split()), round(len(texto.split()) / 2.5)), flush=True)
    print("CTV_GUION " + json.dumps({"texto": texto}, ensure_ascii=True), flush=True)

# ---------------------------------------------------------------- 2) voz con edge-tts y tiempos de cada palabra
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")
def limpiar(t):
    t = EMOJI.sub(" ", t or ""); t = re.sub(r"[*_#`~<>\[\]{}|\\^]", " ", t)
    t = t.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"').replace("’", "'").replace("…", "...")
    return re.sub(r"\s+", " ", t).strip()
async def _tts(texto, voz, salida):
    words = []
    with open(salida, "wb") as audio:
        async for ch in edge_tts.Communicate(texto, voz, boundary="WordBoundary").stream():
            if ch["type"] == "audio": audio.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append((ch["text"], ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))
    return words
def sintetizar(texto, voz):
    h = hashlib.sha1((texto + "|" + voz).encode("utf-8")).hexdigest()[:14]; mp3 = os.path.join(OPS, "voz_%s.mp3" % h); js = os.path.join(OPS, "voz_%s.json" % h)
    if os.path.exists(mp3) and os.path.exists(js):
        try: return mp3, json.load(open(js, encoding="utf-8"))
        except Exception: pass
    ult = None
    for i in range(3):
        try:
            words = asyncio.run(_tts(texto, voz, mp3))
            if words and os.path.getsize(mp3) > 2000: json.dump(words, open(js, "w", encoding="utf-8")); return mp3, words
            ult = "la voz llegó vacía"
        except Exception as ex: ult = str(ex)
        time.sleep(2 + i * 2)
    sys.exit("No se pudo generar la voz (hace falta internet): %s" % (ult or "error desconocido")[:200])

# ---------------------------------------------------------------- 3) palabras, frases cortas y palabras clave
from subs_lato import Capa, norm, STOP, alinear, frases, claves          # estilo Lato compartido con Servicios y Negocios

# ---------------------------------------------------------------- 5) video
def sonda(ruta):
    r = sh([FP, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", ruta])
    try: j = json.loads(r.stdout)
    except Exception: sys.exit("No se pudo leer el video: " + ruta)
    v = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]; a = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    if not v: sys.exit("El archivo no tiene video: " + ruta)
    return int(v[0]["width"]), int(v[0]["height"]), float(j.get("format", {}).get("duration") or 0), bool(a)

def renderizar(video, texto, mp3, B, destino):
    fondo_negro = not video
    if video: W0, H0, dur_v, tiene_audio = sonda(video)
    else: W0, H0, dur_v, tiene_audio = 1080, 1920, 0, False
    k = min(1.0, 1080.0 / max(1, min(W0, H0))); W = int(W0 * k) // 2 * 2; H = int(H0 * k) // 2 * 2         # como maximo 1080 px por el lado corto
    tamano = {"s": 0.85, "m": 1.0, "l": 1.15}.get(P.get("tamano") or "m", 1.0)
    capa = Capa(texto.split(), B, W, H, ini=INI, tamano=tamano, sobre_video=not fondo_negro, claves_on=P.get("claves") is not False, fps=FPS)
    dur = max(round(capa.dur, 2), 3.0); n = int(math.ceil(dur * FPS)); banda, y0 = capa.banda, capa.y0
    oscuro = max(0, min(0.85, float(P.get("oscuro", 45)) / 100.0))
    vf = "[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,fps=%d" % (W, H, W, H, FPS)
    if not fondo_negro and oscuro > 0: vf += ",drawbox=x=0:y=0:w=iw:h=ih:color=black@%.2f:t=fill" % oscuro
    vf += ",format=yuv420p[bg];[1:v]format=rgba[tx];[bg][tx]overlay=0:%d:format=auto,format=yuv420p[v]" % y0
    modo_audio = P.get("sonido") or "quitar"; vol = {"bajo": 0.18, "mantener": 1.0}.get(modo_audio)
    af = "[2:a]adelay=%d|%d,apad[na]" % (int(INI * 1000), int(INI * 1000))
    if tiene_audio and vol: af += ";[0:a]volume=%.2f[oa];[na][oa]amix=inputs=2:duration=first:normalize=0[a]" % vol
    else: af += ";[na]anull[a]"
    cmd = [FF, "-nostdin", "-y", "-v", "error"]
    cmd += ["-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, FPS)] if fondo_negro else ["-stream_loop", "-1", "-i", video]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", "%dx%d" % (W, banda), "-r", str(FPS), "-i", "-", "-i", mp3,
            "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]", "-t", "%.2f" % dur, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", destino]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    marca = -1
    try:
        for f, datos in enumerate(capa.frames(n)):
            p.stdin.write(datos)
            dec = f * 10 // n
            if dec != marca:
                marca = dec
                if dec > 0: print("   %d %%" % (dec * 10), flush=True)
        p.stdin.close()
    except BrokenPipeError: pass
    err = p.stderr.read().decode("utf-8", "replace"); p.wait()
    if p.returncode != 0 or not os.path.exists(destino): print("ERROR ffmpeg: " + err[-400:], flush=True); return False
    return True

def main():
    if MODO == "guion": return escribir_guion()
    texto = limpiar(P.get("texto"))
    if len(texto) < 15: sys.exit("Escribe (o pide a ChatGPT) la narración que quieres subtitular.")
    texto = texto[:6000]
    videos = [v for v in (P.get("videos") or []) if v]
    if P.get("fondo") == "negro": videos = []
    for v in videos:
        if not os.path.exists(v): sys.exit("No se encuentra el video (¿lo moviste o lo borraste?): " + v)
    voz = (P.get("voz") or "").strip() or VOCES_AUTO.get((P.get("idioma") or "es").strip(), VOCES_AUTO["es"])
    print("Generando la narración con la voz %s…" % voz, flush=True)
    mp3, B = sintetizar(texto, voz); print("Narración lista: %.1f s, %d palabras." % (B[-1][2], len(texto.split())), flush=True)
    sello = time.strftime("%Y%m%d-%H%M%S"); ok = 0; lista = videos or [None]
    for i, v in enumerate(lista, 1):
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(v))[0])[:40] if v else "pantalla_negra"
        out = os.path.join(SALIDA, "%s_subtitulado_%s.mp4" % (nombre, sello)); print("[%d/%d] %s …" % (i, len(lista), os.path.basename(v) if v else "sobre pantalla negra"), flush=True)
        try:
            if renderizar(v, texto, mp3, B, out): ok += 1; print("OK " + out, flush=True)
        except Exception as ex:
            import traceback; traceback.print_exc(); print("ERROR con %s: %s" % (nombre, ex), flush=True)
    print("Listo: %d de %d videos en %s" % (ok, len(lista), SALIDA)); sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
