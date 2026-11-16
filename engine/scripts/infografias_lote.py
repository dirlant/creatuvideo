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
P = PRE.get("infografias", {}) or {}
SALIDA = DIRS.get("infografiasResultado") or os.path.join(AG, "infografias", "resultado"); os.makedirs(SALIDA, exist_ok=True)
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

class Ctx:
    def __init__(s, img, W, H, tit, sub, dur):
        s.W, s.H, s.dur, s.tit, s.sub, s.img = W, H, dur, tit, sub, img
        s.cx = W / 2; s.cy = H * (0.52 if tit else 0.5)
        bh = H * (0.70 if not tit and not sub else 0.50 if tit and sub else 0.56)
        s.im = contain(img, int(W * .86), int(bh)); s.iw, s.ih = s.im.size
    def T(s, k, mul, col, **kw):
        return lay_txt(s.tit, k, s.W * mul, col, s.W * .84, **kw) if s.tit else None
    def S(s, k, mul, col, **kw):
        return lay_txt(s.sub, k, s.W * mul, col, s.W * .80, **kw) if s.sub else None
    def textos(s, b, t, tl, sl, esc=1.0, dx=0, a0=.5):
        if tl is not None:
            y = max(tl.height / 2 + .04 * s.H, s.cy - s.ih * esc / 2 - .03 * s.H - tl.height / 2); k = e_out(prog(t, a0, .7)); pegar(b, tl, s.cx + dx, y + (1 - k) * 40, 1, k)
        if sl is not None:
            y = min(s.H - sl.height / 2 - .04 * s.H, s.cy + s.ih * esc / 2 + .03 * s.H + sl.height / 2); k = e_out(prog(t, a0 + .5, .7)); pegar(b, sl, s.cx + dx, y + (1 - k) * 40, 1, k)
    def kb(s, t): return 1 + .025 * t / s.dur

# ---------------------------------------------------------------- ESTILOS (cada uno devuelve frame(t) -> imagen RGB)
def s_minimalista(c):
    bg = plano((c.W, c.H), (250, 250, 248)); iw, ih = int(c.iw * .8), int(c.ih * .8); im = redond(c.im.resize((iw, ih), Image.LANCZOS), 18)
    sh = sombra(iw, ih, 18, 28, 0, 18, (0, 0, 0), .13, 60); card = apilar(sh.size, (sh, (0, 0)), (im, (60, 60)))
    tl = c.T("sansl", .06, (30, 30, 30)); sl = c.S("sansl", .03, (130, 130, 130))
    def f(t):
        b = bg.copy(); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 5), s * c.kb(t), a)
        if tl is not None:
            w = int(c.W * .12 * e_out(prog(t, .9, .7))); y = c.cy - ih / 2 - .03 * c.H - tl.height - 22; d = ImageDraw.Draw(b); d.rectangle((c.cx - w / 2, y, c.cx + w / 2, y + 6), fill=(255, 87, 51))
        c.textos(b, t, tl, sl, .8); return b
    return f

def s_flat(c):
    bg = plano((c.W, c.H), (255, 201, 60)); im = redond(c.im, 30); card = apilar((c.iw + 40, c.ih + 40), (Image.new("RGBA", (c.iw + 40, c.ih + 40), (255, 255, 255, 0)), (0, 0)), (redond(Image.new("RGB", (c.iw + 40, c.ih + 40), (255, 255, 255)), 40), (0, 0)), (im, (20, 20)))
    tl = c.T("negra", .062, (25, 45, 110)); sl = c.S("sans", .032, (25, 45, 110))
    formas = [((0.15, 0.12), 150, (255, 99, 71), 0), ((0.88, 0.2), 110, (46, 134, 222), 1), ((0.1, 0.85), 130, (46, 204, 113), 1), ((0.9, 0.82), 170, (155, 89, 182), 0)]
    def f(t):
        b = bg.copy(); d = ImageDraw.Draw(b)
        for i, ((px, py), r, col, tri) in enumerate(formas):
            x = c.W * px + 30 * math.sin(t * .8 + i); y = c.H * py + 30 * math.cos(t * .7 + i)
            if tri: d.polygon([(x, y - r), (x - r, y + r * .8), (x + r, y + r * .8)], fill=col)
            else: d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 6), s * c.kb(t), a); c.textos(b, t, tl, sl); return b
    return f

def s_skeuo(c):
    W, H = c.W, c.H; ruido = np.random.RandomState(3).randint(-10, 10, (H // 3, W // 3, 1)); base = np.array(vgrad(W // 3, H // 3, (120, 78, 46), (70, 42, 24)), dtype="int16") + ruido
    bg = Image.fromarray(np.clip(base, 0, 255).astype("uint8")).resize((W, H), Image.BILINEAR)
    m = 26; w, h = c.iw + 2 * m, c.ih + 2 * m; marco = vgrad(w, h, (235, 235, 238), (110, 112, 120)); marco = redond(marco, 34)
    inner = redond(c.im, 14); luz = Image.new("RGBA", (c.iw, c.ih), (255, 255, 255, 0)); gl = ImageDraw.Draw(luz); gl.polygon([(0, 0), (c.iw, 0), (0, c.ih * .55)], fill=(255, 255, 255, 60))
    sh = sombra(w, h, 34, 30, 0, 26, (0, 0, 0), .6, 70); card = apilar(sh.size, (sh, (0, 0)), (marco, (70, 70)), (inner, (70 + m, 70 + m)), (luz, (70 + m, 70 + m)))
    tl = c.T("serif", .07, (245, 228, 190), sombra=(3, 3, (40, 22, 10))); sl = c.S("serifr", .034, (235, 215, 180), sombra=(2, 2, (40, 22, 10)))
    def f(t):
        b = bg.copy(); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 7), s * c.kb(t), a, rot=math.sin(t) * .8); c.textos(b, t, tl, sl); return b
    return f

def s_neumorfismo(c):
    col = (224, 229, 236); bg = plano((c.W, c.H), col); m = 40; w, h = c.iw + 2 * m, c.ih + 2 * m; pad = 80
    d1 = sombra(w, h, 56, 24, 22, 22, (163, 177, 198), 1, pad); d2 = sombra(w, h, 56, 24, -22, -22, (255, 255, 255), 1, pad)
    mat = redond(plano((w, h), col), 56); inner = redond(c.im, 34); card = apilar(d1.size, (d1, (0, 0)), (d2, (0, 0)), (mat, (pad, pad)), (inner, (pad + m, pad + m)))
    tl = c.T("sans", .064, (105, 118, 140)); sl = c.S("sansr", .032, (140, 150, 170))
    def f(t):
        b = bg.copy(); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 6), s * c.kb(t), a); c.textos(b, t, tl, sl); return b
    return f

