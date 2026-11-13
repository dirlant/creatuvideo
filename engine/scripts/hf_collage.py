r"""Arma un proyecto de hyperframes que superpone COLLAGES de fotos (centrados, dinamicos) y pildoras de explicacion sobre un video base.
Uso: python hf_collage.py <ffmpeg.exe> <carpeta_proyecto> <video_base.mp4> <palabras_abs.json> <config.json>
config.json:
 { "collages": [ {"ancla": "lees", "n": 1, "centro": "lectura/libro-negocios-1.png", "izq": "...", "der": "...", "dur": 2.6} ],
   "pildoras": [ {"ancla": "ventas", "texto": "VENTAS"}, ... ], "pildoras_fin": 1.0 }
Las fotos se buscan en dianchi\entrada\imagenes\fotos\<ruta>. El proyecto debe existir (npx hyperframes init <carpeta> --skip-skills --skill=hyperframes).
Despues: npx hyperframes check ; npx hyperframes render -o <salida.mp4>   (con ffmpeg en el PATH)
Reglas: collage en la zona central (arriba del subtitulo), 3 fotos solapadas y giradas; entran girando desde los bordes y aterrizan quietas; fotos realistas, no iconos."""
import json, os, re, shutil, subprocess, sys, unicodedata, wave
import numpy as np

FF, PROJ, BASE, PAL, CFG = [os.path.abspath(a) for a in sys.argv[1:6]]
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FOTOS = os.path.join(AG, "dianchi", "entrada", "imagenes", "fotos")
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
palabras = json.load(open(PAL, encoding="utf-8")); cfg = json.load(open(CFG, encoding="utf-8"))
def tiempo(ancla, n=1):
    k = 0
    for w, s, e in palabras:
        if norm(w) == norm(ancla):
            k += 1
            if k == n: return s
    raise SystemExit("no encontre la palabra: " + ancla)

for d in ("assets/fotos", "assets/fonts", "compositions"): os.makedirs(os.path.join(PROJ, d), exist_ok=True)
subprocess.run([FF, "-v", "error", "-y", "-i", BASE, "-c:v", "libx264", "-crf", "17", "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p", "-c:a", "copy", os.path.join(PROJ, "assets", "base.mp4")], check=True)
DUR = round(float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(PROJ, "assets", "base.mp4")], capture_output=True, text=True).stdout) - 0.05, 2)
shutil.copy(r"C:\Windows\Fonts\verdanab.ttf", os.path.join(PROJ, "assets", "fonts", "verdana-bold.ttf"))

EF = bool(cfg.get("efectos"))
sets, js, sfx_t = [], [], []
for i, c in enumerate(cfg.get("collages", [])):
    p = "k%d" % i; t0 = max(tiempo(c["ancla"], c.get("n", 1)) - 0.15, 0); dur = c.get("dur", 2.6)
    cards = ""
    for pos, clave in (("l", "izq"), ("r", "der"), ("c", "centro")):
        rel = c[clave]; nom = os.path.basename(rel) if os.path.isabs(rel) else rel.replace("/", "_")
        origen = rel if os.path.isabs(rel) else os.path.join(FOTOS, rel.replace("/", os.sep))     # ruta absoluta (p. ej. en _operacion\recursos) o relativa a dianchi\entrada\imagenes\fotos
        shutil.copy(origen, os.path.join(PROJ, "assets", "fotos", nom))
        cards += '      <div id="%s-%s" class="card %s"><img src="assets/fotos/%s" /></div>\n' % (p, pos, pos, nom)
    if EF: cards += '      <div id="%s-st" class="star"></div>\n' % p
    sets.append('    <div id="s-%s" class="clip set" data-start="%.2f" data-duration="%.2f" data-track-index="1">\n%s    </div>' % (p, t0, dur + 0.5, cards))
    rot = [(-7, 3, 8), (7, -3, -8), (-8, 2, 7)][i % 3]
    js.append("collage(%s, %.2f, %d, %d, %d, %.2f);" % (json.dumps(p), t0 + 0.05, rot[0], rot[1], rot[2], dur))
    if EF: js.append('tl.fromTo("#%s-st", { scale: 0, rotation: -120 }, { scale: 1, rotation: 14, duration: 0.5, ease: "back.out(3)" }, %.2f);\ntl.to("#%s-st", { scale: 0, opacity: 0, duration: 0.2, ease: "power2.in" }, %.2f);' % (p, t0 + 0.7, p, t0 + dur + 0.05))
    sfx_t += [(t0 + 0.2, -.6), (t0 + 0.3, .6), (t0 + 0.4, 0)]

