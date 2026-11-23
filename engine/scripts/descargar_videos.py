r"""Descarga videos verticales libres de Pexels para usar como B-roll.
Uso: python descargar_videos.py <carpeta_salida> "<busqueda en ingles>" [cantidad=3] [prefijo]
Clave: PEXELS_API_KEY o agente\_operacion\pexels.key. Guarda un indice.json con autor y URL de cada video (licencia Pexels: uso comercial, sin atribucion obligatoria).
Variables opcionales: PEXELS_EVITAR (palabras, separadas por coma, que no pueden aparecer en la descripcion del video) y
PEXELS_REUSAR=1 (si ya no queda nada nuevo, permite repetir clips que usaron OTROS videos; nunca los de esta misma carpeta)."""
import glob, json, os, sys, urllib.error, urllib.parse, urllib.request
OUT, Q = os.path.abspath(sys.argv[1]), sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 3
PRE = sys.argv[4] if len(sys.argv) > 4 else Q.split()[0]
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try: KEY = os.environ.get("PEXELS_API_KEY") or open(os.path.join(AG, "_operacion", "pexels.key")).read().strip()
except OSError:
    print("Falta la clave de Pexels (Ajustes)", file=sys.stderr); sys.exit(2)
H = {"Authorization": KEY, "User-Agent": "agente-videos"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=120).read()
os.makedirs(OUT, exist_ok=True); ip = os.path.join(OUT, "indice.json")
idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else []
REUSAR = os.environ.get("PEXELS_REUSAR") == "1"
EVITAR = [w.strip().lower() for w in (os.environ.get("PEXELS_EVITAR") or "").split(",") if w.strip()]

def buscar(pagina):
    try: return json.loads(get("https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": Q, "per_page": 40, "page": pagina, "orientation": "portrait", "size": "medium"})))
    except urllib.error.HTTPError as ex:
        print("Pexels respondio con error %s (%s)" % (ex.code, "la clave no es valida" if ex.code in (401, 403) else "demasiadas solicitudes: espera un rato" if ex.code == 429 else ex.reason), file=sys.stderr); sys.exit(2)
    except Exception as ex:
        print("No se pudo consultar Pexels (hay internet?): %s" % str(ex)[:150], file=sys.stderr); sys.exit(2)

propios = {i["id"] for i in idx}; hechos = set(propios); k = 0
if not REUSAR:                                      # clips ya usados por otros videos: no se repiten (salvo PEXELS_REUSAR=1)
    for otro in glob.glob(os.path.join(os.path.dirname(OUT), "*", "indice.json")):
        hechos |= {i["id"] for i in json.load(open(otro, encoding="utf-8"))}
    for otro in (glob.glob(os.path.join(AG, "dianchi", "entrada", "videos", "*", "indice.json")) + glob.glob(os.path.join(AG, "dianchi", "_operacion", "recursos", "**", "indice.json"), recursive=True)
                 + glob.glob(os.path.join(AG, "diegao", "_operacion", "recursos", "**", "indice.json"), recursive=True)):
        hechos |= {i["id"] for i in json.load(open(otro, encoding="utf-8"))}
for pagina in (1, 2, 3):                            # si los primeros resultados ya estan usados, se miran los siguientes
    r = buscar(pagina); vs = r.get("videos", [])
    if not vs: break
    for v in vs:
        if k >= N: break
        if v["id"] in hechos or v["duration"] < 5: continue
        if any(w in (v.get("url") or "").lower() for w in EVITAR): continue      # la URL de Pexels lleva la descripcion del video
        fs = [f for f in v["video_files"] if f.get("height") and f["height"] >= f["width"] and 700 <= f["width"] <= 1100 and f["file_type"] == "video/mp4"]
        if not fs: continue
        f = sorted(fs, key=lambda f: abs(f["width"] - 1080))[0]
        nom = "%s-%d.mp4" % (PRE, v["id"])
        open(os.path.join(OUT, nom), "wb").write(get(f["link"]))
        idx.append({"id": v["id"], "archivo": nom, "busqueda": Q, "duracion": v["duration"], "ancho": f["width"], "alto": f["height"], "autor": v["user"]["name"], "url": v["url"], "licencia": "Pexels"}); k += 1; hechos.add(v["id"])
        print(nom, v["duration"], "s", f["width"], "x", f["height"])
    if k >= N: break
json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
