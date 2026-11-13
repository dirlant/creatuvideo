"""Crea clips verticales (30-90 s) de un video largo grabado en una clase (presentador al fondo, alumnas en primer plano).

Igual que crear_clips.py (silencios fuera, cambio de plano cada ~4 s, seguimiento con YOLO) pero:
- los tramos vienen de un JSON: [{"n": 1, "titulo": "...", "rangos": [[ini, fin], ...]}]
- el presentador es pequeno: se detecta en cuadros de 540x960 y el de la cabeza mas arriba es el presentador
- los planos de apoyo son de las alumnas y del asistente de espaldas (la sala), no del oyente unico
Uso: python crear_clips_v2.py <ffmpeg.exe> <video> <transcripcion.json> <carpeta_salida> <clips.json> [--solo 1,3]
"""
import json, os, random, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from ultralytics import YOLO

FF, VIDEO, TRANS, OUT, DEFS = sys.argv[1:6]
SOLO = [int(x) for x in sys.argv[sys.argv.index("--solo") + 1].split(",")] if "--solo" in sys.argv else None
TMP = os.path.join(os.path.dirname(os.path.abspath(TRANS)), "tmp_clips"); os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SW, SH = 720, 1280
GAP, MAXDUR = 0.35, 89.0
CLIPS = [(c["n"], c["titulo"], c["rangos"]) for c in json.load(open(DEFS, encoding="utf-8-sig"))]

PAL = []
for seg in json.load(open(TRANS, encoding="utf-8")):
    PAL += [(w["w"].strip(), w["s"], w["e"]) for w in seg["words"]]
FIN = lambda i: PAL[i][0].endswith((".", "?", "!"))

def ajustar(a, b):
    ini = [i for i in range(len(PAL)) if a - 2 <= PAL[i][1] <= a + 3 and (i == 0 or FIN(i - 1))]
    if ini: a = PAL[min(ini, key=lambda i: abs(PAL[i][1] - a))][1]
    fin = [i for i in range(len(PAL)) if b - 3 <= PAL[i][2] <= b + 3 and FIN(i)]
    if fin: b = PAL[min(fin, key=lambda i: abs(PAL[i][2] - b))][2]
    return a, b

def rachas(a, b):
    ws = [w for w in PAL if w[1] >= a - 0.05 and w[2] <= b + 0.05]; out = []
    for w in ws:
        if out and w[1] - out[-1][1] <= GAP: out[-1][1] = w[2]
        else: out.append([w[1], w[2]])
    res = []
    for s, e in out:
        s2 = s - 0.05; e2 = e + 0.12
        if res and s2 < res[-1][1]: s2 = res[-1][1]
        if e2 - s2 >= 0.25: res.append([s2, e2])
    return res

def plan_clip(rangos):
    runs = []
    for a, b in rangos:
        a, b = ajustar(a, b); runs += rachas(a, b)
    while runs and sum(e - s for s, e in runs) > MAXDUR: runs.pop()
    return runs

