r"""Lote de videos de rubro con guion de Dianchi (formato Vender sin vender, Emocional/Educativo, Miedos u Objeciones, CTA guardar), sin hook.
Uso (con: uv run --python 3.12 --with edge-tts --with pillow --with numpy python dianchi_lote.py <ffmpeg.exe> <modo> [slug ...]):
  verificar   -> calcula los tiempos reales de la voz y avisa de escenas muy cortas o animaciones que se pisan (no descarga nada)
  descargar   -> baja los clips de cada escena y de los collages (Pexels, sin repetir lo ya usado) a dianchi\_operacion\recursos\<slug>
  hoja        -> hoja de contacto por rubro para revisar los clips elegidos
  reemplazar <slug> <n_escena> "<busqueda>"  -> cambia el clip de una escena (n desde 0)
  render      -> arma cada video (generar_dianchi.py) y lo deja en agente\dianchi\resultado
Cada rubro: escenas = [(palabra donde cambia, n-esima aparicion, busqueda en ingles)], burbuja = frase de la clienta, A/B = grupos de pildoras (pasos), collage = 3 fotogramas."""
import glob, json, os, re, shutil, subprocess, sys, time, unicodedata
from PIL import Image, ImageDraw, ImageFont

FF = os.path.abspath(sys.argv[1]); MODO = sys.argv[2]; SOLO = sys.argv[3:]
AG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FPR = FF.replace("ffmpeg.exe", "ffprobe.exe")
OPD = os.path.join(AG, "dianchi", "_operacion"); LOTE = os.path.join(OPD, "lote"); os.makedirs(LOTE, exist_ok=True)
REC = os.path.join(OPD, "recursos")
CINTA = ["Guarda este audio y esta idea", "para tu negocio"]
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode())

# Accion que se pide al final del video (la del formulario de Dianchi). La frase final del guion debe EMPEZAR con la palabra "ancla".
CTAS = {
    "guardar":   dict(ancla="Guarda",    cinta=["Guarda este audio y esta idea", "para tu negocio"], cierre="GUARDA ESTE AUDIO|Y ESTA IDEA|PARA TU NEGOCIO", icono="bm"),
    "comentar":  dict(ancla="Comenta",   cinta=["Comenta tu experiencia", "y cuentanos tu caso"],      cierre="COMENTA|TU EXPERIENCIA|ABAJO", icono="sig"),
    "seguir":    dict(ancla="Sígueme",   cinta=["Sígueme para más ideas", "para tu negocio"],         cierre="SÍGUEME|PARA MÁS IDEAS|PARA TU NEGOCIO", icono="sig"),
    "compartir": dict(ancla="Comparte",  cinta=["Comparte este video", "con quien lo necesite"],       cierre="COMPARTE|ESTE VIDEO|CON QUIEN LO NECESITE", icono="sig"),
    "like":      dict(ancla="Dale",      cinta=["Dale like si te sirvió", "y sigue aprendiendo"],      cierre="DALE LIKE|SI TE SIRVIÓ|ESTE VIDEO", icono="sig"),
    "mensaje":   dict(ancla="Escríbeme", cinta=["Escríbeme un mensaje", "para agendar o consultar"],   cierre="ESCRÍBEME|UN MENSAJE|PARA AGENDAR", icono="sig"),
}

def R(slug, rubro, titulo, gancho, guion, cta, escenas, collage, A=None, hastaA=None, B=None, hastaB=None, bubble=None, marcar=(), sfx_ancla=None, cta_tipo="guardar", voz=None):
    return dict(slug=slug, cta_tipo=cta_tipo, voz=voz, rubro=rubro, titulo=titulo, gancho=gancho, guion=guion, cta=cta, escenas=escenas, collage=collage, A=A, hastaA=hastaA, B=B, hastaB=hastaB, bubble=bubble, marcar=marcar, sfx_ancla=sfx_ancla)

