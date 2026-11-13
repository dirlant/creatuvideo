r"""Convierte un fotograma de cada video de una carpeta en una tarjeta (foto con esquinas redondeadas y borde fucsia) para usar en los collages.
Uso: python fotogramas_a_tarjetas.py <ffmpeg.exe> <carpeta_videos> <carpeta_destino> <prefijo>
Salida: <destino>\<prefijo>-1.png, <prefijo>-2.png ...  (en el orden alfabetico de los videos; el fotograma se toma al 35 % de cada video)
Sirve para que los collages usen imagenes del mismo servicio que el B-roll pero que NO se repiten en el video (se reservan videos aparte en la subcarpeta _collage)."""
import glob, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

FF, SRC, DST, PRE = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]), sys.argv[4]
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
FUC = (214, 20, 128); LADO = 700; MARG = 50; S = 3
os.makedirs(DST, exist_ok=True)

def tarjeta(foto):
    w, h = foto.size; l = min(w, h); y0 = max(0, int((h - l) * 0.35))        # recorte cuadrado, un poco hacia arriba (donde suele estar lo importante)
    foto = foto.crop(((w - l) // 2, y0, (w - l) // 2 + l, y0 + l))
    t = (LADO - 2 * MARG) * S; foto = foto.resize((t, t), Image.LANCZOS).convert("RGBA")
    im = Image.new("RGBA", (LADO * S, LADO * S), (0, 0, 0, 0)); x0, x1, r = MARG * S, (LADO - MARG) * S, 90 * S
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sombra).rounded_rectangle((x0, x0 + 18 * S, x1, x1 + 18 * S), radius=r, fill=(0, 0, 0, 120))
    im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(16 * S)))
    m = Image.new("L", (t, t), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, t - 1, t - 1), radius=r, fill=255)
    im.paste(foto, (x0, x0), m)
    ImageDraw.Draw(im).rounded_rectangle((x0, x0, x1, x1), radius=r, outline=FUC + (255,), width=10 * S)
    return im.resize((LADO, LADO), Image.LANCZOS)

for n, v in enumerate(sorted(glob.glob(os.path.join(SRC, "*.mp4"))), 1):
    dur = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout)
    tmp = os.path.join(DST, "_tmp.png")
    subprocess.run([FF, "-v", "error", "-y", "-ss", "%.2f" % (dur * 0.35), "-i", v, "-frames:v", "1", tmp], check=True)
    tarjeta(Image.open(tmp)).save(os.path.join(DST, "%s-%d.png" % (PRE, n))); os.remove(tmp)
    print(os.path.basename(v), "->", "%s-%d.png" % (PRE, n))
