r"""Subtitulos animados palabra por palabra en Lato (estilo del video de referencia «lash-record-pantalla-negra-lato»). Modulo compartido por
Subtitulado (subtitulado_lote.py) y por los videos de Servicios y Negocios (generar_dianchi.py, opcion «Solo subtitulos»).

Estilo: frases cortas centradas en el medio del video; las palabras aparecen una a una cuando la voz las dice (suben 38 px, crecen de 85 % a 100 % y aparecen en 0,22 s,
con curva de salida 1-(1-p)^3); las palabras clave van GRANDES (Lato Black 112 px, blanco) y el resto chicas (Lato Regular 66 px, gris claro #d6d6d6); letras muy juntas
(-0,06 / -0,07 em), interlineado 1,02 y brillo suave.

Uso:  capa = Capa(tokens, B, W, H, ini=0.0, sobre_video=True)      tokens = palabras del texto (con su puntuacion); B = [(palabra, inicio_s, fin_s)] de la voz
      for datos in capa.frames(n): proceso_ffmpeg.stdin.write(datos)   -> RGBA de W x capa.banda; en ffmpeg: overlay=0:capa.y0"""
import math, os, re, unicodedata
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
STOP = set(norm(w) for w in ("de la que el en y a los se del las un por con no una su para es al lo como mas pero sus le ya o fue este si porque esta entre cuando muy sin sobre tambien me hasta hay donde quien desde todo nos "
    "durante todos uno les ni contra otros ese eso ante ellos e esto antes algunos que unos yo otro otras otra el tanto esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo mi mis tu te ti tus ellas "
    "era eran son ser fueron tiene tienen hace hacen asi aunque cada the and for with that this from your you are was were have has but not they their them what when where which will would can could into about more just than then "
    "also been being does did our out how why who all any each other some such only over very").split())
ENTRADA = 0.22                                # segundos que dura la entrada de cada palabra

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
    """Agrupa las palabras en frases de pantalla de 3 a 8 palabras y ~44 caracteres: corta en puntos, y en comas o dos puntos si la frase ya lleva 3 palabras o mas.
    No separa un articulo de su sustantivo ni una preposicion de lo que sigue (si el corte cae justo despues de una de esas palabras, pasa a la frase siguiente) y no deja palabras sueltas."""
    out, cur, chars = [], [], 0
    for i, tk in enumerate(tokens):
        cur.append(i); chars += len(tk) + 1
        fin = re.search(r"[.!?…]+[\"')\]]*$", tk); pausa = re.search(r"[,;:]+[\"')\]]*$", tk)
        if fin or (pausa and len(cur) >= 3): out.append(cur); cur, chars = [], 0
        elif len(cur) >= 8 or chars >= 44:
            resto = []
            while len(cur) > 2 and norm(re.sub(r"^\W+|\W+$", "", tokens[cur[-1]])) in STOP: resto.insert(0, cur.pop())   # una palabra de enlace no se queda al final de la frase
            out.append(cur); cur = resto; chars = sum(len(tokens[j]) + 1 for j in cur)
    if cur: out.append(cur)
    k = 0
    while k < len(out):                                             # ninguna palabra suelta: se une a la frase vecina
        if len(out[k]) == 1 and len(out) > 1:
            if k > 0 and len(out[k - 1]) < 8: out[k - 1] += out.pop(k); continue
            if k + 1 < len(out) and len(out[k + 1]) < 8: out[k + 1] = out[k] + out[k + 1]; out.pop(k); continue
        k += 1
    return out

def marcadas(marcado, n):
    """Indices de las palabras que el guion marco con asteriscos (*Lash* *Record,*); None si no coincide el numero de palabras."""
    idx, abierto, i = set(), False, 0
    for w in marcado.split():
        limpio = w.replace("*", "")
        if not limpio:
            abierto = not abierto if w.count("*") % 2 else abierto; continue
        if abierto or "*" in w: idx.add(i)
        if w.count("*") % 2: abierto = not abierto
        i += 1
    return idx if i == n else None