RUBROS = [
 R("cabello-keratina", "CABELLO", ["EL ALISADO SE CUIDA", "ANTES Y DESPUÉS DE", "LA *keratina*"],
   "Si crees que un alisado con keratina deja el cabello sin vida, depende de cómo se aplica y se cuida.",
   "Muchas clientas temen que se vea pesado o acartonado. Por eso primero lavamos con un shampoo clarificante, después aplicamos el producto por mechones sin tocar la raíz y por último sellamos con plancha a la temperatura adecuada. Luego te enseñamos a cuidarlo en casa. Si estás embarazada o tu cuero cabelludo es sensible, cuéntanoslo antes.",
   "Guarda este audio para recordarlo antes de tu alisado.",
   [(None, 1, "hair straightening salon keratin"), ("depende", 1, "hairdresser smoothing hair salon"), ("temen", 1, "woman touching damaged hair"), ("Primero", 1, "hairdresser washing hair client salon"), ("aplicamos", 1, "hairdresser applying hair treatment brush"), ("sellamos", 1, "hair flat iron straightening"),
    ("cuidarlo", 1, "woman shiny straight hair"), ("embarazada", 1, "hairdresser talking client salon"), ("Guarda", 1, "woman smooth hair smiling")],
   ("cuidarlo", 1, "straight shiny hair close up"),
   A=[("lavamos", "LAVAMOS A FONDO"), ("aplicamos", "POR MECHONES"), ("sellamos", "SELLAMOS CON PLANCHA")], hastaA="Luego",
   bubble=("temen", "“SE VERÁ ACARTONADO”", "Por"), marcar=("clarificante", "temperatura")),
 R("cabello-rizos", "CABELLO", ["LOS RIZOS SE CORTAN", "EN SECO Y CON", "*forma*"],
   "Cortar rizos como si fueran cabello liso es la razón por la que pierden su forma.",
   "Si te da miedo salir con el cabello esponjado o desigual, hay una técnica para eso. Primero miramos cómo cae cada rizo en seco, después cortamos mechón por mechón respetando su patrón y por último definimos con producto y difusor. Así el volumen queda parejo y los rizos mantienen su forma. Si usas tratamientos químicos o tu cuero cabelludo es sensible, avísanos antes.",
   "Guarda este audio para recordarlo antes de tu corte.",
   [(None, 1, "curly hair haircut salon"), ("pierden", 1, "woman curly hair salon"), ("miedo", 1, "woman curly hair mirror unhappy"), ("Primero", 1, "hairdresser curly hair looking"), ("cortamos", 1, "hairdresser cutting curly hair"), ("definimos", 1, "curly hair diffuser styling"),
    ("parejo", 1, "woman curly hair smiling"), ("químicos", 1, "hairdresser talking client salon"), ("Guarda", 1, "woman curls happy")],
   ("parejo", 1, "curly hair close up"),
   A=[("miramos", "MIRAMOS CADA RIZO"), ("cortamos", "CORTE MECHÓN A MECHÓN"), ("definimos", "DEFINIMOS CON DIFUSOR")], hastaA="Así",
   bubble=("miedo", "“ME QUEDARÁ ESPONJADO”", "Primero"), marcar=("técnica", "patrón")),
 R("depilacion-cera", "DEPILACIÓN", ["LA CERA SE APLICA", "CON LA PIEL LISTA", "Y SIN *prisa*"],
   "Si la depilación con cera te parece muy dolorosa, la preparación cambia todo.",
   "Muchas personas la evitan por miedo al dolor. Primero revisamos tu piel y el largo del vello, después aplicamos la cera tibia en pequeñas zonas y por último calmamos la piel con un producto suave. Así la sesión es más rápida y cómoda. Si tienes la piel irritada, usas medicamentos para la piel o estás embarazada, avísanos antes de empezar.",
   "Guarda este audio para recordarlo antes de tu próxima cita.",
   [(None, 1, "waxing salon legs hair removal"), ("preparación", 1, "esthetician talking client consultation"), ("Muchas", 1, "woman worried waxing"), ("Primero", 1, "esthetician checking skin"), ("aplicamos", 1, "wax applying skin close up"), ("calmamos", 1, "esthetician applying soothing lotion skin"),
    ("cómoda", 1, "woman relaxed salon smiling"), ("irritada", 1, "woman skin consultation beauty"), ("embarazada", 1, "beauty clinic reception client"), ("Guarda", 1, "woman smooth skin smiling")],
   ("cómoda", 1, "leg waxing salon"),
   A=[("revisamos", "REVISAMOS TU PIEL"), ("aplicamos", "CERA TIBIA POR ZONAS"), ("calmamos", "CALMAMOS LA PIEL")], hastaA="Así",
   bubble=("miedo", "“VA A DOLER MUCHÍSIMO”", "Primero"), marcar=("tibia", "cómoda")),
 R("manicure-spa", "MANOS", ["UN SPA DE MANOS", "NO ES SOLO", "*relajación*"],
   "Un spa de manos no es un lujo, es cuidar la piel que más usas.",
   "Si piensas que es solo para ocasiones especiales, mira lo que incluye. Primero exfoliamos para retirar la piel opaca, después hidratamos con crema y masaje suave y por último envolvemos tus manos en toalla tibia. Tus manos quedan suaves y descansadas. Si tienes heridas, irritación o alguna alergia a cremas, avísanos para elegir otro producto.",
   "Guarda este audio para recordarlo antes de tu próximo spa.",
   [(None, 1, "hand spa treatment salon"), ("piensas", 1, "woman thinking manicure salon"), ("Primero", 1, "hand scrub exfoliation"), ("hidratamos", 1, "hand massage cream spa"), ("envolvemos", 1, "warm towel hands spa"),
    ("descansadas", 1, "woman soft hands smiling"), ("alergia", 1, "manicurist talking client"), ("Guarda", 1, "woman hands lotion smiling")],
   ("descansadas", 1, "hand massage spa"),
   A=[("exfoliamos", "EXFOLIAMOS LA PIEL"), ("hidratamos", "CREMA Y MASAJE"), ("envolvemos", "TOALLA TIBIA")], hastaA="suaves",
   bubble=("piensas", "“ES UN LUJO INNECESARIO”", "Primero"), marcar=("exfoliamos", "suaves")),
 R("maquillaje-fiesta", "MAQUILLAJE", ["EL MAQUILLAJE DE FIESTA", "SE PRUEBA CON", "LA *luz* CORRECTA"],
   "Un maquillaje de fiesta no tiene por qué verse pesado ni desaparecer a las dos horas.",
   "Si te preocupa que en las fotos se vea diferente, lo importante es la piel. Primero preparamos con hidratación y prebase, después aplicamos la base en capas finas y por último sellamos con polvo solo donde hace falta. Así dura más y se ve natural con flash. Si tienes alergia a algún cosmético o usas lentes de contacto, cuéntanoslo antes.",
   "Guarda este audio para recordarlo antes de tu evento.",
   [(None, 1, "makeup artist party makeup"), ("desaparecer", 1, "woman applying lipstick"), ("preocupa", 1, "woman worried makeup mirror"), ("Primero", 1, "makeup artist skin prep"), ("aplicamos", 1, "makeup foundation brush face"), ("sellamos", 1, "makeup setting powder brush"),
    ("natural", 1, "woman natural makeup smiling"), ("alergia", 1, "makeup artist talking client"), ("lentes", 1, "makeup artist applying eyeliner"), ("Guarda", 1, "woman glamour makeup smiling")],
   ("natural", 1, "makeup eyeshadow close up"),
   A=[("preparamos", "PREPARAMOS LA PIEL"), ("aplicamos", "BASE EN CAPAS FINAS"), ("sellamos", "SELLAMOS CON POLVO")], hastaA="Así",
   bubble=("preocupa", "“SE VERÁ MUY PESADO”", "Primero"), marcar=("piel", "flash")),
 R("barberia-ninos", "BARBERÍA", ["EL PRIMER CORTE SE", "HACE CON PACIENCIA", "Y *calma*"],
   "Si tu hijo se asusta en la barbería, el problema casi nunca es el corte.",
   "Muchos niños temen a las tijeras y a la máquina. Por eso primero lo dejamos mirar y tocar las herramientas, después explicamos cada paso con palabras simples y por último cortamos con descansos si lo necesita. Cuando se siente seguro, el corte es más rápido. Si tiene sensibilidad al ruido o a los productos, cuéntanoslo antes.",
   "Guarda este audio para recordarlo antes de la próxima visita.",
   [(None, 1, "barber cutting kid hair"), ("problema", 1, "barber shop kid haircut"), ("temen", 1, "scared child haircut"), ("Primero", 1, "child barber chair"), ("explicamos", 1, "barber talking to child"), ("cortamos", 1, "barber trimming child hair clippers"),
    ("seguro", 1, "child smiling haircut mirror"), ("ruido", 1, "barber talking parent child"), ("Guarda", 1, "boy happy new haircut")],
   ("seguro", 1, "kid haircut barbershop"),
   A=[("dejamos", "MIRA LAS HERRAMIENTAS"), ("explicamos", "EXPLICAMOS CADA PASO"), ("cortamos", "CORTE CON DESCANSOS")], hastaA="Cuando",
   bubble=("temen", "“SE VA A ASUSTAR”", "Por"), marcar=("herramientas", "descansos")),
 R("cejas-laminado", "CEJAS", ["EL LAMINADO PEINA", "TUS CEJAS HACIA", "*arriba*"],
   "El laminado de cejas no cambia tu forma, solo ordena los pelos que ya tienes.",
   "Si te da miedo que queden artificiales, lo que cuenta es el diseño previo. Primero revisamos la dirección de tu vello, después aplicamos la solución para suavizarlo y peinarlo hacia arriba y por último fijamos y nutrimos con un aceite. El efecto dura unas semanas y se ve natural. Si tienes la piel sensible, alergias o te depilaste hace poco, avísanos antes.",
   "Guarda este audio para recordarlo antes de tu laminado.",
   [(None, 1, "eyebrow lamination brows salon"), ("ordena", 1, "woman eyebrows makeup mirror"), ("miedo", 1, "woman looking eyebrows mirror"), ("Primero", 1, "eyebrow brush combing brows"), ("aplicamos", 1, "brow lamination solution applying"), ("fijamos", 1, "brow technician close up eyebrows"),
    ("natural", 1, "woman natural brows smiling"), ("sensible", 1, "beauty technician consultation"), ("Guarda", 1, "woman eyebrows happy")],
   ("natural", 1, "eyebrows woman brows close"),
   A=[("revisamos", "REVISAMOS TU VELLO"), ("aplicamos", "SUAVIZAMOS Y PEINAMOS"), ("fijamos", "FIJAMOS Y NUTRIMOS")], hastaA="efecto",
   bubble=("miedo", "“SE VERÁN ARTIFICIALES”", "Primero"), marcar=("diseño", "vello")),
 R("cuero-cabelludo", "CABELLO", ["UN CUERO CABELLUDO", "SANO SE LIMPIA", "CON *suavidad*"],
   "Si tu cuero cabelludo se siente tirante o con picor, no siempre es culpa del shampoo.",
   "Muchas personas lo notan tarde, cuando el cabello ya se ve apagado. Primero observamos tu cuero cabelludo con calma, después hacemos una limpieza suave con masaje y por último enjuagamos y te recomendamos una rutina simple. Si el picor persiste, hay heridas o irritación fuerte, conviene que consultes con un dermatólogo.",
   "Guarda este audio para recordarlo antes de tu próximo lavado.",
   [(None, 1, "scalp treatment salon"), ("culpa", 1, "woman worried hair mirror salon"), ("notan", 1, "woman touching scalp hair"), ("Primero", 1, "hairdresser examining scalp"), ("hacemos", 1, "scalp massage shampoo"), ("enjuagamos", 1, "hair rinse salon sink"),
    ("persiste", 1, "hairdresser talking client salon"), ("consultes", 1, "woman hair smiling"), ("Guarda", 1, "woman healthy hair smiling")],
   ("heridas", 1, "scalp massage head hair"),
   A=[("observamos", "OBSERVAMOS CON CALMA"), ("hacemos", "LIMPIEZA CON MASAJE"), ("enjuagamos", "RUTINA SENCILLA")], hastaA="persiste",
   bubble=("notan", "“¿SERÁ MI SHAMPOO?”", "Primero"), marcar=("calma", "rutina")),
]

