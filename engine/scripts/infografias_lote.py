r"""INFOGRAFIAS ANIMADAS: una imagen se transforma en videos animados con distintos estilos de diseno.
Uso: uv run --python 3.12 --with pillow --with numpy python scripts\infografias_lote.py <ffmpeg.exe> generar
Lee los datos de los ajustes de la app (presets.infografias): imagen, estilos (lista), titulo, subtitulo, duracion, formato."""
import json, math, os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

FF = os.path.abspath(sys.argv[1]); MODO = sys.argv[2] if len(sys.argv) > 2 else "generar"
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def _ajustes():
    try: return json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: return {}
AJ = _ajustes(); PRE = AJ.get("presets", {}); DIRS = AJ.get("dirs", {})
ATX = PRE.get("lineaActiva") == "animtexto"          # «Animación de Texto»: mismo motor, pero el texto lo escribe la persona en vez de salir de una imagen
P = PRE.get("animtexto" if ATX else "infografias", {}) or {}
SALIDA = (DIRS.get("animtextoResultado") or os.path.join(AJ.get("workspace") or AG, "animtexto", "resultado")) if ATX else (DIRS.get("infografiasResultado") or os.path.join(AG, "infografias", "resultado")); os.makedirs(SALIDA, exist_ok=True)
FORMATOS = {"reels": (1080, 1920), "cuadrado": (1080, 1080), "vertical": (1080, 1350)}
FPS = 30

# ---------------------------------------------------------------- utilidades
def lerp(a, b, x): return a + (b - a) * x
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return cl((t - a) / d)
def e_out(x): return 1 - (1 - x) ** 3
def e_back(x): c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def e_io(x): return 3 * x * x - 2 * x ** 3
def ent(t, a=0.15, d=0.9): x = prog(t, a, d); return lerp(0.55, 1.0, e_back(x)), cl(x * 2.5)
def flot(t, amp=9): return amp * math.sin(t * 1.7) * prog(t, 0.8, 0.5)

FUENTES = {"sans": ["segoeuib", "arialbd"], "sansr": ["segoeui", "arial"], "sansl": ["segoeuil", "segoeui", "arial"], "negra": ["ariblk", "arialbd"],
           "serif": ["georgiab", "timesbd"], "serifr": ["georgia", "times"], "mono": ["consolab", "consola", "lucon"],
           "mano": ["segoeprb", "comicbd"], "impact": ["impact", "ariblk"], "redonda": ["comicbd", "segoeuib"]}
def F(k, s):
    for n in FUENTES[k]:
        p = r"C:\Windows\Fonts\%s.ttf" % n
        if os.path.exists(p): return ImageFont.truetype(p, max(8, int(s)))
    return ImageFont.load_default()

def lay_txt(txt, k, size, color, maxw, align="center", stroke=0, scol=(0, 0, 0), lh=1.16, sombra=None, mayus=False):
    if mayus: txt = txt.upper()
    f = F(k, size); d = ImageDraw.Draw(Image.new("L", (1, 1))); lines, cur = [], ""
    for w in txt.split():
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= maxw or not cur: cur = test
        else: lines.append(cur); cur = w
    lines.append(cur); lines = [l for l in lines if l][:4] or [""]
    pad = stroke + 10 + (abs(sombra[0]) + abs(sombra[1]) if sombra else 0)
    wm = int(max(d.textlength(l, font=f) for l in lines)) + pad * 2; hh = int(size * lh * len(lines)) + pad * 2 + int(size * .2)
    im = Image.new("RGBA", (wm, hh), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lw = d.textlength(l, font=f); x = (wm - lw) / 2 if align == "center" else pad if align == "left" else wm - lw - pad; y = pad + i * size * lh
        if sombra: dr.text((x + sombra[0], y + sombra[1]), l, font=f, fill=sombra[2], stroke_width=stroke, stroke_fill=sombra[2])
        dr.text((x, y), l, font=f, fill=color, stroke_width=stroke, stroke_fill=scol)
    return im

def brillo(layer, radio=14, k=1.0):
    g = layer.filter(ImageFilter.GaussianBlur(radio)); a = g.getchannel("A").point(lambda v: min(255, int(v * k))); g.putalpha(a); return g

def pegar(base, L, cx, cy, s=1.0, a=1.0, rot=0.0):
    if L is None or a <= 0.004 or s <= 0.01: return
    if rot: L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(s - 1) > 0.004: L = L.resize((max(1, int(L.width * s)), max(1, int(L.height * s))), Image.BILINEAR)
    m = L.getchannel("A")
    if a < 0.995: m = m.point(lambda v: int(v * a))
    base.paste(L.convert("RGB"), (int(cx - L.width / 2), int(cy - L.height / 2)), m)

def contain(im, w, h):
    s = min(w / im.width, h / im.height); return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
def cover(im, w, h):
    return ImageOps.fit(im, (int(w), int(h)), Image.LANCZOS)
def mask_rr(size, r, fill=255):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=fill); return m
def redond(im, r):
    x = im.convert("RGBA"); x.putalpha(mask_rr(x.size, r)); return x
def sombra(w, h, r, blur, dx, dy, col, al, pad):
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(m).rounded_rectangle((pad + dx, pad + dy, pad + dx + w, pad + dy + h), r, fill=int(255 * al))
    m = m.filter(ImageFilter.GaussianBlur(blur)); L = Image.new("RGBA", m.size, tuple(col) + (255,)); L.putalpha(m); return L
def apilar(size, *partes):
    L = Image.new("RGBA", size, (0, 0, 0, 0))
    for p, pos in partes: L.alpha_composite(p, (int(pos[0]), int(pos[1])))
    return L
def plano(size, col):
    return Image.new("RGB", size, tuple(col))
def vgrad(w, h, c1, c2, horizontal=False):
    n = w if horizontal else h; t = np.linspace(0, 1, n)[:, None]
    arr = (np.array(c1)[None, :] * (1 - t) + np.array(c2)[None, :] * t).astype("uint8")
    a = np.tile(arr[None, :, :], (h, 1, 1)) if horizontal else np.tile(arr[:, None, :], (1, w, 1))
    return Image.fromarray(a, "RGB")
def blobs(w, h, cols, t, vel=0.4, r=0.6):
    sw, sh = max(8, w // 6), max(8, h // 6); yy, xx = np.mgrid[0:sh, 0:sw]; xx = xx / sw; yy = yy / sh
    out = np.zeros((sh, sw, 3)); ws = np.zeros((sh, sw, 1)) + 1e-6
    for i, col in enumerate(cols):
        ph = i * 2.1; cx = .5 + .45 * math.sin(t * vel + ph); cy = .5 + .45 * math.cos(t * vel * .8 + ph * 1.3)
        wg = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r * 0.18))[..., None]; out += wg * np.array(col); ws += wg
    return Image.fromarray((out / ws).astype("uint8")).resize((w, h), Image.BICUBIC)
def inflar(mask, col, amt=14, blur=12):
    L = Image.new("RGBA", mask.size, tuple(col) + (255,)); L.putalpha(mask)
    luz = ImageChops.multiply(ImageChops.subtract(mask, ImageChops.offset(mask, amt, amt)).filter(ImageFilter.GaussianBlur(blur)), mask)
    som = ImageChops.multiply(ImageChops.subtract(mask, ImageChops.offset(mask, -amt, -amt)).filter(ImageFilter.GaussianBlur(blur)), mask)
    B = Image.new("RGBA", mask.size, (255, 255, 255, 255)); B.putalpha(luz.point(lambda v: int(v * .8))); L.alpha_composite(B)
    D = Image.new("RGBA", mask.size, (60, 30, 50, 255)); D.putalpha(som.point(lambda v: int(v * .45))); L.alpha_composite(D)
    return L
