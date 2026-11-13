r"""Video de rubro SIN hook, construido a partir de un guion de Dianchi: las ESCENAS (B-roll), los sonidos y las animaciones se arman segun las palabras del guion.
Uso: python generar_dianchi.py <ffmpeg.exe> <config.json>      (con: uv run --python 3.12 --with edge-tts --with pillow --with numpy python ...)
Pasos: voz Jorge 1.3x (edge-tts) -> escenas de B-roll que cambian en la palabra indicada (con empuje de camara) -> titulo del gancho (chip del rubro + titulo) -> cinta fucsia fija ->
       subtitulos sin fondo (solo cambia de color la palabra activa) -> sonidos sintetizados -> base.mp4 ; despues collages, pildoras y tarjeta final con hyperframes (hf_collage.py) y render.
config.json: ver agente\dianchi\_operacion\unas-pedicura\config.json (rubro, titulo, gancho, guion, cta, cinta, clips_dir, escenas[], sfx[], collages[], pildoras*, cierre, salida)."""
import asyncio, glob, json, os, re, shutil, subprocess, sys, unicodedata, wave
from datetime import datetime
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FF, CFG = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(AG, "scripts"))
import procesar
from procesar import render
VERDANA = r"C:\Windows\Fonts\verdanab.ttf"; FONTB = os.path.join(AG, "_operacion", "_work", "Billabong.otf")
procesar.FP = VERDANA; procesar.CAJA = False; procesar.CHIP_FUCSIA = True     # titulo sin caja; solo el rubro lleva chip fucsia
C = json.load(open(CFG, encoding="utf-8"))
VOICE, VEL = C.get("voz", "es-MX-JorgeNeural"), 1.3
SLUG = C["slug"]
EF = bool(C.get("efectos"))          # efectos tendencia: palabra activa con "pop", zoom-punch + destello en cada corte, pildoras con rebote y brillo, collage flotante, barra de progreso
OP = os.path.join(AG, C.get("operacion", "dianchi/_operacion").replace("/", os.sep))          # carpeta de recursos (_operacion) de la linea: dianchi\_operacion o diegao\_operacion
W = os.path.join(OP, "_trabajo", SLUG); os.makedirs(W, exist_ok=True)
CLIPS = C["clips_dir"] if os.path.isabs(C["clips_dir"]) else os.path.join(AG, C["clips_dir"])
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
dur = lambda f: float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True, encoding="utf-8").stdout)

# ---------------- texto: gancho + guion + CTA (*palabra* = palabra clave en Billabong) ----------------
ACENTOS = {"ambicion": "ambición", "carisimo": "carísimo", "cercania": "cercanía", "conversacion": "conversación", "cuticula": "cutícula", "decision": "decisión", "hidratacion": "hidratación", "maquina": "máquina",
           "diseno": "diseño", "numeros": "números", "preparacion": "preparación", "presion": "presión", "salon": "salón", "sesion": "sesión", "tecnica": "técnica"}
restaurar = lambda s: re.sub(r"\*([^*]+)\*", lambda m: "*" + ACENTOS.get(m.group(1), m.group(1)) + "*", s)
titulo = [restaurar(l) for l in C["titulo"]]
marcado = restaurar(" ".join(x for x in (C["gancho"], C["guion"], C["cta"]) if x))
texto = marcado.replace("*", "")
n_gancho = len(C["gancho"].replace("*", "").split())
flags_tok = ["*" in t for t in marcado.split()]; norm_w = lambda s: re.sub(r"[^\w]", "", s.lower()); claves = {norm_w(t) for t in marcado.split() if "*" in t}

async def tts():
    words, audio = [], open(os.path.join(W, "voz_base.mp3"), "wb")
    async for ch in edge_tts.Communicate(texto, VOICE, boundary="WordBoundary").stream():
        if ch["type"] == "audio": audio.write(ch["data"])
        elif ch["type"] == "WordBoundary": words.append((ch["text"], ch["offset"] / 1e7 / VEL, (ch["offset"] + ch["duration"]) / 1e7 / VEL))
    audio.close(); return words