def marcado(guion, claves):
    for k in claves: guion = re.sub(r"\b(%s)\b" % re.escape(k), r"*\1*", guion, count=1)
    return guion
an = lambda a: (a, 1) if isinstance(a, str) else a       # ancla -> (palabra, n)
def item(a, t): w, n = an(a); return {"ancla": w, "n": n, "texto": t}

def config(Rr, clips_dir, fotos):
    esc = []
    for i, (a, n, q) in enumerate(Rr["escenas"]):
        e = {"clip": "s%02d.mp4" % i}                       # se reemplaza por el archivo real al descargar
        if a is not None:
            w, nn = an(a)
            if w == "Guarda": w = CTAS[Rr.get("cta_tipo") or "guardar"]["ancla"]      # la ultima escena se ancla en la palabra de la accion elegida
            e["ancla"] = w; e["n"] = nn
        esc.append(e)
    cfg = {"slug": Rr["slug"], "rubro": Rr["rubro"], "titulo": Rr["titulo"], "gancho": Rr["gancho"], "guion": marcado(Rr["guion"], Rr["marcar"]), "cta": Rr["cta"], "cinta": CTAS[Rr.get("cta_tipo") or "guardar"]["cinta"],
           "clips_dir": clips_dir, "salida": "dianchi/resultado", "operacion": "dianchi/_operacion", "efectos": os.environ.get("CTV_EFECTOS", "1") != "0", "voz": os.environ.get("CTV_VOZ", "es-MX-JorgeNeural"), "titulo_top": 420, "escenas": esc,
           "sfx": [{"tipo": "sparkle", "ancla": an(Rr["collage"][0])[0], "n": an(Rr["collage"][0])[1], "desfase": 0.1}, {"tipo": "ding", "ancla": CTAS[Rr.get("cta_tipo") or "guardar"]["ancla"]}],
           "pildoras_top": 380, "pildoras_paso": 108, "cierre": {"ancla": CTAS[Rr.get("cta_tipo") or "guardar"]["ancla"], "texto": CTAS[Rr.get("cta_tipo") or "guardar"]["cierre"], "icono": CTAS[Rr.get("cta_tipo") or "guardar"]["icono"]}}
    w, n = an(Rr["collage"][0]); cfg["collages"] = [{"ancla": w, "n": n, "centro": fotos + "/col-1.png", "izq": fotos + "/col-2.png", "der": fotos + "/col-3.png", "dur": 2.4}]
    if Rr["A"]: cfg["pildoras"] = [item(a, t) for a, t in Rr["A"]]; cfg["pildoras_hasta"] = an(Rr["hastaA"])[0]
    if Rr["B"]: cfg["pildoras2"] = [item(a, t) for a, t in Rr["B"]]; cfg["pildoras2_hasta"] = an(Rr["hastaB"])[0]
    if Rr["bubble"]:
        a, t, h = Rr["bubble"]; w, n = an(a); cfg["pildoras3"] = [{"ancla": w, "n": n, "texto": t}]; cfg["pildoras3_hasta"] = an(h)[0]
    if Rr.get("voz"): cfg["voz"] = Rr["voz"]                          # voz propia del guion (por ejemplo, otro idioma)
    ev = lambda k: os.environ.get("CTV_EV_" + k, "1") != "0"          # eventos del video activables desde la app
    if not ev("COLLAGE"): cfg["collages"] = []; cfg["sfx"] = [x for x in cfg["sfx"] if x["tipo"] != "sparkle"]
    if not ev("PASOS"):
        for k in ("pildoras", "pildoras_hasta", "pildoras2", "pildoras2_hasta"): cfg.pop(k, None)
    if not ev("BURBUJA"):
        for k in ("pildoras3", "pildoras3_hasta"): cfg.pop(k, None)
    if not ev("SFX"): cfg["sfx"] = []
    if not ev("CIERRE"): cfg.pop("cierre", None)
    return cfg