modelo = YOLO(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "por-cortar", "_operacion", "clips_trabajo", "yolov8n.pt"))
def seguimiento(runs):
    a, b = min(r[0] for r in runs) - 0.5, max(r[1] for r in runs) + 0.5
    raw = subprocess.run([FF, "-v", "error", "-ss", "%.2f" % max(a, 0), "-to", "%.2f" % b, "-i", VIDEO, "-vf", "fps=3,scale=540:960",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8); n = len(fr) // (540 * 960 * 3); fr = fr[: n * 540 * 960 * 3].reshape(n, 960, 540, 3)
    k4 = SW / 540.0; det = []
    for k in range(n):
        r = modelo(fr[k], imgsz=960, classes=[0], conf=0.2, verbose=False)[0]
        cajas = [tuple(v for v in bx.xyxy[0].tolist()) for bx in r.boxes]
        cajas = [c for c in cajas if (c[3] - c[1]) > 100 and c[1] < 420]     # el presentador: persona de pie con la cabeza arriba
        if cajas:
            x1, y1, x2, y2 = min(cajas, key=lambda c: c[1])
            det.append((max(a, 0) + k / 3.0, (x1 + x2) / 2 * k4, y1 * k4, y2 * k4))
    return det

TIPOS = ["MEDIO_AMPLIO", "MEDIO", "AMPLIO", "CLOSE", "MEDIO_D", "CLOSE_I", "MEDIO_AMPLIO", "CLOSE_D"]
ANCHO = {"MEDIO_AMPLIO": 630, "MEDIO": 540, "AMPLIO": 720, "CLOSE": 460, "MEDIO_D": 520, "CLOSE_I": 440, "CLOSE_D": 440}
SALA = {"SALA_ESPALDA": (110, 445, 520), "SALA_IZQ": (0, 445, 400), "SALA_DER": (320, 420, 400)}   # (x, y, ancho) del plano de apoyo

def planos(runs, rnd):
    T = sum(e - s for s, e in runs); cortes = []; t = 0
    for s, e in runs: t += e - s; cortes.append(t)
    shots, t0, k, sala = [], 0.0, 0, 0
    while t0 < T - 0.1:
        es_sala = k in (2, 7, 12)
        objetivo = t0 + (2.0 if es_sala else rnd.uniform(3.4, 4.6))
        cand = [c for c in cortes if abs(c - objetivo) <= 0.7 and c > t0 + 1.5]
        t1 = min(cand, key=lambda c: abs(c - objetivo)) if cand else objetivo
        if T - t1 < 2.2: t1 = T
        if es_sala: tipo = list(SALA)[sala % 3]; sala += 1
        else: tipo = TIPOS[(k - sum(1 for q in (2, 7, 12) if q < k)) % len(TIPOS)]
        shots.append((t0, min(t1, T), tipo)); t0 = t1; k += 1
    return shots, T

def fuente(runs, t):
    acu = 0
    for s, e in runs:
        if t <= acu + (e - s): return s + (t - acu)
        acu += e - s
    return runs[-1][1]

def recorte(tipo, cx, y1):
    if tipo in SALA:
        x, y, w = SALA[tipo]; h = w * 16 / 9
    else:
        w = ANCHO[tipo]; h = w * 16 / 9
        off = {"MEDIO_D": -70, "CLOSE_I": 60, "CLOSE_D": -60}.get(tipo, 0)
        x = cx + off - w / 2; y = (SH - h) / 2 if tipo == "AMPLIO" else y1 - (0.30 if w >= 600 else 0.20) * h
    x = max(0, min(SW - w, x)); y = max(0, min(SH - h, y))
    return int(w) // 2 * 2, int(h) // 2 * 2, int(x) // 2 * 2, int(y) // 2 * 2

def render(n, titulo, runs, shots, det, dest):
    a0 = max(min(r[0] for r in runs) - 1, 0); b0 = max(r[1] for r in runs) + 1
    corte = os.path.join(TMP, "corte_%02d.mp4" % n)
    N = len(runs); vf = ["[0:v]fps=30,format=yuv420p,split=%d%s" % (N, "".join("[s%d]" % i for i in range(N)))]
    af = ["[0:a]asplit=%d%s" % (N, "".join("[b%d]" % i for i in range(N)))]
    for i, (s, e) in enumerate(runs):
        vf.append("[s%d]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS[v%d]" % (i, s - a0, e - a0, i))
        af.append("[b%d]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=0.008,afade=t=out:st=%.3f:d=0.008[a%d]" % (i, s - a0, e - a0, max(e - s - 0.008, 0), i))
    cc = "".join("[v%d][a%d]" % (i, i) for i in range(N)) + "concat=n=%d:v=1:a=1[v][a]" % N
    subprocess.run([FF, "-y", "-v", "error", "-ss", "%.3f" % a0, "-to", "%.3f" % b0, "-i", VIDEO, "-filter_complex", ";".join(vf + af + [cc]),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-c:a", "pcm_s16le", corte], check=True)
    K = len(shots); vf = ["[0:v]split=%d%s" % (K, "".join("[x%d]" % i for i in range(K)))]
    for i, (t0, t1, tipo) in enumerate(shots):
        d_ = [p for p in det if fuente(runs, t0) - 0.2 <= p[0] <= fuente(runs, t1) + 0.2] or sorted(det, key=lambda p: abs(p[0] - fuente(runs, (t0 + t1) / 2)))[:3]
        cx = statistics.median(p[1] for p in d_); y1 = statistics.median(p[2] for p in d_)
        w, h, x, y = recorte(tipo, cx, y1); D = max(t1 - t0, 0.5)
        vf.append("[x%d]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,crop=%d:%d:%d:%d,"
                  "scale=w='trunc(1080*(1+0.06*t/%.2f)/2)*2':h='trunc(1920*(1+0.06*t/%.2f)/2)*2':eval=frame:flags=lanczos,"
                  "crop=1080:1920,setsar=1,unsharp=5:5:0.7:5:5:0.0,format=yuv420p[p%d]" % (i, t0, t1, w, h, x, y, D, D, i))
    vf.append("".join("[p%d]" % i for i in range(K)) + "concat=n=%d:v=1:a=0[vout]" % K)
    vf.append("[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    subprocess.run([FF, "-y", "-v", "error", "-i", corte, "-filter_complex", ";".join(vf), "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", "30",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", dest], check=True)
    os.remove(corte)

def main():
    indice, jobs = [], []
    for n, titulo, rangos in CLIPS:
        if SOLO and n not in SOLO: continue
        runs = plan_clip(rangos); det = seguimiento(runs)
        shots, T = planos(runs, random.Random(2000 + n))
        print("clip %02d %-45s %.1f s, %d rachas, %d planos, %d detecciones" % (n, titulo, T, len(runs), len(shots), len(det)), flush=True)
        jobs.append((n, titulo, runs, shots, det, os.path.join(OUT, "%02d - %s.mp4" % (n, titulo))))
        indice.append((n, titulo, rangos, T, len(shots)))
    with ThreadPoolExecutor(3) as ex:
        futs = [(j[0], ex.submit(render, *j)) for j in jobs]
        for n, f in futs:
            try: f.result(); print("listo clip %02d" % n, flush=True)
            except Exception as e: print("FALLO clip %02d: %s" % (n, e), flush=True)
    with open(os.path.join(OUT, "indice.txt"), "a", encoding="utf-8") as f:
        for n, titulo, rangos, T, k in indice: f.write("%02d | %s | %.0f s | original %s | %d planos\n" % (n, titulo, T, ", ".join("%d-%d s" % tuple(r) for r in rangos), k))

main()