def dash_rect(dr, box, col, w=4, d=18, g=12, r=0):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        L = math.hypot(bx - ax, by - ay); n = int(L // (d + g)) + 1
        for i in range(n):
            s0 = i * (d + g) / L; s1 = min(1, (i * (d + g) + d) / L)
            dr.line((ax + (bx - ax) * s0, ay + (by - ay) * s0, ax + (bx - ax) * s1, ay + (by - ay) * s1), fill=col, width=w)

class _Ctx: pass

# ---------------------------------------------------------------- 1) INTERPRETAR LA IMAGEN (Claude Code lee la imagen, traduce y ordena el texto)
ETQ_DEF = {"es": ("No digas", "Mejor di"), "en": ("Don't say", "Say instead"), "pt": ("Não diga", "Diga"), "de": ("Sag nicht", "Sag lieber"), "fr": ("Ne dis pas", "Dis plutôt"), "it": ("Non dire", "Meglio dire")}
VOCES_AUTO = {"es": "es-MX-JorgeNeural", "en": "en-US-GuyNeural", "pt": "pt-BR-AntonioNeural", "de": "de-DE-ConradNeural", "fr": "fr-FR-HenriNeural", "it": "it-IT-DiegoNeural"}
IDIOMAS = {"":"el mismo idioma que aparece en la imagen", "es": "español", "en": "inglés", "pt": "portugués", "de": "alemán"}
def buscar_claude():
    import glob, shutil
    w = shutil.which("claude")
    if w: return w
    h = os.path.expanduser("~"); c = os.path.join(h, ".local", "bin", "claude.exe")
    if os.path.exists(c): return c
    for d in sorted(glob.glob(os.path.join(h, ".vscode", "extensions", "anthropic.claude-code*")), reverse=True):
        for r, _, fs in os.walk(d):
            if "claude.exe" in fs: return os.path.join(r, "claude.exe")
    return None

def interpretar(img, idioma, texto=None):
    import hashlib, re as _re
    op = os.path.join(AG, "infografias", "_operacion", "lectura"); os.makedirs(op, exist_ok=True)
    h = hashlib.sha1((texto.encode("utf-8") + b"t1" if texto is not None else img.tobytes()[:2000000]) + idioma.encode() + b"v4").hexdigest()[:16]; cache = os.path.join(op, "lectura_%s.json" % h)
    if os.path.exists(cache):
        try: print("Texto de la imagen: ya estaba leído, se reutiliza.", flush=True); return json.load(open(cache, encoding="utf-8"))
        except Exception: pass
    cl_ = buscar_claude()
    if not cl_: sys.exit("No se encontró Claude Code, que es el que lee el texto de la imagen. Instálalo e inicia sesión (Ajustes → Claude Code).")
    if texto is None: big = img if max(img.size) <= 1800 else contain(img, 1800, 1800); big.save(os.path.join(op, "imagen_entrada.png"))
    cabeza = ('Usa la herramienta Read para ver la imagen ./imagen_entrada.png. Es una infografía o un diseño con texto. Lee TODO el texto y reorganízalo para una animación de texto de varias escenas. ' if texto is None else
              'Este es el texto que la persona quiere narrar y animar en un video de texto (puede ser un guion, una lista de consejos, una explicación o una historia):\n<<<\n' + texto + '\n>>>\nDivídelo en escenas para una animación de texto, conservando sus palabras y su orden (puedes acortar una frase muy larga, pero no inventes ideas ni cambies el sentido). Copia las cifras, nombres y datos exactamente como están escritos, y deja "subtitulo" vacío si el texto no trae una bajada propia. Donde abajo se habla de «la imagen» entiende «este texto». ')
    prompt = cabeza + ('Escribe el texto en %s (traduce si hace falta; conserva cifras, nombres propios y marcas). Responde SOLO con un JSON válido, sin explicaciones ni bloques de código, con esta forma exacta: '
              '{"idioma":"código de 2 letras del idioma del texto que escribes (es, en, pt, de, fr, it…)","titulo":"título principal, corto","subtitulo":"bajada o texto de apoyo, o vacío",'
              '"puntos":[{"tipo":"paso|contraste|dato|lista","transicion":"zoom|deslizar|subir|giro|fade","encabezado":"idea corta de 1 a 6 palabras, sin numeración","texto":"explicación breve, o vacío","a":"","b":"","etq_a":"","etq_b":"","tachar":true,"dato":"","items":[]}],'
              '"cierre":"frase final o llamado a la acción si existe, o vacío"}. '
              'Tú decides cómo se anima cada bloque según su SIGNIFICADO; elige para cada punto un "tipo": '
              '"paso" = una idea, paso o consejo con encabezado corto y texto opcional. '
              '"contraste" = el bloque compara dos cosas (No digas / Mejor di, Mito / Realidad, Antes / Después, Error / Correcto, Evita / Usa, Pregunta / Respuesta…): pon en "a" lo primero (lo que se descarta o la pregunta) y en "b" lo segundo, solo las frases; '
              '"etq_a" y "etq_b" son las etiquetas cortas de cada lado en el idioma de salida (p. ej. No digas / Mejor di); "tachar" = true si "a" es algo malo o incorrecto que se descarta (se animará tachándolo), false si es neutro (pregunta, antes). '
              '"dato" = una cifra o estadística destacada: "dato" es solo la cifra (p. ej. 87%% o 3x o $25) y "texto" explica qué significa. '
              '"lista" = un bloque con varios elementos cortos (requisitos, ingredientes, viñetas): "items" con 2 a 6 elementos cortos y "encabezado" con el título de la lista. '
              'Para cada punto elige también una "transicion" según el sentido: "zoom" para algo importante o de impacto, "deslizar" para pasos o secuencias, "subir" para consejos o crecimiento, "giro" para cambios o contrastes, "fade" para algo calmado; varíalas. '
              'Reglas: máximo 7 puntos, uno por cada bloque, paso o dato de la imagen en el orden en que se leen; no inventes nada que no esté en la imagen; no pongas números de paso en los encabezados; deja vacíos los campos que no correspondan al tipo; '
              'si la imagen es solo una foto sin texto, describe en 3 a 5 puntos cortos lo que muestra.') % IDIOMAS.get(idioma, IDIOMAS[""])
    if texto is not None: prompt = prompt.replace("máximo 7 puntos", "máximo 10 puntos")
    e = dict(os.environ); e.pop("ELECTRON_RUN_AS_NODE", None); e["PYTHONIOENCODING"] = "utf-8"
    print("Leyendo el texto de la imagen con Claude Code… (puede tardar unos segundos)" if texto is None else "Interpretando tu texto con Claude Code… (puede tardar unos segundos)", flush=True)
    try: r = subprocess.run([cl_, "-p", prompt, "--allowedTools", "Read", "--output-format", "text"], cwd=op, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=e)
    except Exception as ex: sys.exit("No se pudo ejecutar Claude Code: %s" % ex)
    sal = (r.stdout or "").strip(); m = _re.search(r"\{.*\}", sal, _re.S)
    try: D = json.loads(m.group(0)) if m else None
    except Exception: D = None
    if not D or not (D.get("titulo") or D.get("puntos")):
        sys.exit("No se pudo leer la imagen. Comprueba que Claude Code tenga la sesión iniciada (Ajustes → Claude Code). Respuesta: " + (sal or r.stderr or "vacía")[:300])
    S_ = lambda v: str(v or "").strip()
    cod = S_(D.get("idioma")).lower()[:2] or "es"; ed_ = ETQ_DEF.get(cod, ETQ_DEF["es"]); cic = ["zoom", "deslizar", "subir", "giro", "fade"]
    def punto(i, p):
        tp = S_(p.get("tipo")).lower(); a, b = S_(p.get("a")), S_(p.get("b")); items = [S_(x) for x in (p.get("items") or []) if S_(x)][:6]; dato = S_(p.get("dato"))
        if tp == "contraste" and not (a and b): tp = "paso"
        if tp == "lista" and len(items) < 2: tp = "paso"
        if tp == "dato" and not dato: tp = "paso"
        if tp not in ("paso", "contraste", "dato", "lista"): tp = "paso"
        tr = S_(p.get("transicion")).lower(); tr = tr if tr in cic else cic[i % len(cic)]; tach = p.get("tachar"); tach = True if tach is None else bool(tach)
        return {"tipo": tp, "transicion": tr, "encabezado": S_(p.get("encabezado")), "texto": S_(p.get("texto")), "a": a, "b": b, "etq_a": S_(p.get("etq_a")) or ed_[0], "etq_b": S_(p.get("etq_b")) or ed_[1], "tachar": tach, "dato": dato, "items": items}
    ps = [p for p in (D.get("puntos") or []) if isinstance(p, dict) and (p.get("encabezado") or p.get("texto") or (p.get("a") and p.get("b")) or p.get("dato") or p.get("items"))][:(10 if texto is not None else 7)]
    D = {"idioma": cod, "titulo": S_(D.get("titulo")), "subtitulo": S_(D.get("subtitulo")), "cierre": S_(D.get("cierre")), "puntos": [punto(i, p) for i, p in enumerate(ps)]}
    json.dump(D, open(cache, "w", encoding="utf-8"), ensure_ascii=False); return D

# ---------------------------------------------------------------- 2) TEXTO ANIMADO PALABRA POR PALABRA
def maq(txt, fk, size, color, maxw, mayus=False, lh=1.2, align="center"):
    if mayus: txt = txt.upper()
    f = F(fk, size); d = ImageDraw.Draw(Image.new("L", (1, 1))); esp = d.textlength(" ", font=f); lineas = [[]]; ancho = 0
    for w in txt.split():
        ww = d.textlength(w, font=f)
        if lineas[-1] and ancho + esp + ww > maxw: lineas.append([]); ancho = 0
        ancho += ww + (esp if lineas[-1] else 0); lineas[-1].append((w, ww))
    lineas = lineas[:7]; pal = []; lin = []
    for i, ln in enumerate(lineas):
        lw = sum(w for _, w in ln) + esp * max(0, len(ln) - 1); x = (maxw - lw) / 2 if align == "center" else 0; lin.append((x, x + lw, i * size * lh))
        for w, ww in ln: pal.append((w, x, i * size * lh)); x += ww + esp
    return dict(p=pal, f=f, col=color, w=maxw, h=len(lineas) * size * lh + size * .3, n=max(1, len(pal)), size=size, lin=lin)
def dib_pal(C, M, tr, ini, paso, ox, oy, sombra=None):
    d = ImageDraw.Draw(C, "RGBA")
    for i, (w, x, y) in enumerate(M["p"]):
        k = e_out(prog(tr, ini + i * paso, .35))
        if k <= 0: continue
        yy = oy + y + (1 - k) * 18
        if sombra: d.text((ox + x + sombra[0], yy + sombra[1]), w, font=M["f"], fill=tuple(sombra[2]) + (int(255 * k),))
        d.text((ox + x, yy), w, font=M["f"], fill=tuple(M["col"][:3]) + (int(255 * k),))

# ---------------------------------------------------------------- 3) TEMAS (un diseno por estilo)
def panel_s(w, h, r=28, fill=(255, 255, 255), sh=(30, 0, 22, (0, 0, 0), .2), borde=None, pad=80):
    L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if sh: L.alpha_composite(sombra(w, h, r, sh[0], sh[1], sh[2], sh[3], sh[4], pad))
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0)); fl = tuple(fill) if len(fill) == 4 else tuple(fill) + (255,)
    ImageDraw.Draw(p).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fl, outline=borde[1] if borde else None, width=borde[0] if borde else 0); L.alpha_composite(p, (pad, pad)); return L, pad
