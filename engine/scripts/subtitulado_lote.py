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
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
STOP = set(norm(w) for w in ("de la que el en y a los se del las un por con no una su para es al lo como mas pero sus le ya o fue este si porque esta entre cuando muy sin sobre tambien me hasta hay donde quien desde todo nos "
    "durante todos uno les ni contra otros ese eso ante ellos e esto antes algunos que unos yo otro otras otra el tanto esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo mi mis tu te ti tus ellas "
    "era eran son ser fueron tiene tienen hace hacen asi aunque cada the and for with that this from your you are was were have has but not they their them what when where which will would can could into about more just than then "
    "also been being does did our out how why who all any each other some such only over very").split())
def alinear(tokens, B):
    """Tiempo de inicio de cada palabra del texto, a partir de los limites de palabra que entrega la voz (se emparejan en orden)."""
    n = len(tokens); t0 = [None] * n; j = 0
    for i, tk in enumerate(tokens):
        nt = norm(tk)
        for k in range(j, min(len(B), j + 4)):
            nb = norm(B[k][0])
            if nb and (nb == nt or nt.startswith(nb) or nb.startswith(nt)): t0[i] = B[k][1]; j = k + 1; break
    if all(v is None for v in t0):                                  # sin coincidencias: se reparte por letras sobre la duracion total
        tot = sum(len(t) for t in tokens) or 1; fin = B[-1][2] if B else 1.0; acum = 0
        for i, tk in enumerate(tokens): t0[i] = acum / tot * fin; acum += len(tk)
    i = 0
    while i < n:                                                    # huecos: se interpolan entre vecinos
        if t0[i] is None:
            a = i - 1; b = i
            while b < n and t0[b] is None: b += 1
            ta = t0[a] if a >= 0 else 0.0; tb = t0[b] if b < n else (B[-1][2] if B else ta + 0.4 * (b - a))
            for k in range(i, b): t0[k] = ta + (tb - ta) * (k - a) / (b - a)
            i = b
        else: i += 1
    for i in range(1, n): t0[i] = max(t0[i], t0[i - 1] + 0.04)      # siempre crecientes
    return t0
def frases(tokens):
    """Agrupa las palabras en frases cortas (como las lineas del video de referencia): corta en puntos y comas, y por largo."""
    out, cur, chars = [], [], 0
    for i, tk in enumerate(tokens):
        cur.append(i); chars += len(tk) + 1
        fin = re.search(r"[.!?…]+[\"')\]]*$", tk); pausa = re.search(r"[,;:]+[\"')\]]*$", tk)
        if fin or (pausa and len(cur) >= 3) or len(cur) >= 8 or chars >= 44: out.append(cur); cur, chars = [], 0
    if cur:
        if out and len(cur) <= 1 and len(out[-1]) < 8: out[-1] += cur            # una palabra suelta se une a la frase anterior
        else: out.append(cur)
    return out
def claves(tokens, idxs):
    """Palabras clave de una frase (las que van GRANDES): las mas largas y significativas; 1 o 2 por frase."""
    c = []
    for pos, i in enumerate(idxs):
        w = re.sub(r"^\W+|\W+$", "", tokens[i]); nw = norm(w)
        if len(nw) < 4 or nw in STOP: continue
        puntos = len(nw) + (4 if (w[:1].isupper() and pos > 0) else 0) + (6 if any(ch.isdigit() for ch in w) else 0)
        c.append((puntos, i))
    c.sort(reverse=True); k = 1 if len(idxs) <= 4 else 2
    return {i for _, i in c[:k]}