def claves(tokens, idxs, marcas=None):
    """Palabras clave de una frase (las que van GRANDES): 1 si la frase tiene 4 palabras o menos y 2 si tiene mas. Si el guion las marco con asteriscos se usan esas;
    si no, las mas largas y significativas (sustantivos, verbos fuertes, nombres propios, cifras): nunca articulos, preposiciones ni conectores."""
    k = 1 if len(idxs) <= 4 else 2
    c = []
    for pos, i in enumerate(idxs):
        w = re.sub(r"^\W+|\W+$", "", tokens[i]); nw = norm(w)
        if len(nw) < 3 or nw in STOP: continue
        puntos = len(nw) + (4 if (w[:1].isupper() and pos > 0) else 0) + (6 if any(ch.isdigit() for ch in w) else 0) + (50 if (marcas and i in marcas) else 0)
        c.append((puntos, i))
    c.sort(reverse=True)
    if marcas and any(i in marcas for _, i in c): return {i for p, i in c[:k] if i in marcas}
    return {i for _, i in c[:k]}

def fuente(grande, px):
    nombre = "Lato-Black.ttf" if grande else "Lato-Regular.ttf"          # en el espacio de trabajo las fuentes de la app quedan en _operacion/_work/fonts
    carpetas = [os.path.join(AG, "_operacion", "_work", "fonts"), os.path.join(AG, "assets", "fonts"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")]
    for p in [os.path.join(c, nombre) for c in carpetas] + [r"C:\Windows\Fonts\seguibl.ttf" if grande else r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arialbd.ttf" if grande else r"C:\Windows\Fonts\arial.ttf"]:
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
        else:                                                                                          # pantalla negra: brillo blanco (text-shadow: 0 4px 30px rgba(255,255,255,.12))
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

class Capa:
    """Capa de subtitulos: calcula las frases y genera, cuadro a cuadro, la imagen RGBA de la banda de texto (centrada en el video)."""
    def __init__(self, tokens, B, W, H, ini=0.0, tamano=1.0, sobre_video=True, claves_on=True, fps=30, cola=1.0, marcado=None):
        self.W, self.H, self.fps = W, H, fps; self.st = Estilo(W, H, tamano, sobre_video=sobre_video)
        t0 = alinear(tokens, B); self.fin_voz = B[-1][2] if B else t0[-1] + 0.5
        fr = frases(tokens); self.chunks = []; marcas = marcadas(marcado, len(tokens)) if marcado else None
        for k, idxs in enumerate(fr):
            grandes = claves(tokens, idxs, marcas) if claves_on else set(); its = self.st.maquetar(idxs, tokens, grandes)
            a = t0[idxs[0]]; b = t0[fr[k + 1][0]] if k + 1 < len(fr) else self.fin_voz + 0.6
            self.chunks.append(dict(ini=a + ini - 0.02, fin=b + ini - 0.02, items=its, t0=[t0[it["i"]] + ini for it in its]))
        self.dur = self.fin_voz + ini + cola
        self.banda = min(H, int(1100 * self.st.s) // 2 * 2); self.y0 = (H - self.banda) // 2 // 2 * 2; self.cy = H / 2 - self.y0   # cy: centro del video dentro de la banda
    def frames(self, n=None):
        n = n or int(math.ceil(self.dur * self.fps)); st, cy = self.st, self.cy
        vacio = Image.new("RGBA", (self.W, self.banda), (0, 0, 0, 0)); vacio_b = vacio.tobytes(); ult_clave = None; ult_bytes = vacio_b; estatico = {}
        for f in range(n):
            t = f / float(self.fps); c = next((c for c in self.chunks if c["ini"] <= t < c["fin"]), None)
            if c is None: yield vacio_b; continue
            ci = self.chunks.index(c); k_fin = 0; anim = []
            for j, it in enumerate(c["items"]):
                pr = (t - c["t0"][j]) / ENTRADA
                if pr >= 1: k_fin = j + 1
                elif pr > 0: anim.append((it, pr))
            clave = (ci, k_fin, tuple(round(pr, 3) for _, pr in anim))
            if clave == ult_clave: yield ult_bytes; continue
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
            ult_clave, ult_bytes = clave, datos; yield datos