def ventana(w, h, bar, colbar, colcuerpo, titulo, tcol, r=0, botones=True, pad=50, sh=(1, 18, 18, (60, 0, 90), .8), bisel=False):
    L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if sh: L.alpha_composite(sombra(w, h, r, sh[0], sh[1], sh[2], sh[3], sh[4], pad))
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=colcuerpo + (255,), outline=(255, 255, 255) if bisel else (0, 0, 0, 40), width=2 if not bisel else 3)
    d.rectangle((4, 4, w - 5, bar - 6), fill=colbar) if bisel else d.rounded_rectangle((0, 0, w - 1, bar), r, fill=colbar + (255,))
    d.text((18, bar / 2 - 18), titulo[:24], font=F("sans", 30), fill=tcol)
    if botones:
        for i, g in enumerate(("_", "□", "x")):
            x = w - 52 - i * 46
            if bisel: d.rectangle((x, 8, x + 36, bar - 12), fill=(192, 192, 192), outline=(0, 0, 0)); d.text((x + 11, 6), g, font=F("sans", 26), fill=(0, 0, 0))
            else: d.text((x + 8, bar / 2 - 18), {"_": "—", "□": "▢", "x": "✕"}[g], font=F("sansr", 28), fill=tcol)
    L.alpha_composite(p, (pad, pad)); return L, pad

def base_tema(W, H, **kw):
    t = dict(ft="sans", fh="sans", fb="sansr", tit=(30, 30, 30), sub=(110, 110, 110), ph=(30, 30, 30), pb=(90, 90, 90), ac=(255, 87, 51), bn=(255, 255, 255), bshape="circle", esc=1.0, pw=lambda i: .86 * W, cy=.5 * H, ctop=0, mx=.06, my=.05,
             over=None, rot=lambda i: 0.0, sombra_t=None, mayus=False)
    t.update(kw); return t

def T_minimalista(W, H):
    bg = plano((W, H), (250, 250, 248)); return base_tema(W, H, bg=lambda t: bg.copy(), panel=lambda w, h, i: panel_s(w, h, 24, (255, 255, 255), (30, 0, 20, (0, 0, 0), .12)), ft="sansl", fh="sans", fb="sansr", ac=(255, 87, 51))
def T_flat(W, H):
    forms = [((.15, .12), 150, (255, 99, 71), 0), ((.88, .2), 110, (46, 134, 222), 1), ((.1, .88), 130, (46, 204, 113), 1), ((.9, .86), 170, (155, 89, 182), 0)]
    def bg(t):
        b = plano((W, H), (255, 201, 60)); d = ImageDraw.Draw(b)
        for i, ((px, py), r, col, tri) in enumerate(forms):
            x = W * px + 30 * math.sin(t * .8 + i); y = H * py + 30 * math.cos(t * .7 + i)
            d.polygon([(x, y - r), (x - r, y + r * .8), (x + r, y + r * .8)], fill=col) if tri else d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        return b
    return base_tema(W, H, bg=bg, panel=lambda w, h, i: panel_s(w, h, 34, (255, 255, 255), None, pad=10), ft="negra", fh="negra", tit=(25, 45, 110), sub=(25, 45, 110), ph=(25, 45, 110), pb=(60, 70, 110), ac=(46, 134, 222))
def T_skeuo(W, H):
    rs = np.random.RandomState(3).randint(-10, 10, (H // 3, W // 3, 1)); base = np.array(vgrad(W // 3, H // 3, (120, 78, 46), (70, 42, 24)), dtype="int16") + rs
    fondo = Image.fromarray(np.clip(base, 0, 255).astype("uint8")).resize((W, H), Image.BILINEAR)
    def panel(w, h, i):
        pad = 70; m = 24; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 34, 30, 0, 26, (0, 0, 0), .6, pad))
        L.alpha_composite(redond(vgrad(w, h, (235, 235, 238), (110, 112, 120)), 34), (pad, pad)); L.alpha_composite(redond(plano((w - 2 * m, h - 2 * m), (250, 244, 228)), 16), (pad + m, pad + m))
        g = Image.new("RGBA", (w - 2 * m, h - 2 * m), (0, 0, 0, 0)); ImageDraw.Draw(g).polygon([(0, 0), (w - 2 * m, 0), (0, (h - 2 * m) * .5)], fill=(255, 255, 255, 50)); L.alpha_composite(g, (pad + m, pad + m)); return L, pad
    return base_tema(W, H, bg=lambda t: fondo.copy(), panel=panel, ft="serif", fh="serif", fb="serifr", tit=(245, 228, 190), sub=(235, 215, 180), ph=(80, 45, 20), pb=(95, 65, 40), ac=(170, 60, 40), mx=.09, my=.07, sombra_t=(3, 3, (40, 22, 10)))
def T_neumorfismo(W, H):
    col = (224, 229, 236); bg = plano((W, H), col)
    def panel(w, h, i):
        pad = 90; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 56, 24, 22, 22, (163, 177, 198), 1, pad)); L.alpha_composite(sombra(w, h, 56, 24, -22, -22, (255, 255, 255), 1, pad)); L.alpha_composite(redond(plano((w, h), col), 56), (pad, pad)); return L, pad
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=panel, tit=(105, 118, 140), sub=(140, 150, 170), ph=(95, 108, 135), pb=(130, 140, 165), ac=(110, 130, 225))
def T_glass(W, H):
    cols = [(255, 94, 98), (255, 153, 102), (120, 80, 255), (30, 190, 220), (255, 90, 200)]
    orbe = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); ImageDraw.Draw(orbe).ellipse((0, 0, 259, 259), fill=(255, 255, 255, 90), outline=(255, 255, 255, 200), width=3)
    def bg(t):
        b = blobs(W, H, cols, t, .5, .55); pegar(b, orbe, W * .85 + 20 * math.sin(t), H * .15 + 25 * math.cos(t)); pegar(b, orbe, W * .12 + 25 * math.cos(t * .9), H * .88 + 20 * math.sin(t), .7); return b
    def panel(w, h, i):
        L, p = panel_s(w, h, 50, (255, 255, 255, 62), (30, 0, 24, (30, 10, 80), .3), borde=(3, (255, 255, 255, 150))); return L, p
    return base_tema(W, H, bg=bg, panel=panel, tit=(255, 255, 255), sub=(255, 255, 255), ph=(255, 255, 255), pb=(255, 255, 255), ac=(255, 255, 255), bn=(110, 60, 210), sombra_t=(0, 3, (60, 20, 110)))
def T_clay(W, H):
    bolas = []
    for d_, col in ((150, (120, 200, 255)), (110, (255, 214, 90)), (90, (160, 230, 170))):
        m = Image.new("L", (d_, d_), 0); ImageDraw.Draw(m).ellipse((0, 0, d_ - 1, d_ - 1), fill=255); bolas.append(apilar((d_ + 40, d_ + 40), (inflar(m, col, 12, 10), (20, 20))))
    pos = [(.14, .1), (.88, .17), (.82, .9)]; fondo = vgrad(W, H, (255, 232, 240), (232, 225, 255))
    def bg(t):
        b = fondo.copy()
        for i, (bo, (px, py)) in enumerate(zip(bolas, pos)): pegar(b, bo, W * px, H * py + 22 * math.sin(t * 1.4 + i * 2))
        return b
    def panel(w, h, i):
        pad = 70; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 110, 30, 0, 30, (190, 90, 130), .45, pad)); L.alpha_composite(inflar(mask_rr((w, h), 110), (255, 205, 220), 18, 14), (pad, pad)); return L, pad
    return base_tema(W, H, bg=bg, panel=panel, ft="redonda", fh="redonda", fb="redonda", tit=(130, 60, 100), sub=(160, 100, 140), ph=(120, 45, 85), pb=(150, 80, 120), ac=(120, 190, 255), mx=.09, my=.08)