def s_glass(c):
    W, H = c.W, c.H; cols = [(255, 94, 98), (255, 153, 102), (120, 80, 255), (30, 190, 220), (255, 90, 200)]; m = 34; w, h = c.iw + 2 * m, c.ih + 2 * m
    panel = Image.new("RGBA", (w, h), (255, 255, 255, 62)); ImageDraw.Draw(panel).rounded_rectangle((0, 0, w - 1, h - 1), 50, outline=(255, 255, 255, 150), width=3); panel.putalpha(ImageChops.multiply(panel.getchannel("A"), mask_rr((w, h), 50)))
    sh = sombra(w, h, 50, 30, 0, 24, (30, 10, 80), .35, 70); card = apilar(sh.size, (sh, (0, 0)), (panel, (70, 70)), (redond(c.im, 30), (70 + m, 70 + m)))
    orbe = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); od = ImageDraw.Draw(orbe); od.ellipse((0, 0, 259, 259), fill=(255, 255, 255, 90), outline=(255, 255, 255, 200), width=3)
    tl = c.T("sans", .066, (255, 255, 255), sombra=(0, 3, (60, 20, 110))); sl = c.S("sansr", .032, (255, 255, 255, 230))
    def f(t):
        b = blobs(W, H, cols, t, .5, .55); pegar(b, orbe, c.W * .85 + 20 * math.sin(t), c.H * .2 + 25 * math.cos(t), 1, 1); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 8), s * c.kb(t), a)
        pegar(b, orbe, c.W * .12 + 25 * math.cos(t * .9), c.H * .86 + 20 * math.sin(t), .7, 1); c.textos(b, t, tl, sl); return b
    return f

def s_clay(c):
    W, H = c.W, c.H; bg = vgrad(W, H, (255, 232, 240), (232, 225, 255)); m = 44; w, h = c.iw + 2 * m, c.ih + 2 * m; pad = 70
    mat = inflar(mask_rr((w, h), 110), (255, 170, 190), 18, 14); sh = sombra(w, h, 110, 30, 0, 30, (190, 90, 130), .45, pad)
    inner = inflar(mask_rr((c.iw, c.ih), 70), (255, 255, 255), 8, 8); ci = c.im.convert("RGBA"); ci.putalpha(mask_rr(ci.size, 70))
    card = apilar(sh.size, (sh, (0, 0)), (mat, (pad, pad)), (ci, (pad + m, pad + m)))
    bolas = []
    for d, col in ((150, (120, 200, 255)), (110, (255, 214, 90)), (90, (160, 230, 170))):
        bolas.append(apilar((d + 40, d + 40), (inflar((lambda mm: (ImageDraw.Draw(mm).ellipse((0, 0, d - 1, d - 1), fill=255), mm)[1])(Image.new("L", (d, d), 0)), col, 12, 10), (20, 20))))
    pos = [(.14, .1), (.88, .17), (.82, .88)]
    tl = c.T("redonda", .066, (130, 60, 100)); sl = c.S("redonda", .032, (160, 100, 140))
    def f(t):
        b = bg.copy()
        for i, (bo, (px, py)) in enumerate(zip(bolas, pos)): pegar(b, bo, c.W * px, c.H * py + 22 * math.sin(t * 1.4 + i * 2), 1, 1)
        s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 8), s * c.kb(t), a); c.textos(b, t, tl, sl); return b
    return f

def s_neobrutalismo(c):
    W, H = c.W, c.H; bg = plano((W, H), (255, 222, 89)); bd = 10; w, h = c.iw + 2 * bd, c.ih + 2 * bd; off = 26
    card = apilar((w + off, h + off), (plano((w, h), (0, 0, 0)).convert("RGBA"), (off, off)), (plano((w, h), (255, 255, 255)).convert("RGBA"), (0, 0)), (c.im.convert("RGBA"), (bd, bd)))
    ImageDraw.Draw(card).rectangle((0, 0, w - 1, h - 1), outline=(0, 0, 0), width=bd)
    tl = c.T("negra", .06, (0, 0, 0), mayus=True)
    if tl is not None:
        caja = Image.new("RGBA", (tl.width + 50 + 16, tl.height + 30 + 16), (0, 0, 0, 0)); cd = ImageDraw.Draw(caja); cd.rectangle((16, 16, caja.width - 1, caja.height - 1), fill=(0, 0, 0)); cd.rectangle((0, 0, caja.width - 17, caja.height - 17), fill=(255, 110, 170), outline=(0, 0, 0), width=8); caja.alpha_composite(tl, (25, 15))
    else: caja = None
    sl = c.S("sans", .032, (0, 0, 0))
    star = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); sd = ImageDraw.Draw(star); pts = [(130 + (125 if i % 2 == 0 else 70) * math.cos(i * math.pi / 8), 130 + (125 if i % 2 == 0 else 70) * math.sin(i * math.pi / 8)) for i in range(16)]; sd.polygon(pts, fill=(80, 200, 255), outline=(0, 0, 0)); sd.line(pts + [pts[0]], fill=(0, 0, 0), width=8)
    def f(t):
        b = bg.copy(); x = prog(t, .15, .8); dx = (1 - e_back(x)) * -W * .9
        pegar(b, star, c.W * .86, c.H * .13, 1, 1, rot=t * 40); pegar(b, card, c.cx + dx, c.cy + flot(t, 6), c.kb(t), cl(x * 4))
        if caja is not None:
            k = e_back(prog(t, .6, .6)); y = max(caja.height / 2 + .03 * c.H, c.cy - c.ih / 2 - .02 * c.H - caja.height / 2); pegar(b, caja, c.cx, y, k, cl(k * 3), rot=-3)
        if sl is not None: k = e_out(prog(t, 1.1, .6)); pegar(b, sl, c.cx, min(c.H - 80, c.cy + c.ih / 2 + .05 * c.H), 1, k)
        return b
    return f

