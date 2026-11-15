r"""Video de ESTRATEGIA DE PRECIOS (Reels 1080x1920, 15 s): narracion con voz + recuadro centrado con titulo, lo que incluye el servicio,
precio promocional y CTA (precio y CTA sobre fondo amarillo con letras blancas) sobre videos de fondo (Pexels automatico o carpeta).
Uso: uv run --python 3.12 --with edge-tts --with pillow --with numpy python scripts\precios_lote.py <ffmpeg.exe> <modo>
Modos:  generar -> voz + fondo + imagenes + montaje final (todo)
        aspecto -> vuelve a montar el video con el aspecto grafico de los ajustes, reutilizando la voz, el fondo y las imagenes ya preparados
Los datos del formulario y el aspecto los lee de los ajustes de la app (presets.precios y presets.preciosEstilo)."""
import asyncio, glob, json, os, random, re, shutil, subprocess, sys, unicodedata, wave
from datetime import datetime
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

FF = os.path.abspath(sys.argv[1]); MODO = sys.argv[2] if len(sys.argv) > 2 else "generar"
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
VERDANA = r"C:\Windows\Fonts\verdanab.ttf"
OPP = os.path.join(AG, "precios", "_operacion"); W = os.path.join(OPP, "_trabajo"); os.makedirs(W, exist_ok=True)
DUR = 15.0                       # duracion fija del video
INI = 0.35                       # la voz arranca a los 0.35 s
env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())

def _ajustes():
    try: return json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: return {}
AJ = _ajustes(); PRE = AJ.get("presets", {}); DIRS = AJ.get("dirs", {})
P = PRE.get("precios", {}) or {}
SALIDA = DIRS.get("preciosResultado") or os.path.join(AG, "precios", "resultado"); os.makedirs(SALIDA, exist_ok=True)
ESTILO = {"tarjeta": "#1c1030", "opacidad": 0.80, "amarillo": "#FFD400", "letras": "#FFFFFF", "chip": "#D61480", "escala": 1.0, "posicion": "centro"}
ESTILO.update({k: v for k, v in (PRE.get("preciosEstilo", {}) or {}).items() if v not in (None, "")})

# ---------------------------------------------------------------- textos por idioma
TXT = {
    "es": dict(incluye="INCLUYE", promo="PRECIO PROMOCIONAL", y="y", cta={"me": "Escríbeme", "nos": "Escríbenos"}, nar_incluye="Incluye", nar_precio="Precio promocional"),
    "en": dict(incluye="INCLUDES", promo="PROMOTIONAL PRICE", y="and", cta={"me": "Message me", "nos": "Message us"}, nar_incluye="Includes", nar_precio="Promotional price"),
    "pt": dict(incluye="INCLUI", promo="PREÇO PROMOCIONAL", y="e", cta={"me": "Escreva para mim", "nos": "Escreva para nós"}, nar_incluye="Inclui", nar_precio="Preço promocional"),
    "de": dict(incluye="ENTHÄLT", promo="AKTIONSPREIS", y="und", cta={"me": "Schreib mir", "nos": "Schreib uns"}, nar_incluye="Enthält", nar_precio="Aktionspreis"),
}
IDIOMA = P.get("idioma") if P.get("idioma") in TXT else "es"; T = TXT[IDIOMA]
VOZ = P.get("voz") or {"es": "es-MX-JorgeNeural", "en": "en-US-GuyNeural", "pt": "pt-BR-AntonioNeural", "de": "de-DE-ConradNeural"}[IDIOMA]
RUBRO = (P.get("rubro") or "").strip(); SERVICIO = (P.get("servicio") or "").strip(); TITULO = (P.get("titulo") or "").strip()
ITEMS = [l.strip(" -•·*\t") for l in re.split(r"[\r\n]+", P.get("incluye") or "") if l.strip(" -•·*\t")][:5]
UBIC = (P.get("ubicacion") or "").strip()[:48]; PRECIO = (P.get("precio") or "").strip(); CTA = T["cta"].get(P.get("cta"), T["cta"]["me"])
if not (TITULO and PRECIO) and MODO == "generar": sys.exit("Falta el título o el precio promocional.")

def sh(cmd, **kw):
    kw.setdefault("env", env)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
def dims(p):
    r = sh([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", p])
    j = json.loads(r.stdout); return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])