def T_neobrutalismo(W, H):
    bg = plano((W, H), (255, 222, 89)); star = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); sd = ImageDraw.Draw(star)
    pts = [(130 + (125 if i % 2 == 0 else 70) * math.cos(i * math.pi / 8), 130 + (125 if i % 2 == 0 else 70) * math.sin(i * math.pi / 8)) for i in range(16)]; sd.polygon(pts, fill=(80, 200, 255)); sd.line(pts + [pts[0]], fill=(0, 0, 0), width=8)
    def b_(t): b = bg.copy(); pegar(b, star, W * .86, H * .1, 1, 1, rot=t * 40); return b
    def panel(w, h, i):
        off = 26; pad = 40; L = Image.new("RGBA", (w + 2 * pad + off, h + 2 * pad + off), (0, 0, 0, 0)); d = ImageDraw.Draw(L); d.rectangle((pad + off, pad + off, pad + off + w, pad + off + h), fill=(0, 0, 0)); d.rectangle((pad, pad, pad + w, pad + h), fill=(255, 255, 255), outline=(0, 0, 0), width=10); return L, pad
    return base_tema(W, H, bg=b_, panel=panel, ft="negra", fh="negra", fb="sans", tit=(0, 0, 0), sub=(0, 0, 0), ph=(0, 0, 0), pb=(30, 30, 30), ac=(255, 110, 170), bn=(0, 0, 0), bshape="square", mayus=True)