env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
def sh(cmd, **kw):
    kw.setdefault("env", env); return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
def _lote_actual():                  # slugs del lote que la app pidio crear (dianchi/prompt/lote_actual.txt, uno por linea)
    f = os.path.join(AG, "dianchi", "prompt", "lote_actual.txt")
    try: return [l.strip() for l in open(f, encoding="utf-8") if l.strip() and not l.startswith("#")]
    except OSError: return []
_LOTE = [] if SOLO or MODO == "listar" else _lote_actual()
SEL = [r for r in RUBROS if (r["slug"] in SOLO if SOLO else (r["slug"] in _LOTE if _LOTE else True))]
def prog(i, Rr):                     # la app muestra "N de M" con esta linea (no es para leer)
    print("CTV_PROGRESO %s %d %d %s" % (MODO, i, len(SEL), Rr["slug"]), flush=True)

def rutas(Rr):
    base = os.path.join(REC, Rr["slug"]); return base, os.path.join(base, "clips"), os.path.join(base, "fotos")

def ovr():
    p = os.path.join(LOTE, "reemplazos.json"); return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

def cfg_final(Rr):
    base, clips, fotos = rutas(Rr); c = config(Rr, clips, fotos.replace("\\", "/"))
    for i, e in enumerate(c["escenas"]):
        g = sorted(glob.glob(os.path.join(clips, "s%02d-*.mp4" % i)))
        if g: e["clip"] = g[0]
    return c