def s_bento(c):
    W, H = c.W, c.H; bg = plano((W, H), (240, 240, 243)); g = 22; x0 = int(W * .05); aw = W - 2 * x0; y0 = int(H * .05); ah = H - 2 * y0
    h1, h2, h3 = int(ah * .17), int(ah * .50), int(ah * .13); h4 = ah - h1 - h2 - h3 - 3 * g; cw = (aw - g) // 2
    tiles = [(x0, y0, aw, h1, (255, 213, 79), "t"), (x0, y0 + h1 + g, aw, h2, (255, 255, 255), "i"), (x0, y0 + h1 + h2 + 2 * g, cw, h3, (138, 180, 248), "s"), (x0 + cw + g, y0 + h1 + h2 + 2 * g, aw - cw - g, h3, (255, 138, 128), "d1"), (x0, y0 + h1 + h2 + h3 + 3 * g, aw, h4, (129, 199, 132), "d2")]
    tt = c.tit or ""; capas = []
    for (x, y, w, h, col, k) in tiles:
        L = Image.new("RGBA", (w, h), (0, 0, 0, 0)); L.alpha_composite(redond(plano((w, h), col), 42))
        if k == "i":
            im = contain(c.img, w - 40, h - 40); L.alpha_composite(redond(im, 26), ((w - im.width) // 2, (h - im.height) // 2))
        elif k == "t" and tt: tx = lay_txt(tt, "negra", min(h * .42, c.W * .07), (40, 30, 0), w - 60); L.alpha_composite(tx, ((w - tx.width) // 2, (h - tx.height) // 2))
        elif k == "s" and c.sub: tx = lay_txt(c.sub, "sans", min(h * .2, c.W * .034), (20, 40, 90), w - 40); L.alpha_composite(tx, ((w - tx.width) // 2, (h - tx.height) // 2))
        elif k == "d1":
            dd = ImageDraw.Draw(L)
            for i in range(4): dd.rounded_rectangle((40 + i * 70, h - 30 - (30 + i * 18), 90 + i * 70, h - 30), 10, fill=(255, 255, 255, 230))
        elif k == "d2":
            dd = ImageDraw.Draw(L); dd.ellipse((w / 2 - h * .3, h / 2 - h * .3, w / 2 + h * .3, h / 2 + h * .3), outline=(255, 255, 255, 255), width=18)
            for i in range(3): dd.ellipse((60 + i * 70, 40, 100 + i * 70, 80), fill=(255, 255, 255, 220))
        capas.append((L, x + w / 2, y + h / 2))
    def f(t):
        b = bg.copy()
        for i, (L, cx, cy) in enumerate(capas):
            x = prog(t, .15 + i * .22, .7); pegar(b, L, cx, cy, lerp(.4, 1, e_back(x)) * (1 + .012 * math.sin(t * 1.5 + i)), cl(x * 3))
        return b
    return f

def s_neon(c):
    W, H = c.W, c.H; cyan = (0, 240, 255); mag = (255, 40, 200); w, h = c.iw + 40, c.ih + 40; pad = 70
    b0 = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d0 = ImageDraw.Draw(b0); d0.rounded_rectangle((pad, pad, pad + w, pad + h), 26, outline=cyan + (255,), width=8); d0.rounded_rectangle((pad + 14, pad + 14, pad + w - 14, pad + h - 14), 18, outline=mag + (255,), width=3)
    gl = brillo(b0, 22, 2.2); card = apilar(b0.size, (plano((w, h), (10, 6, 24)).convert("RGBA"), (pad, pad)), (c.im.convert("RGBA"), (pad + 20, pad + 20)), (gl, (0, 0)), (b0, (0, 0)))
    tl = c.T("mono", .062, cyan); tg = brillo(tl, 14, 2.0) if tl is not None else None; sl = c.S("mono", .03, mag); sg = brillo(sl, 10, 2.0) if sl is not None else None
    def fondo(t):
        b = vgrad(W, H, (6, 3, 18), (22, 6, 40)); d = ImageDraw.Draw(b, "RGBA"); off = (t * 60) % 90
        for i in range(-1, W // 90 + 2): d.line((i * 90, 0, i * 90, H), fill=(120, 40, 220, 55), width=2)
        for j in range(-1, H // 90 + 2): d.line((0, j * 90 + off, W, j * 90 + off), fill=(120, 40, 220, 55), width=2)
        return b
    def f(t):
        b = fondo(t); s, a = ent(t); pul = .75 + .25 * math.sin(t * 5)
        pegar(b, card, c.cx, c.cy + flot(t, 6), s * c.kb(t), a * (.85 + .15 * pul))
        if tl is not None:
            y = max(tl.height / 2 + .04 * H, c.cy - c.ih / 2 - .05 * H - tl.height / 2); k = e_out(prog(t, .5, .7)); pegar(b, tg, c.cx, y, 1, k * pul); pegar(b, tl, c.cx, y + (1 - k) * 40, 1, k)
        if sl is not None:
            y = min(H - sl.height / 2 - .04 * H, c.cy + c.ih / 2 + .06 * H); k = e_out(prog(t, 1., .7)); pegar(b, sg, c.cx, y, 1, k * pul); pegar(b, sl, c.cx, y, 1, k)
        d = ImageDraw.Draw(b, "RGBA")
        for yy in range(0, H, 6): d.line((0, yy, W, yy), fill=(0, 0, 0, 14))
        return b
    return f

def s_aurora(c):
    W, H = c.W, c.H; cols = [(30, 220, 160), (40, 120, 255), (150, 70, 255), (20, 200, 220), (255, 90, 190), (60, 255, 150)]; m = 20; w, h = c.iw + 2 * m, c.ih + 2 * m
    panel = Image.new("RGBA", (w, h), (255, 255, 255, 40)); ImageDraw.Draw(panel).rounded_rectangle((0, 0, w - 1, h - 1), 60, outline=(255, 255, 255, 130), width=2); panel.putalpha(ImageChops.multiply(panel.getchannel("A"), mask_rr((w, h), 60)))
    sh = sombra(w, h, 60, 34, 0, 26, (10, 20, 60), .4, 80); card = apilar(sh.size, (sh, (0, 0)), (panel, (80, 80)), (redond(c.im, 44), (80 + m, 80 + m)))
    tl = c.T("sans", .068, (255, 255, 255), sombra=(0, 3, (20, 30, 90))); sl = c.S("sansl", .034, (255, 255, 255))
    def f(t):
        b = blobs(W, H, cols, t, .35, .8); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 9), s * c.kb(t), a); c.textos(b, t, tl, sl); return b
    return f

def s_retro(c):
    W, H = c.W, c.H; bar = 52; m = 16; w, h = c.iw + 2 * m, c.ih + 2 * m + bar; pad = 40
    ven = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ven); d.rectangle((0, 0, w - 1, h - 1), fill=(192, 192, 192), outline=(255, 255, 255)); d.rectangle((4, 4, w - 4, 4 + bar - 10), fill=(0, 0, 170))
    d.text((16, 6), c.tit[:22] if c.tit else "infografia.exe", font=F("sans", 30), fill=(255, 255, 255))
    for i in range(3): x = w - 46 - i * 44; d.rectangle((x, 8, x + 34, 4 + bar - 14), fill=(192, 192, 192), outline=(0, 0, 0)); d.text((x + 9, 5), "_□x"[i], font=F("sans", 26), fill=(0, 0, 0))
    ven.alpha_composite(c.im.convert("RGBA"), (m, bar + m - 6)); sh = sombra(w, h, 0, 1, 20, 20, (60, 0, 90), .85, pad); card = apilar(sh.size, (sh, (0, 0)), (ven, (pad, pad)))
    tl = c.T("impact", .085, (255, 113, 206), stroke=0, sombra=(6, 6, (1, 205, 254)), mayus=True); sl = c.S("mono", .032, (255, 255, 255), sombra=(3, 3, (120, 0, 160)))
    def f(t):
        b = vgrad(W, H, (255, 113, 206), (130, 60, 220)); d = ImageDraw.Draw(b, "RGBA"); sy = int(H * .62); cx = W // 2; r = int(W * .3)
        d.ellipse((cx - r, sy - 2 * r, cx + r, sy), fill=(255, 220, 90))
        for i in range(6): d.rectangle((cx - r, sy - r * .9 + i * r * .18, cx + r, sy - r * .9 + i * r * .18 + 4 + i * 3), fill=(255, 113, 206))
        d.rectangle((0, sy, W, H), fill=(30, 10, 70)); off = (t * 50) % 80
        for k in range(-12, 13): d.line((cx + k * 120 * .35, sy, cx + k * 420, H), fill=(1, 205, 254, 160), width=2)
        j = 0; y = sy + off * .2
        while y < H: d.line((0, y, W, y), fill=(1, 205, 254, 160), width=2); j += 1; y += 14 + j * 9
        s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 7), s * c.kb(t), a); c.textos(b, t, tl, sl); return b
    return f

def s_isometrico(c):
    W, H = c.W, c.H; sc = min(W * .86 / ((c.img.width + c.img.height) * .866), H * .38 / ((c.img.width + c.img.height) * .5)); a, bb = .866 * sc, .5 * sc
    w0, h0 = c.img.size; ow, oh = int((w0 + h0) * a) + 2, int((w0 + h0) * bb) + 2; coef = (1 / (2 * a), 1 / (2 * bb), -h0 / 2, -1 / (2 * a), 1 / (2 * bb), h0 / 2)
    src = c.img.convert("RGBA"); top = src.transform((ow, oh), Image.AFFINE, coef, Image.BICUBIC); al = top.getchannel("A"); dark = Image.new("RGBA", (ow, oh), (60, 70, 120, 255)); dark.putalpha(al)
    esp = 26; blk = Image.new("RGBA", (ow, oh + esp), (0, 0, 0, 0))
    for i in range(esp, 0, -1): blk.alpha_composite(dark if i > 8 else Image.blend(dark, Image.new("RGBA", dark.size, (90, 100, 170, 255)), .3).convert("RGBA"), (0, i))
    blk.alpha_composite(top, (0, 0))
    def cubo(sz, cols):
        L = Image.new("RGBA", (int(sz * 1.8), int(sz * 2.1)), (0, 0, 0, 0)); d = ImageDraw.Draw(L); cx = L.width / 2; yy = sz * .3; k = sz * .9
        d.polygon([(cx, yy), (cx + k, yy + k * .5), (cx, yy + k), (cx - k, yy + k * .5)], fill=cols[0]); d.polygon([(cx - k, yy + k * .5), (cx, yy + k), (cx, yy + k * 2), (cx - k, yy + k * 1.5)], fill=cols[1]); d.polygon([(cx + k, yy + k * .5), (cx, yy + k), (cx, yy + k * 2), (cx + k, yy + k * 1.5)], fill=cols[2]); return L
    cubos = [(cubo(90, ((255, 190, 90), (225, 150, 50), (190, 120, 30))), .14, .12), (cubo(70, ((120, 220, 190), (80, 180, 150), (50, 140, 110))), .86, .78), (cubo(60, ((255, 140, 170), (225, 100, 130), (190, 70, 100))), .84, .16), (cubo(80, ((140, 160, 255), (100, 120, 225), (70, 90, 190))), .12, .82)]
    tl = c.T("sans", .066, (50, 55, 110)); sl = c.S("sansr", .032, (80, 90, 140)); sw = int(ow * .9); sdw = Image.new("RGBA", (sw, int(sw * .3)), (0, 0, 0, 0)); ImageDraw.Draw(sdw).ellipse((0, 0, sw - 1, int(sw * .3) - 1), fill=(60, 60, 120, 120)); sdw = sdw.filter(ImageFilter.GaussianBlur(24))
    def f(t):
        b = vgrad(W, H, (226, 233, 255), (250, 232, 245)); s, a = ent(t); y = c.cy + flot(t, 12) + 20
        pegar(b, sdw, c.cx, c.cy + oh / 2 + esp + 60, s * (1 - .04 * math.sin(t * 1.7)), a * .8)
        for i, (cb, px, py) in enumerate(cubos): pegar(b, cb, W * px, H * py + 24 * math.sin(t * 1.3 + i * 1.7), e_back(prog(t, .4 + i * .15, .6)), 1)
        pegar(b, blk, c.cx, y, s * c.kb(t), a)
        if tl is not None: k = e_out(prog(t, .5, .7)); pegar(b, tl, c.cx, max(tl.height / 2 + .04 * H, c.cy - oh / 2 - .05 * H - tl.height / 2) + (1 - k) * 40, 1, k)
        if sl is not None: k = e_out(prog(t, 1., .7)); pegar(b, sl, c.cx, min(H - sl.height / 2 - .04 * H, c.cy + oh / 2 + esp + .09 * H) + (1 - k) * 40, 1, k)
        return b
    return f

def s_ilustrado(c):
    W, H = c.W, c.H; rs = np.random.RandomState(7); gr = rs.randint(-9, 9, (H // 2, W // 2, 1)); bg = Image.fromarray(np.clip(np.array(plano((W // 2, H // 2), (247, 240, 224)), dtype="int16") + gr, 0, 255).astype("uint8")).resize((W, H), Image.BILINEAR)
    pad = 30; w, h = c.iw + 2 * pad, c.ih + pad * 2 + 90; pol = Image.new("RGBA", (w, h), (0, 0, 0, 0)); pol.alpha_composite(plano((w, h), (255, 255, 255)).convert("RGBA")); pol.alpha_composite(c.im.convert("RGBA"), (pad, pad))
    sh = sombra(w, h, 4, 18, 8, 14, (60, 40, 20), .4, 50); card = apilar(sh.size, (sh, (0, 0)), (pol, (50, 50)))
    for ax, ay in ((card.width * .5 - 90, 36), ):
        cinta = Image.new("RGBA", (190, 56), (255, 214, 90, 200)); card.alpha_composite(cinta.rotate(-4, expand=True), (int(ax), int(ay)))
    tl = c.T("mano", .068, (60, 40, 30)); sl = c.S("mano", .034, (100, 75, 60)); rj = np.random.RandomState(2)
    def onda(x0, x1, y, amp, n=40): return [(lerp(x0, x1, i / n), y + amp * math.sin(i * .9) + rj.uniform(-2, 2)) for i in range(n + 1)]
    ond = onda(c.W * .25, c.W * .75, 0, 8)
    def estrella(cx, cy, r): return [(cx + (r if i % 2 == 0 else r * .45) * math.sin(i * math.pi / 5), cy - (r if i % 2 == 0 else r * .45) * math.cos(i * math.pi / 5)) for i in range(11)]
    def f(t):
        b = bg.copy(); d = ImageDraw.Draw(b); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 6), s, a, rot=2.5 * math.sin(t * .9))
        c.textos(b, t, tl, sl)
        if tl is not None:
            y = max(tl.height / 2 + .04 * H, c.cy - c.ih / 2 - .03 * H - tl.height / 2) + tl.height / 2 + 4; n = int(len(ond) * prog(t, 1., .8))
            if n > 1: d.line([(x, yy + y) for x, yy in ond[:n]], fill=(240, 90, 90), width=7, joint="curve")
        n = int(11 * prog(t, 1.3, .7)); e = estrella(W * .86, H * .14 + 6 * math.sin(t * 2), 56)
        if n > 1: d.line(e[:n + 1], fill=(40, 140, 220), width=6, joint="curve")
        n = int(40 * prog(t, 1.6, .8)); sp = [(W * .12 + (i * 1.5) * math.cos(i * .35) * 2.2, H * .88 + (i * 1.5) * math.sin(i * .35) * 2.2) for i in range(41)]
        if n > 1: d.line(sp[:n], fill=(60, 170, 110), width=6, joint="curve")
        return b
    return f

def s_editorial(c):
    W, H = c.W, c.H; bg = plano((W, H), (244, 239, 230)); ink = (20, 20, 20); marg = int(W * .07)
    cab = lay_txt("EDICIÓN ESPECIAL · INFOGRAFÍA", "sans", W * .026, ink, W * .86, align="left"); num = lay_txt("01", "serif", W * .2, (200, 40, 40), W, align="right")
    tl = lay_txt(c.tit, "serif", W * .105, ink, W * .86, align="left", lh=1.02) if c.tit else None; sl = lay_txt(c.sub, "serifr", W * .036, (70, 70, 70), W * .86, align="left") if c.sub else None
    im = c.im
    def f(t):
        b = bg.copy(); d = ImageDraw.Draw(b); k = e_out(prog(t, .1, .8)); d.rectangle((marg, 70, marg + (W - 2 * marg) * k, 76), fill=ink); pegar(b, cab, marg + cab.width / 2 - 10, 112, 1, e_out(prog(t, .3, .6)))
        ty = 170
        if tl is not None: kk = e_out(prog(t, .4, .8)); pegar(b, tl, marg + tl.width / 2 - 10, ty + tl.height / 2 + (1 - kk) * 40, 1, kk); ty += tl.height + 20
        d.rectangle((marg, ty, marg + (W - 2 * marg) * e_out(prog(t, .9, .8)), ty + 3), fill=ink); ty += 30
        hh = min(im.height, H - ty - (sl.height if sl is not None else 0) - 160); sh_ = contain(im, W - 2 * marg, hh); rev = e_io(prog(t, .8, 1.1))
        if sh_.height * rev > 2: b.paste(sh_.crop((0, 0, sh_.width, int(sh_.height * rev))), (int((W - sh_.width) / 2), int(ty)))
        yb = ty + sh_.height + 18
        if sl is not None: kk = e_out(prog(t, 1.7, .7)); pegar(b, sl, marg + sl.width / 2 - 10, yb + sl.height / 2 + (1 - kk) * 20, 1, kk)
        pegar(b, num, W - marg - num.width / 2 + 10, H - 120, 1, .9 * e_out(prog(t, 1.2, .8))); return b
    return f

def s_memphis(c):
    W, H = c.W, c.H; bg = plano((W, H), (255, 245, 225)); bd = 10; w, h = c.iw + 2 * bd, c.ih + 2 * bd
    card = apilar((w + 52, h + 52), (plano((w, h), (255, 87, 127)).convert("RGBA"), (52, 52)), (plano((w, h), (0, 200, 200)).convert("RGBA"), (26, 26)), (plano((w, h), (255, 255, 255)).convert("RGBA"), (0, 0)), (c.im.convert("RGBA"), (bd, bd)))
    ImageDraw.Draw(card).rectangle((0, 0, w - 1, h - 1), outline=(0, 0, 0), width=bd)
    def forma(k, col, sz):
        L = Image.new("RGBA", (sz + 20, sz + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(L); o = 10
        if k == "c": d.ellipse((o, o, o + sz, o + sz), fill=col, outline=(0, 0, 0), width=6)
        elif k == "t": d.polygon([(o + sz / 2, o), (o + sz, o + sz), (o, o + sz)], fill=col, outline=(0, 0, 0))
        elif k == "z": d.line([(o + i * sz / 6, o + (sz if i % 2 else 0) * .6 + sz * .2) for i in range(7)], fill=col, width=14, joint="curve")
        elif k == "p":
            for i in range(3):
                for j in range(3): d.ellipse((o + i * sz / 3, o + j * sz / 3, o + i * sz / 3 + 12, o + j * sz / 3 + 12), fill=col)
        elif k == "r": d.rectangle((o, o, o + sz, o + sz * .6), fill=col, outline=(0, 0, 0), width=6)
        return L
    fs = [("c", (255, 214, 0), 130, .12, .1), ("t", (94, 80, 255), 150, .86, .13), ("z", (255, 87, 127), 160, .14, .9), ("p", (0, 160, 160), 150, .85, .88), ("r", (255, 140, 0), 120, .9, .5), ("c", (0, 200, 200), 90, .08, .5), ("t", (255, 214, 0), 100, .5, .95)]
    capas = [(forma(k, col, sz), px, py) for k, col, sz, px, py in fs]
    tl = c.T("negra", .068, (0, 0, 0), sombra=(6, 6, (255, 214, 0)), mayus=True); sl = c.S("sans", .032, (60, 40, 110))
    def f(t):
        b = bg.copy()
        for i, (L, px, py) in enumerate(capas): pegar(b, L, W * px + 22 * math.sin(t * .9 + i), H * py + 22 * math.cos(t * .8 + i * 1.3), e_back(prog(t, .1 + i * .08, .6)), 1, rot=t * (25 if i % 2 else -20))
        s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 7), s * c.kb(t), a, rot=math.sin(t * 1.2) * 1.2); c.textos(b, t, tl, sl); return b
    return f

def s_material(c):
    W, H = c.W, c.H; bg = plano((W, H), (238, 238, 238)); barh = int(H * .085); pri = (98, 0, 238)
    w, h = c.iw, c.ih; pad = 70; s1 = sombra(w, h, 14, 8, 0, 6, (0, 0, 0), .35, pad); s2 = sombra(w, h, 14, 30, 0, 26, (0, 0, 0), .45, pad); im = redond(c.im, 14)
    c1 = apilar(s1.size, (s1, (0, 0)), (im, (pad, pad))); c2 = apilar(s2.size, (s2, (0, 0)), (im, (pad, pad)))
    tl = lay_txt(c.tit, "sansr", W * .05, (255, 255, 255), W * .8, align="left") if c.tit else None; sl = c.S("sansr", .03, (66, 66, 66))
    fab = Image.new("RGBA", (190, 190), (0, 0, 0, 0)); fd = ImageDraw.Draw(fab); fd.ellipse((15, 25, 175, 185), fill=(0, 0, 0, 90)); fab = fab.filter(ImageFilter.GaussianBlur(6)); fd = ImageDraw.Draw(fab); fd.ellipse((15, 15, 175, 175), fill=(255, 64, 129)); fd.rectangle((88, 55, 102, 135), fill=(255, 255, 255)); fd.rectangle((55, 88, 135, 102), fill=(255, 255, 255))
    def f(t):
        b = bg.copy(); d = ImageDraw.Draw(b, "RGBA"); k = e_out(prog(t, 0, .5)); d.rectangle((0, 0, W, barh * k), fill=pri)
        if tl is not None: pegar(b, tl, 40 + tl.width / 2, barh / 2, 1, e_out(prog(t, .3, .5)))
        for i in range(3): d.ellipse((W - 50 - i * 22 - 5, barh / 2 - 5, W - 50 - i * 22 + 5, barh / 2 + 5), fill=(255, 255, 255, 230))
        s, a = ent(t, .3); el = e_io(prog(t, .9, .9)); pegar(b, c1, c.cx, c.cy + flot(t, 3), s * c.kb(t), a); pegar(b, c2, c.cx, c.cy + flot(t, 3) - 8 * el, s * c.kb(t), a * el)
        r = prog(t, 1.7, .9)
        if 0 < r < 1:
            rr = r * max(c.iw, c.ih) * .75; ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(ov).ellipse((c.cx - rr, c.cy - rr, c.cx + rr, c.cy + rr), fill=(98, 0, 238, int(90 * (1 - r)))); mk = Image.new("L", (W, H), 0); mk.paste(mask_rr((c.iw, c.ih), 14), (int(c.cx - c.iw / 2), int(c.cy - c.ih / 2))); ov.putalpha(ImageChops.multiply(ov.getchannel("A"), mk)); b.paste(ov.convert("RGB"), (0, 0), ov.getchannel("A"))
        if sl is not None: kk = e_out(prog(t, 1.1, .6)); pegar(b, sl, c.cx, min(H - 200, c.cy + c.ih / 2 + .05 * H), 1, kk)
        pegar(b, fab, W - 130, H - 130, e_back(prog(t, 1.3, .6)) * (1 + .05 * math.sin(t * 3)), 1); return b
    return f

def s_apple(c):
    W, H = c.W, c.H; fondo = ImageOps.fit(c.img.convert("RGB"), (int(W * 1.18), int(H * 1.18)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(60))
    fondo = Image.blend(fondo, Image.new("RGB", fondo.size, (40, 40, 60)), .15); fondo = ImageEnhance_color(fondo, 1.5)
    w, h = c.iw, c.ih; pad = 80; im = redond(c.im, 64); sh = sombra(w, h, 64, 34, 0, 30, (0, 0, 0), .5, pad)
    borde = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(borde).rounded_rectangle((0, 0, w - 1, h - 1), 64, outline=(255, 255, 255, 120), width=3); card = apilar(sh.size, (sh, (0, 0)), (im, (pad, pad)), (borde, (pad, pad)))
    cap = None
    if c.tit:
        t0 = lay_txt(c.tit, "sans", W * .05, (255, 255, 255), W * .74); cap = Image.new("RGBA", (t0.width + 80, t0.height + 40), (0, 0, 0, 0)); cd = ImageDraw.Draw(cap); cd.rounded_rectangle((0, 0, cap.width - 1, cap.height - 1), cap.height // 2, fill=(255, 255, 255, 60), outline=(255, 255, 255, 140), width=2); cap.alpha_composite(t0, (40, 20))
    sl = c.S("sansl", .032, (255, 255, 255))
    def f(t):
        z = 1 + .06 * t / c.dur; fw, fh = int(W * z), int(H * z); bg = fondo.resize((fw, fh), Image.BILINEAR).crop(((fw - W) // 2, (fh - H) // 2, (fw - W) // 2 + W, (fh - H) // 2 + H)); s, a = ent(t); pegar(bg, card, c.cx, c.cy + flot(t, 8), s * c.kb(t), a)
        g = prog((t - 1.4) % 4.0, 0, 1.0)
        if t > 1.4 and g < 1:
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0)); x = int(lerp(-w * .4, w * 1.1, g)); ImageDraw.Draw(ov).polygon([(x, 0), (x + 120, 0), (x - 90, h), (x - 210, h)], fill=(255, 255, 255, 90)); ov = ov.filter(ImageFilter.GaussianBlur(18)); ov.putalpha(ImageChops.multiply(ov.getchannel("A"), mask_rr((w, h), 64)))
            bg.paste(ov.convert("RGB"), (int(c.cx - w / 2), int(c.cy + flot(t, 8) - h / 2)), ov.getchannel("A"))
        if cap is not None: k = e_back(prog(t, .6, .7)); pegar(bg, cap, c.cx, max(cap.height / 2 + .04 * H, c.cy - h / 2 - .04 * H - cap.height / 2), k, cl(k * 3))
        if sl is not None: k = e_out(prog(t, 1., .7)); pegar(bg, sl, c.cx, min(H - sl.height / 2 - .04 * H, c.cy + h / 2 + .04 * H + sl.height / 2) + (1 - k) * 30, 1, k)
        return bg
    return f
def ImageEnhance_color(im, k):
    from PIL import ImageEnhance
    return ImageEnhance.Color(im).enhance(k)

def s_fluent(c):
    W, H = c.W, c.H; acc = (0, 120, 212); bar = 66; w, h = c.iw, c.ih + bar; pad = 70
    ven = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ven); d.rectangle((0, 0, w, bar), fill=(248, 248, 250)); d.text((22, 13), (c.tit or "Infografía")[:26], font=F("sansr", 30), fill=(30, 30, 30))
    for i, g in enumerate(("—", "▢", "✕")): d.text((w - 150 + i * 50, 12), g, font=F("sansr", 30), fill=(60, 60, 60))
    ven.alpha_composite(c.im.convert("RGBA"), (0, bar)); ven.putalpha(mask_rr((w, h), 14)); bd = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(bd).rounded_rectangle((0, 0, w - 1, h - 1), 14, outline=(0, 0, 0, 40), width=2)
    sh = sombra(w, h, 14, 26, 0, 20, (0, 0, 0), .35, pad); card = apilar(sh.size, (sh, (0, 0)), (ven, (pad, pad)), (bd, (pad, pad)))
    luz = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); ld = ImageDraw.Draw(luz)
    for r in range(150, 0, -6): ld.ellipse((150 - r, 150 - r, 150 + r, 150 + r), fill=(255, 255, 255, int(70 * (1 - r / 150))))
    sl = c.S("sansr", .03, (40, 40, 40)); ac = None
    if sl is not None:
        ac = Image.new("RGBA", (sl.width + 60, sl.height + 30), (0, 0, 0, 0)); ImageDraw.Draw(ac).rounded_rectangle((0, 0, ac.width - 1, ac.height - 1), 20, fill=(255, 255, 255, 200), outline=(0, 0, 0, 30), width=2); ac.alpha_composite(sl, (30, 15))
    def f(t):
        b = blobs(W, H, [(243, 243, 243), (222, 236, 250), (236, 232, 250), (250, 240, 232)], t, .3, .9); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 6), s * c.kb(t), a)
        g = prog(t, 1., 2.0)
        if 0 < g < 1:
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ov.alpha_composite(luz, (int(lerp(-150, w - 150, g)), int(h * .5 - 150 + 120 * math.sin(g * 6)))); ov.putalpha(ImageChops.multiply(ov.getchannel("A"), mask_rr((w, h), 14))); b.paste(ov.convert("RGB"), (int(c.cx - w / 2), int(c.cy + flot(t, 6) - h / 2)), ov.getchannel("A"))
        d = ImageDraw.Draw(b); yy = c.cy + h / 2 + 40; d.rounded_rectangle((c.cx - 180, yy, c.cx + 180, yy + 8), 4, fill=(200, 200, 200)); d.rounded_rectangle((c.cx - 180, yy, c.cx - 180 + 360 * e_io(prog(t, .8, 2.0)), yy + 8), 4, fill=acc)
        if ac is not None: k = e_out(prog(t, 1.2, .6)); pegar(b, ac, c.cx, yy + 70 + ac.height / 2, 1, k)
        return b
    return f

def s_responsivo(c):
    W, H = c.W, c.H; tl = c.T("sans", .056, (30, 41, 90)); labs = ["Móvil", "Tablet", "Escritorio"]; ars = [.47, .75, 1.6]
    lt = [lay_txt(x, "sans", W * .032, (110, 120, 160), W) for x in labs]; la = [lay_txt(x, "sans", W * .032, (255, 255, 255), W) for x in labs]
    def ar(t):
        ph = ((t - .4) / ((c.dur - .4) / 3)) if t > .4 else 0; ph = cl(ph, 0, 2.999); i = int(ph); x = ph - i; x = e_io(cl((x - .45) / .5)) if i < 2 else 0
        return ars[i] + (ars[min(2, i + 1)] - ars[i]) * x, (i + (1 if x > .5 else 0)) if i < 2 else 2
    def f(t):
        b = vgrad(W, H, (238, 243, 255), (222, 232, 252)); a_r, idx = ar(t); mw = W * .8; mh = H * (.5 if c.tit else .58); w = min(mw, mh * a_r); h = w / a_r; bz = 26 if a_r < 1 else 20; sp = ent(t)
        cy = c.cy + (.0 if c.tit else 0); cy = H * (.5 if c.tit else .46); d = ImageDraw.Draw(b)
        sh = sombra(int(w), int(h), 40, 30, 0, 26, (30, 41, 90), .35, 60); b.paste(sh.convert("RGB"), (int(c.cx - sh.width / 2), int(cy - sh.height / 2)), sh.getchannel("A").point(lambda v: int(v * sp[1])))
        d.rounded_rectangle((c.cx - w / 2, cy - h / 2, c.cx + w / 2, cy + h / 2), 38 if a_r < 1 else 24, fill=(28, 28, 34)); sw, shh = int(w - 2 * bz), int(h - 2 * bz)
        scr = Image.new("RGB", (sw, shh), (255, 255, 255)); im = contain(c.img, sw, shh); scr.paste(im, ((sw - im.width) // 2, (shh - im.height) // 2)); b.paste(scr, (int(c.cx - sw / 2), int(cy - shh / 2)), mask_rr((sw, shh), 20 if a_r < 1 else 8))
        if a_r > 1.2: d.rectangle((c.cx - 90, cy + h / 2, c.cx + 90, cy + h / 2 + 26), fill=(160, 165, 180)); d.rounded_rectangle((c.cx - 200, cy + h / 2 + 24, c.cx + 200, cy + h / 2 + 44), 8, fill=(190, 195, 210))
        for i in range(3):
            x = c.cx + (i - 1) * 270; src = la[i] if i == idx else lt[i]
            if i == idx: d.rounded_rectangle((x - 120, H * .9 - 34, x + 120, H * .9 + 34), 34, fill=(60, 90, 230))
            pegar(b, src, x, H * .9, 1, 1)
        if tl is not None: k = e_out(prog(t, .4, .6)); pegar(b, tl, c.cx, max(tl.height / 2 + .035 * H, .09 * H) + (1 - k) * 30, 1, k)
        return b
    return f

def s_accesible(c):
    W, H = c.W, c.H; bd = 14; w, h = c.iw + 2 * bd, c.ih + 2 * bd; card = Image.new("RGBA", (w, h), (255, 255, 255, 255)); card.alpha_composite(c.im.convert("RGBA"), (bd, bd)); card = redond(card.convert("RGB"), 18)
    tl = c.T("sans", .08, (255, 221, 0)); sl = c.S("sans", .042, (255, 255, 255)); pills = []
    for txt, col, fg in (("Contraste 21:1", (255, 255, 255), (0, 0, 0)), ("WCAG AAA", (0, 200, 90), (0, 0, 0)), ("Aa  Texto grande", (255, 221, 0), (0, 0, 0))):
        tx = lay_txt(txt, "sans", W * .03, fg, W); L = Image.new("RGBA", (tx.width + 50, tx.height + 24), (0, 0, 0, 0)); ImageDraw.Draw(L).rounded_rectangle((0, 0, L.width - 1, L.height - 1), L.height // 2, fill=col); L.alpha_composite(tx, (25, 8)); pills.append(L)
    def f(t):
        b = plano((W, H), (0, 0, 0)); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 4), s * c.kb(t), a); k = prog(t, .6, .6)
        if k > 0:
            d = ImageDraw.Draw(b); ex = 26 + 4 * math.sin(t * 4); sc_ = s * c.kb(t); x0, y0 = c.cx - w * sc_ / 2 - ex, c.cy + flot(t, 4) - h * sc_ / 2 - ex; x1, y1 = c.cx + w * sc_ / 2 + ex, c.cy + flot(t, 4) + h * sc_ / 2 + ex
            if int(t * 2.5) % 2 == 0 or k < 1: d.rounded_rectangle((x0, y0, x1, y1), 30, outline=(255, 221, 0), width=int(10 * k))
        c.textos(b, t, tl, sl, 1.05)
        tot = sum(p.width for p in pills) + 30 * 2; x = c.cx - tot / 2; y = min(H - 70, c.cy + c.ih / 2 + .13 * H)
        if sl is None: y = min(H - 70, c.cy + c.ih / 2 + .06 * H)
        for i, p in enumerate(pills): kk = e_back(prog(t, 1.2 + i * .25, .5)); pegar(b, p, x + p.width / 2, y, kk, cl(kk * 3)); x += p.width + 30
        return b
    return f

def s_atomico(c):
    W, H = c.W, c.H; marg = int(W * .07); mono = lambda tx, col=(90, 100, 140): lay_txt(tx, "mono", W * .026, col, W)
    acc = (88, 80, 236); tl = c.T("sans", .062, (30, 35, 80)); sl = c.S("sansr", .03, (80, 88, 130)); w, h = c.iw + 50, c.ih + 50; marco = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0)); sh = sombra(w, h, 22, 18, 0, 12, (40, 40, 100), .25, 40)
    card = apilar(sh.size, (sh, (0, 0)), (redond(plano((w, h), (255, 255, 255)), 22), (40, 40)), (redond(c.im, 14), (65, 65)))
    sw = [(88, 80, 236), (255, 87, 127), (255, 190, 60), (30, 200, 160), (30, 35, 80)]; lab = [mono("ÁTOMOS"), mono("MOLÉCULAS"), mono("ORGANISMO", acc)]
    boton = Image.new("RGBA", (250, 76), (0, 0, 0, 0)); ImageDraw.Draw(boton).rounded_rectangle((0, 0, 249, 75), 38, fill=acc); boton.alpha_composite(lay_txt("Botón", "sans", 34, (255, 255, 255), 240), (60, 8))
    chip = Image.new("RGBA", (220, 76), (0, 0, 0, 0)); ImageDraw.Draw(chip).rounded_rectangle((0, 0, 219, 75), 38, fill=(255, 255, 255), outline=(200, 205, 230), width=3); chip.alpha_composite(lay_txt("Etiqueta", "sans", 30, (30, 35, 80), 200), (38, 10))
    def f(t):
        b = plano((W, H), (247, 248, 252)); d = ImageDraw.Draw(b)
        for x in range(0, W, 60):
            for y in range(0, H, 60): d.ellipse((x, y, x + 4, y + 4), fill=(215, 220, 238))
        ty = H * .08
        if tl is not None: k = e_out(prog(t, .1, .6)); pegar(b, tl, c.cx, max(tl.height / 2 + .03 * H, ty + tl.height / 2) + (1 - k) * 25, 1, k); ty += tl.height + 14
        y1 = ty + 40; pegar(b, lab[0], marg + 80, y1 - 40, 1, e_out(prog(t, .3, .4)))
        for i, col in enumerate(sw): kk = e_back(prog(t, .35 + i * .12, .5)); x = marg + 40 + i * 86; d2 = 60 * kk; d.ellipse((x - d2 / 2 + 40, y1 + 40 - d2 / 2, x + d2 / 2 + 40, y1 + 40 + d2 / 2), fill=col)
        pegar(b, boton, W - marg - 125, y1 + 40, e_back(prog(t, 1., .5)), 1); y2 = y1 + 150; pegar(b, lab[1], marg + 105, y2 - 15, 1, e_out(prog(t, .9, .4))); pegar(b, chip, marg + 110, y2 + 55, e_back(prog(t, 1.2, .5)), 1)
        cy = max(c.cy + .06 * H, y2 + 130 + h / 2) if c.tit else c.cy + .06 * H; cy = min(cy, H - h / 2 - .12 * H); s, a = ent(t, 1.5, .8); pegar(b, card, c.cx, cy + flot(t, 4), s, a)
        k = prog(t, 2.0, .6)
        if k > 0: dash_rect(d, (c.cx - w / 2 - 20, cy - h / 2 - 20, c.cx + w / 2 + 20, cy + h / 2 + 20), acc, 4); pegar(b, lab[2], c.cx, cy - h / 2 - 46, 1, k)
        if sl is not None: pegar(b, sl, c.cx, min(H - sl.height / 2 - .03 * H, cy + h / 2 + .06 * H), 1, e_out(prog(t, 2.2, .6)))
        return b
    return f