# ---------------------------------------------------------------- 4) dibujo: Lato, letras juntas, brillo suave
def fuente(grande, px):
    for p in ([os.path.join(AG, "assets", "fonts", "Lato-Black.ttf")] if grande else [os.path.join(AG, "assets", "fonts", "Lato-Regular.ttf")]) + [r"C:\Windows\Fonts\seguibl.ttf" if grande else r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arialbd.ttf" if grande else r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, max(8, int(round(px))))
    return ImageFont.load_default()
class Estilo:
    def __init__(self, W, H, escala_usuario=1.0, sobre_video=False):
        self.sobre_video = sobre_video; self.W, self.H = W, H; s = min(W, H) / 1080.0 * escala_usuario; self.s = s
        self.px_p, self.px_g = 66 * s, 112 * s                         # chica / grande
        self.fp, self.fg = fuente(False, self.px_p), fuente(True, self.px_g)
        self.ls_p, self.ls_g = -0.06 * self.px_p, -0.07 * self.px_g     # espaciado entre letras
        self.col_p, self.col_g = (214, 214, 214), (255, 255, 255)
        self.hueco_x, self.hueco_y = 22 * s, 6 * s
        self.ancho = min(880 * s, W * 0.86)
        self.pad = int(50 * s)
    def medir(self, txt, grande):
        f = self.fg if grande else self.fp; ls = self.ls_g if grande else self.ls_p
        return sum(f.getlength(ch) + ls for ch in txt)
    def imagen_palabra(self, txt, grande):
        f = self.fg if grande else self.fp; ls = self.ls_g if grande else self.ls_p; col = self.col_g if grande else self.col_p
        asc, desc = f.getmetrics(); w = int(math.ceil(self.medir(txt, grande))); pad = self.pad
        tam = (max(2, w + 2 * pad), asc + desc + 2 * pad)
        m = Image.new("L", tam, 0); d = ImageDraw.Draw(m); x = pad
        for ch in txt: d.text((x, pad + asc), ch, font=f, fill=255, anchor="ls"); x += f.getlength(ch) + ls
        im = Image.new("RGBA", tam, (255, 255, 255, 0))
        if self.sobre_video:                                                                           # sobre un video: sombra oscura suave para que se lea
            halo = m.filter(ImageFilter.GaussianBlur(11 * self.s)).point(lambda v: min(255, int(v * 0.95))); color_halo = (0, 0, 0, 255)
        else:                                                                                          # pantalla negra: brillo blanco, como en la referencia (text-shadow: 0 4px 30px rgba(255,255,255,.12))
            halo = m.filter(ImageFilter.GaussianBlur(15 * self.s)).point(lambda v: int(v * 0.16)); color_halo = (255, 255, 255, 255)
        halo_off = Image.new("L", tam, 0); halo_off.paste(halo, (0, int(4 * self.s)))
        im.paste(color_halo, (0, 0), halo_off)
        txt_im = Image.new("RGBA", tam, col + (0,)); txt_im.putalpha(m); im.alpha_composite(txt_im)
        return im, (pad, pad + asc), (asc, desc)
    def maquetar(self, idxs, tokens, grandes):
        """Posiciona las palabras de una frase: lineas centradas, palabras alineadas por su linea base, todo centrado en el medio del video."""
        items = []
        for i in idxs:
            g = i in grandes; im, (ox, oy), (asc, desc) = self.imagen_palabra(tokens[i], g); size = self.px_g if g else self.px_p
            alto = 1.02 * size; base = (alto - (asc + desc)) / 2 + asc
            items.append(dict(i=i, g=g, im=im, ox=ox, oy=oy, w=self.medir(tokens[i], g), arriba=base, abajo=alto - base))
        lineas, cur, ancho = [], [], 0.0
        for it in items:
            if cur and ancho + self.hueco_x + it["w"] > self.ancho: lineas.append(cur); cur, ancho = [], 0.0
            ancho += it["w"] + (self.hueco_x if cur else 0); cur.append(it)
        if cur: lineas.append(cur)
        alturas = [max(it["arriba"] for it in ln) + max(it["abajo"] for it in ln) for ln in lineas]
        total = sum(alturas) + self.hueco_y * (len(lineas) - 1); y = -total / 2                      # coordenadas relativas al centro del video
        for ln, alto in zip(lineas, alturas):
            wl = sum(it["w"] for it in ln) + self.hueco_x * (len(ln) - 1); x = self.W / 2 - wl / 2; linea_base = y + max(it["arriba"] for it in ln)
            for it in ln: it["x"] = x; it["yb"] = linea_base; x += it["w"] + self.hueco_x
            y += alto + self.hueco_y
        return items

def ease(p): return 1 - (1 - p) ** 3
def sobre(dst, src, x, y):
    """alpha_composite con recorte (admite posiciones fuera de la banda)."""
    x, y = int(round(x)), int(round(y)); sw, sh_ = src.size; dw, dh = dst.size
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dw, x + sw), min(dh, y + sh_)
    if x1 <= x0 or y1 <= y0: return
    dst.alpha_composite(src.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

# ---------------------------------------------------------------- 5) video
def sonda(ruta):
    r = sh([FP, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", ruta])
    try: j = json.loads(r.stdout)
    except Exception: sys.exit("No se pudo leer el video: " + ruta)
    v = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]; a = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    if not v: sys.exit("El archivo no tiene video: " + ruta)
    return int(v[0]["width"]), int(v[0]["height"]), float(j.get("format", {}).get("duration") or 0), bool(a)

def construir_frases(tokens, t0, B_fin, st):
    fr = frases(tokens); out = []
    for k, idxs in enumerate(fr):
        grandes = claves(tokens, idxs) if P.get("claves") is not False else set()
        its = st.maquetar(idxs, tokens, grandes)
        ini = t0[idxs[0]]; fin_ = (t0[fr[k + 1][0]] if k + 1 < len(fr) else B_fin + 0.6)
        out.append(dict(ini=ini + INI - 0.02, fin=fin_ + INI - 0.02, items=its, t0=[t0[it["i"]] + INI for it in its]))
    return out

def renderizar(video, texto, mp3, B, destino):
    fondo_negro = not video
    if video: W0, H0, dur_v, tiene_audio = sonda(video)
    else: W0, H0, dur_v, tiene_audio = 1080, 1920, 0, False
    k = min(1.0, 1080.0 / max(1, min(W0, H0))); W = int(W0 * k) // 2 * 2; H = int(H0 * k) // 2 * 2         # como maximo 1080 px por el lado corto
    tamano = {"s": 0.85, "m": 1.0, "l": 1.15}.get(P.get("tamano") or "m", 1.0); st = Estilo(W, H, tamano, sobre_video=not fondo_negro)
    tokens = texto.split(); t0 = alinear(tokens, B); fin_voz = B[-1][2] if B else t0[-1] + 0.5
    chunks = construir_frases(tokens, t0, fin_voz, st)
    dur = round(fin_voz + INI + 1.0, 2); dur = max(dur, 3.0); n = int(math.ceil(dur * FPS))
    banda = min(H, int(1100 * st.s) // 2 * 2); y0 = (H - banda) // 2 // 2 * 2; cy = H / 2 - y0                 # la banda de texto va centrada; cy = centro del video dentro de la banda
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
    vacio = Image.new("RGBA", (W, banda), (0, 0, 0, 0)); vacio_b = vacio.tobytes(); ult_clave = None; ult_bytes = vacio_b; estatico = {}; marca = -1
    try:
        for f in range(n):
            t = f / float(FPS); c = next((c for c in chunks if c["ini"] <= t < c["fin"]), None)
            if c is None: clave, datos = ("vacio",), vacio_b
            else:
                ci = chunks.index(c); k_fin = 0; anim = []
                for j, it in enumerate(c["items"]):
                    pr = (t - c["t0"][j]) / 0.22
                    if pr >= 1: k_fin = j + 1
                    elif pr > 0: anim.append((it, pr))
                clave = (ci, k_fin, tuple(round(pr, 3) for _, pr in anim))
                if clave == ult_clave: datos = ult_bytes
                else:
                    base = estatico.get((ci, k_fin))
                    if base is None:
                        prev = estatico.get((ci, k_fin - 1)) if k_fin > 0 else None
                        base = prev.copy() if prev is not None else vacio.copy()
                        if k_fin > 0 and prev is not None: it = c["items"][k_fin - 1]; sobre(base, it["im"], it["x"] - it["ox"], it["yb"] - it["oy"] + cy)
                        elif k_fin > 0:
                            for it in c["items"][:k_fin]: sobre(base, it["im"], it["x"] - it["ox"], it["yb"] - it["oy"] + cy)
                        estatico = {kk: vv for kk, vv in estatico.items() if kk[0] == ci}; estatico[(ci, k_fin)] = base
                    if anim:
                        fr = base.copy()
                        for it, pr in anim:
                            e = ease(min(1.0, pr)); sc = 0.85 + 0.15 * e; im = it["im"]; w2, h2 = max(1, int(im.width * sc)), max(1, int(im.height * sc))
                            r = im.resize((w2, h2), Image.BILINEAR); a = r.getchannel("A").point(lambda v, e=e: int(v * e)); r.putalpha(a)
                            cx = it["x"] - it["ox"] + im.width / 2; cyy = it["yb"] - it["oy"] + im.height / 2 + cy + 38 * st.s * (1 - e)
                            sobre(fr, r, cx - w2 / 2, cyy - h2 / 2)
                        datos = fr.tobytes()
                    else: datos = base.tobytes()
                    ult_clave, ult_bytes = clave, datos
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