words = asyncio.run(tts())
subprocess.run([FF, "-y", "-v", "error", "-i", os.path.join(W, "voz_base.mp3"), "-af", "atempo=%s" % VEL, os.path.join(W, "voz.mp3")], check=True)
vd = dur(os.path.join(W, "voz.mp3")); TOT = vd + 0.35
print("voz %.1fs palabras %d (gancho %d)" % (vd, len(words), n_gancho), flush=True)
NW = [norm(w[0]) for w in words]
def tiempo(ancla, n=1):
    k = 0
    for i, w in enumerate(NW):
        if w == norm(ancla):
            k += 1
            if k == n: return words[i][1]
    raise SystemExit("no encontre la palabra: %s (n=%d)" % (ancla, n))
json.dump([(w[0], round(w[1], 3), round(w[2], 3)) for w in words], open(os.path.join(W, "palabras_abs.json"), "w", encoding="utf-8"), ensure_ascii=False)

# ---------------- subtitulos: sin fondo, solo cambia de color la palabra activa ----------------
flags = {id(w): (flags_tok[n] if len(flags_tok) == len(words) else norm_w(w[0]) in claves) for n, w in enumerate(words)}
fv, fb = ImageFont.truetype(VERDANA, 80), ImageFont.truetype(FONTB, 135)
usa_bill = lambda x: bool(flags[id(x)]) and re.fullmatch(r"[a-z]+", re.sub(r"[^\w]", "", x[0].lower())) is not None
ancho = lambda ws: sum((fb.getlength(x[0].lower()) if usa_bill(x) else fv.getlength(x[0].upper())) for x in ws) + fv.getlength(" ") * max(len(ws) - 1, 0)
cabe = lambda ch: max(ancho(ch[:(len(ch) + 1) // 2]), ancho(ch[(len(ch) + 1) // 2:])) <= 860
chunks, i = [], 0
while i < len(words):
    ch, j = [], i
    while j < len(words) and len(ch) < 6:
        ch.append(words[j]); j += 1
        if len(ch) >= 3 and re.search(r"[.,;:?!]$", words[j - 1][0]): break
    while len(ch) > 1 and not cabe(ch): ch.pop(); j -= 1
    chunks.append(ch); i = j
ts = lambda s: "%d:%02d:%05.2f" % (s // 3600, (s % 3600) // 60, s % 60)
ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "", "[V4+ Styles]",
       "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
       "Style: S,Verdana,80,&H00FFFFFF,&H00FFFFFF,&H00301020,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,5,90,90,230,1", "", "[Events]",
       "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
for ci, ch in enumerate(chunks):
    fin = ch[-1][2] + 0.05 if ci == len(chunks) - 1 else chunks[ci + 1][0][1]; k = (len(ch) + 1) // 2
    for i, w in enumerate(ch):
        e = ch[i + 1][1] if i + 1 < len(ch) else fin; parts = []
        for j, x in enumerate(ch):
            t = (r"{\fnBillabong\fs135\b0}%s{\fnVerdana\fs80\b1}" % x[0].lower()) if usa_bill(x) else x[0].upper()
            if j == i: t = (r"{\c&HA43FFF&\t(0,90,\fscx116\fscy116)\t(90,190,\fscx100\fscy100)}%s{\c&HFFFFFF&}" if EF else r"{\c&HA43FFF&}%s{\c&HFFFFFF&}") % t
            parts.append(t)
        ass.append("Dialogue: 0,%s,%s,S,,0,0,0,,%s" % (ts(w[1]), ts(e), " ".join(parts[:k]) + r"\N" + " ".join(parts[k:])))
open(os.path.join(W, "sub.ass"), "w", encoding="utf-8").write("\n".join(ass))

# ---------------- cinta fucsia fija ("Guarda este audio y esta idea para tu negocio") ----------------
lineas = [l.strip().upper() for l in C["cinta"]]; Wd = 1080
f = ImageFont.truetype(VERDANA, 27); tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
tw = max(tmp.textlength(l, font=f) for l in lineas); paso = int(f.size * 1.3); alto = 20 + paso * len(lineas) + 20; SSC = 3
capa = Image.new("RGBA", (Wd * SSC, alto * SSC), (0, 0, 0, 0)); cd = ImageDraw.Draw(capa)
cd.rounded_rectangle((((Wd - tw) / 2 - 48) * SSC, 0, ((Wd + tw) / 2 + 48) * SSC, alto * SSC), radius=30 * SSC, fill=(214, 20, 128, 255))
capa = capa.resize((Wd, alto), Image.LANCZOS); cd = ImageDraw.Draw(capa)
for k, l in enumerate(lineas): cd.text((Wd / 2, 20 + paso * (k + 0.5)), l, font=f, fill=(255, 255, 255, 255), anchor="mm")
capa.save(os.path.join(W, "cinta.png"))

# ---------------- titulo del gancho: chip del rubro + titulo (solo mientras suena el gancho) ----------------
procesar.TOP = int(C.get("titulo_top", 420))
render(titulo, C["rubro"], os.path.join(W, "titulo.png"))
t_titulo_fin = max(words[n_gancho][1] - 0.1, 2.5) if n_gancho < len(words) else 3.0

# ---------------- escenas: cada una cambia en la palabra de su ancla ----------------
esc = C["escenas"]
t0s = [0.0 if not e.get("ancla") else max(tiempo(e["ancla"], e.get("n", 1)) - 0.05, 0) for e in esc]
t1s = t0s[1:] + [TOT]

if os.environ.get("SOLO_TIEMPOS"):      # modo verificacion: tabla de escenas y choques entre animaciones, sin descargar ni renderizar nada
    t_tit = max(words[n_gancho][1] - 0.1, 2.5) if n_gancho < len(words) else 3.0
    iv = [("titulo", 0.1, t_tit)]
    for nombre, k, kh in (("pildoras", "pildoras", "pildoras_hasta"), ("pasos", "pildoras2", "pildoras2_hasta"), ("burbuja", "pildoras3", "pildoras3_hasta")):
        g = C.get(k)
        if g:
            ts_ = [tiempo(x["ancla"], x.get("n", 1)) for x in g]; fin_ = (tiempo(C[kh]) - 0.4) if C.get(kh) else ts_[-1] + 1.2
            iv.append((nombre, ts_[0] - 0.1, fin_ + 0.1))
    for c in C.get("collages", []):
        t0c = max(tiempo(c["ancla"], c.get("n", 1)) - 0.15, 0); iv.append(("collage", t0c, t0c + c.get("dur", 2.4) + 0.1))
    if C.get("cierre"): iv.append(("cierre", tiempo(C["cierre"]["ancla"]) - 0.1, TOT))
    print("TIEMPOS %s: voz %.1fs | escenas: %s" % (SLUG, vd, " ".join("%.1f" % x for x in t0s)))
    print("  animaciones: " + " | ".join("%s %.1f-%.1f" % x for x in iv))
    for a in range(len(iv)):
        for b in range(a + 1, len(iv)):
            if iv[a][1] < iv[b][2] and iv[b][1] < iv[a][2]: print("  CHOQUE: %s con %s" % (iv[a][0], iv[b][0]))
    cortas = [i + 1 for i in range(len(esc)) if t1s[i] - t0s[i] < 1.5]
    if cortas: print("  escenas muy cortas:", cortas)
    sys.exit(0)
entradas, fcs = [], []
for k, e in enumerate(esc):
    d = t1s[k] - t0s[k]
    if d < 1.2: print("  aviso: la escena %d dura solo %.2f s" % (k + 1, d))
    clip = e["clip"] if os.path.isabs(e["clip"]) else os.path.join(CLIPS, e["clip"])
    off = e.get("inicio", 0.3)
    zin = e.get("zoom", "in" if k % 2 == 0 else "out")
    fz = "1+0.07*t/%.3f" % d if zin == "in" else "1.07-0.07*t/%.3f" % d
    # cada escena se prepara en su propio ffmpeg (un solo ffmpeg con todas las escenas y empuje de camara se caia en algunos videos)
    esc_mp4 = os.path.join(W, "esc_%02d.mp4" % k)
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,eq=brightness=-0.05:saturation=1.06,"
          "scale=w='trunc(1080*(%s)/2)*2':h='trunc(1920*(%s)/2)*2':eval=frame:flags=bilinear,crop=1080:1920,setsar=1,fps=30,format=yuv420p" % (fz, fz))
    rr = subprocess.run([FF, "-y", "-v", "error", "-stream_loop", "-1", "-ss", "%.2f" % off, "-i", clip, "-t", "%.3f" % d, "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-g", "30", esc_mp4],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if rr.returncode != 0 or not os.path.exists(esc_mp4): sys.exit("escena %d (%s) fallo: %s" % (k + 1, clip, (rr.stderr or "sin salida")[-600:]))
    entradas += ["-i", esc_mp4]
    fcs.append("[%d:v]setpts=PTS-STARTPTS[s%d]" % (4 + k, k))
cortes = t0s[1:]

# ---------------- sonidos sintetizados: whoosh en cada corte + sonidos de momentos del guion ----------------
SR = 44100; sfx = np.zeros((int((TOT + 1) * SR), 2), np.float32); rng = np.random.default_rng(4)
def put(x, t, pan=0.0):
    i = int(max(t, 0) * SR); x = x[: len(sfx) - i]; a = (pan + 1) * np.pi / 4
    sfx[i:i + len(x), 0] += x * np.cos(a); sfx[i:i + len(x), 1] += x * np.sin(a)
def whoosh():
    n = int(.3 * SR); t = np.arange(n) / SR; r = rng.normal(size=n); r = r - np.convolve(r, np.ones(40) / 40, "same"); return r * np.sin(np.pi * np.clip(t / .3, 0, 1)) ** 2 * .22
def ding():
    n = int(.9 * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * 988 * t) + .4 * np.sin(2 * np.pi * 1976 * t)) * np.exp(-t * 5) * .22
def sparkle():
    out = np.zeros(int(.7 * SR))
    for k, f0 in enumerate((1320, 1568, 1976, 2349)):
        n = int(.35 * SR); t = np.arange(n) / SR; s0 = int(k * .07 * SR); out[s0:s0 + n] += np.sin(2 * np.pi * f0 * t) * np.exp(-t * 11) * .13
    return out[: int(.7 * SR)]
def tap():
    n = int(.08 * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * 180 * t) * np.exp(-t * 45) * .5
def brush():
    n = int(.35 * SR); t = np.arange(n) / SR; r = rng.normal(size=n); r = r - np.convolve(r, np.ones(14) / 14, "same"); return r * np.sin(np.pi * np.clip(t / .35, 0, 1)) * .16
def pop():          # burbuja suave: aparece un texto
    n = int(.14 * SR); t = np.arange(n) / SR; f0 = 420 + 700 * np.exp(-t * 40); return np.sin(2 * np.pi * np.cumsum(f0) / SR) * np.exp(-t * 28) * .30
def tick():         # clic muy suave en las pausas
    n = int(.05 * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * 1500 * t) + .5 * np.sin(2 * np.pi * 2300 * t)) * np.exp(-t * 90) * .16
def bueno():        # "bien": dos notas que suben (acierto, palabra positiva)
    out = np.zeros(int(.5 * SR))
    for k, f0 in enumerate((880, 1318)):
        n = int(.3 * SR); t = np.arange(n) / SR; s0 = int(k * .11 * SR); out[s0:s0 + n] += (np.sin(2 * np.pi * f0 * t) + .25 * np.sin(2 * np.pi * 2 * f0 * t)) * np.exp(-t * 9) * .20
    return out
def malo():         # "mal": tono grave que baja, un poco aspero (palabra negativa)
    n = int(.42 * SR); t = np.arange(n) / SR; ph = 2 * np.pi * np.cumsum(230 * np.exp(-t * 2.4)) / SR
    return (np.sin(ph) + .45 * np.sign(np.sin(ph))) * np.exp(-t * 5.5) * .17
def swish():        # corte de toma: soplido muy corto y suave
    n = int(.17 * SR); t = np.arange(n) / SR; r = rng.normal(size=n); r = r - np.convolve(r, np.ones(30) / 30, "same"); return r * np.sin(np.pi * np.clip(t / .17, 0, 1)) ** 2 * .13
SONIDOS = {"bueno": bueno, "malo": malo, "swish": swish, "ding": ding, "sparkle": sparkle, "tap": tap, "brush": brush, "whoosh": whoosh, "pop": pop, "tick": tick}
if not C.get("sin_whoosh"):
    for k, t in enumerate(cortes): put(whoosh(), t - .12, [-.5, .5][k % 2])
if C.get("sonido_cortes"):     # un soplido suave en cada cambio de toma
    for k, t in enumerate(cortes): put(swish(), t - .06, [-.3, .3][k % 2])
for s in C.get("sfx", []): put(SONIDOS[s["tipo"]](), tiempo(s["ancla"], s.get("n", 1)) + s.get("desfase", 0), s.get("pan", 0))
if C.get("sfx_texto"):     # sonidos atados a los cambios de texto: titulo, burbuja, pasos, collage, y un clic en cada pausa
    put(pop(), 0.15, 0)
    for g in ("pildoras", "pildoras2", "pildoras3"):
        for j, x in enumerate(C.get(g, [])): put(pop(), tiempo(x["ancla"], x.get("n", 1)) - 0.05, [-.2, .2][j % 2])
    for c_ in C.get("collages", []):
        t0c = max(tiempo(c_["ancla"], c_.get("n", 1)) - 0.15, 0)
        for j in range(3): put(pop(), t0c + 0.1 + 0.18 * j, [0, -.35, .35][j])
    npz = 0
    for i in range(len(words) - 1):
        gap = words[i + 1][1] - words[i][2]
        if gap >= C.get("pausa_min", 0.16) and words[i + 1][1] > 3.0 and words[i + 1][1] < TOT - 2.5: put(tick(), words[i][2] + 0.03, 0); npz += 1
    print("sonidos de texto: pausas con clic", npz, flush=True)
with wave.open(os.path.join(W, "sfx.wav"), "wb") as wv:
    wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

# ---------------- ensamblado de la base (sin collages: esos van con hyperframes) ----------------
n = len(esc)
fc = list(fcs)
fc.append("%sconcat=n=%d:v=1:a=0[bv]" % ("".join("[s%d]" % k for k in range(n)), n))
fc.append("[2:v]format=rgba,fade=t=in:st=0.1:d=0.3:alpha=1,fade=t=out:st=%.2f:d=0.3:alpha=1[ti]" % (t_titulo_fin - 0.3))
fc.append("[bv][ti]overlay=0:0:format=auto:eof_action=pass:enable='between(t,0.1,%.2f)'[v1]" % t_titulo_fin)
fc.append("[3:v]format=rgba,fade=t=in:st=0.4:d=0.3:alpha=1[ci]")
fc.append("[v1][ci]overlay=0:1150:format=auto:eof_action=pass:enable='gte(t,0.4)'[v2]")
fc.append("[v2]subtitles=sub.ass:fontsdir=.,format=yuv420p[vo]")
fc.append("[0:a]aresample=44100,aformat=channel_layouts=stereo[va];[1:a]aresample=44100,aformat=channel_layouts=stereo[sa];"
          "[va][sa]amix=inputs=2:duration=first:weights='1 0.5':normalize=0,alimiter=limit=0.85:level=disabled[a]")
open(os.path.join(W, "filtro.txt"), "w", encoding="utf-8").write(";\n".join(fc))
shutil.copy(VERDANA, os.path.join(W, "verdanab.ttf")); shutil.copy(FONTB, os.path.join(W, "Billabong.otf"))
base_dir = os.path.join(W, "base"); os.makedirs(base_dir, exist_ok=True); base = os.path.join(base_dir, "base.mp4")
cmd = [FF, "-y", "-v", "error", "-i", "voz.mp3", "-i", "sfx.wav", "-loop", "1", "-framerate", "30", "-t", "%.2f" % TOT, "-i", "titulo.png",
       "-loop", "1", "-framerate", "30", "-t", "%.2f" % TOT, "-i", "cinta.png"] + entradas + [
       "-/filter_complex", "filtro.txt", "-map", "[vo]", "-map", "[a]", "-t", "%.2f" % TOT, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "17", "-preset", "medium",
       "-g", "30", "-keyint_min", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", base]
print("armando la base: %d escenas..." % n, flush=True)
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=W)
if r.returncode != 0 or not os.path.exists(base): sys.exit("ffmpeg codigo %s: %s" % (r.returncode, (r.stderr or r.stdout or "sin salida")[-1500:]))
print("base OK", base, flush=True)
if os.environ.get("DETENER_BASE"): sys.exit(0)

# ---------------- animaciones con hyperframes: collages, pildoras y tarjeta final ----------------
HF = os.path.join(OP, "hf"); os.makedirs(HF, exist_ok=True); proj = os.path.join(HF, "dianchi-" + SLUG)
env = dict(os.environ); env["PATH"] = os.path.dirname(FF) + os.pathsep + env["PATH"]; env["PYTHONIOENCODING"] = "utf-8"
if not os.path.exists(os.path.join(proj, "hyperframes.json")):
    subprocess.run("npx --yes hyperframes@0.9.28 init dianchi-%s --skip-skills --skill=hyperframes" % SLUG, cwd=HF, env=env, shell=True, capture_output=True)
cfg = {k: C[k] for k in ("collages", "pildoras", "pildoras_hasta", "pildoras2", "pildoras2_hasta", "pildoras3", "pildoras3_hasta", "pildoras_top", "pildoras_paso", "cierre") if k in C}
if EF: cfg["efectos"] = True; cfg["cortes"] = [round(x, 2) for x in cortes]
cfgp = os.path.join(W, "cfg_hf.json"); json.dump(cfg, open(cfgp, "w", encoding="utf-8"), ensure_ascii=False)
r = subprocess.run([sys.executable, os.path.join(AG, "scripts", "hf_collage.py"), FF, proj, base, os.path.join(W, "palabras_abs.json"), cfgp], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout.strip() or r.stderr[-800:], flush=True)
if r.returncode != 0: sys.exit(1)
carpeta = C["salida"] if os.path.isabs(C["salida"]) else os.path.join(AG, C["salida"]); os.makedirs(carpeta, exist_ok=True)
nombre = re.sub(r'[\\/:*?"<>|]', "", " ".join(" ".join(titulo).replace("*", "").split())).strip().upper()
salida = os.path.join(carpeta, "%s %s.mp4" % (nombre, datetime.now().strftime("%Y-%m-%d %H-%M")))
print("renderizando con hyperframes...", flush=True)
r = subprocess.run('npx --yes hyperframes@0.9.28 render -o "%s" -q looks' % salida, cwd=proj, env=env, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("OK" if os.path.exists(salida) else (r.stdout[-700:] + r.stderr[-700:]), "->", salida, flush=True)
