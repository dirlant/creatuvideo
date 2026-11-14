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

def _lote_actual():                  # slugs del lote que la app pidio crear (diegao/prompt/lote_actual.txt, uno por linea)
    f = os.path.join(AG, "diegao", "prompt", "lote_actual.txt")
    try: return [l.strip() for l in open(f, encoding="utf-8") if l.strip() and not l.startswith("#")]
    except OSError: return []

if __name__ == "__main__":
    _LOTE = [] if SOLO or MODO == "listar" else _lote_actual()
    vs = [v for v in V if (v["slug"] in SOLO if SOLO else (v["slug"] in _LOTE if _LOTE else True))]
    if MODO == "listar":
        print(json.dumps([{"slug": v["slug"], "rubro": v["rubro"], "titulo": " ".join(v["titulo"]).replace("*", "")} for v in V], ensure_ascii=False))
    elif MODO == "preparar":
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
