"""Editor automatico: anima un video vertical de una persona hablando a camara.

- Camara: cambio de plano cada ~3.5 s (zooms, encuadres, inclinaciones), siguiendo la cara con YOLO.
- Graficos animados (Pillow): titulos fucsia que entran con rebote, iconos/emojis a color, tipeo, tachado, destellos en cada corte.
- Subtitulos palabra por palabra (solo cambia de color la palabra activa).
- Sonidos sintetizados (whoosh en cada corte, pop en cada icono, clics de tipeo, ding de regalo...).
Uso: python animar_video.py <ffmpeg.exe> <video> <transcripcion.json> <carpeta_salida>
"""
import json, math, os, re, shutil, statistics, subprocess, sys, wave
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ultralytics import YOLO

FF, VIDEO, TRANS, OUT = sys.argv[1:5]
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WK = os.path.join(os.path.dirname(os.path.abspath(TRANS)), "montaje"); os.makedirs(os.path.join(WK, "gfx"), exist_ok=True); os.makedirs(OUT, exist_ok=True)
VERD, EMO_F, BILL = r"C:\Windows\Fonts\verdanab.ttf", r"C:\Windows\Fonts\seguiemj.ttf", AG + r"\_operacion\_work\Billabong.otf"
W, H, FPS = 1080, 1920, 30
FUC, ROSA, BLANCO, OSC = (214, 20, 128), (255, 63, 164), (255, 255, 255), (28, 28, 34)
SR = 44100
rng = np.random.default_rng(11)

DUR = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO], capture_output=True, text=True).stdout)
NF = int(math.ceil(DUR * FPS))

# ---------------- palabras (con correcciones de la transcripcion) ----------------
raw = [(w["w"].strip(), w["s"], w["e"]) for seg in json.load(open(TRANS, encoding="utf-8")) for w in seg["words"]]
PAL = []
for i, (w, s, e) in enumerate(raw):
    if i in (26, 48): continue                                   # "de" y "Este" sobran
    if i == 12: m = (s + e) / 2; PAL += [("Miss", s, m), ("Mundo", m, e)]; continue
    if i == 55: w = "véanlo"
    PAL.append((w, s, e))

# ---------------- plano de camara ----------------
CORTES = [0, 3.34, 6.72, 10.12, 14.48, 18.02, 21.24, 24.96, 28.14, 31.94, 35.32, DUR]
#          zoom, desplazamiento x (px), inclinacion (grados)
PLANOS = [(1.00, 0, 0), (1.22, -30, 0), (1.00, 0, 2.0), (1.33, 0, 0), (1.12, 0, -2.0), (1.30, 30, 0),
          (1.00, 0, 0), (1.25, 0, 2.0), (1.35, 0, 0), (1.10, 0, -2.0), (1.28, 0, 0)]