def dur_audio(f): return float(sh([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).stdout)
def hexrgb(h, a=255):
    h = (h or "#000000").lstrip("#"); h = h if len(h) == 6 else "000000"
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# ---------------------------------------------------------------- narracion (segmentos para sincronizar el recuadro)
def lista(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " " + T["y"] + " " + items[-1]
def segmentos():
    seg = []
    ini = TITULO if not SERVICIO or norm(SERVICIO) in norm(TITULO) else SERVICIO + ". " + TITULO
    seg.append(("titulo", ini.rstrip(".") + "."))
    for i, it in enumerate(ITEMS): seg.append(("item%d" % i, (T["nar_incluye"] + " " if i == 0 else "") + it.rstrip(".") + ("," if i < len(ITEMS) - 1 else ".")))
    seg.append(("precio", T["nar_precio"] + ": " + PRECIO + "."))
    seg.append(("cta", CTA + "."))
    return seg

async def tts(texto, salida):
    words = []
    with open(salida, "wb") as audio:
        async for ch in edge_tts.Communicate(texto, VOZ, boundary="WordBoundary").stream():
            if ch["type"] == "audio": audio.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append((ch["text"], ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))
    return words

def voz():
    seg = segmentos(); texto = " ".join(t for _, t in seg)
    base = os.path.join(W, "voz_base.mp3")
    words = asyncio.run(tts(texto, base)); raw = dur_audio(base)
    vel = max(1.1, min(1.5, raw / (DUR - 1.8)))        # la narracion tiene que caber en los 15 s: se acelera lo necesario (1.1x a 1.5x)
    # inicio (s) de cada segmento = inicio de su primera palabra
    cuentas = [len(t.split()) for _, t in seg]; marcas = {}; k = 0
    if len(words) == sum(cuentas):
        for (nombre, _), c in zip(seg, cuentas): marcas[nombre] = words[k][1] / vel + INI; k += c
    else:                                              # el motor de voz agrupo palabras distinto: se reparte por caracteres
        tot = sum(len(t) for _, t in seg); acum = 0
        for nombre, t in seg: marcas[nombre] = (acum / tot) * (raw / vel) + INI; acum += len(t)
    fin = raw / vel + INI
    if fin > DUR - 0.3: print("Aviso: la narración dura %.1f s y se recorta a los %d s. Acorta los textos." % (fin, DUR), flush=True)
    json.dump({"vel": vel, "marcas": marcas, "fin": fin}, open(os.path.join(W, "voz_info.json"), "w", encoding="utf-8"))
    print("voz %.1fs (x%.2f -> %.1fs)" % (raw, vel, fin), flush=True)

# ---------------------------------------------------------------- fondo (videos) e imagenes
BUSQUEDAS = {
    "barberia": ["barber cutting hair", "barbershop man haircut"], "cabello": ["hairdresser styling hair woman", "woman hair salon blow dry"],
    "cejas": ["eyebrow shaping woman", "eyebrow microblading"], "cosmetologia": ["facial treatment woman spa", "skin care facial cosmetologist"],
    "depilacion": ["waxing hair removal woman", "laser hair removal treatment"], "estetica": ["beauty salon treatment woman", "aesthetic clinic facial"],
    "maquillaje": ["makeup artist applying makeup", "woman makeup application"], "masajes": ["massage therapy woman", "relaxing spa massage"],
    "micropigmentacion": ["microblading eyebrows", "permanent makeup lips"], "pestanas": ["eyelash extension woman", "lash technician"],
    "pies": ["pedicure feet salon", "foot spa pedicure"], "podologia": ["podiatrist foot care", "foot treatment clinic"], "unas": ["manicure nails salon", "nail art woman hands"],
}
GENERALES = ["beauty salon woman service", "woman spa treatment"]

def pool_carpeta(carpeta):
    out = []
    for ext in ("mp4", "mov", "mkv", "webm"):
        for f in glob.glob(os.path.join(carpeta, "**", "*." + ext), recursive=True):
            try: out.append((f,) + dims(f)[2:])
            except Exception: pass
    return out

def pool_pexels():
    if not (env.get("PEXELS_API_KEY") or os.path.exists(os.path.join(AG, "_operacion", "pexels.key"))):
        sys.exit("Falta la clave de Pexels (Ajustes) o elige «De una carpeta» en los videos.")
    qs = next((q for k, q in BUSQUEDAS.items() if k in norm(RUBRO)), []) + GENERALES
    out = os.path.join(OPP, "recursos", "pexels", norm(RUBRO) or "general"); os.makedirs(out, exist_ok=True)
    for i, q in enumerate(qs[:3]):
        r = sh([sys.executable, os.path.join(AG, "scripts", "descargar_videos.py"), out, q, "3", "pr%d" % i])
        print("pexels «%s»: %d videos nuevos" % (q, len(r.stdout.strip().splitlines())), flush=True)
    res = []
    for f in sorted(glob.glob(os.path.join(out, "*.mp4"))):
        try: w, h, d = dims(f)
        except Exception: continue
        if d >= 3.2: res.append((f, d))
    if not res: sys.exit("No se pudieron descargar videos de Pexels. Revisa la clave y la conexión, o usa «De una carpeta».")
    return res

def fondo(rnd):
    if P.get("videos") == "carpeta":
        carpeta = DIRS.get("preciosVideos") or os.path.join(AG, "precios", "entrada", "videos")
        pl = pool_carpeta(carpeta)
        if not pl: sys.exit("No hay videos en la carpeta elegida: " + carpeta)
        print("videos de la carpeta: %d" % len(pl), flush=True)
    else:
        pl = pool_pexels()
    cortes = os.path.join(W, "cortes"); shutil.rmtree(cortes, ignore_errors=True); os.makedirs(cortes)
    orden = list(pl); rnd.shuffle(orden); lista_ = []
    for k in range(5):                                  # 5 tomas de 3 s: cambio de imagen cada 3 segundos
        src, d = orden[k % len(orden)]; ss = rnd.uniform(0.2, max(0.3, d - 3.2)) if d > 3.4 else 0
        out = os.path.join(cortes, "c%d.mp4" % k)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,eq=brightness=-0.07:saturation=1.05,format=yuv420p"
        r = sh([FF, "-nostdin", "-y", "-v", "error", "-stream_loop", "-1", "-ss", "%.2f" % ss, "-i", src, "-t", "3.0", "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-g", "30", out])
        if not os.path.exists(out): sys.exit("corte falló: " + (r.stderr or "")[-300:])
        lista_.append(out)
    lst = os.path.join(W, "lista.txt"); open(lst, "w").write("".join("file '%s'\n" % f.replace("\\", "/") for f in lista_))
    fb = os.path.join(W, "fondo.mp4")
    r = sh([FF, "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", fb])
    if not os.path.exists(fb): sys.exit("no se pudo armar el fondo: " + (r.stderr or "")[-300:])
    return lista_

def imagenes(cortes, rnd):
    fotos = os.path.join(W, "fotos"); shutil.rmtree(fotos, ignore_errors=True); os.makedirs(fotos)
    fuentes = []
    if P.get("imagenes") == "carpeta":
        carpeta = DIRS.get("preciosImagenes") or os.path.join(AG, "precios", "entrada", "imagenes")
        for ext in ("jpg", "jpeg", "png", "webp"): fuentes += glob.glob(os.path.join(carpeta, "**", "*." + ext), recursive=True)
        if not fuentes: print("Aviso: no hay imágenes en la carpeta elegida; se usan imágenes de los videos del fondo.", flush=True)
        rnd.shuffle(fuentes)
    if not fuentes:                                     # automatico: fotogramas de los propios videos del fondo
        for k in (0, 2, 4):
            f = os.path.join(fotos, "fr%d.png" % k)
            sh([FF, "-nostdin", "-y", "-v", "error", "-ss", "1.2", "-i", cortes[k % len(cortes)], "-frames:v", "1", f])
            if os.path.exists(f): fuentes.append(f)
    for k in range(3):
        im = ImageOps.exif_transpose(Image.open(fuentes[k % len(fuentes)])).convert("RGB")
        ImageOps.fit(im, (640, 640), Image.LANCZOS).save(os.path.join(fotos, "img%d.png" % (k + 1)))

# ---------------------------------------------------------------- el recuadro (se dibuja al doble de tamano y se reduce, para bordes suaves)
K = 2
def maquetar(estado):
    """Devuelve (alto_del_recuadro, dibujar) ; dibujar(etapa) -> imagen RGBA 1080x1920 con todo lo visible hasta esa etapa."""
    e = ESTILO; s = float(e["escala"]); tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    F = lambda n: ImageFont.truetype(VERDANA, int(n * s * K))
    px = lambda v: int(v * K)
    CW, PAD = 900, 54; INNER = CW - 2 * PAD
    letras, amar, chipc = hexrgb(e["letras"]), hexrgb(e["amarillo"]), hexrgb(e["chip"])
    borde_t = (110, 75, 0, 255)                        # contorno suave oscuro para que las letras blancas se lean sobre el amarillo
    def envolver(t, f, maxw):
        out, ln = [], ""
        for w in t.split():
            c = (ln + " " + w).strip()
            if tmp.textlength(c, font=f) <= maxw * K or not ln: ln = c
            else: out.append(ln); ln = w
        if ln: out.append(ln)
        return out
    ops = []; y = PAD
    # --- etapa 0: ubicacion, rubro, fotos, servicio, titulo (todo centrado)
    if UBIC:
        f = F(36); ops.append((0, "ubic", y, UBIC, f, letras)); y += 36 * s * 1.3 + 22
    if RUBRO:
        f = F(32); w = tmp.textlength(RUBRO.upper(), font=f) / K + 64; h = 60 * s
        ops.append((0, "chip", y, w, h, f)); y += h + 26
    ph = (INNER - 2 * 18) / 3
    ops.append((0, "fotos", y, ph, 0, None)); y += ph + 28
    if SERVICIO:
        f = F(40); ls = envolver(SERVICIO, f, INNER)[:2]
        for l in ls: ops.append((0, "centro", y, l, f, letras[:3] + (215,))); y += 40 * s * 1.35
        y += 6
    f = F(66); ls = envolver(TITULO, f, INNER)[:3]
    for l in ls: ops.append((0, "centro", y, l, f, letras)); y += 66 * s * 1.25
    y += 26
    # --- etapas 1..n: lo que incluye
    if ITEMS:
        f = F(30); ops.append((1, "centro", y, T["incluye"], f, amar)); y += 30 * s * 1.7
    fi = F(42)
    for i, it in enumerate(ITEMS):
        ls = envolver("+ " + it, fi, INNER)[:2]
        for j, l in enumerate(ls): ops.append((1 + i, "centro", y + j * 42 * s * 1.25, l, fi, letras))
        y += len(ls) * 42 * s * 1.25 + 14
    y += 18
    # --- precio (amarillo, letras blancas)
    sp = len(ITEMS) + 1
    fp, fl = F(88), F(28); hp = (26 + 30 + 18 + 100 + 22) * s
    ops.append((sp, "precio", y, hp, (fp, fl), None)); y += hp + 22
    # --- CTA (amarillo, letras blancas)
    sc = len(ITEMS) + 2
    fc = F(64); hc = 112 * s
    ops.append((sc, "cta", y, hc, fc, None)); y += hc + PAD - 22
    H = y
    top = {"arriba": 120, "abajo": 1920 - H - 200}.get(e["posicion"], (1920 - H) / 2)
    def dibujar(etapa):
        im = Image.new("RGBA", (px(1080), px(1920)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x0 = 90
        d.rounded_rectangle((px(x0), px(top), px(x0 + CW), px(top + H)), radius=px(46), fill=hexrgb(e["tarjeta"], int(255 * float(e["opacidad"]))))
        for et, tipo, yy, a, b, c in ops:
            if et > etapa: continue
            Y = top + yy
            if tipo == "chip":
                cx = 540; d.rounded_rectangle((px(cx - a / 2), px(Y), px(cx + a / 2), px(Y + b)), radius=px(b / 2), fill=chipc)
                d.text((px(cx), px(Y + b / 2)), RUBRO.upper(), font=c, fill=(255, 255, 255, 255), anchor="mm")
            elif tipo == "fotos":
                for k in range(3):
                    xx = x0 + PAD + k * (a + 18); ft = Image.open(os.path.join(W, "fotos", "img%d.png" % (k + 1))).convert("RGBA").resize((px(a), px(a)), Image.LANCZOS)
                    m = Image.new("L", ft.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, ft.size[0], ft.size[1]), radius=px(26), fill=255)
                    im.paste(ft, (px(xx), px(Y)), m)
            elif tipo == "centro":
                d.text((px(540), px(Y)), a, font=b, fill=c, anchor="ma")
            elif tipo == "ubic":       # pin + texto, centrados juntos
                wt = d.textlength(a, font=b) / K; pw = 30 * s; x_ini = 540 - (pw + 14 + wt) / 2; cy = Y + 36 * s * .55; r = 11 * s
                px_ = x_ini + pw / 2; d.ellipse((px(px_ - r), px(cy - r - 4 * s), px(px_ + r), px(cy + r - 4 * s)), fill=(255, 59, 92, 255))
                d.polygon([(px(px_ - r * .8), px(cy + r * .35 - 4 * s)), (px(px_ + r * .8), px(cy + r * .35 - 4 * s)), (px(px_), px(cy + r * 1.9 - 4 * s))], fill=(255, 59, 92, 255))
                d.ellipse((px(px_ - r * .4), px(cy - r * .4 - 4 * s), px(px_ + r * .4), px(cy + r * .4 - 4 * s)), fill=(255, 255, 255, 255))
                d.text((px(x_ini + pw + 14), px(cy)), a, font=b, fill=c, anchor="lm")
            elif tipo == "izq":
                d.text((px(x0 + PAD), px(Y)), a, font=b, fill=c, anchor="la")
            elif tipo == "item":
                cy = Y + 21 * s + 2; r = 17 * s; cx = x0 + PAD + r
                d.ellipse((px(cx - r), px(cy - r), px(cx + r), px(cy + r)), fill=amar)
                d.line([(px(cx - r * .45), px(cy + r * .02)), (px(cx - r * .1), px(cy + r * .38)), (px(cx + r * .5), px(cy - r * .32))], fill=(40, 25, 0, 255), width=px(4 * s), joint="curve")
                for j, l in enumerate(a): d.text((px(x0 + PAD + 2 * r + 20), px(Y + j * 42 * s * 1.25)), l, font=b, fill=c, anchor="la")
            elif tipo in ("precio", "cta"):
                d.rounded_rectangle((px(x0 + PAD), px(Y), px(x0 + PAD + INNER), px(Y + a)), radius=px(38), fill=amar)
                if tipo == "precio":
                    fp_, fl_ = b
                    d.text((px(540), px(Y + 26 * s)), T["promo"], font=fl_, fill=letras, anchor="ma", stroke_width=px(2), stroke_fill=borde_t)
                    d.text((px(540), px(Y + (26 + 30 + 14) * s)), PRECIO, font=fp_, fill=letras, anchor="ma", stroke_width=px(4), stroke_fill=borde_t)
                else:
                    d.text((px(540), px(Y + a / 2)), CTA, font=b, fill=letras, anchor="mm", stroke_width=px(4), stroke_fill=borde_t)
        return im.resize((1080, 1920), Image.LANCZOS)
    return dibujar, sc

# ---------------------------------------------------------------- sonidos suaves (un "pop" por cada elemento que aparece y un "ding" con el CTA)
def sonidos(tiempos, t_cta):
    SR = 44100; sfx = np.zeros((int((DUR + 1) * SR), 2), np.float32)
    def put(x, t):
        i = int(max(t, 0) * SR); x = x[: len(sfx) - i]; sfx[i:i + len(x), 0] += x; sfx[i:i + len(x), 1] += x
    def pop():
        n = int(.14 * SR); t = np.arange(n) / SR; f0 = 420 + 700 * np.exp(-t * 40); return np.sin(2 * np.pi * np.cumsum(f0) / SR) * np.exp(-t * 28) * .28
    def ding():
        n = int(.9 * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * 988 * t) + .4 * np.sin(2 * np.pi * 1976 * t)) * np.exp(-t * 5) * .22
    for t in tiempos: put(pop(), t - 0.05)
    put(ding(), t_cta)
    f = os.path.join(W, "sfx.wav")
    with wave.open(f, "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- montaje final
def montar():
    for f in ("fondo.mp4", "voz_base.mp3", "voz_info.json"):
        if not os.path.exists(os.path.join(W, f)): sys.exit("Todavía no hay un video generado: primero genera el video completo.")
    info = json.load(open(os.path.join(W, "voz_info.json"), encoding="utf-8")); m = info["marcas"]
    dibujar, sc = maquetar(info)
    # etapa 0 al inicio; etapas 1..n = cada item; precio; cta
    t_et = [0.3] + [m.get("item%d" % i, 0) for i in range(len(ITEMS))] + [m["precio"], m["cta"]]
    if not ITEMS: t_et = [0.3, m["precio"], m["cta"]]
    # los tiempos deben crecer: separacion minima entre etapas
    for i in range(1, len(t_et)): t_et[i] = max(t_et[i], t_et[i - 1] + 0.25)
    etapas = list(range(len(t_et)))
    n_etapas = len(t_et)
    # las etapas del recuadro: 0 (titulo) y luego una por elemento; "dibujar(etapa)" recibe el numero logico (item i = i+1, precio = n+1, cta = n+2)
    logicas = [0] + ([i + 1 for i in range(len(ITEMS))] if ITEMS else []) + [len(ITEMS) + 1, len(ITEMS) + 2]
    for k, lg in enumerate(logicas): dibujar(lg).save(os.path.join(W, "etapa%d.png" % k))
    sonidos(t_et[1:], t_et[-1])
    entradas = []; fc = []; prev = "0:v"
    for k in range(n_etapas):
        entradas += ["-loop", "1", "-framerate", "30", "-t", "%.2f" % DUR, "-i", "etapa%d.png" % k]
        a = t_et[k] if k else 0.25; b = t_et[k + 1] if k + 1 < n_etapas else DUR
        fc.append("[%d:v]format=rgba%s[e%d]" % (3 + k, (",fade=t=in:st=%.2f:d=0.25:alpha=1" % a) if k == 0 else "", k))
        fc.append("[%s][e%d]overlay=0:0:format=auto:enable='between(t,%.2f,%.2f)'[o%d]" % (prev, k, a, b, k)); prev = "o%d" % k
    fc.append("[%s]format=yuv420p[vo]" % prev)
    fc.append("[1:a]atempo=%.3f,adelay=%d|%d,aresample=44100,aformat=channel_layouts=stereo[va];[2:a]aresample=44100,aformat=channel_layouts=stereo[sa];"
              "[va][sa]amix=inputs=2:duration=longest:weights='1 0.5':normalize=0,alimiter=limit=0.85:level=disabled,apad=whole_dur=%.2f[a]" % (info["vel"], int(INI * 1000), int(INI * 1000), DUR))
    open(os.path.join(W, "filtro.txt"), "w", encoding="utf-8").write(";\n".join(fc))
    nombre_prev = None
    try: nombre_prev = json.load(open(os.path.join(W, "ultimo.json"), encoding="utf-8")).get("archivo")
    except Exception: pass
    if MODO == "aspecto" and nombre_prev and os.path.dirname(nombre_prev):
        salida = nombre_prev
    else:
        base = re.sub(r'[\\/:*?"<>|]', "", SERVICIO or TITULO).strip()[:60] or "precios"
        salida = os.path.join(SALIDA, "%s %s.mp4" % (base.upper(), datetime.now().strftime("%Y-%m-%d %H-%M")))
    tmp = os.path.join(W, "salida_tmp.mp4")
    cmd = [FF, "-nostdin", "-y", "-v", "error", "-i", "fondo.mp4", "-i", "voz_base.mp3", "-i", "sfx.wav"] + entradas + ["-/filter_complex", "filtro.txt", "-map", "[vo]", "-map", "[a]", "-t", "%.2f" % DUR,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "17", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", tmp]
    print("montando el video (%d s)..." % DUR, flush=True)
    r = sh(cmd, cwd=W)
    if r.returncode != 0 or not os.path.exists(tmp): sys.exit("ffmpeg código %s: %s" % (r.returncode, (r.stderr or r.stdout or "sin salida")[-1200:]))
    os.makedirs(os.path.dirname(salida), exist_ok=True); shutil.move(tmp, salida)
    json.dump({"archivo": salida}, open(os.path.join(W, "ultimo.json"), "w", encoding="utf-8"))
    print("OK ->", salida, flush=True)

if __name__ == "__main__":
    if MODO == "generar":
        rnd = random.Random()
        print("1/4 voz y tiempos...", flush=True); voz()
        print("2/4 videos de fondo...", flush=True); cortes = fondo(rnd)
        print("3/4 imágenes...", flush=True); imagenes(cortes, rnd)
        print("4/4 montaje...", flush=True); montar()
    elif MODO == "aspecto":
        montar()
    else:
        sys.exit("modo desconocido: " + MODO)