def T_bento(W, H):
    bg = plano((W, H), (240, 240, 243)); cols = [(255, 213, 79), (138, 180, 248), (255, 138, 128), (129, 199, 132), (206, 147, 216), (128, 222, 234), (255, 171, 145)]
    def panel(w, h, i): L, p = panel_s(w, h, 46, cols[i % len(cols)], None, pad=10); return L, p
    def over(b, t, i):
        d = ImageDraw.Draw(b); k = e_back(prog(t % 4, 0, .8))
        for j, col in enumerate((cols[(i + 1) % 7], cols[(i + 2) % 7])):
            x = W * (.08 if j == 0 else .56); w_ = W * .36; y = H * .045 if j == 0 else H * .9; d.rounded_rectangle((x, y, x + w_ * k, y + H * .05), 24, fill=col)
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=panel, tit=(40, 30, 0), sub=(90, 80, 40), ph=(30, 30, 40), pb=(50, 50, 60), ac=(255, 255, 255), bn=(40, 40, 50), over=over, ft="negra", fh="negra")
def T_neon(W, H):
    cyan = (0, 240, 255); mag = (255, 40, 200)
    def bg(t):
        b = vgrad(W, H, (6, 3, 18), (22, 6, 40)); d = ImageDraw.Draw(b, "RGBA"); off = (t * 60) % 90
        for i in range(-1, W // 90 + 2): d.line((i * 90, 0, i * 90, H), fill=(120, 40, 220, 55), width=2)
        for j in range(-1, H // 90 + 2): d.line((0, j * 90 + off, W, j * 90 + off), fill=(120, 40, 220, 55), width=2)
        return b
    def panel(w, h, i):
        pad = 70; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); b0 = Image.new("RGBA", L.size, (0, 0, 0, 0)); d = ImageDraw.Draw(b0); d.rounded_rectangle((pad, pad, pad + w, pad + h), 26, outline=cyan + (255,), width=8); d.rounded_rectangle((pad + 14, pad + 14, pad + w - 14, pad + h - 14), 18, outline=mag + (255,), width=3)
        L.alpha_composite(redond(plano((w, h), (12, 8, 30)), 26) if False else Image.new("RGBA", (1, 1))); fondo = Image.new("RGBA", (w, h), (12, 8, 30, 235)); L.alpha_composite(fondo, (pad, pad)); L.alpha_composite(brillo(b0, 22, 2.2)); L.alpha_composite(b0); return L, pad
    def over(b, t, i):
        d = ImageDraw.Draw(b, "RGBA")
        for yy in range(0, H, 6): d.line((0, yy, W, yy), fill=(0, 0, 0, 14))
    return base_tema(W, H, bg=bg, panel=panel, ft="mono", fh="mono", fb="mono", tit=cyan, sub=mag, ph=cyan, pb=(225, 225, 255), ac=mag, over=over)
def T_aurora(W, H):
    cols = [(30, 220, 160), (40, 120, 255), (150, 70, 255), (20, 200, 220), (255, 90, 190), (60, 255, 150)]
    return base_tema(W, H, bg=lambda t: blobs(W, H, cols, t, .35, .8), panel=lambda w, h, i: panel_s(w, h, 60, (255, 255, 255, 46), (34, 0, 26, (10, 20, 60), .35), borde=(2, (255, 255, 255, 130))), tit=(255, 255, 255), sub=(255, 255, 255), ph=(255, 255, 255), pb=(255, 255, 255), ac=(255, 255, 255), bn=(30, 90, 200), sombra_t=(0, 3, (20, 30, 90)))
def T_retro(W, H):
    def bg(t):
        b = vgrad(W, H, (255, 113, 206), (130, 60, 220)); d = ImageDraw.Draw(b, "RGBA"); sy = int(H * .62); cx = W // 2; r = int(W * .3); d.ellipse((cx - r, sy - 2 * r, cx + r, sy), fill=(255, 220, 90))
        for i in range(6): d.rectangle((cx - r, sy - r * .9 + i * r * .18, cx + r, sy - r * .9 + i * r * .18 + 4 + i * 3), fill=(255, 113, 206))
        d.rectangle((0, sy, W, H), fill=(30, 10, 70)); off = (t * 50) % 80
        for k in range(-12, 13): d.line((cx + k * 42, sy, cx + k * 420, H), fill=(1, 205, 254, 160), width=2)
        j = 0; y = sy + off * .2
        while y < H: d.line((0, y, W, y), fill=(1, 205, 254, 160), width=2); j += 1; y += 14 + j * 9
        return b
    return base_tema(W, H, bg=bg, panel=lambda w, h, i: ventana(w, h, 56, (0, 0, 170), (192, 192, 192), "paso_%d.exe" % (i + 1), (255, 255, 255), bisel=True), ctop=56, ft="impact", fh="impact", fb="mono", tit=(255, 255, 255), sub=(255, 255, 255), ph=(0, 0, 120), pb=(20, 20, 20), ac=(255, 60, 170), bn=(255, 255, 255), sombra_t=(6, 6, (1, 205, 254)), mayus=True)
def T_isometrico(W, H):
    def cubo(sz, cols):
        L = Image.new("RGBA", (int(sz * 1.8), int(sz * 2.1)), (0, 0, 0, 0)); d = ImageDraw.Draw(L); cx = L.width / 2; yy = sz * .3; k = sz * .9
        d.polygon([(cx, yy), (cx + k, yy + k * .5), (cx, yy + k), (cx - k, yy + k * .5)], fill=cols[0]); d.polygon([(cx - k, yy + k * .5), (cx, yy + k), (cx, yy + k * 2), (cx - k, yy + k * 1.5)], fill=cols[1]); d.polygon([(cx + k, yy + k * .5), (cx, yy + k), (cx, yy + k * 2), (cx + k, yy + k * 1.5)], fill=cols[2]); return L
    cubos = [(cubo(90, ((255, 190, 90), (225, 150, 50), (190, 120, 30))), .14, .1), (cubo(70, ((120, 220, 190), (80, 180, 150), (50, 140, 110))), .86, .9), (cubo(60, ((255, 140, 170), (225, 100, 130), (190, 70, 100))), .86, .12), (cubo(80, ((140, 160, 255), (100, 120, 225), (70, 90, 190))), .12, .88)]
    fondo = vgrad(W, H, (226, 233, 255), (250, 232, 245))
    def bg(t):
        b = fondo.copy()
        for i, (cb, px, py) in enumerate(cubos): pegar(b, cb, W * px, H * py + 24 * math.sin(t * 1.3 + i * 1.7))
        return b
    def panel(w, h, i):
        pad = 60; esp = 28; L = Image.new("RGBA", (w + 2 * pad + esp, h + 2 * pad + esp), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 14, 30, esp, esp + 18, (50, 60, 130), .35, pad))
        for k in range(esp, 0, -2): L.alpha_composite(redond(plano((w, h), (70, 82, 150) if k > 8 else (90, 102, 175)), 14), (pad + k // 2, pad + k))
        L.alpha_composite(redond(plano((w, h), (255, 255, 255)), 14), (pad, pad)); return L, pad
    return base_tema(W, H, bg=bg, panel=panel, tit=(50, 55, 110), sub=(80, 90, 140), ph=(40, 45, 100), pb=(80, 90, 140), ac=(255, 140, 90))
def T_ilustrado(W, H):
    rs = np.random.RandomState(7); gr = rs.randint(-9, 9, (H // 2, W // 2, 1)); bg = Image.fromarray(np.clip(np.array(plano((W // 2, H // 2), (247, 240, 224)), dtype="int16") + gr, 0, 255).astype("uint8")).resize((W, H), Image.BILINEAR)
    def panel(w, h, i):
        pad = 60; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 4, 18, 8, 14, (60, 40, 20), .4, pad)); L.alpha_composite(Image.new("RGBA", (w, h), (254, 252, 246, 255)), (pad, pad))
        cinta = Image.new("RGBA", (190, 56), (255, 214, 90, 200)).rotate(-4, expand=True); L.alpha_composite(cinta, (int(pad + w / 2 - 95), pad - 28)); return L, pad
    def estrella(cx, cy, r): return [(cx + (r if i % 2 == 0 else r * .45) * math.sin(i * math.pi / 5), cy - (r if i % 2 == 0 else r * .45) * math.cos(i * math.pi / 5)) for i in range(11)]
    def b_(t):
        b = bg.copy(); d = ImageDraw.Draw(b); n = int(11 * prog(t % 6, .2, .8)); e = estrella(W * .86, H * .1, 56)
        if n > 1: d.line(e[:n + 1], fill=(40, 140, 220), width=6, joint="curve")
        sp = [(W * .12 + (i * 1.5) * math.cos(i * .35) * 2.2, H * .9 + (i * 1.5) * math.sin(i * .35) * 2.2) for i in range(41)]; n = int(40 * prog(t % 6, 1., .9))
        if n > 1: d.line(sp[:n], fill=(60, 170, 110), width=6, joint="curve")
        return b
    return base_tema(W, H, bg=b_, panel=panel, ft="mano", fh="mano", fb="mano", tit=(60, 40, 30), sub=(100, 75, 60), ph=(60, 40, 30), pb=(100, 75, 60), ac=(240, 90, 90), rot=lambda i: (-2.5 if i % 2 == 0 else 2.2))
def T_editorial(W, H):
    bg = plano((W, H), (244, 239, 230)); ink = (20, 20, 20); marg = int(W * .07); cab = lay_txt("EDICIÓN ESPECIAL · INFOGRAFÍA", "sans", W * .026, ink, W * .86, align="left")
    def over(b, t, i):
        d = ImageDraw.Draw(b); k = e_out(prog(t % 100, .1, .8)); d.rectangle((marg, 70, marg + (W - 2 * marg) * k, 76), fill=ink); pegar(b, cab, marg + cab.width / 2 - 10, 112); d.rectangle((marg, H - 90, marg + (W - 2 * marg) * k, H - 86), fill=ink)
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=None, over=over, ft="serif", fh="serif", fb="serifr", tit=ink, sub=(70, 70, 70), ph=ink, pb=(60, 60, 60), ac=(200, 40, 40), bshape="num", pw=lambda i: .84 * W)
def T_memphis(W, H):
    def forma(k, col, sz):
        L = Image.new("RGBA", (sz + 20, sz + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(L); o = 10
        if k == "c": d.ellipse((o, o, o + sz, o + sz), fill=col, outline=(0, 0, 0), width=6)
        elif k == "t": d.polygon([(o + sz / 2, o), (o + sz, o + sz), (o, o + sz)], fill=col, outline=(0, 0, 0))
        elif k == "z": d.line([(o + i * sz / 6, o + (sz if i % 2 else 0) * .6 + sz * .2) for i in range(7)], fill=col, width=14, joint="curve")
        elif k == "p":
            for i in range(3):
                for j in range(3): d.ellipse((o + i * sz / 3, o + j * sz / 3, o + i * sz / 3 + 12, o + j * sz / 3 + 12), fill=col)
        else: d.rectangle((o, o, o + sz, o + sz * .6), fill=col, outline=(0, 0, 0), width=6)
        return L
    fs = [("c", (255, 214, 0), 130, .12, .08), ("t", (94, 80, 255), 150, .86, .1), ("z", (255, 87, 127), 160, .14, .92), ("p", (0, 160, 160), 150, .85, .9), ("r", (255, 140, 0), 120, .92, .5), ("c", (0, 200, 200), 90, .07, .5)]
    capas = [(forma(k, col, sz), px, py) for k, col, sz, px, py in fs]; bg0 = plano((W, H), (255, 245, 225))
    def bg(t):
        b = bg0.copy()
        for i, (L, px, py) in enumerate(capas): pegar(b, L, W * px + 22 * math.sin(t * .9 + i), H * py + 22 * math.cos(t * .8 + i * 1.3), 1, 1, rot=t * (25 if i % 2 else -20))
        return b
    def panel(w, h, i):
        pad = 60; L = Image.new("RGBA", (w + 2 * pad + 52, h + 2 * pad + 52), (0, 0, 0, 0)); d = ImageDraw.Draw(L); d.rectangle((pad + 52, pad + 52, pad + 52 + w, pad + 52 + h), fill=(255, 87, 127)); d.rectangle((pad + 26, pad + 26, pad + 26 + w, pad + 26 + h), fill=(0, 200, 200)); d.rectangle((pad, pad, pad + w, pad + h), fill=(255, 255, 255), outline=(0, 0, 0), width=10); return L, pad
    return base_tema(W, H, bg=bg, panel=panel, ft="negra", fh="negra", fb="sans", tit=(0, 0, 0), sub=(60, 40, 110), ph=(0, 0, 0), pb=(60, 40, 110), ac=(255, 214, 0), bn=(0, 0, 0), sombra_t=(6, 6, (255, 214, 0)), mayus=True)
def T_material(W, H):
    bg = plano((W, H), (238, 238, 238)); barh = int(H * .085); fab = Image.new("RGBA", (190, 190), (0, 0, 0, 0)); fd = ImageDraw.Draw(fab); fd.ellipse((15, 25, 175, 185), fill=(0, 0, 0, 90)); fab = fab.filter(ImageFilter.GaussianBlur(6)); fd = ImageDraw.Draw(fab)
    fd.ellipse((15, 15, 175, 175), fill=(255, 64, 129)); fd.rectangle((88, 55, 102, 135), fill=(255, 255, 255)); fd.rectangle((55, 88, 135, 102), fill=(255, 255, 255))
    def over(b, t, i):
        d = ImageDraw.Draw(b, "RGBA"); d.rectangle((0, 0, W, barh), fill=(98, 0, 238)); d.text((40, barh / 2 - 22), "Infografía", font=F("sansr", 40), fill=(255, 255, 255))
        for j in range(3): d.ellipse((W - 50 - j * 22 - 5, barh / 2 - 5, W - 50 - j * 22 + 5, barh / 2 + 5), fill=(255, 255, 255, 230))
        pegar(b, fab, W - 130, H - 130, 1 + .05 * math.sin(t * 3))
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=lambda w, h, i: panel_s(w, h, 14, (255, 255, 255), (28, 0, 20, (0, 0, 0), .4)), over=over, cy=.52 * H, tit=(33, 33, 33), sub=(90, 90, 90), ph=(33, 33, 33), pb=(90, 90, 90), ac=(98, 0, 238), fb="sansr")
def T_apple(W, H):
    cols = [(255, 94, 98), (255, 153, 102), (120, 80, 255), (30, 190, 220), (255, 90, 200)]
    def bg(t): return Image.blend(blobs(W, H, cols, t, .3, .9), Image.new("RGB", (W, H), (20, 20, 40)), .35)
    return base_tema(W, H, bg=bg, panel=lambda w, h, i: panel_s(w, h, 72, (255, 255, 255, 70), (34, 0, 28, (0, 0, 0), .4), borde=(3, (255, 255, 255, 130))), tit=(255, 255, 255), sub=(255, 255, 255), ph=(255, 255, 255), pb=(240, 240, 250), ac=(255, 255, 255), bn=(40, 40, 80), fh="sans", fb="sansl")
def T_fluent(W, H):
    cols = [(243, 243, 243), (222, 236, 250), (236, 232, 250), (250, 240, 232)]
    return base_tema(W, H, bg=lambda t: blobs(W, H, cols, t, .3, .9), panel=lambda w, h, i: ventana(w, h, 66, (248, 248, 250), (255, 255, 255), "Paso %d" % (i + 1), (30, 30, 30), r=14, sh=(26, 0, 20, (0, 0, 0), .35), pad=70), ctop=66, tit=(30, 30, 30), sub=(80, 80, 80), ph=(30, 30, 30), pb=(80, 80, 80), ac=(0, 120, 212), fb="sansr")
def T_responsivo(W, H):
    fondo = vgrad(W, H, (238, 243, 255), (222, 232, 252)); labs = ["Móvil", "Tablet", "Escritorio"]; lt = [lay_txt(x, "sans", W * .032, (110, 120, 160), W) for x in labs]; la = [lay_txt(x, "sans", W * .032, (255, 255, 255), W) for x in labs]
    def panel(w, h, i):
        pad = 60; bz = 26 if i % 3 == 0 else 20; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); L.alpha_composite(sombra(w, h, 40, 30, 0, 26, (30, 41, 90), .35, pad)); d = ImageDraw.Draw(L)
        d.rounded_rectangle((pad, pad, pad + w, pad + h), 40 if i % 3 == 0 else 24, fill=(28, 28, 34)); d.rounded_rectangle((pad + bz, pad + bz, pad + w - bz, pad + h - bz), 20 if i % 3 == 0 else 8, fill=(255, 255, 255)); return L, pad
    def over(b, t, i):
        d = ImageDraw.Draw(b)
        for j in range(3):
            x = W / 2 + (j - 1) * 270
            if j == max(0, i) % 3: d.rounded_rectangle((x - 120, H * .92 - 34, x + 120, H * .92 + 34), 34, fill=(60, 90, 230))
            pegar(b, la[j] if j == max(0, i) % 3 else lt[j], x, H * .92)
    return base_tema(W, H, bg=lambda t: fondo.copy(), panel=panel, over=over, pw=lambda i: (.64, .82, .9)[i % 3] * W, cy=.47 * H, mx=.12, my=.1, tit=(30, 41, 90), sub=(80, 90, 150), ph=(30, 41, 90), pb=(80, 90, 130), ac=(60, 90, 230))
def T_accesible(W, H):
    bg = plano((W, H), (0, 0, 0))
    def panel(w, h, i):
        pad = 50; L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(L); d.rounded_rectangle((pad, pad, pad + w, pad + h), 24, fill=(0, 0, 0), outline=(255, 255, 255), width=12); dash_rect(d, (pad - 24, pad - 24, pad + w + 24, pad + h + 24), (255, 221, 0), 8, 30, 18); return L, pad
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=panel, esc=1.12, ft="sans", fh="sans", fb="sans", tit=(255, 221, 0), sub=(255, 255, 255), ph=(255, 221, 0), pb=(255, 255, 255), ac=(255, 221, 0), bn=(0, 0, 0))
def T_atomico(W, H):
    base = plano((W, H), (247, 248, 252)); d = ImageDraw.Draw(base)
    for x in range(0, W, 60):
        for y in range(0, H, 60): d.ellipse((x, y, x + 4, y + 4), fill=(215, 220, 238))
    acc = (88, 80, 236); labs = ["ÁTOMO", "MOLÉCULA", "ORGANISMO"]; sw = [(88, 80, 236), (255, 87, 127), (255, 190, 60), (30, 200, 160), (30, 35, 80)]
    lays = [lay_txt(x, "mono", W * .028, acc, W) for x in labs]
    def panel(w, h, i):
        pad = 70; L, p = panel_s(w, h, 26, (255, 255, 255), (18, 0, 12, (40, 40, 100), .25), pad=pad); dd = ImageDraw.Draw(L); dash_rect(dd, (pad - 14, pad - 14, pad + w + 14, pad + h + 14), acc, 4); return L, pad
    def over(b, t, i):
        dd = ImageDraw.Draw(b)
        for j, col in enumerate(sw): k = e_back(prog(t % 100, .2 + j * .1, .5)); r = 24 * k; x = W * .1 + j * 70; dd.ellipse((x - r, H * .055 - r, x + r, H * .055 + r), fill=col)
        pegar(b, lays[max(0, i) % 3], W / 2, H * .15 if i >= 0 else H * .1, 1, 1)
    return base_tema(W, H, bg=lambda t: base.copy(), panel=panel, over=over, tit=(30, 35, 80), sub=(80, 88, 130), ph=(30, 35, 80), pb=(80, 88, 130), ac=acc, cy=.52 * H)