def seguimiento():
    modelo = YOLO(os.path.join(AG, "por-cortar", "_operacion", "clips_trabajo", "yolov8n.pt"))
    raw_ = subprocess.run([FF, "-v", "error", "-i", VIDEO, "-vf", "fps=3", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fw, fh = 576, 1024; n = len(raw_) // (fw * fh * 3); fr = np.frombuffer(raw_, np.uint8)[: n * fw * fh * 3].reshape(n, fh, fw, 3)
    pts = []
    for k in range(n):
        r = modelo(fr[k], imgsz=640, classes=[0], conf=0.3, verbose=False)[0]
        cajas = [tuple(b.xyxy[0].tolist()) for b in r.boxes]
        if cajas:
            x1, y1, x2, y2 = max(cajas, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
            pts.append((k / 3.0, (x1 + x2) / 2, y1 + 0.24 * (y2 - y1)))     # centro de la cara aproximado
    return pts

def camara(pts, destino):
    vf = ["[0:v]fps=30,format=yuv420p,split=%d%s" % (len(PLANOS), "".join("[x%d]" % i for i in range(len(PLANOS))))]
    for i, (z, dx, rot) in enumerate(PLANOS):
        t0, t1 = CORTES[i], CORTES[i + 1]
        d_ = [p for p in pts if t0 - 0.3 <= p[0] <= t1 + 0.3] or pts
        cx = statistics.median(p[1] for p in d_) + dx; fy = statistics.median(p[2] for p in d_)
        w = 576 / z; h = 1024 / z
        x = max(0, min(576 - w, cx - w / 2)); y = max(0, min(1024 - h, fy - 0.46 * h))     # la cara mas abajo: deja libre la franja de los titulos
        extra = 1.10 if rot else 1.0                                            # margen para que la inclinacion no deje esquinas negras
        D = max(t1 - t0, 0.5)
        f = ("[x%d]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,crop=%d:%d:%d:%d,"
             "scale=w='trunc(1080*%.2f*(1+0.05*t/%.2f)/2)*2':h='trunc(1920*%.2f*(1+0.05*t/%.2f)/2)*2':eval=frame:flags=lanczos"
             % (i, t0, t1, int(w) // 2 * 2, int(h) // 2 * 2, int(x) // 2 * 2, int(y) // 2 * 2, extra, D, extra, D))
        if rot: f += ",rotate=a=%.5f:ow=iw:oh=ih:c=black" % (rot * math.pi / 180)
        f += ",crop=1080:1920,setsar=1,unsharp=5:5:0.8:5:5:0.0,format=yuv420p[p%d]" % i
        vf.append(f)
    vf.append("".join("[p%d]" % i for i in range(len(PLANOS))) + "concat=n=%d:v=1:a=0[v]" % len(PLANOS))
    subprocess.run([FF, "-y", "-v", "error", "-i", VIDEO, "-filter_complex", ";".join(vf), "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "14",
                    "-preset", "veryfast", "-pix_fmt", "yuv420p", destino], check=True)

# ---------------- graficos animados ----------------
def ease_back(t):
    t = max(0.0, min(1.0, t)); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def ease_out(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def sprite_emoji(e, px=240):
    f = ImageFont.truetype(EMO_F, px); im = Image.new("RGBA", (int(px * 1.6),) * 2, (0, 0, 0, 0))
    ImageDraw.Draw(im).text((im.width / 2, im.height / 2), e, font=f, embedded_color=True, anchor="mm")
    return im.crop(im.getbbox())

def sprite_chip(lineas, fondo=FUC, color=BLANCO, sz=64, tachado=0.0):
    f = ImageFont.truetype(VERD, sz); ancho = max(f.getlength(l) for l in lineas); lh = int(sz * 1.25); px, py = 46, 26
    w, h = int(ancho + 2 * px), int(lh * len(lineas) + 2 * py); S = 3
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle((0, 0, w * S, h * S), radius=int(h * S * .28), fill=fondo + (255,))
    im = im.resize((w, h), Image.LANCZOS); d = ImageDraw.Draw(im)
    for k, l in enumerate(lineas): d.text((w / 2, py + lh * (k + .5)), l, font=f, fill=color + (255,), anchor="mm")
    if tachado > 0: d.line((px - 10, h / 2, px - 10 + (w - 2 * px + 20) * tachado, h / 2), fill=(255, 59, 92, 255), width=12)
    sh = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((30, 38, w + 30, h + 38), radius=int(h * .28), fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(10)); sh.alpha_composite(im, (30, 30)); return sh

def poner(lienzo, sp, cx, cy, escala=1.0, rot=0.0, alfa=1.0):
    if escala <= 0.02 or alfa <= 0.01: return
    s = sp.resize((max(2, int(sp.width * escala)), max(2, int(sp.height * escala))), Image.BILINEAR)
    if abs(rot) > 0.1: s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alfa < 0.99: s.putalpha(s.getchannel("A").point(lambda v: int(v * alfa)))
    lienzo.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2))) if (0 <= cx - s.width / 2 and 0 <= cy - s.height / 2 and cx + s.width / 2 <= W and cy + s.height / 2 <= H) else \
        lienzo.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)

# titulos arriba: (inicio, fin, lineas, estilo)
CHIPS = [
    (0.25, 3.25, ["ENTREVISTA CON", "EL JURADO"], "normal"),
    (3.34, 6.55, ["MISS MUNDO", "LATINA USA"], "normal"),
    (6.72, 8.25, ["LA TEMIDA", "ENTREVISTA"], "normal"),
    (8.32, 12.30, ["CONSEJOS PARA TU", "MEJOR ENTREVISTA"], "normal"),
    (12.50, 14.40, ["MI CONSEJO #1"], "normal"),
    (14.50, 16.15, ["ENTREVISTA"], "tachado"),
    (16.22, 19.05, ["CONVERSACIÓN"], "normal"),
    (19.12, 21.15, ["ENTRA", "RELAJADA"], "normal"),
    (21.30, 24.35, ["¿NECESITAS", "CONSEJOS O TIPS?"], "normal"),
    (24.50, 28.10, ["TIPS PARA TUS", "CONCURSOS"], "normal"),
    (28.20, 31.00, [], "tipeo"),
    (31.10, 33.50, ["TE REGALO UNA", "GUÍA GRATIS"], "normal"),
    (33.60, 36.40, ["TIPS PRÁCTICOS", "PARA TU ENTREVISTA"], "normal"),
    (36.50, DUR, ["CONCURSOS DE", "BELLEZA"], "normal"),
]
# iconos laterales: (inicio, emoji, lado)
ICONOS = [(0.5, "🎤", "D"), (3.34, "👑", "I"), (6.72, "😰", "D"), (8.28, "💡", "I"), (12.9, "⭐", "D"), (14.70, "❌", "D"), (16.48, "💬", "I"),
          (20.52, "😌", "D"), (24.62, "✨", "I"), (27.24, "🏆", "D"), (29.12, "📩", "I"), (31.94, "🎁", "D"), (33.62, "✅", "I"), (37.14, "🏅", "D")]
DUR_ICONO = 1.7

def graficos():
    sprites = {e: sprite_emoji(e) for _, e, _ in ICONOS}
    chips = {i: sprite_chip(l) for i, (_, _, l, est) in enumerate(CHIPS) if l and est == "normal"}
    tachos = {int(p * 10) / 10: None for p in []}
    etiqueta = sprite_chip(["RESPONDE ESTA HISTORIA CON:"], sz=40)
    for n in range(NF):
        t = n / FPS; lz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # destello blanco en cada corte
        for c in CORTES[1:-1]:
            if 0 <= t - c < 0.14:
                lz.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(85 * (1 - (t - c) / 0.14)))))
        # titulos
        for i, (a, b, lineas, est) in enumerate(CHIPS):
            if not (a <= t <= b): continue
            tau = t - a; sal = b - t
            esc = ease_back(tau / 0.30); dy = (1 - ease_out(tau / 0.30)) * -110; alfa = min(1.0, tau / 0.12)
            if sal < 0.18: esc *= 0.75 + 0.25 * (sal / 0.18); alfa *= sal / 0.18; dy -= 30 * (1 - sal / 0.18)
            if est == "normal":
                sp = chips[i]; poner(lz, sp, W / 2, 190 + sp.height / 2 + dy, esc, 0, alfa)
            elif est == "tachado":
                sp = sprite_chip(lineas, fondo=OSC, tachado=ease_out((tau - 0.30) / 0.25)); poner(lz, sp, W / 2 + (6 * math.sin(tau * 60) if 0.5 < tau < 0.8 else 0), 190 + sp.height / 2 + dy, esc, 0, alfa)
            else:                                           # tipeo: mensaje que se escribe
                texto = "ENTREVISTA"; k = int(max(0, min(len(texto), (t - 28.9) / 0.10 + (1 if t >= 28.9 else 0))))
                cur = "|" if int(t * 4) % 2 == 0 and k < len(texto) else ""
                burbuja = sprite_chip([texto[:k] + cur if (texto[:k] + cur) else " "], fondo=(245, 245, 250), color=OSC, sz=76)
                poner(lz, etiqueta, W / 2, 190 + etiqueta.height / 2 + dy, esc, 0, alfa)
                poner(lz, burbuja, W / 2, 190 + etiqueta.height + 40 + burbuja.height / 2 + dy, esc, 0, alfa)
        # iconos laterales
        for a, e, lado in ICONOS:
            if not (a <= t <= a + DUR_ICONO): continue
            tau = t - a; sal = a + DUR_ICONO - t
            esc = ease_back(tau / 0.32) * (0.78 if e in ("⭐", "✨") else 1.0); alfa = 1.0
            if sal < 0.2: esc *= sal / 0.2; alfa = sal / 0.2
            x = 150 if lado == "I" else W - 150; y = 960 + 16 * math.sin(tau * 4.5)
            sp = sprites[e]; escala = 215 / max(sp.size) * esc
            poner(lz, sp, x, y, escala, 7 * math.sin(tau * 5.5) * (1 if lado == "I" else -1), alfa)
        lz.save(os.path.join(WK, "gfx", "g_%05d.png" % (n + 1)), compress_level=1)