if MODO == "listar":
    print(json.dumps([{"slug": r["slug"], "rubro": r["rubro"], "titulo": " ".join(r["titulo"]).replace("*", "")} for r in RUBROS], ensure_ascii=False))

elif MODO == "verificar":
    for _i, Rr in enumerate(SEL, 1):
        prog(_i, Rr)
        pal = len(marcado(Rr["guion"], ()).split()); print("== %s | guion %d palabras" % (Rr["slug"], pal), flush=True)
        c = cfg_final(Rr); p = os.path.join(LOTE, Rr["slug"] + ".json"); json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        r = sh([sys.executable, os.path.join(AG, "scripts", "generar_dianchi.py"), FF, p], cwd=AG, env=dict(env, SOLO_TIEMPOS="1"))
        print((r.stdout.strip() or r.stderr[-400:]), flush=True)

def relleno_local():
    """Videos propios de relleno (carpeta dianchi/entrada/videos): lista de .mp4/.mov/.mkv"""
    out = []
    for ext in ("mp4", "mov", "mkv", "webm"): out += glob.glob(os.path.join(AG, "dianchi", "entrada", "videos", "**", "*." + ext), recursive=True)
    return [f for f in out if os.sep + "_" not in f.replace(os.path.join(AG, "dianchi", "entrada", "videos"), "")]