# grupos de pildoras: "pildoras" (+ "pildoras_hasta") y opcionalmente "pildoras2" (+ "pildoras2_hasta"), "pildoras3"...
for gi, (clave, hasta) in enumerate((("pildoras", "pildoras_hasta"), ("pildoras2", "pildoras2_hasta"), ("pildoras3", "pildoras3_hasta"))):
    pil = cfg.get(clave, [])
    if not pil: continue
    px = "x%d" % gi
    t_ini = [tiempo(x["ancla"], x.get("n", 1)) for x in pil]; fin = (tiempo(cfg[hasta]) - 0.4) if cfg.get(hasta) else t_ini[-1] + cfg.get("pildoras_fin", 1.2)
    cuerpo = "".join('      <div id="%s-%d" class="cap" style="top:%dpx">%s%s</div>\n' % (px, k, cfg.get("pildoras_top", 440) + cfg.get("pildoras_paso", 140) * k, x["texto"], '<i class="sh"></i>' if EF else "") for k, x in enumerate(pil))
    sets.append('    <div id="s-%s" class="clip set" data-start="%.2f" data-duration="%.2f" data-track-index="1">\n%s    </div>' % (px, t_ini[0] - 0.1, fin - t_ini[0] + 0.5, cuerpo))
    for k, t in enumerate(t_ini):
        if EF:
            js.append('tl.fromTo("#%s-%d", { scale: 0.5, rotation: -4, y: 30, opacity: 0 }, { scale: 1, rotation: 0, y: 0, opacity: 1, duration: 0.5, ease: "back.out(2.4)" }, %.2f);' % (px, k, t - 0.05))
            js.append('tl.fromTo("#%s-%d .sh", { x: -300 }, { x: 1250, duration: 0.7, ease: "power2.inOut" }, %.2f);' % (px, k, t + 0.2))
        else:
            js.append('tl.fromTo("#%s-%d", { x: -140, opacity: 0 }, { x: 0, opacity: 1, duration: 0.4, ease: "power4.out" }, %.2f);' % (px, k, t - 0.05))
        sfx_t.append((t, 0))
    js.append("[%s].forEach((s) => tl.to(s, { opacity: 0, filter: \"blur(8px)\", duration: 0.2, ease: \"power2.in\" }, %.2f));" % (",".join('"#%s-%d"' % (px, k) for k in range(len(pil))), fin))


cz = cfg.get("cierre")
if cz:
    tz = max(tiempo(cz["ancla"], cz.get("n", 1)) - 0.1, 0); lineas = "<br>".join(cz["texto"].split("|"))
    sets.append('    <div id="s-z" class="clip set" data-start="%.2f" data-duration="%.2f" data-track-index="1">\n      <div id="z-card" class="cierre"><div id="z-bm" class="%s"></div><div class="zt">%s</div></div>\n    </div>' % (tz, DUR - tz - 0.05, cz.get("icono", "bm"), lineas))
    js.append('tl.fromTo("#z-card", { y: 90, scale: 0.85, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, %.2f);' % tz)
    js.append('tl.fromTo("#z-bm", { scale: 1 }, { scale: 1.18, duration: 0.14, yoyo: true, repeat: 1, ease: "power2.out" }, %.2f);' % (tz + 0.7))
    sfx_t += [(tz + 0.1, 0), (tz + 0.75, 0)]