def T_oscuro(W, H, dark):
    bgc = (16, 18, 26) if dark else (246, 247, 251); tc = (240, 242, 250) if dark else (25, 28, 45); sc = (150, 158, 185) if dark else (100, 108, 135); bg = plano((W, H), bgc)
    def panel(w, h, i):
        pad = 80
        if dark:
            L = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); gl = Image.new("RGBA", L.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle((pad, pad, pad + w, pad + h), 30, fill=(110, 130, 255, 70)); L.alpha_composite(gl.filter(ImageFilter.GaussianBlur(26)))
            L.alpha_composite(redond(plano((w, h), (28, 31, 44)), 30), (pad, pad)); ImageDraw.Draw(L).rounded_rectangle((pad, pad, pad + w, pad + h), 30, outline=(120, 135, 255, 180), width=3); return L, pad
        return panel_s(w, h, 30, (255, 255, 255), (28, 0, 22, (60, 70, 120), .28))
    def over(b, t, i):
        d = ImageDraw.Draw(b); x0 = W - 210; d.rounded_rectangle((x0, 55, x0 + 120, 105), 25, fill=(60, 66, 100) if dark else (205, 210, 230)); kx = x0 + 25 + 70 * (1 if dark else 0); d.ellipse((kx - 19, 61, kx + 19, 99), fill=(255, 255, 255))
    return base_tema(W, H, bg=lambda t: bg.copy(), panel=panel, over=over, tit=tc, sub=sc, ph=tc, pb=sc, ac=(110, 130, 255), bn=(255, 255, 255))

TEMAS = {"minimalista": T_minimalista, "flat": T_flat, "skeuo": T_skeuo, "neumorfismo": T_neumorfismo, "glass": T_glass, "clay": T_clay, "neobrutalismo": T_neobrutalismo, "bento": T_bento, "neon": T_neon, "aurora": T_aurora,
         "retro": T_retro, "isometrico": T_isometrico, "ilustrado": T_ilustrado, "editorial": T_editorial, "memphis": T_memphis, "material": T_material, "apple": T_apple, "fluent": T_fluent, "responsivo": T_responsivo,
         "accesible": T_accesible, "atomico": T_atomico, "oscuro": None}
ESTILOS = list(TEMAS.keys())

# ---------------------------------------------------------------- 4) VOZ (texto a voz con edge-tts, una pista por escena)
def guiones(D):
    G = []                                                   # una lista de frases por escena: intro, puntos, cierre
    pt = lambda x: x.strip().rstrip(".:;,") + "."
    if D["titulo"]: G.append([(pt(D["titulo"]) + " " + (pt(D["subtitulo"]) if D["subtitulo"] else "")).strip()])
    for p in D["puntos"]:
        if p["tipo"] == "contraste": G.append(["%s: %s" % (p["etq_a"], pt(p["a"])), "%s: %s" % (p["etq_b"], pt(p["b"]))])
        elif p["tipo"] == "dato": G.append([" ".join(pt(x) for x in (p["encabezado"], p["dato"], p["texto"]) if x)])
        elif p["tipo"] == "lista": G.append([" ".join(pt(x) for x in [p["encabezado"]] + p["items"] if x)])
        else: G.append([" ".join(pt(x) for x in (p["encabezado"], p["texto"]) if x)])
    if D["cierre"]: G.append([D["cierre"]])
    return G

def sintetizar(G, voz, carpeta):
    import asyncio, re as _re, wave, edge_tts
    os.makedirs(carpeta, exist_ok=True); auds = []; fallos = 0; total = 0
    def limpiar(tx):                                         # el servicio de voz rechaza simbolos, emojis y comillas raras
        tx = _re.sub(r"[\"“”«»‘’`*_#<>|\[\]{}~^=\\/]", " ", tx); tx = _re.sub(r"[^\w\s.,;:¿?¡!%$€&'()+\-]", " ", tx); return _re.sub(r"\s+", " ", tx).strip()
    for i, segs in enumerate(G):
        fila = []
        for j, tx in enumerate(segs):
            mp3 = os.path.join(carpeta, "s%d_%d.mp3" % (i, j)); wav = mp3[:-4] + ".wav"; limpio = limpiar(tx); total += 1; ok = False
            if _re.search(r"\w", limpio):
                for intento in range(3):
                    try:
                        if os.path.exists(mp3): os.remove(mp3)
                        asyncio.run(edge_tts.Communicate(limpio, voz).save(mp3))
                        if os.path.exists(mp3) and os.path.getsize(mp3) > 500: ok = True; break
                    except Exception as ex: err = str(ex)
                    time.sleep(1.5)
            if ok:
                subprocess.run([FF, "-nostdin", "-y", "-v", "error", "-i", mp3, "-ar", "24000", "-ac", "1", wav], check=True)
                with wave.open(wav) as w: fila.append((wav, w.getnframes() / 24000.0))
            else:                                            # una frase sin voz no cancela el video: queda en silencio con duracion estimada
                fallos += 1; print("Aviso: no se pudo narrar «%s»; esa frase queda sin voz." % tx[:60], flush=True); fila.append((None, max(1.5, .35 * len(limpio.split()))))
        auds.append(fila)
    if fallos == total: sys.exit("No se pudo generar la voz con %s (hace falta internet). Prueba otra voz o elige «Sin voz»." % voz)
    return auds

def mezclar(segs, total, ruta):
    import wave
    SR = 24000; arr = np.zeros(int((total + 1) * SR), dtype=np.float32)
    for ini, wav in segs:
        if wav is None: continue
        with wave.open(wav) as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        a = int(ini * SR); arr[a:a + len(x)] += x[:max(0, len(arr) - a)]
    arr = np.clip(arr, -32768, 32767).astype(np.int16)
    with wave.open(ruta, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(arr.tobytes())

# ---------------------------------------------------------------- 5) ESCENAS: intro -> un panel por punto (segun su tipo) -> cierre
def dato_contador(s, k):                                     # "87%" -> cuenta de 0 a 87 mientras aparece
    import re as _re
    m = _re.match(r"^(\D*?)(\d[\d.,]*)(.*)$", s)
    if not m: return s
    pre, num, suf = m.groups(); dec = len(num.split(".")[-1]) if "." in num and len(num.split(".")[-1]) <= 2 else (len(num.split(",")[-1]) if "," in num and len(num.split(",")[-1]) <= 2 else 0)
    try: val = float(num.replace(",", ".")) if dec else float(num.replace(",", "").replace(".", ""))
    except Exception: return s
    cur = val * k; return pre + ("%.*f" % (dec, cur) if dec else "{:,}".format(int(round(cur))).replace(",", num[1:2] if len(num) > 4 and num[1:2] in ",." else "")) + suf

def trans(kind, tr, ret, W, H, ultima):
    pi = prog(tr, 0, .55); po = 0 if ultima else 1 - cl(ret / .3); al = min(cl(tr / .35), 1 if ultima else cl(ret / .3)); sc, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
    if kind == "fade": sc = lerp(.92, 1, e_out(pi))
    elif kind == "deslizar": dx = (1 - e_out(pi)) * W * .8 - po * W * .8
    elif kind == "subir": dy = (1 - e_out(pi)) * H * .35 - po * H * .15; sc = lerp(.9, 1, e_out(pi))
    elif kind == "giro": rot = (1 - e_out(pi)) * -14 + po * 10; sc = lerp(.7, 1, e_out(pi))
    else: sc = lerp(.45, 1, e_back(pi)) * lerp(1, 1.18, po)                                  # zoom
    return sc, dx, dy, rot, al

class Video:
    def __init__(s, th, D, W, H, k, auds=None):
        s.th, s.W, s.H, s.sc = th, W, H, []; e = th["esc"]; t = 0.0; may = th["mayus"]; ix = 0
        def dur_seg(n, j=0, minimo=1.2):                      # duracion de lo que se dice: la real de la voz, o una estimada
            return auds[ix][j][1] if auds else max(minimo, .3 * n) * k
        if D["titulo"]:
            tm = maq(D["titulo"], th["ft"], W * .088 * e, th["tit"], W * .84, may); sm = maq(D["subtitulo"], th["fb"], W * .04 * e, th["sub"], W * .8) if D["subtitulo"] else None
            a = dur_seg(tm["n"] + (sm["n"] if sm else 0), 0, 1.6); dur = max(2.2 * k, .35 + a + .7); s.sc.append(dict(k="intro", a=t, b=t + dur, tm=tm, sm=sm, offs=[.35], durs=[a])); t += dur; ix += 1
        for i, p in enumerate(D["puntos"]):
            pw = int(th["pw"](i)); mx = int(pw * th["mx"]); iw = pw - 2 * mx; bd = W * .105 * e if th["bshape"] != "none" else 0; gap = W * .028; tp = p["tipo"]; sc = dict(k="punto", i=i, tp=tp, trans=p["transicion"]); hm = None
            if p["encabezado"] and tp in ("dato", "lista"): hm = maq(p["encabezado"], th["fh"], W * .05 * e, th["ph"], iw, may)
            if tp == "contraste":
                lb = W * .05 * e; la = maq(p["etq_a"], th["fh"], lb, (235, 70, 70) if p["tachar"] else th["ac"], iw, True); lbb = maq(p["etq_b"], th["fh"], lb, (40, 190, 110), iw, True)
                am = maq(p["a"], th["fh"], W * .06 * e, th["pb"], iw, may); bm = maq(p["b"], th["fh"], W * .066 * e, th["ph"], iw, may)
                ch = bd + gap + la["h"] + am["h"] + gap + lbb["h"] + bm["h"]; a1 = dur_seg(am["n"] + 2, 0); a2 = dur_seg(bm["n"] + 2, 1); o2 = .35 + a1 + .7; dur = o2 + a2 + .9
                sc.update(la=la, lb=lbb, am=am, bm=bm, offs=[.35, o2], durs=[a1, a2], tstrike=.35 + a1 + .05)
            elif tp == "dato":
                bm = maq(p["texto"], th["fb"], W * .046 * e, th["pb"], iw) if p["texto"] else None; fz = W * .2 * e; d0 = ImageDraw.Draw(Image.new("L", (1, 1))); ff = F("negra", fz)
                while d0.textlength(p["dato"], font=ff) > iw and fz > 30: fz *= .92; ff = F("negra", fz)
                ch = (hm["h"] + gap if hm else 0) + fz * 1.25 + (gap + bm["h"] if bm else 0); a = dur_seg((hm["n"] if hm else 0) + 3 + (bm["n"] if bm else 0), 0, 2.0); dur = max(3.0 * k, .35 + a + .9)
                sc.update(hm=hm, bm=bm, fz=fz, ff=ff, offs=[.35], durs=[a])
            elif tp == "lista":
                its = [maq(x, th["fb"], W * .05 * e, th["pb"], iw - W * .07 * e, False, 1.2, "left") for x in p["items"]]; hh = bd + gap + (hm["h"] + gap if hm else 0) + sum(m["h"] + W * .012 for m in its); ch = hh
                a = dur_seg(sum(m["n"] for m in its) + (hm["n"] if hm else 0), 0, 2.4); dur = max(3.2 * k, .35 + a + .9); sc.update(hm=hm, its=its, offs=[.35], durs=[a])
            else:
                hm = maq(p["encabezado"] or p["texto"], th["fh"], W * .068 * e, th["ph"], iw, may) if (p["encabezado"] or p["texto"]) else None
                bm = maq(p["texto"], th["fb"], W * .046 * e, th["pb"], iw) if (p["texto"] and p["encabezado"]) else None
                ch = bd + gap + (hm["h"] if hm else 0) + (W * .02 + bm["h"] if bm else 0); a = dur_seg((hm["n"] if hm else 0) + (bm["n"] if bm else 0), 0, 1.8); dur = max(2.6 * k, .35 + a + .8); sc.update(hm=hm, bm=bm, offs=[.35], durs=[a])
            if tp == "dato": bd = 0
            my = int(max(W * .04, ch * th["my"] * 1.4)); ph = int(ch + 2 * my + th["ctop"]); ph = max(int(H * .3), min(ph, int(H * .86))); my = int((ph - th["ctop"] - ch) / 2)
            pan = th["panel"](pw, ph, i) if th["panel"] else None; sc.update(a=t, b=t + dur, pw=pw, ph=ph, mx=mx, my=my, bd=bd, gap=gap, ch=ch, iw=iw, pan=pan); s.sc.append(sc); t += dur; ix += 1
        if D["cierre"]:
            cm = maq(D["cierre"], th["ft"], W * .075 * e, th["tit"], W * .82, may); a = dur_seg(cm["n"], 0, 1.6); dur = max(2.2 * k, .35 + a + .8); s.sc.append(dict(k="cierre", a=t, b=t + dur, tm=cm, offs=[.35], durs=[a])); t += dur; ix += 1
        if not s.sc: sys.exit("No hay texto que animar.")
        s.total = t
    def segmentos(s, auds):                                  # (segundo absoluto, archivo wav) de cada frase narrada
        return [(sc["a"] + o, auds[i][j][0]) for i, sc in enumerate(s.sc) for j, o in enumerate(sc["offs"])]
    def _bloque(s, b, M, cx, cy, tr, ini, paso, alpha, sombra=None):
        w, h = int(M["w"]) + 40, int(M["h"]) + 30; C = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dib_pal(C, M, tr, ini, paso, 20, 8, sombra); pegar(b, C, cx, cy, 1, alpha)
    def _insignia(s, C, act, tr):
        th = s.th; kb = e_back(prog(tr, .15, .5)); bd = act["bd"]; cx = C.width / 2; cy = bd / 2; r = bd / 2 * max(0.01, kb); d = ImageDraw.Draw(C, "RGBA"); fn = F("negra" if th["bshape"] != "num" else "serif", bd * (.5 if th["bshape"] != "num" else 1.0))
        if th["bshape"] == "circle": d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=th["ac"])
        elif th["bshape"] == "square": d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), 8, fill=th["ac"], outline=(0, 0, 0), width=6)
        col = th["bn"] if th["bshape"] != "num" else th["ac"]
        if kb > .3: d.text((cx, cy), str(act["i"] + 1), font=fn, fill=tuple(col[:3]) + (int(255 * cl(kb)),), anchor="mm")
    def frame(s, t):
        th = s.th; W, H = s.W, s.H; b = th["bg"](t); act = None
        for sc in s.sc:
            if sc["a"] <= t < sc["b"]: act = sc; break
        if act is None: act = s.sc[-1]
        ultima = act is s.sc[-1]; tr = t - act["a"]; ret = act["b"] - t; al = min(cl(tr / .4), cl(ret / .3)) if not ultima else cl(tr / .4); idx = -1
        pas = lambda M, a: min(.3, max(.06, a * .85 / M["n"]))
        if act["k"] in ("intro", "cierre"):
            tm, sm = act["tm"], act.get("sm"); n = tm["n"] + (sm["n"] if sm else 0); paso = min(.3, max(.06, act["durs"][0] * .85 / n)); o = act["offs"][0]; tot = tm["h"] + (sm["h"] + W * .03 if sm else 0); y0 = H * .5 - tot / 2
            s._bloque(b, tm, W / 2, y0 + tm["h"] / 2, tr, o, paso, al, th["sombra_t"])
            ImageDraw.Draw(b).rectangle((W / 2 - W * .1 * e_out(prog(tr, .5, .6)), y0 - W * .05, W / 2 + W * .1 * e_out(prog(tr, .5, .6)), y0 - W * .05 + 10), fill=th["ac"])
            if sm: s._bloque(b, sm, W / 2, y0 + tm["h"] + W * .03 + sm["h"] / 2, tr, o + tm["n"] * paso + .2, paso, al)
        else:
            idx = act["i"]; tp = act["tp"]; C = Image.new("RGBA", (act["iw"] + 40, int(act["ch"] + 40)), (0, 0, 0, 0)); y = 0.0; o = act["offs"][0]; a0 = act["durs"][0]
            if act["bd"]: s._insignia(C, act, tr); y = act["bd"] + act["gap"]
            if tp == "contraste":                            # "No digas X / Mejor di Y", "Mito / Realidad"...: se dice y se tacha lo primero, luego aparece lo segundo
                o2 = act["offs"][1]; a2 = act["durs"][1]; la, lb, am, bm = act["la"], act["lb"], act["am"], act["bm"]
                dib_pal(C, la, tr, o, .1, 20, y); y += la["h"]; dib_pal(C, am, tr, o + .2, pas(am, a0), 20, y)
                p = e_io(prog(tr, act["tstrike"], .45)) if th and act.get("tachar", True) and s._tachar(idx) else 0; d = ImageDraw.Draw(C, "RGBA")
                for (x0, x1, ly) in am["lin"]:
                    if p > 0: d.line((20 + x0 - 8, y + ly + am["size"] * .6, 20 + x0 - 8 + (x1 - x0 + 16) * p, y + ly + am["size"] * .6), fill=(235, 70, 70, 255), width=max(6, int(am["size"] * .12)))
                y += am["h"] + W * .028; dib_pal(C, lb, tr, o2, .1, 20, y); y += lb["h"]; dib_pal(C, bm, tr, o2 + .2, pas(bm, a2), 20, y, th["sombra_t"])
            elif tp == "dato":
                hm, bm = act["hm"], act["bm"]
                if hm: dib_pal(C, hm, tr, o, pas(hm, a0), 20, y, th["sombra_t"]); y += hm["h"] + act["gap"]
                kd = e_out(prog(tr, o + .2, 1.0)); ka = cl((tr - o - .2) / .3); d = ImageDraw.Draw(C, "RGBA"); txt = dato_contador(s._dato(idx), kd)
                if ka > 0: d.text((C.width / 2, y + act["fz"] * .62 + (1 - kd) * 14), txt, font=act["ff"], fill=tuple(th["ac"][:3]) + (int(255 * ka),), anchor="mm")
                y += act["fz"] * 1.25 + act["gap"]
                if bm: dib_pal(C, bm, tr, o + 1.0, pas(bm, a0), 20, y)
            elif tp == "lista":
                hm, its = act["hm"], act["its"]
                if hm: dib_pal(C, hm, tr, o, pas(hm, a0), 20, y, th["sombra_t"]); y += hm["h"] + act["gap"]
                d = ImageDraw.Draw(C, "RGBA"); bw = W * .07 * th["esc"]; ini = o + (hm["n"] * .12 if hm else 0) + .2; n = len(its)
                for j, m in enumerate(its):
                    ij = ini + j * max(.35, (a0 * .8) / n); kk = e_back(prog(tr, ij, .4)); r = W * .016 * max(.01, kk)
                    if kk > 0: d.ellipse((20 + bw * .4 - r, y + m["size"] * .6 - r, 20 + bw * .4 + r, y + m["size"] * .6 + r), fill=th["ac"])
                    dib_pal(C, m, tr, ij + .1, .08, 20 + bw, y); y += m["h"] + W * .012
            else:
                hm, bm = act["hm"], act["bm"]; paso = min(.3, max(.06, a0 * .85 / max(1, (hm["n"] if hm else 0) + (bm["n"] if bm else 0)))); ini = o
                if hm: dib_pal(C, hm, tr, ini, paso, 20, y, th["sombra_t"]); y += hm["h"] + W * .02; ini += hm["n"] * paso + .15
                if bm: dib_pal(C, bm, tr, ini, paso, 20, y)
            sc_, dx, dy, rot, al2 = trans(act["trans"], tr, ret, W, H, ultima); sc_ *= 1 + .012 * tr / max(.1, act["b"] - act["a"])
            if act["pan"]:
                L, pad = act["pan"]; L = L.copy(); L.alpha_composite(C, (int(pad + act["mx"] - 20), int(pad + act["my"] + th["ctop"]))); pegar(b, L, W / 2 + dx, th["cy"] + dy, sc_, al2, th["rot"](idx) + rot)
            else: pegar(b, C, W / 2 + dx, th["cy"] + dy, sc_, al2, rot)
        if th["over"]: th["over"](b, t, idx)
        return b
    def _tachar(s, i): return s.D_tachar[i] if hasattr(s, "D_tachar") else True
    def _dato(s, i): return s.D_dato[i]

