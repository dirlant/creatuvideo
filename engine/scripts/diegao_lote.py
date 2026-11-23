r"""Lote de videos de Diegao (dolores de las duenas de salon) con cortes ALEATORIOS de 3 s de los videos del evento (agente\diegao\entrada\evento-receta).
Uso: uv run --python 3.12 --with edge-tts --with pillow --with numpy python scripts\diegao_lote.py <ffmpeg.exe> <modo> [slug ...]
Modos:  preparar -> voz + tiempos, escenas por palabra (cada ~3 s), cortes aleatorios, tarjetas del collage, config y verificacion de choques (no renderiza)
        render   -> genera cada video (hyperframes, 2 a la vez), lo pasa a H.264 y lo deja en diegao\resultado
Cada video: gancho + guion (prompt de Diegao: tu a tu, gancho afirmativo, sin cifras inventadas) + CTA "Sigueme". Datos al final de este archivo."""
import glob, json, os, random, re, shutil, subprocess, sys, unicodedata

FF = os.path.abspath(sys.argv[1]); MODO = sys.argv[2]; SOLO = sys.argv[3:]
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OPG = os.path.join(AG, "diegao", "_operacion")
EV = os.path.join(AG, "diegao", "entrada", "evento-receta")
PROXY = os.path.join(OPG, "recursos", "proxy")
REC = os.path.join(OPG, "recursos")
CFGD = os.path.join(OPG, "lote")
os.makedirs(CFGD, exist_ok=True)
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())
env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"