colage = """<template>
  <style>
    @font-face { font-family: "VerdanaB"; src: url("assets/fonts/verdana-bold.ttf"); font-weight: 700; }
    #root { position: absolute; inset: 0; font-family: "VerdanaB", sans-serif; }
    .set { position: absolute; left: 0; top: 0; width: 1080px; height: 1000px; }
    .card { position: absolute; border-radius: 30px; border: 11px solid #fff; overflow: hidden; background: #fff; box-shadow: 0 22px 50px rgba(0,0,0,.5); }
    .card img { width: 100%%; height: 100%%; object-fit: cover; display: block; }
    .c { left: 305px; top: 370px; width: 470px; height: 470px; z-index: 3; }
    .l { left: 30px; top: 490px; width: 350px; height: 350px; z-index: 1; }
    .r { left: 700px; top: 460px; width: 350px; height: 350px; z-index: 2; }
    .cierre { position: absolute; left: 190px; top: 420px; width: 700px; padding: 34px 20px; text-align: center; background: rgba(255,255,255,.96); color: #1d0f19; border-radius: 40px; box-shadow: 0 24px 56px rgba(0,0,0,.5); }
    .cal { width: 116px; height: 108px; margin: 0 auto 16px; border-radius: 18px; border: 7px solid #D61480; background: linear-gradient(#D61480 0 34px, #fff 34px); }
    .sig { width: 108px; height: 108px; margin: 0 auto 16px; border-radius: 50%%; background: linear-gradient(#fff,#fff) center/54px 10px no-repeat, linear-gradient(#fff,#fff) center/10px 54px no-repeat, #D61480; }
    .bm { width: 84px; height: 112px; margin: 0 auto 16px; background: #D61480; clip-path: polygon(0 0, 100%% 0, 100%% 100%%, 50%% 74%%, 0 100%%); }
    .zt { font-size: 52px; line-height: 1.2; }
    .star { position: absolute; left: 700px; top: 320px; width: 130px; height: 130px; z-index: 4; background: #FFD23F; clip-path: polygon(50%% 0, 61%% 35%%, 98%% 35%%, 68%% 57%%, 79%% 91%%, 50%% 70%%, 21%% 91%%, 32%% 57%%, 2%% 35%%, 39%% 35%%); }
    .sh { position: absolute; top: 0; left: 0; width: 150px; height: 100%%; background: linear-gradient(100deg, transparent, rgba(214,20,128,.30), transparent); transform: translateX(-300px) skewX(-20deg); }
    .cap { overflow: hidden; position: absolute; left: 100px; width: 880px; padding: 24px 0; text-align: center; background: rgba(255,255,255,.95); color: #26121e; border-radius: 40px; border-left: 18px solid #D61480; font-size: 46px; box-shadow: 0 12px 36px rgba(0,0,0,.45); white-space: nowrap; }
  </style>
  <div id="root" data-composition-id="collage" data-width="1080" data-height="1920">
%s
  </div>
  <script>
    const EFX = %s;
    const tl = gsap.timeline({ paused: true });
    function collage(p, t0, rotL, rotC, rotR, hold) {
      tl.fromTo("#" + p + "-l", { x: -520, rotation: rotL - 28, opacity: 0 }, { x: 0, rotation: rotL, opacity: 1, duration: 0.55, ease: "power4.out" }, t0);
      tl.fromTo("#" + p + "-r", { x: 520, rotation: rotR + 28, opacity: 0 }, { x: 0, rotation: rotR, opacity: 1, duration: 0.55, ease: "power4.out" }, t0 + 0.1);
      tl.fromTo("#" + p + "-c", { y: 420, scale: 0.55, rotation: rotC - 10, opacity: 0 }, { y: 0, scale: 1, rotation: rotC, opacity: 1, duration: 0.6, ease: "back.out(1.4)" }, t0 + 0.2);
      if (EFX) {
        tl.to("#" + p + "-c", { y: -14, rotation: rotC + 1.6, duration: hold - 0.85, ease: "sine.inOut" }, t0 + 0.75);
        tl.to("#" + p + "-l", { x: 10, y: 6, rotation: rotL - 1.4, duration: hold - 0.85, ease: "sine.inOut" }, t0 + 0.75);
        tl.to("#" + p + "-r", { x: -10, y: -6, rotation: rotR + 1.4, duration: hold - 0.85, ease: "sine.inOut" }, t0 + 0.75);
      }
      ["l", "r", "c"].forEach((k) => tl.to("#" + p + "-" + k, { scale: 0.88, opacity: 0, filter: "blur(8px)", duration: 0.22, ease: "power2.in" }, t0 + hold));
    }
    %s
    window.__timelines["collage"] = tl;
  </script>
</template>
""" % ("\n".join(sets), "true" if EF else "false", "\n    ".join(js))
open(os.path.join(PROJ, "compositions", "collage.html"), "w", encoding="utf-8").write(colage)

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
      <div id="collage" data-composition-id="collage" data-composition-src="compositions/collage.html" data-start="0" data-duration="%(d)s" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
      <audio id="sfx" src="assets/sfx.wav" data-start="0" data-duration="%(d)s" data-track-index="2" data-volume="0.5"></audio>