def cortar_local(src, dst, seg=4.5):
    import random
    d = float(sh([FPR, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]).stdout or 0)
    ss = random.uniform(0, max(d - seg, 0)) if d > seg else 0
    sh([FF, "-nostdin", "-y", "-v", "error", "-ss", "%.2f" % ss, "-i", src, "-t", "%.2f" % seg, "-an", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p", dst])
    return os.path.exists(dst)

if MODO == "descargar" and os.environ.get("CTV_RELLENO_LOCAL") == "1":
    import random
    fuentes = relleno_local(); random.shuffle(fuentes)
    if not fuentes: sys.exit("No hay videos en la carpeta de relleno (dianchi/entrada/videos). Elige una en Ajustes.")
    usados = 0
    for _i, Rr in enumerate(SEL, 1):
        prog(_i, Rr)
        base, clips, fotos = rutas(Rr); os.makedirs(os.path.join(clips, "_collage"), exist_ok=True); os.makedirs(fotos, exist_ok=True)
        for i in range(len(Rr["escenas"])):
            if glob.glob(os.path.join(clips, "s%02d-*.mp4" % i)): continue
            src = fuentes[usados % len(fuentes)]; usados += 1
            cortar_local(src, os.path.join(clips, "s%02d-local%d.mp4" % (i, usados)))
        col = os.path.join(clips, "_collage")
        if len(glob.glob(os.path.join(col, "*.mp4"))) < 3:
            for k in range(3):
                src = fuentes[usados % len(fuentes)]; usados += 1; cortar_local(src, os.path.join(col, "col-%d.mp4" % (k + 1)), 3.0)
        sh([sys.executable, os.path.join(AG, "scripts", "fotogramas_a_tarjetas.py"), FF, col, fotos, "col"])
        print("%s: %d escenas con videos de relleno propios" % (Rr["slug"], len(Rr["escenas"])), flush=True)

elif MODO == "descargar":
    ov = ovr()
    for _i, Rr in enumerate(SEL, 1):
        prog(_i, Rr)
        base, clips, fotos = rutas(Rr); os.makedirs(clips, exist_ok=True); os.makedirs(os.path.join(clips, "_collage"), exist_ok=True); os.makedirs(fotos, exist_ok=True)
        grupos = {}
        for i, (a, n, q) in enumerate(Rr["escenas"]): grupos.setdefault(ov.get(Rr["slug"], {}).get(str(i), q), []).append(i)
        for q, idxs in grupos.items():
            faltan = [i for i in idxs if not glob.glob(os.path.join(clips, "s%02d-*.mp4" % i))]
            if not faltan: continue
            antes = set(glob.glob(os.path.join(clips, "q*.mp4")))
            sh([sys.executable, os.path.join(AG, "scripts", "descargar_videos.py"), clips, q, str(len(faltan)), "q"]); time.sleep(1)
            nuevos = sorted(set(glob.glob(os.path.join(clips, "q*.mp4"))) - antes)
            for i, f in zip(faltan, nuevos): os.rename(f, os.path.join(clips, "s%02d-%s" % (i, os.path.basename(f).split("-", 1)[1])))
            print("  %s: '%s' -> %d/%d clips" % (Rr["slug"], q, len(nuevos), len(faltan)), flush=True)
        col = os.path.join(clips, "_collage")
        if len(glob.glob(os.path.join(col, "*.mp4"))) < 3:
            sh([sys.executable, os.path.join(AG, "scripts", "descargar_videos.py"), col, Rr["collage"][2], "3", "col"]); time.sleep(1)
        sh([sys.executable, os.path.join(AG, "scripts", "fotogramas_a_tarjetas.py"), FF, col, fotos, "col"])
        print("%s: %d escenas, %d collage" % (Rr["slug"], len(glob.glob(os.path.join(clips, "s*-*.mp4"))), len(glob.glob(os.path.join(fotos, "col-*.png")))), flush=True)

elif MODO == "hoja":
    fnt = ImageFont.truetype(r"C:\Windows\Fonts\verdanab.ttf", 15)
    for _i, Rr in enumerate(SEL, 1):
        prog(_i, Rr)
        base, clips, fotos = rutas(Rr); celdas = []
        for i in range(len(Rr["escenas"])):
            g = sorted(glob.glob(os.path.join(clips, "s%02d-*.mp4" % i)))
            if not g: celdas.append(None); continue
            d = float(sh([FPR, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", g[0]]).stdout or 4)
            tmp = os.path.join(base, "_f.png"); sh([FF, "-v", "error", "-y", "-ss", "%.2f" % (d * 0.4), "-i", g[0], "-frames:v", "1", "-vf", "scale=170:302:force_original_aspect_ratio=increase,crop=170:302", tmp])
            celdas.append(Image.open(tmp).convert("RGB").copy())
        for k in (1, 2, 3):
            p = os.path.join(fotos, "col-%d.png" % k)
            celdas.append(Image.open(p).convert("RGBA").resize((170, 170)) if os.path.exists(p) else None)
        n = len(celdas); hoja = Image.new("RGB", (170 * n, 302 + 20), (30, 30, 30)); d = ImageDraw.Draw(hoja)
        for k, im in enumerate(celdas):
            if im is not None: hoja.paste(im, (170 * k, 20), im if im.mode == "RGBA" else None)
            d.text((170 * k + 4, 2), ("E%d" % k) if k < len(Rr["escenas"]) else "collage", font=fnt, fill=(255, 255, 255))
        out = os.path.join(LOTE, "hoja_%s.png" % Rr["slug"]); hoja.save(out); print(out)

elif MODO == "reemplazar":
    slug, idx, q = SOLO[0], int(SOLO[1]), SOLO[2]
    p = os.path.join(LOTE, "reemplazos.json"); ov = ovr(); ov.setdefault(slug, {})[str(idx)] = q; json.dump(ov, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    Rr = next(r for r in RUBROS if r["slug"] == slug); base, clips, fotos = rutas(Rr)
    for f in glob.glob(os.path.join(clips, "s%02d-*.mp4" % idx)):
        os.makedirs(os.path.join(clips, "_descartados"), exist_ok=True); shutil.move(f, os.path.join(clips, "_descartados", os.path.basename(f)))
    antes = set(glob.glob(os.path.join(clips, "q*.mp4")))
    sh([sys.executable, os.path.join(AG, "scripts", "descargar_videos.py"), clips, q, "1", "q"])
    for f in sorted(set(glob.glob(os.path.join(clips, "q*.mp4"))) - antes): os.rename(f, os.path.join(clips, "s%02d-%s" % (idx, os.path.basename(f).split("-", 1)[1]))); print("escena %d ->" % idx, os.path.basename(f))

elif MODO == "render":
    for _i, Rr in enumerate(SEL, 1):
        prog(_i, Rr)
        c = cfg_final(Rr); p = os.path.join(LOTE, Rr["slug"] + ".json"); json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("== %s" % Rr["slug"], flush=True)
        r = sh([sys.executable, os.path.join(AG, "scripts", "generar_dianchi.py"), FF, p], cwd=AG, env=dict(env, PATH=os.path.dirname(FF) + os.pathsep + env["PATH"]))
        print((r.stdout.strip().splitlines() or [""])[-1] if r.returncode == 0 else r.stderr[-600:], flush=True)

# ---- collage con las imagenes propias de la persona (dianchi/entrada/imagenes), si se activo en la app
if MODO == "descargar" and os.environ.get("CTV_IMAGENES_COLLAGE") == "1":
    import random
    from PIL import ImageOps
    raiz = os.path.join(AG, "dianchi", "entrada", "imagenes"); imgs = []
    for ext in ("jpg", "jpeg", "png", "webp"): imgs += glob.glob(os.path.join(raiz, "**", "*." + ext), recursive=True)
    imgs = [f for f in imgs if os.sep + "fotos" + os.sep not in f]
    if not imgs: print("Aviso: no hay imagenes en dianchi/entrada/imagenes; el collage usara fotogramas de los videos.", flush=True)
    else:
        random.shuffle(imgs)
        for Rr in SEL:
            fotos = rutas(Rr)[2]; os.makedirs(fotos, exist_ok=True)
            for k in range(3):
                im = ImageOps.exif_transpose(Image.open(imgs[(k + 3 * SEL.index(Rr)) % len(imgs)])).convert("RGB")
                ImageOps.fit(im, (700, 700), Image.LANCZOS).save(os.path.join(fotos, "col-%d.png" % (k + 1)))
            print("%s: collage con %d imagenes propias" % (Rr["slug"], min(3, len(imgs))), flush=True)