def s_oscuro(c):
    W, H = c.W, c.H; tx, ty, tr = W - 150, 90, 150
    def tema(dark):
        bgc = (16, 18, 26) if dark else (246, 247, 251); tc = (240, 242, 250) if dark else (25, 28, 45); sc = (150, 158, 185) if dark else (100, 108, 135)
        w, h = c.iw, c.ih; pad = 70
        if dark: gl = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle((pad, pad, pad + w, pad + h), 28, fill=(110, 130, 255, 70)); sh = gl.filter(ImageFilter.GaussianBlur(26))
        else: sh = sombra(w, h, 28, 28, 0, 22, (60, 70, 120), .28, pad)
        card = apilar(sh.size, (sh, (0, 0)), (redond(c.im, 28), (pad, pad)))
        if dark: ImageDraw.Draw(card).rounded_rectangle((pad, pad, pad + w, pad + h), 28, outline=(120, 135, 255, 180), width=3)
        return bgc, card, c.T("sans", .064, tc), c.S("sansr", .032, sc)
    L = tema(False); D = tema(True)
    def capa(t, th, dark):
        bgc, card, tl, sl = th; b = plano((W, H), bgc); s, a = ent(t); pegar(b, card, c.cx, c.cy + flot(t, 7), s * c.kb(t), a); c.textos(b, t, tl, sl)
        d = ImageDraw.Draw(b); k = e_io(prog(t, 1.4, .5)) if dark else 0; x0 = W - 210; d.rounded_rectangle((x0, 55, x0 + 120, 105), 25, fill=(60, 66, 100) if dark else (205, 210, 230)); kx = x0 + 25 + 70 * (1 if dark else 0)
        d.ellipse((kx - 19, 61, kx + 19, 99), fill=(255, 255, 255)); return b
    def f(t):
        t0, t1 = 1.4, 2.6
        if t < t0: return capa(t, L, False)
        k = e_io(prog(t, t0, t1 - t0)); a = capa(t, L, False); bb = capa(t, D, True)
        if k >= 1: return bb
        m = Image.new("L", (W, H), 0); r = k * math.hypot(W, H) * 1.05; ImageDraw.Draw(m).ellipse((tx - r, ty - r, tx + r, ty + r), fill=255); return Image.composite(bb, a, m)
    return f