MENTOR_HTML
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
MENTOR_JS
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""" % {"d": DUR}
# mentor sin fondo (WebM con alfa) abajo a la derecha, ocupando 3/4 del alto de la pantalla, solo mientras dura su frase inicial; va mudo (el audio ya esta en el video base)
mh = cfg.get("mentor"); m_html = m_js = ""
if mh:
    shutil.copy(mh["webm"], os.path.join(PROJ, "assets", "mentor_recorte.webm"))
    mw = int(1080 * mh.get("escala", 0.62)); mhgt = int(1920 * mh.get("escala", 0.62))
    m_html = ('      <div id="mentor-wrap" style="position:absolute; right:0; bottom:0; width:%dpx; height:%dpx;">\n'
              '        <video id="mentor" class="clip" src="assets/mentor_recorte.webm" data-start="0" data-duration="%.2f" data-track-index="3" muted playsinline style="width:100%%; height:100%%; object-fit:contain;"></video>\n'
              '      </div>' % (mw, mhgt, mh["dur"]))
    m_js = ('      tl.fromTo("#mentor-wrap", { x: 320, opacity: 0 }, { x: 0, opacity: 1, duration: 0.4, ease: "power4.out" }, 0.05);\n'
            '      tl.to("#mentor-wrap", { x: 320, opacity: 0, duration: 0.3, ease: "power2.in" }, %.2f);' % (mh["dur"] - 0.3))
ef_html = ef_js = ""
if EF:
    ef_html = ('      <div id="flash" style="position:absolute; inset:0; background:#fff; opacity:0; pointer-events:none;"></div>\n'
               '      <div id="bar" style="position:absolute; left:0; top:0; width:1080px; height:10px; background:#D61480; transform-origin:left center;"></div>')
    for t in cfg.get("cortes", []):
        ef_js += '      tl.fromTo("#base", { scale: 1.06 }, { scale: 1, duration: 0.3, ease: "power3.out", immediateRender: false }, %.2f);\n' % max(t - 0.02, 0)
        ef_js += '      tl.fromTo("#flash", { opacity: 0.35 }, { opacity: 0, duration: 0.2, ease: "power1.out", immediateRender: false }, %.2f);\n' % max(t - 0.02, 0)
    ef_js += '      tl.fromTo("#bar", { scaleX: 0 }, { scaleX: 1, duration: %.2f, ease: "none" }, 0);\n' % DUR
index = index.replace("MENTOR_HTML", m_html + ("\n" + ef_html if ef_html else "")).replace("MENTOR_JS", m_js + ("\n" + ef_js if ef_js else ""))
open(os.path.join(PROJ, "index.html"), "w", encoding="utf-8").write(index)

SR = 44100; out = np.zeros((int((DUR + 1) * SR), 2), np.float32)
for k, (t, pan) in enumerate(sfx_t):
    n = int(.16 * SR); tt = np.arange(n) / SR; f = 420 + 35 * (k % 4) + 550 * (1 - np.exp(-tt * 30)); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 26) * .5
    i = int(max(t, 0) * SR); x = x[: len(out) - i]; a = (pan + 1) * np.pi / 4
    out[i:i + len(x), 0] += x * np.cos(a); out[i:i + len(x), 1] += x * np.sin(a)
with wave.open(os.path.join(PROJ, "assets", "sfx.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
print("proyecto listo:", PROJ, "| duracion", DUR, "| collages", len(cfg.get("collages", [])), "| pildoras", len(pil))
