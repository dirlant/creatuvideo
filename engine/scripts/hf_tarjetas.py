r"""Superpone TARJETAS de texto animadas (estilo lamina de carrusel) sobre un video base con hyperframes.
Uso: python hf_tarjetas.py <ffmpeg.exe> <carpeta_proyecto> <video_base.mp4> <palabras_abs.json> <config.json>
config.json: {"tarjetas": [ {"tipo": "titulo|hook|frase|cta", "num": "1", "ancla": "uno", "n": 1, "fin": "dos", "n_fin": 1, "html": "<span class=hl>NADIE</span> te dice esto..."} ]}
 - ancla/n: palabra del audio donde aparece la tarjeta; fin/n_fin: palabra donde desaparece (la tarjeta sale 0.15 s antes). La ultima puede omitir fin (dura hasta el final).
 - html admite <span class=hl> (color fucsia) y <span class=bb> (Billabong fucsia, solo letras a-z sin tildes).
El proyecto debe existir (npx hyperframes init <carpeta> --skip-skills --skill=hyperframes). Despues: check y render con ffmpeg en el PATH."""
import json, os, re, shutil, subprocess, sys, unicodedata, wave
import numpy as np

FF, PROJ, BASE, PAL, CFG = [os.path.abspath(a) for a in sys.argv[1:6]]
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
palabras = json.load(open(PAL, encoding="utf-8")); cfg = json.load(open(CFG, encoding="utf-8"))
def tiempo(ancla, n=1):
    k = 0
    for w, s, e in palabras:
        if norm(w) == norm(ancla):
            k += 1
            if k == n: return s
    raise SystemExit("no encontre la palabra: " + ancla)

for d in ("assets/fonts", "compositions"): os.makedirs(os.path.join(PROJ, d), exist_ok=True)
subprocess.run([FF, "-v", "error", "-y", "-i", BASE, "-c:v", "libx264", "-crf", "17", "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p", "-c:a", "copy", os.path.join(PROJ, "assets", "base.mp4")], check=True)
DUR = round(float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(PROJ, "assets", "base.mp4")], capture_output=True, text=True).stdout) - 0.05, 2)
shutil.copy(r"C:\Windows\Fonts\verdanab.ttf", os.path.join(PROJ, "assets", "fonts", "verdana-bold.ttf"))
shutil.copy(os.path.join(AG, "_operacion", "_work", "Billabong.otf"), os.path.join(PROJ, "assets", "fonts", "Billabong.otf"))

cards, js, sfx_t = [], [], []
for i, c in enumerate(cfg["tarjetas"]):
    t0 = max(tiempo(c["ancla"], c.get("n", 1)) - 0.1, 0)
    t1 = (tiempo(c["fin"], c.get("n_fin", 1)) - 0.15) if c.get("fin") else DUR - 0.1
    num = '<div class="num">%s</div>' % c["num"] if c.get("num") else ""
    cards.append('    <div id="t%d" class="clip tj %s" data-start="%.2f" data-duration="%.2f" data-track-index="1"><div id="t%d-in" class="tin">%s<div class="tx">%s</div></div></div>' % (i, c.get("tipo", "hook"), t0, t1 - t0 + 0.3, i, num, c["html"]))
    rot = [-2, 2, -1.5, 1.5][i % 4]
    js.append('tl.fromTo("#t%d-in", { y: 90, scale: 0.88, rotation: %d, opacity: 0 }, { y: 0, scale: 1, rotation: %s, opacity: 1, duration: 0.5, ease: "back.out(1.3)" }, %.2f);' % (i, rot * 3, rot, t0))
    js.append('tl.to("#t%d-in", { opacity: 0, y: -40, filter: "blur(8px)", duration: 0.2, ease: "power2.in" }, %.2f);' % (i, t1))
    sfx_t.append(t0 + 0.05)

html = """<template>
  <style>
    @font-face { font-family: "VerdanaB"; src: url("assets/fonts/verdana-bold.ttf"); font-weight: 700; }
    @font-face { font-family: "Billabong"; src: url("assets/fonts/Billabong.otf"); }
    #root { position: absolute; inset: 0; font-family: "VerdanaB", sans-serif; }
    .tj { position: absolute; left: 0; top: 0; width: 1080px; height: 1000px; }
    .tin { position: absolute; left: 90px; top: 330px; width: 900px; padding: 44px 46px; background: rgba(255,255,255,.96); border-radius: 36px; box-shadow: 0 24px 56px rgba(0,0,0,.5); color: #1d0f19; }
    .tx { font-size: 54px; line-height: 1.18; text-align: center; }
    .hl { color: #D61480; }
    .bb { font-family: "Billabong"; color: #D61480; font-size: 1.9em; line-height: .8; font-weight: 400; }
    .num { position: absolute; left: -26px; top: -40px; width: 96px; height: 96px; border-radius: 50%%; background: #D61480; color: #fff; font-size: 52px; text-align: center; line-height: 96px; box-shadow: 0 10px 24px rgba(0,0,0,.4); }
    .titulo .tx { font-size: 64px; }
    .titulo .big { font-size: 150px; line-height: 1; display: block; }
    .frase .tx { font-size: 58px; }
    .cta .tx { font-size: 60px; }
  </style>
  <div id="root" data-composition-id="tarjetas" data-width="1080" data-height="1920">
%s
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    %s
    window.__timelines["tarjetas"] = tl;
  </script>
</template>
""" % ("\n".join(cards), "\n    ".join(js))
open(os.path.join(PROJ, "compositions", "tarjetas.html"), "w", encoding="utf-8").write(html)
index = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #000; }
      #base { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="%(d)s" data-width="1080" data-height="1920">
      <video id="base" class="clip" src="assets/base.mp4" data-start="0" data-duration="%(d)s" data-track-index="0" data-has-audio="true" playsinline></video>
      <div id="tarjetas" data-composition-id="tarjetas" data-composition-src="compositions/tarjetas.html" data-start="0" data-duration="%(d)s" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
      <audio id="sfx" src="assets/sfx.wav" data-start="0" data-duration="%(d)s" data-track-index="2" data-volume="0.5"></audio>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""" % {"d": DUR}
open(os.path.join(PROJ, "index.html"), "w", encoding="utf-8").write(index)
SR = 44100; out = np.zeros((int((DUR + 1) * SR), 2), np.float32)
for k, t in enumerate(sfx_t):
    n = int(.16 * SR); tt = np.arange(n) / SR; f = 420 + 35 * (k % 4) + 550 * (1 - np.exp(-tt * 30)); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 26) * .45
    i = int(max(t, 0) * SR); x = x[: len(out) - i]; a = ([-.4, .4, 0][k % 3] + 1) * np.pi / 4
    out[i:i + len(x), 0] += x * np.cos(a); out[i:i + len(x), 1] += x * np.sin(a)
with wave.open(os.path.join(PROJ, "assets", "sfx.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
print("proyecto listo:", PROJ, "| duracion", DUR, "| tarjetas", len(cfg["tarjetas"]))