# ---------------- sonidos ----------------
def pop(f0=520):
    n = int(.15 * SR); t = np.arange(n) / SR; f = f0 + 600 * (1 - np.exp(-t * 30))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28) * .55
def whoosh(d=.32):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); y = np.zeros(n); a = np.linspace(.03, .4, n)
    for i in range(1, n): y[i] = y[i - 1] + a[i] * (x[i] - y[i - 1])
    y = y * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.3
    return y / np.abs(y).max() * .4
def swish():
    n = int(.22 * SR); t = np.arange(n) / SR
    return np.diff(rng.standard_normal(n + 1)) * np.sin(np.pi * t / t[-1]) ** 2 * .28
def tecla():
    n = int(.035 * SR); t = np.arange(n) / SR
    return (np.diff(rng.standard_normal(n + 1)) * np.exp(-t * 170) * .6 + np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 200) * .25)
def ding():
    n = int(.9 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1568 * t) + .5 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t * 5.5) * .35
def slash():
    n = int(.18 * SR); t = np.arange(n) / SR; x = np.diff(rng.standard_normal(n + 1)); return x * np.exp(-t * 22) * np.linspace(0.2, 1, n) ** .5 * .55
def destello():
    n = int(1.0 * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for k, f in enumerate([2093, 2637, 3136, 3951]):
        i0 = int(k * .07 * SR); out[i0:] += (np.sin(2 * np.pi * f * t[: n - i0]) * np.exp(-t[: n - i0] * 7)) * .2
    return out

def sfx(destino):
    ev = []
    for c in CORTES[1:-1]: ev.append((c - .03, whoosh, .55, -.6 if len(ev) % 2 else .6))
    for a, b, l, est in CHIPS: ev.append((a, swish, .8, 0.0))
    for k, (a, e, lado) in enumerate(ICONOS):
        ev.append((a, (lambda f0=450 + 60 * (k % 4): pop(f0)), .8, -.5 if lado == "I" else .5))
    ev.append((14.62, slash, .9, 0.0))
    for k in range(10): ev.append((28.9 + k * .10, tecla, .8, -.2 + .04 * k))
    ev += [(31.94, ding, .9, 0.0), (33.62, (lambda: ding() * .6), .8, 0.0), (37.14, destello, .8, 0.0), (0.2, swish, .6, 0.0)]
    out = np.zeros((int((DUR + 1) * SR), 2), np.float32)
    for t, fn, g, pan in ev:
        x = fn() * g; i = int(t * SR); ang = (pan + 1) * np.pi / 4; x = x[: len(out) - i]
        out[i:i + len(x), 0] += x * np.cos(ang); out[i:i + len(x), 1] += x * np.sin(ang)
    out = np.clip(out, -1, 1)
    with wave.open(destino, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())

# ---------------- subtitulos (solo cambia de color la palabra activa) ----------------
CLAVES = {"entrevista", "entrevistas", "jurado", "relajadas", "tips", "consejos"}
def subtitulos(destino):
    fv, fb = ImageFont.truetype(VERD, 66), ImageFont.truetype(BILL, 118)
    bill = lambda w: re.sub(r"[^\wáéíóúñ]", "", w.lower()) in CLAVES
    ancho = lambda ws: sum((fb.getlength(re.sub(r"[^\w]", "", x[0]).lower()) if bill(x[0]) else fv.getlength(x[0].upper())) for x in ws) + fv.getlength(" ") * (len(ws) - 1)
    grupos, i = [], 0
    while i < len(PAL):
        g, j = [], i
        while j < len(PAL) and len(g) < 6:
            g.append(PAL[j]); j += 1
            if len(g) >= 3 and re.search(r"[.,;:?!]$", PAL[j - 1][0]): break
        while len(g) > 1 and max(ancho(g[:(len(g) + 1) // 2]), ancho(g[(len(g) + 1) // 2:] or g[:1])) > 900: g.pop(); j -= 1
        grupos.append(g); i = j
    ts = lambda s: "%d:%02d:%05.2f" % (s // 3600, (s % 3600) // 60, s % 60)
    ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "", "[V4+ Styles]",
           "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
           "Style: S,Verdana,66,&H00FFFFFF,&H00FFFFFF,&H00301020,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,90,90,520,1", "",
           "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    for gi, g in enumerate(grupos):
        fin = g[-1][2] + 0.05 if gi == len(grupos) - 1 else grupos[gi + 1][0][1]; k = (len(g) + 1) // 2
        for a, w in enumerate(g):
            e = g[a + 1][1] if a + 1 < len(g) else fin; partes = []
            for b, x in enumerate(g):
                t = (r"{\fnBillabong\fs118\b0}%s{\fnVerdana\fs66\b1}" % re.sub(r"[^\w]", "", x[0]).lower()) if bill(x[0]) else x[0].upper()
                if b == a: t = r"{\c&HA43FFF&}%s{\c&HFFFFFF&}" % t
                partes.append(t)
            ass.append("Dialogue: 0,%s,%s,S,,0,0,0,,%s" % (ts(w[1]), ts(e), " ".join(partes[:k]) + r"\N" + " ".join(partes[k:])))
    open(destino, "w", encoding="utf-8").write("\n".join(ass))

def main():
    cam = os.path.join(WK, "camara.mp4")
    print("1/5 siguiendo la cara y montando la camara...", flush=True); camara(seguimiento(), cam)
    print("2/5 dibujando graficos animados (%d cuadros)..." % NF, flush=True); graficos()
    print("3/5 sintetizando sonidos...", flush=True); sfx(os.path.join(WK, "sfx.wav"))
    print("4/5 subtitulos...", flush=True); subtitulos(os.path.join(WK, "sub.ass"))
    shutil.copy(VERD, os.path.join(WK, "verdanab.ttf")); shutil.copy(BILL, os.path.join(WK, "Billabong.otf"))
    nombre = "TU ENTREVISTA DE CONCURSO ES UNA CONVERSACIÓN %s.mp4" % datetime.now().strftime("%Y-%m-%d %H-%M")
    destino = os.path.join(OUT, nombre)
    fc = ("[0:v][2:v]overlay=0:0:format=auto:shortest=1[vg];[vg]subtitles=sub.ass:fontsdir=.,format=yuv420p[vo];"
          "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=stereo,aresample=44100[v];"
          "[v][3:a]amix=inputs=2:duration=first:weights='1 0.6':normalize=0,alimiter=limit=0.85:level=disabled[aout]")
    print("5/5 montaje final...", flush=True)
    r = subprocess.run([FF, "-y", "-v", "error", "-i", "camara.mp4", "-i", VIDEO, "-framerate", "30", "-i", "gfx/g_%05d.png", "-i", "sfx.wav",
                        "-filter_complex", fc, "-map", "[vo]", "-map", "[aout]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-profile:v", "high", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", destino],
                       capture_output=True, text=True, cwd=WK)
    print("OK" if r.returncode == 0 else r.stderr[-1500:]); print(destino)

main()