ESTILOS = {"minimalista": s_minimalista, "flat": s_flat, "skeuo": s_skeuo, "neumorfismo": s_neumorfismo, "glass": s_glass, "clay": s_clay, "neobrutalismo": s_neobrutalismo,
           "bento": s_bento, "neon": s_neon, "aurora": s_aurora, "retro": s_retro, "isometrico": s_isometrico, "ilustrado": s_ilustrado, "editorial": s_editorial, "memphis": s_memphis,
           "material": s_material, "apple": s_apple, "fluent": s_fluent, "responsivo": s_responsivo, "accesible": s_accesible, "atomico": s_atomico, "oscuro": s_oscuro}

# ---------------------------------------------------------------- render
def render(clave, img, W, H, tit, sub, dur, ruta):
    c = Ctx(img, W, H, tit, sub, dur); f = ESTILOS[clave](c); n = int(dur * FPS)
    cmd = [FF, "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-t", "%.3f" % dur, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", ruta]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            fr = f(i / FPS)
            if fr.size != (W, H): fr = fr.resize((W, H))
            p.stdin.write(fr.convert("RGB").tobytes())
        p.stdin.close()
    except BrokenPipeError: pass
    return p.wait() == 0

def main():
    ruta = (P.get("imagen") or "").strip()
    if not ruta or not os.path.exists(ruta): sys.exit("Falta la imagen (o la ruta ya no existe): " + ruta)
    estilos = [e for e in (P.get("estilos") or []) if e in ESTILOS]
    if not estilos: sys.exit("Elige al menos un estilo.")
    W, H = FORMATOS.get(P.get("formato"), FORMATOS["reels"]); dur = cl(float(P.get("duracion") or 8), 4, 20); tit = (P.get("titulo") or "").strip(); sub = (P.get("subtitulo") or "").strip()
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB"); sello = time.strftime("%Y%m%d-%H%M%S"); ok = 0
    for i, e in enumerate(estilos, 1):
        out = os.path.join(SALIDA, "infografia_%s_%s.mp4" % (e, sello)); print("[%d/%d] Estilo %s ..." % (i, len(estilos), e), flush=True)
        try:
            if render(e, img, W, H, tit, sub, dur, out): ok += 1; print("OK " + out, flush=True)
            else: print("ERROR: ffmpeg no pudo crear " + out, flush=True)
        except Exception as ex:
            import traceback; traceback.print_exc(); print("ERROR en el estilo %s: %s" % (e, ex), flush=True)
    print("Listo: %d de %d videos en %s" % (ok, len(estilos), SALIDA)); sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