def construir(clave, D, W, H, dur_fija, auds=None):
    def nuevo(th, k):
        v = Video(th, D, W, H, k, auds); v.D_tachar = [p["tachar"] for p in D["puntos"]]; v.D_dato = [p["dato"] for p in D["puntos"]]; return v
    th = T_oscuro(W, H, False) if clave == "oscuro" else TEMAS[clave](W, H)
    v0 = nuevo(th, 1.0); k = 1.0
    if not auds and dur_fija: k = min(1.6, dur_fija / v0.total)
    if k != 1.0: v0 = nuevo(th, k)
    if clave != "oscuro": return v0.frame, v0.total, v0
    v1 = nuevo(T_oscuro(W, H, True), k); T0 = v0.total * .38; tx, ty = W - 150, 80
    def f(t):
        a = v0.frame(t)
        if t < T0: return a
        kk = e_io(prog(t, T0, 1.0)); bb = v1.frame(t)
        if kk >= 1: return bb
        m = Image.new("L", (W, H), 0); r = kk * math.hypot(W, H) * 1.05; ImageDraw.Draw(m).ellipse((tx - r, ty - r, tx + r, ty + r), fill=255); return Image.composite(bb, a, m)
    return f, v0.total, v0

# ---------------------------------------------------------------- render
def render(clave, D, W, H, dur_fija, ruta, auds=None, carpeta=None):
    f, total, v = construir(clave, D, W, H, dur_fija, auds); dur = total + .8; n = int(dur * FPS)
    if auds: mez = os.path.join(carpeta, "mezcla_%s.wav" % clave); mezclar(v.segmentos(auds), total, mez); audio = ["-i", mez, "-af", "apad"]
    else: audio = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd = [FF, "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-"] + audio + ["-map", "0:v", "-map", "1:a", "-t", "%.3f" % dur,
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", ruta]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            fr = f(min(i / FPS, total - 0.001))
            if fr.size != (W, H): fr = fr.resize((W, H))
            p.stdin.write(fr.convert("RGB").tobytes())
        p.stdin.close()
    except BrokenPipeError: pass
    return p.wait() == 0

def main():
    ruta = (P.get("imagen") or "").strip(); texto = None
    if ATX:
        texto = (P.get("texto") or "").strip(); img = None
        if len(texto) < 15: sys.exit("Escribe el texto que quieres animar (al menos una frase).")
        texto = texto[:6000]
    elif P.get("imagenB64"):                                   # la app guarda la imagen dentro de los ajustes
        import base64, io
        img = Image.open(io.BytesIO(base64.b64decode(P["imagenB64"].split(",", 1)[-1])))
    elif ruta and os.path.exists(ruta): img = Image.open(ruta)
    else: sys.exit("Falta la imagen (o la ruta ya no existe): " + ruta)
    estilos = [e for e in (P.get("estilos") or []) if e in TEMAS]
    if not estilos: sys.exit("Elige al menos un estilo.")
    W, H = FORMATOS.get(P.get("formato"), FORMATOS["reels"])
    try: dur_fija = float(P.get("duracion") or 0)
    except Exception: dur_fija = 0
    dur_fija = cl(dur_fija, 6, 40) if dur_fija else 0
    if img is not None: img = ImageOps.exif_transpose(img).convert("RGB")
    D = interpretar(img, P.get("idioma") or "", texto)
    if (P.get("titulo") or "").strip(): D["titulo"] = P["titulo"].strip()
    if (P.get("subtitulo") or "").strip(): D["subtitulo"] = P["subtitulo"].strip()
    print("Título: %s | %d puntos | cierre: %s" % (D["titulo"], len(D["puntos"]), "sí" if D["cierre"] else "no"), flush=True)
    print("Interpretación de Claude Code: " + ", ".join("%d:%s/%s" % (i + 1, p["tipo"], p["transicion"]) for i, p in enumerate(D["puntos"])), flush=True)
    auds = None; carpeta = os.path.join(AG, "infografias", "_operacion", "voz"); voz = (P.get("voz") or "").strip()
    if voz != "none":
        voz = voz or VOCES_AUTO.get(D["idioma"], VOCES_AUTO["es"]); print("Generando la narración con la voz %s…" % voz, flush=True); auds = sintetizar(guiones(D), voz, carpeta)
    sello = time.strftime("%Y%m%d-%H%M%S"); ok = 0
    for i, e in enumerate(estilos, 1):
        out = os.path.join(SALIDA, ("animtexto_%s_%s.mp4" if ATX else "infografia_%s_%s.mp4") % (e, sello)); print("[%d/%d] Estilo %s ..." % (i, len(estilos), e), flush=True)
        try:
            if render(e, D, W, H, dur_fija, out, auds, carpeta): ok += 1; print("OK " + out, flush=True)
            else: print("ERROR: ffmpeg no pudo crear " + out, flush=True)
        except Exception as ex:
            import traceback; traceback.print_exc(); print("ERROR en el estilo %s: %s" % (e, ex), flush=True)
    print("Listo: %d de %d videos en %s" % (ok, len(estilos), SALIDA)); sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