# ---------------------------------------------------------------- ajustes de la app (propios de Diegao)
def _ajustes():
    try: return json.load(open(os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: return {}
_AJ = _ajustes(); _PRE = _AJ.get("presets", {}); _DIRS = _AJ.get("dirs", {})
VIDEOS_PEXELS = _PRE.get("rellenoLocalDiegao") is False      # False = automatico (Pexels); por defecto: videos del evento
IMG_CARPETA = bool(_PRE.get("imagenesCollageDiegao"))
IMG_DIR = _DIRS.get("diegaoImagenes") or os.path.join(AG, "diegao", "entrada", "imagenes")
# busquedas (en ingles) de Pexels por tema; si el tema no esta, se usan las generales
BUSQUEDAS = {
    "administracion": ["woman writing in planner desk", "small business owner organizing paperwork"],
    "finanzas": ["woman counting money calculator", "business owner reviewing finances"],
    "agenda": ["woman checking calendar planner", "salon appointment booking"],
    "precios": ["woman pricing service calculator", "business owner thinking prices"],
    "estrategia": ["woman planning strategy whiteboard", "entrepreneur planning notebook"],
    "fidelizacion": ["happy client salon smiling", "woman greeting customer"],
    "atencion": ["salon receptionist welcoming client", "hairdresser talking with client"],
    "protocolos": ["salon cleaning sanitizing tools", "organized beauty salon station"],
    "estructura": ["team meeting small business women", "salon team working together"],
    "espiritualidad": ["woman meditating sunrise", "woman journaling gratitude"],
    "mentalidad": ["confident woman entrepreneur", "woman motivated looking at city"],
}
GENERALES = ["beauty salon owner woman", "woman entrepreneur working", "hairdresser salon interior"]

# ---------------------------------------------------------------- datos
# slug, rubro(chip), titulo, gancho, guion, cta, objecion (ancla, n, texto, hasta), pasos [(ancla, n, texto)], pasos_hasta
V = [
 dict(slug="administracion", buenas=[('Anota', 1), ('decidir', 1)], malas=[('quita', 1), ('tiempo', 1)], rubro="ADMINISTRACIÓN", titulo=["ADMINISTRAR NO ES", "BUROCRACIA, ES", "*control*"],
      gancho="Si no administras tu salón, tu salón te administra a ti.",
      guion="Muchas dueñas dicen que no tienen *tiempo* para administrar, que ellas solo quieren atender. Pero cada cobro sin anotar y cada gasto sin revisar te quita tranquilidad. Anota cada día lo que entra y lo que sale. Separa tu *sueldo* del dinero del negocio. Y dedica una hora fija a la semana para revisar todo. Administrar es poder decidir con información.",
      burbuja=("tiempo", 1, "“NO TENGO TIEMPO”", "atender"),
      pasos=[("Anota", 1, "1 · ANOTA TODO"), ("Separa", 1, "2 · SEPARA TU SUELDO"), ("dedica", 1, "3 · REVISA CADA SEMANA")], pasos_hasta=("decidir", 1)),
 dict(slug="finanzas", buenas=[('ganancia', 1), ('ganar', 2)], malas=[('nadie', 1), ('falla', 1)], rubro="FINANZAS", titulo=["EL PRECIO DE TU", "SERVICIO DEBE", "DEJAR *ganancia*"],
      gancho="Vender mucho no significa ganar mucho, y nadie te lo explicó.",
      guion="Hay dueñas que dicen vender *bastante* y aun así no les queda dinero. Casi nunca falla la venta, falla el cálculo. Calcula lo que gastas en productos, tiempo y local por servicio. Súmale tu *ganancia* antes de poner el precio. Y aparta una parte de cada ingreso para gastos fijos. Así dejas de vender por vender y empiezas a ganar.",
      burbuja=("bastante", 1, "“VENDO Y NO ME QUEDA”", "Casi"),
      pasos=[("Calcula", 1, "1 · CALCULA TU COSTO"), ("Súmale", 1, "2 · SUMA TU GANANCIA"), ("aparta", 1, "3 · APARTA PARA GASTOS")], pasos_hasta=("empiezas", 1)),
 dict(slug="agenda-vacia", buenas=[('promoción', 1), ('llena', 2)], malas=[('huecos', 1), ('nadie', 1)], rubro="AGENDA", titulo=["UNA AGENDA SE LLENA", "CON UNA *invitación*"],
      gancho="Publicar todos los días no llena tu agenda.",
      guion="Muchas dueñas publican a diario y aun así tienen huecos en su *agenda*. Mostrar tu trabajo no basta si nadie sabe cómo reservar. Ofrece una promoción clara para las horas libres. Escribe a tus clientas anteriores con un mensaje personal. Y deja en cada publicación una invitación simple: escríbeme para agendar. Una agenda se llena con una *invitación*, no con suerte.",
      burbuja=("publican", 1, "“PUBLICO Y NADIE AGENDA”", "Mostrar"),
      pasos=[("Ofrece", 1, "1 · PROMO HORAS LIBRES"), ("Escribe", 1, "2 · MENSAJE PERSONAL"), ("deja", 1, "3 · INVITA A AGENDAR")], pasos_hasta=("suerte", 1)),
 dict(slug="precios-baratos", buenas=[('valora', 1), ('gradual', 1)], malas=[('regateo', 1), ('miedo', 1)], rubro="PRECIOS", titulo=["COBRAR POCO TAMBIÉN", "TIENE UN *costo*"],
      gancho="Bajar tus precios no atrae clientas, atrae regateo.",
      guion="Muchas dueñas cobran poco por *miedo* a que sus clientas se vayan. Pero un precio bajo no cubre tu tiempo, tus productos ni tu descanso. Primero calcula cuánto cuesta realmente cada servicio. Explica qué incluye y por qué vale ese *precio*. Sube de forma gradual, avisando con anticipación. Quien valora tu trabajo se queda, y quien solo busca precio no era tu mercado.",
      burbuja=("miedo", 1, "“SI SUBO, SE VAN”", "Pero"),
      pasos=[("calcula", 1, "1 · CALCULA TU COSTO"), ("Explica", 1, "2 · EXPLICA EL VALOR"), ("Sube", 1, "3 · SUBE GRADUAL")], pasos_hasta=("Quien", 1)),
 dict(slug="inasistencias", buenas=[('anticipo', 1), ('respeta', 1)], malas=[('pierde', 1), ('llegan', 1)], rubro="INASISTENCIAS", titulo=["CADA HUECO VACÍO", "TE CUESTA *dinero*"],
      gancho="Una cita sin compromiso es una cita que se pierde.",
      guion="Muchas dueñas se quejan de clientas que *reservan* y no llegan. Cada hueco vacío es tiempo que no recuperas. Pide un pequeño *anticipo* para confirmar la reserva. Envía un recordatorio un día antes. Y define una política clara de cambios que tus clientas conozcan desde el inicio. Cuando la regla está clara, nadie se ofende y tu agenda se respeta.",
      burbuja=("reservan", 1, "“RESERVAN Y NO LLEGAN”", "Cada"),
      pasos=[("Pide", 1, "1 · PIDE UN ANTICIPO"), ("Envía", 1, "2 · ENVÍA RECORDATORIO"), ("define", 1, "3 · REGLAS CLARAS")], pasos_hasta=("Cuando", 1)),
 dict(slug="marketing", buenas=[('claridad', 1), ('compite', 1)], malas=[('solo', 1)], rubro="MARKETING", titulo=["PEQUEÑO NO ES", "LO MISMO QUE", "*invisible*"],
      gancho="Tu salón no necesita más seguidores, necesita más claridad.",
      guion="Muchas dueñas creen que el *marketing* es solo para salones grandes. Pero el marketing es hacer que la persona correcta entienda qué ofreces. Define a quién le quieres vender. Muestra tu trabajo con resultados reales, sin inventar nada. Cuenta cómo reservar en cada publicación. Y mantén un ritmo constante, aunque sea poco. Un salón pequeño que se comunica bien compite con cualquiera.",
      burbuja=("creen", 1, "“ES SOLO PARA GRANDES”", "Pero"),
      pasos=[("Define", 1, "1 · DEFINE A QUIÉN"), ("Muestra", 1, "2 · MUESTRA TU TRABAJO"), ("Cuenta", 1, "3 · CUENTA CÓMO RESERVAR"), ("mantén", 1, "4 · SÉ CONSTANTE")], pasos_hasta=("pequeño", 1)),
 dict(slug="publicidad-objecion", buenas=[('oferta', 1), ('rápido', 1)], malas=[('tirar', 1), ('apaga', 1)], rubro="PUBLICIDAD", titulo=["TU ANUNCIO SÍ", "TRAJO GENTE, FALLÓ", "EL *seguimiento*"],
      gancho="La publicidad no es tirar *plata*, es lo que pasa después del anuncio.",
      guion="Imagina una dueña de salón que paga anuncios un mes. Llegan *mensajes*, pero contesta horas después y no da seguimiento. Concluye que la publicidad no sirve, y la apaga. Pero el anuncio sí trajo personas interesadas. Falló lo que vino después. Define una *oferta* clara. Responde rápido. Haz *seguimiento* a cada mensaje. Y mide cuántos escribieron y cuántos agendaron.",
      burbuja=("publicidad", 2, "“LA PUBLICIDAD NO SIRVE”", "apaga"),
      pasos=[("Define", 1, "1 · OFERTA CLARA"), ("Responde", 1, "2 · RESPONDE RÁPIDO"), ("Haz", 1, "3 · DA SEGUIMIENTO"), ("mide", 1, "4 · MIDE RESULTADOS")], pasos_hasta=("agendaron", 1)),
]
# ---------------------------------------------------------------- guiones creados por la app con la API de ChatGPT (diegao/prompt/guiones_nuevos.json)
GN_F = os.path.join(AG, "diegao", "prompt", "guiones_nuevos.json")
def _v_de_json(d):
    return dict(slug=d["slug"], buenas=[tuple(x) for x in d.get("buenas", [])], malas=[tuple(x) for x in d.get("malas", [])], rubro=d["rubro"], titulo=list(d["titulo"]),
                gancho=d["gancho"], guion=d["guion"], burbuja=tuple(d["burbuja"]), pasos=[tuple(x) for x in d["pasos"]], pasos_hasta=tuple(d["pasos_hasta"]))
def _cargar_extra():
    try: arr = json.load(open(GN_F, encoding="utf-8"))
    except Exception: return []
    out = []
    for d in arr:
        try: out.append(_v_de_json(d))
        except Exception: pass
    return out
_ya = {v["slug"] for v in V}
V.extend([x for x in _cargar_extra() if x["slug"] not in _ya])

CTA = "Sígueme para más ideas para tu negocio."

def sh(cmd, **kw):
    kw.setdefault("env", env)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)

def dims(p):
    r = sh([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", p])
    j = json.loads(r.stdout); return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])

def pool():
    """Videos fuente (diegao/entrada/evento-receta, cualquier subcarpeta): se crean proxies 540p la primera vez y se usan solo los verticales."""
    fuentes = []
    for ext in ("mp4", "mov", "mkv"): fuentes += glob.glob(os.path.join(EV, "**", "*." + ext), recursive=True)
    os.makedirs(PROXY, exist_ok=True); out = []
    for src in sorted(fuentes):
        n = os.path.splitext(os.path.basename(src))[0]; px = os.path.join(PROXY, n + ".mp4")
        if not os.path.exists(px):
            sh([FF, "-nostdin", "-y", "-v", "error", "-i", src, "-vf", "scale=-2:540", "-an", "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", px])
        if not os.path.exists(px): continue
        w, h, d = dims(px)
        if h <= w or n == "IMG_0613" or d < 3.4: continue      # solo verticales; 0613 esta de cabeza
        out.append((src, d))
    return out

def pool_pexels(v):
    """Modo automatico: descarga de Pexels clips verticales del tema del guion (ver BUSQUEDAS) y los devuelve como (ruta, duracion)."""
    if not (os.environ.get("PEXELS_API_KEY") or os.path.exists(os.path.join(AG, "_operacion", "pexels.key"))):
        sys.exit("Falta la clave de Pexels (Ajustes) o elige 'De una carpeta' en el paso 4 de Diegao.")
    base = norm(v["slug"] + " " + v.get("rubro", ""))
    qs = next((q for k, q in BUSQUEDAS.items() if k in base), []) + GENERALES
    out = os.path.join(REC, "pexels", v["slug"]); os.makedirs(out, exist_ok=True)
    for i, q in enumerate(qs[:4]):
        n = 4 if i < 2 else 3
        r = sh([sys.executable, os.path.join(AG, "scripts", "descargar_videos.py"), out, q, str(n), v["slug"][:12] + "%d" % i])
        print("pexels", v["slug"], "«" + q + "»", len(r.stdout.strip().splitlines()), "videos", flush=True)
    res = []
    for f in sorted(glob.glob(os.path.join(out, "*.mp4"))):
        try: w, h, d = dims(f)
        except Exception: continue
        if h > w and d >= 3.4: res.append((f, d))
    if not res: sys.exit("No se pudieron descargar videos de Pexels para " + v["slug"] + ". Revisa la clave y la conexion, o usa 'De una carpeta'.")
    return res

def poner_imagenes(fotos, rnd):
    """Collage con las imagenes propias (carpeta elegida en el paso 3): reemplaza las 3 tarjetas hechas con fotogramas."""
    from PIL import Image, ImageOps
    imgs = []
    for ext in ("jpg", "jpeg", "png", "webp"): imgs += glob.glob(os.path.join(IMG_DIR, "**", "*." + ext), recursive=True)
    if not imgs: print("Aviso: no hay imagenes en", IMG_DIR, "; el collage usa fotogramas de los videos.", flush=True); return
    rnd.shuffle(imgs)
    for k in range(3):
        im = ImageOps.exif_transpose(Image.open(imgs[k % len(imgs)])).convert("RGB")
        ImageOps.fit(im, (700, 700), Image.LANCZOS).save(os.path.join(fotos, "col-%d.png" % (k + 1)))

def trabajo(v): return os.path.join(OPG, "_trabajo", v["slug"])

def config(v, escenas, extra=None):
    marc = lambda s: s
    c = {"slug": v["slug"], "rubro": v["rubro"], "titulo": v["titulo"], "gancho": v["gancho"], "guion": v["guion"], "cta": CTA,
         "cinta": ["Sígueme para más ideas", "para tu negocio"], "clips_dir": "diegao/_operacion/recursos/cortes3s/" + v["slug"], "salida": "diegao/resultado", "operacion": "diegao/_operacion",
         "titulo_top": 420, "escenas": escenas, "voz": os.environ.get("CTV_VOZ", "es-MX-JorgeNeural"), "sin_whoosh": True, "sonido_cortes": True,
         "sfx": [{"tipo": "bueno", "ancla": a, "n": n} for a, n in v.get("buenas", [])] + [{"tipo": "malo", "ancla": a, "n": n} for a, n in v.get("malas", [])] + [{"tipo": "ding", "ancla": "Sígueme"}],
         "collages": [], "pildoras2": [{"ancla": a, "n": n, "texto": t} for a, n, t in v["pasos"]], "pildoras2_hasta": v["pasos_hasta"][0],
         "pildoras3": [{"ancla": v["burbuja"][0], "n": v["burbuja"][1], "texto": v["burbuja"][2]}], "pildoras3_hasta": v["burbuja"][3],
         "pildoras_top": 380, "pildoras_paso": 108, "cierre": {"ancla": "Sígueme", "texto": "SÍGUEME|PARA MÁS IDEAS|PARA TU NEGOCIO", "icono": "sig"}}
    if extra: c.update(extra)
    return c

def correr(cfgp, extra_env=None):
    e = dict(env); e.update(extra_env or {})
    return subprocess.run([sys.executable, os.path.join(AG, "scripts", "generar_dianchi.py"), FF, cfgp], capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)

def preparar(v, rnd, pl, usados):
    s = v["slug"]; W = trabajo(v); cp = os.path.join(CFGD, s + ".json")
    stub = config(v, [{"clip": "x.mp4"}]); json.dump(stub, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    r = correr(cp, {"SOLO_TIEMPOS": "1"})                                    # solo para obtener la voz y los tiempos por palabra
    if not os.path.exists(os.path.join(W, "palabras_abs.json")): sys.exit("sin tiempos: " + (r.stdout + r.stderr)[-800:])
    pal = json.load(open(os.path.join(W, "palabras_abs.json"), encoding="utf-8"))
    NW = [norm(p[0]) for p in pal]; TOT = float(re.search(r"voz ([\d.]+)s", r.stdout).group(1)) + 0.35
    idx_sig = NW.index(norm("Sígueme")); t_sig = pal[idx_sig][1]
    # escenas: una cada ~2.3-3.0 s (patron de interrupcion cada 3 s), en el inicio de una palabra; la ultima empieza en "Sigueme"
    starts = [0]
    while len(starts) < 20:
        t = 0.0 if len(starts) == 1 else pal[starts[-1]][1]
        if t_sig - t <= 3.0: break
        cand = [i for i, p in enumerate(pal) if t + 2.3 <= p[1] <= t + 3.0 and p[1] <= t_sig - 1.5 and i < idx_sig]
        if not cand: cand = [i for i, p in enumerate(pal) if p[1] > t + 1.5 and i < idx_sig][:1]
        if not cand: break
        starts.append(max(cand))
    starts.append(idx_sig)
    escenas = []; os.makedirs(os.path.join(REC, "cortes3s", s), exist_ok=True)
    for f in glob.glob(os.path.join(REC, "cortes3s", s, "*.mp4")): os.remove(f)
    for k, i in enumerate(starts):
        t0 = 0.0 if k == 0 else pal[i][1]; t1 = pal[starts[k + 1]][1] if k + 1 < len(starts) else TOT
        n = NW[:i + 1].count(NW[i]); dur = min(t1 - t0 + 0.2, 3.0)
        cand = [c for c in pl if c[0] not in usados] or pl
        src, d = rnd.choice(cand); usados.add(src)
        ss = rnd.uniform(0.2, max(0.3, d - 3.2))
        out = os.path.join(REC, "cortes3s", s, "c%02d.mp4" % k)
        rr = sh([FF, "-nostdin", "-y", "-v", "error", "-ss", "%.2f" % ss, "-i", src, "-t", "%.2f" % max(dur, 2.0), "-vf", "scale=1080:1920,fps=30", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])
        if not os.path.exists(out): sys.exit("corte fallo %s: %s" % (src, rr.stderr[-300:]))
        e = {"clip": "c%02d.mp4" % k, "inicio": 0}
        if k: e.update({"ancla": pal[i][0], "n": n})
        escenas.append(e)
    # collage con 3 cortes del propio video (fotogramas -> tarjetas)
    col = os.path.join(REC, "cortes3s", s, "_collage"); shutil.rmtree(col, ignore_errors=True); os.makedirs(col)
    for j, k in enumerate((1, len(escenas) // 2, len(escenas) - 2)): shutil.copy(os.path.join(REC, "cortes3s", s, "c%02d.mp4" % k), os.path.join(col, "col%d.mp4" % (j + 1)))
    fotos = os.path.join(REC, "cortes3s", s, "fotos")
    sh([sys.executable, os.path.join(AG, "scripts", "fotogramas_a_tarjetas.py"), FF, col, fotos, "col"])
    if IMG_CARPETA: poner_imagenes(fotos, rnd)
    hasta = v["burbuja"][3]
    for dur in (2.0, 1.6, 1.2, 0):
        extra = {}
        if dur: extra["collages"] = [{"ancla": hasta, "centro": fotos + "/col-1.png", "izq": fotos + "/col-2.png", "der": fotos + "/col-3.png", "dur": dur}]
        cfg = config(v, escenas, extra); json.dump(cfg, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        r = correr(cp, {"SOLO_TIEMPOS": "1"})
        if "CHOQUE" not in r.stdout: break
    print(r.stdout.strip(), "| collage dur", dur, flush=True)

def render(v):
    cp = os.path.join(CFGD, v["slug"] + ".json")
    log = open(os.path.join(CFGD, v["slug"] + ".log"), "w", encoding="utf-8")
    return subprocess.Popen([sys.executable, os.path.join(AG, "scripts", "generar_dianchi.py"), FF, cp], stdout=log, stderr=subprocess.STDOUT, env=env), log

# ---------------------------------------------------------------- NO REPETIR GUIONES: historial de lo ya generado + deteccion de guiones parecidos
HECHOS_F = os.path.join(OPG, "hechos.json")
def _carpeta_resultado():
    return _DIRS.get("diegaoResultado") or os.path.join(AG, "diegao", "resultado")
def hechos_leer():
    """{slug: {fecha, titulo}} de los guiones ya convertidos en video. La primera vez, si ya hay videos en la carpeta de resultados, los guiones existentes se dan por hechos (para no rehacerlos)."""
    try: return json.load(open(HECHOS_F, encoding="utf-8"))
    except Exception: pass
    base = {}
    if glob.glob(os.path.join(_carpeta_resultado(), "*.mp4")):
        import datetime; hoy = datetime.date.today().isoformat()
        base = {v["slug"]: {"fecha": hoy, "titulo": " ".join(v["titulo"]).replace("*", ""), "origen": "ya existian"} for v in V}
        json.dump(base, open(HECHOS_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return base
def hechos_marcar(v):
    import datetime
    h = hechos_leer(); h[v["slug"]] = {"fecha": datetime.date.today().isoformat(), "titulo": " ".join(v["titulo"]).replace("*", "")}
    json.dump(h, open(HECHOS_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

_STOP = set("para pero como cada esto esta estas estos solo mas muy sus tus tiene tienen hace hacen donde cuando porque aunque tambien entre sobre desde hasta una unos unas del los las que con por sin muchas duenas duena salon clientas clienta tu su".split())
def _toks(s): return {w for w in re.findall(r"[a-z]{4,}", unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()) if w not in _STOP}
def _jac(a, b): return len(a & b) / max(1, len(a | b))
def parecido(a, b):
    """Parecido entre dos guiones (0 a 1): el mayor entre el del texto del guion, el del gancho y el del titulo."""
    g = _jac(_toks(a["guion"]), _toks(b["guion"])); h = _jac(_toks(a["gancho"]), _toks(b["gancho"])); t = _jac(_toks(" ".join(a["titulo"])), _toks(" ".join(b["titulo"])))
    return max(g, h * 0.9, t * 0.9), g, h, t
UMBRAL = 0.5
def verificar_repetidos(nuevos, todos):
    """Compara cada guion nuevo con TODOS los demas de la lista (los ya generados y los de este mismo lote). Si hay repetidos, avisa y detiene."""
    malos = []; vistos = set()
    for v in nuevos:
        for o in todos:
            if o is v: continue
            k = frozenset((v["slug"], o["slug"]))
            if k in vistos: continue
            vistos.add(k)
            if o["slug"] == v["slug"]: malos.append((v["slug"], o["slug"], 1.0, "mismo slug")); continue
            s, g, h, t = parecido(v, o)
            if s >= UMBRAL: malos.append((v["slug"], o["slug"], s, "guion %d%% · gancho %d%% · título %d%%" % (g * 100, h * 100, t * 100)))
    if malos:
        print("GUIONES REPETIDOS O MUY PARECIDOS:", flush=True)
        for a, b, s, d in malos: print("  · «%s» se parece a «%s» (%d%%: %s)" % (a, b, s * 100, d), flush=True)
        sys.exit("Hay %d guion(es) repetidos o casi iguales a otros. Reescribe esos guiones con otro tema, otro gancho y otro ángulo (o quítalos de la lista) y vuelve a generar." % len(malos))
    print("Guiones: %d nuevos, ninguno repetido." % len(nuevos), flush=True)

# ---------------------------------------------------------------- ESCRIBIR LOS GUIONES con la API de ChatGPT y el prompt de Diegao (modo «guiones»)
def _json_de(v):
    return {"slug": v["slug"], "rubro": v["rubro"], "titulo": v["titulo"], "gancho": v["gancho"], "guion": v["guion"], "buenas": [list(x) for x in v["buenas"]], "malas": [list(x) for x in v["malas"]],
            "burbuja": list(v["burbuja"]), "pasos": [list(x) for x in v["pasos"]], "pasos_hasta": list(v["pasos_hasta"])}
def _ejemplo(v):
    """Un guion existente en el formato JSON que se le pide a ChatGPT (palabras ancla sin numero de repeticion)."""
    return {"slug": v["slug"], "rubro": v["rubro"], "titulo": v["titulo"], "gancho": v["gancho"], "guion": v["guion"], "buenas": [a for a, n in v["buenas"]], "malas": [a for a, n in v["malas"]],
            "objecion": {"texto": v["burbuja"][2], "ancla": v["burbuja"][0], "hasta": v["burbuja"][3]}, "pasos": [{"ancla": a, "texto": t} for a, n, t in v["pasos"]], "pasos_hasta": v["pasos_hasta"][0]}
def norm_acentos(s): return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()).strip("-")
    return s[:38].strip("-") or "guion"
def _convertir(d, existentes, max_palabras):
    """Valida lo que devolvio ChatGPT y lo pasa al formato del motor. ChatGPT escribe el guion por PARTES (intro con la objecion, frases de los pasos, cierre) y
    la app calcula sola las palabras ancla (donde aparece la objecion, donde empieza cada paso, donde terminan): asi no depende de que el modelo las acierte.
    Devuelve (v, []) o (None, [errores])."""
    err = []
    S_ = lambda x: re.sub(r"\s+", " ", str(x or "")).strip()
    gancho = S_(d.get("gancho")); intro = S_(d.get("intro")).replace("*", ""); cierre = S_(d.get("cierre")).replace("*", "")
    pasos_in = [p for p in (d.get("pasos") or []) if isinstance(p, dict) and S_(p.get("frase"))]
    if not gancho or not intro: return None, ["faltan el gancho o la intro"]
    if "?" in gancho or "¿" in gancho: err.append("el gancho no puede llevar signos de pregunta: debe ser una afirmación")
    if not 3 <= len(pasos_in) <= 4: err.append("debe haber 3 o 4 pasos, cada uno con su frase")
    if re.search(r"s[ií]gueme", intro + " " + cierre + " " + " ".join(S_(p.get("frase")) for p in pasos_in), re.I): err.append("no escribas el «Sígueme» final: la app lo agrega sola")
    # el guion se arma: intro + frase de cada paso + cierre (se anotan las posiciones de cada parte)
    partes = [intro] + [S_(p["frase"]).replace("*", "") for p in pasos_in[:4]] + ([cierre] if cierre else [])
    for k, p in enumerate(partes[:-1] if cierre else partes):
        if not re.search(r"[.!?]$", p): partes[k] = p + "."
    if cierre and not re.search(r"[.!?]$", partes[-1]): partes[-1] += "."
    titulo = [S_(x) for x in (d.get("titulo") or []) if S_(x)]
    if not 2 <= len(titulo) <= 3: err.append("el título debe tener 2 o 3 líneas")
    elif not any(re.search(r"\*[^*]+\*", x) for x in titulo):                       # reparacion: la ultima palabra del titulo pasa a ser la clave
        ult = titulo[-1].split(); ult[-1] = "*" + norm_acentos(ult[-1]).lower() + "*"; titulo[-1] = " ".join(ult)
    toks_g = [norm(w) for w in gancho.replace("*", "").split()]; n_g = len(toks_g); palabras_p = []; rangos = []
    for p in partes:
        w = p.split(); rangos.append((n_g + len(palabras_p), n_g + len(palabras_p) + len(w) - 1)); palabras_p += w
    toks = toks_g + [norm(w) for w in palabras_p]; total = len(toks)
    tope = min(68, int(max_palabras * 1.25))
    if total > tope: err.append("tiene %d palabras entre gancho y guion y el máximo es %d: acórtalo (intro más corta y frases de pasos breves)" % (total, tope))
    if total < max_palabras * 0.5: err.append("es muy corto (%d palabras): debe acercarse a %d" % (total, max_palabras))
    ob_txt = re.sub(r"[“”\"«»]", "", S_(d.get("objecion"))).upper()
    if not ob_txt: err.append("falta «objecion»: la queja típica de la dueña en 2 a 5 palabras (por ejemplo NO TENGO TIEMPO)")
    elif len(ob_txt) > 32: ob_txt = " ".join(ob_txt.split()[:5])[:32].strip()
    def n_de(i): return toks[:i + 1].count(toks[i])
    if err: return None, err
    # ancla de la objecion: la palabra mas significativa de la primera frase de la intro; termina al final de la intro
    ini_i, fin_i = rangos[0]; pal_i = palabras_p[:fin_i - n_g + 1]; cand = [(len(norm(w)), j) for j, w in enumerate(pal_i[:max(4, len(pal_i) // 2)]) if len(norm(w)) >= 5 and norm(w) not in _STOP]
    j_anc = max(cand)[1] if cand else min(1, len(pal_i) - 1); ob_anc = n_g + j_anc; ob_hasta = fin_i
    if ob_hasta <= ob_anc: ob_anc = max(n_g, ob_hasta - 1)
    pasos = []
    for k, p in enumerate(pasos_in[:4], 1):
        i0 = rangos[k][0]; etq = S_(p.get("texto")).upper(); etq = re.sub(r"^\d+\s*[·.\-)]*\s*", "", etq)
        while len(etq) > 22 and " " in etq: etq = etq.rsplit(" ", 1)[0]                       # etiqueta de la pildora: maximo ~24 caracteres con el numero
        if not etq: etq = " ".join(palabras_p[i0 - n_g:i0 - n_g + 3]).upper()
        pasos.append((palabras_p[i0 - n_g].strip(" .,;:!"), n_de(i0), "%d · %s" % (k, etq[:22])))
    k_ult = len(pasos); ph = rangos[k_ult][1]                                                  # los pasos terminan al final de la frase del ultimo paso
    def pal_en(i): return re.sub(r"^\W+|\W+$", "", palabras_p[i - n_g])
    sfx = []
    for tipo, lista in (("buenas", d.get("buenas") or []), ("malas", d.get("malas") or [])):
        for w in lista[:3]:
            wn = norm(re.sub(r"^\W+|\W+$", "", str(w)))
            i = next((q for q in range(n_g, total) if toks[q] == wn), None) if wn else None
            if i is not None and i < total - 1: sfx.append((tipo, pal_en(i), n_de(i), i))
    sfx.sort(key=lambda x: x[3]); lim = []
    for s_ in sfx:
        if not lim or s_[3] - lim[-1][3] >= 4: lim.append(s_)
    slug = _slug(d.get("slug") or " ".join(titulo)); base = slug; k = 2
    while slug in existentes: slug = "%s-%d" % (base, k); k += 1
    rubro = re.sub(r"[^A-Za-zÁÉÍÓÚÑÜáéíóúñü ]", "", S_(d.get("rubro"))).strip().upper()[:18] or "EMPRENDIMIENTO"
    v = dict(slug=slug, buenas=[(w, n) for t_, w, n, i in lim if t_ == "buenas"], malas=[(w, n) for t_, w, n, i in lim if t_ == "malas"], rubro=rubro, titulo=titulo, gancho=gancho,
             guion=" ".join(partes), burbuja=(pal_en(ob_anc), n_de(ob_anc), "“%s”" % ob_txt, pal_en(ob_hasta)), pasos=pasos, pasos_hasta=(pal_en(ph), n_de(ph)))
    return v, []

def generar_guiones():
    """Modo «guiones»: por cada combinacion pedida en la app (presets.diegaoPedido) escribe un guion con la API de ChatGPT, siguiendo el prompt de Diegao y lo que el usuario eligio
    (rubro, temática, formato, gancho, problema a resolver). Comprueba que el guion sea valido y que no repita a otro; lo guarda en guiones_nuevos.json y deja la lista del lote en lote_actual.txt."""
    import urllib.request, urllib.error
    pedido = _PRE.get("diegaoPedido") or []
    if not pedido: sys.exit("No hay nada que escribir: elige al menos un valor en cada opción del paso 1.")
    key = (_AJ.get("openaiKey") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key: sys.exit("Falta la clave de OpenAI (ChatGPT): pégala en Ajustes → Clave de OpenAI.")
    modelo = (_AJ.get("openaiModelo") or "gpt-4o-mini").strip()
    leer = lambda f, n: (open(os.path.join(AG, "diegao", "prompt", f), encoding="utf-8").read()[:n] if os.path.exists(os.path.join(AG, "diegao", "prompt", f)) else "")
    reglas = leer("diegao_mentor.md", 9000); ajustes = leer("AJUSTES.md", 9000)
    ejemplo = json.dumps({"slug": "administracion", "rubro": "ADMINISTRACIÓN", "titulo": ["ADMINISTRAR NO ES", "BUROCRACIA, ES", "*control*"], "gancho": "Si no administras tu salón, tu salón te administra a ti.",
        "intro": "Muchas dueñas dicen que no tienen tiempo para administrar, que ellas solo quieren atender. Pero cada cobro sin anotar y cada gasto sin revisar te quita tranquilidad.", "objecion": "NO TENGO TIEMPO",
        "pasos": [{"frase": "Anota cada día lo que entra y lo que sale.", "texto": "ANOTA TODO"}, {"frase": "Separa tu sueldo del dinero del negocio.", "texto": "SEPARA TU SUELDO"}, {"frase": "Y dedica una hora fija a la semana para revisar todo.", "texto": "REVISA CADA SEMANA"}],
        "cierre": "Administrar es poder decidir con información.", "buenas": ["tranquilidad"], "malas": ["gasto"]}, ensure_ascii=False, indent=1)
    sistema = ("Eres la guionista de Diegao, mentora de negocios de belleza. Escribes guiones de videos cortos para DUEÑAS de salón, siguiendo estas reglas del prompt de Diegao:\n\n" + reglas
               + "\n\nAJUSTES ACUMULADOS (se aplican siempre):\n" + ajustes
               + "\n\nFORMATO DE SALIDA (obligatorio). Responde SOLO con un objeto JSON, sin texto antes ni después, con estas claves:\n"
               '{"slug":"nombre-corto-en-minusculas","rubro":"UNA PALABRA DEL TEMA EN MAYÚSCULAS","titulo":["LÍNEA 1","LÍNEA 2","*palabra* clave"],"gancho":"afirmación contundente sin signos de pregunta",'
               '"intro":"1 o 2 frases que plantean el problema y nombran la queja típica de la dueña","objecion":"NO TENGO TIEMPO",'
               '"pasos":[{"frase":"frase completa y breve del paso 1, que empieza con un verbo en imperativo","texto":"ETIQUETA CORTA"}],"cierre":"una frase final breve y contundente",'
               '"buenas":["palabra positiva"],"malas":["palabra negativa"]}\n'
               "Reglas del formato: (1) «gancho» es la primera frase que dice la voz; no se repite en ninguna otra parte. (2) La narración completa será: gancho + intro + las frases de los pasos (en orden) + cierre, y después la app agrega sola el «Sígueme para más ideas para tu negocio»: NO lo escribas tú. "
               "(3) «objecion»: la queja de la dueña en 2 a 5 palabras, en mayúsculas, que la «intro» menciona. (4) Entre 3 y 4 pasos concretos; la «etiqueta» de cada paso va en mayúsculas y tiene MÁXIMO 20 caracteres (sin número). "
               "(5) «titulo»: 2 o 3 líneas en MAYÚSCULAS, 40 a 50 caracteres en total, con UNA palabra clave entre *asteriscos* en minúscula y sin tildes ni ñ, sin repetir el gancho. "
               "(6) «buenas» y «malas»: 1 o 2 palabras sueltas, copiadas tal cual de tus frases (positivas y negativas de verdad en su contexto). (7) Sin cifras ni resultados inventados, sin símbolos decorativos, sin descripciones visuales, español neutro y de tú. "
               "(8) Escribe frases CORTAS: respeta el máximo de palabras que se indica en el pedido, contando gancho + intro + pasos + cierre.\n\nEJEMPLO DE UN GUION YA HECHO (imita el nivel de concreción y el formato, NO el tema):\n" + ejemplo)
    nuevos = []; usados = {v["slug"] for v in V}; hechos_json = []
    try: hechos_json = json.load(open(GN_F, encoding="utf-8"))
    except Exception: pass
    def historial():
        return "\n".join("- %s · «%s» · gancho: %s" % (v["slug"], " ".join(v["titulo"]).replace("*", ""), v["gancho"]) for v in V[-70:])
    def pedir(mensajes):
        cuerpo = json.dumps({"model": modelo, "temperature": 0.9, "max_tokens": 1800, "response_format": {"type": "json_object"}, "messages": mensajes}).encode("utf-8")
        rq = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=cuerpo, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try: r = json.loads(urllib.request.urlopen(rq, timeout=150).read().decode("utf-8"))
        except urllib.error.HTTPError as ex:
            try: m = json.loads(ex.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception: m = ""
            sys.exit("La API de ChatGPT respondió con error %s: %s" % (ex.code, (m or ex.reason)[:300].replace(key, "…")))
        except Exception as ex: sys.exit("No se pudo consultar la API de ChatGPT (hace falta internet): %s" % str(ex)[:200].replace(key, "…"))
        return r["choices"][0]["message"]["content"] or ""
    print("Escribiendo %d guion(es) con ChatGPT (%s) y el prompt de Diegao…" % (len(pedido), modelo), flush=True)
    for i, it in enumerate(pedido, 1):
        dur = max(10, min(30, int(it.get("duracion") or 25))); max_pal = int(dur * 2.5) - 7          # 7 palabras ocupa el «Sígueme para más ideas para tu negocio»
        print("CTV_PROGRESO guiones %d %d %s" % (i, len(pedido), _slug(it.get("tematica") or it.get("problema") or "guion")), flush=True)
        prob = (it.get("problema") or "").strip()
        usuario = ("Escribe UN guion nuevo con estos datos del pedido:\n- Tipo de negocio de la dueña: %s\n- Temática (dolor): %s%s\n- Formato: %s → %s\n- Tipo de gancho: %s → %s\n- Objetivo de la frase final antes del «Sígueme»: %s → %s\n"
                   % (it.get("rubro", ""), (it.get("tematica") or "la que corresponda al problema indicado abajo (tú la deduces: finanzas, administración, estrategia, fidelización, atención, protocolos, estructura, espiritualidad o mentalidad)"), (" → " + it["tematica_def"]) if it.get("tematica_def") else "", it.get("formato", ""), it.get("formato_def", ""), it.get("gancho", ""), it.get("gancho_def", ""), it.get("accion", ""), it.get("accion_def", "")))
        usuario += ("- Problema a resolver (OBLIGATORIO, el guion trata exactamente de esto): %s\n" % prob) if prob else "- Problema a resolver: elige tú uno concreto y real de esa temática, distinto de los guiones ya hechos\n"
        if int(it.get("variaciones") or 1) > 1: usuario += "- Es la variación %s de %s sobre lo mismo: usa un ángulo y un gancho distintos a los otros.\n" % (it.get("variacion", 1), it.get("variaciones"))
        usuario += ("- Longitud: entre gancho y guion un MÁXIMO de %d palabras (el video dura %d segundos con el «Sígueme» final) y no menos de %d.\n\nGUIONES QUE YA EXISTEN (no repitas tema, gancho ni ideas):\n%s"
                    % (max_pal, dur, int(max_pal * 0.7), historial()))
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]; v = None; errs = []
        for intento in range(3):
            txt = pedir(msgs)
            try: d = json.loads(txt)
            except Exception: d = None
            if not isinstance(d, dict): errs = ["la respuesta no fue un JSON válido"]; v = None
            else:
                v, errs = _convertir(d, usados, max_pal)
                if v is not None:
                    otro = max(V, key=lambda o: parecido(v, o)[0]) if V else None
                    if otro is not None and parecido(v, otro)[0] >= UMBRAL:
                        errs = ["se parece demasiado (%d%%) al guion ya existente «%s»: cambia el tema, el gancho y las ideas" % (parecido(v, otro)[0] * 100, otro["slug"])]; v = None
            if v is not None: break
            print("  intento %d: %s" % (intento + 1, "; ".join(errs)[:300]), flush=True)
            msgs += [{"role": "assistant", "content": txt}, {"role": "user", "content": "Corrige estos problemas y responde de nuevo SOLO con el JSON completo:\n- " + "\n- ".join(errs)}]
        if v is None: print("  ✗ no se pudo crear el guion %d de %d (%s): se omite." % (i, len(pedido), "; ".join(errs)[:200]), flush=True); continue
        usados.add(v["slug"]); V.append(v); nuevos.append(v); hechos_json.append(_json_de(v))
        json.dump(hechos_json, open(GN_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  ✓ %s · «%s» · %d palabras" % (v["slug"], " ".join(v["titulo"]).replace("*", ""), len((v["gancho"] + " " + v["guion"]).replace("*", "").split())), flush=True)
    if not nuevos: sys.exit("No se pudo crear ningún guion nuevo. Revisa el registro.")
    os.makedirs(os.path.dirname(GN_F), exist_ok=True)
    open(os.path.join(AG, "diegao", "prompt", "lote_actual.txt"), "w", encoding="utf-8").write("\n".join(v["slug"] for v in nuevos) + "\n")
    print("Guiones nuevos creados: %d de %d (listos para preparar y generar)." % (len(nuevos), len(pedido)), flush=True)

def _lote_actual():                  # slugs del lote que la app pidio crear (diegao/prompt/lote_actual.txt, uno por linea)
    f = os.path.join(AG, "diegao", "prompt", "lote_actual.txt")
    try: return [l.strip() for l in open(f, encoding="utf-8") if l.strip() and not l.startswith("#")]
    except OSError: return []

if __name__ == "__main__":
    _LOTE = [] if SOLO or MODO == "listar" else _lote_actual()
    if MODO in ("preparar", "render") and not SOLO:
        _H = hechos_leer()                 # solo se generan los guiones NUEVOS: un guion ya convertido en video no se vuelve a hacer
        vs = [v for v in V if (v["slug"] in _LOTE if _LOTE else True) and v["slug"] not in _H]
        if not vs: sys.exit("No hay guiones nuevos para generar: los %d guiones de la lista ya se convirtieron en video. Pídele a Claude Code guiones nuevos (se le entrega el historial para que no repita) y vuelve a generar. Para rehacer uno en concreto, elígelo en «Paso a paso»." % len(V))
        print("Guiones nuevos por generar: %d (ya hechos: %d)" % (len(vs), len([1 for v in V if v["slug"] in _H])), flush=True)
    else:
        vs = [v for v in V if (v["slug"] in SOLO if SOLO else (v["slug"] in _LOTE if _LOTE else True))]
    if MODO == "listar":
        print(json.dumps([{"slug": v["slug"], "rubro": v["rubro"], "titulo": " ".join(v["titulo"]).replace("*", ""), "gancho": v["gancho"], "guion": v["guion"].replace("*", "")[:170]} for v in V], ensure_ascii=False))
    elif MODO == "verificar":
        verificar_repetidos(V, V)
    elif MODO == "guiones":
        generar_guiones()
    elif MODO == "preparar":
        verificar_repetidos(vs, V)        # antes de gastar tiempo: ¿algun guion nuevo repite a otro?
        rnd = random.Random(2611); pl = [] if VIDEOS_PEXELS else pool(); usados = set(); print("videos:", "Pexels (automatico)" if VIDEOS_PEXELS else "carpeta, %d clips verticales" % len(pl), flush=True)
        for _i, v in enumerate(vs, 1):
            print("CTV_PROGRESO preparar %d %d %s" % (_i, len(vs), v["slug"]), flush=True)   # la app lo muestra como progreso
            preparar(v, rnd, pool_pexels(v) if VIDEOS_PEXELS else pl, usados)
    elif MODO == "render":
        pend = list(vs); act = []; _k = 0
        import time
        while pend or act:
            while pend and len(act) < 2: v = pend.pop(0); _k += 1; print("CTV_PROGRESO render %d %d %s" % (_k, len(vs), v["slug"]), flush=True); act.append((v,) + render(v)); print("render", v["slug"], flush=True)
            time.sleep(10)
            for a in list(act):
                if a[1].poll() is not None: a[2].close(); act.remove(a); print("listo", a[0]["slug"], a[1].returncode, flush=True)
                if a[1].returncode == 0: hechos_marcar(a[0])
