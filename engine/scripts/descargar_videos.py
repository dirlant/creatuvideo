r"""Descarga videos verticales libres de Pexels para usar como B-roll.
Uso: python descargar_videos.py <carpeta_salida> "<busqueda en ingles>" [cantidad=3] [prefijo]
Clave: PEXELS_API_KEY o agente\_operacion\pexels.key. Guarda un indice.json con autor y URL de cada video (licencia Pexels: uso comercial, sin atribucion obligatoria)."""
import json, os, sys, urllib.parse, urllib.request
OUT, Q = os.path.abspath(sys.argv[1]), sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 3
PRE = sys.argv[4] if len(sys.argv) > 4 else Q.split()[0]
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KEY = os.environ.get("PEXELS_API_KEY") or open(os.path.join(AG, "_operacion", "pexels.key")).read().strip()
H = {"Authorization": KEY, "User-Agent": "agente-videos"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=120).read()
os.makedirs(OUT, exist_ok=True); ip = os.path.join(OUT, "indice.json")
idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else []
r = json.loads(get("https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": Q, "per_page": 20, "orientation": "portrait", "size": "medium"})))
hechos = {i["id"] for i in idx}; k = 0
import glob
for otro in glob.glob(os.path.join(os.path.dirname(OUT), "*", "indice.json")):
    hechos |= {i["id"] for i in json.load(open(otro, encoding="utf-8"))}
for otro in glob.glob(os.path.join(AG, "dianchi", "entrada", "videos", "*", "indice.json")) + glob.glob(os.path.join(AG, "dianchi", "_operacion", "recursos", "**", "indice.json"), recursive=True) + glob.glob(os.path.join(AG, "diegao", "_operacion", "recursos", "**", "indice.json"), recursive=True):
    hechos |= {i["id"] for i in json.load(open(otro, encoding="utf-8"))}
for v in r.get("videos", []):
    if k >= N: break
    if v["id"] in hechos or v["duration"] < 5: continue
    fs = [f for f in v["video_files"] if f.get("height") and f["height"] >= f["width"] and 700 <= f["width"] <= 1100 and f["file_type"] == "video/mp4"]
    if not fs: continue
    f = sorted(fs, key=lambda f: abs(f["width"] - 1080))[0]
    nom = "%s-%d.mp4" % (PRE, v["id"])
    open(os.path.join(OUT, nom), "wb").write(get(f["link"]))
    idx.append({"id": v["id"], "archivo": nom, "busqueda": Q, "duracion": v["duration"], "ancho": f["width"], "alto": f["height"], "autor": v["user"]["name"], "url": v["url"], "licencia": "Pexels"}); k += 1
    print(nom, v["duration"], "s", f["width"], "x", f["height"])
json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
