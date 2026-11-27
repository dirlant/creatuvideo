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
if MODO in ("listar", "agregar", "describir", "cancelar", "cortar_lanzar"):    # «Personalizados»: los instaladores anteriores lanzan este script para esa seccion; se redirige a su motor
    import json as _j, runpy as _r
    try: _lp = (_j.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8")).get("presets", {}) or {}).get("lineaActiva")
    except Exception: _lp = None
    if _lp == "personalizados": _r.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "personalizados_lote.py"), run_name="__main__"); sys.exit(0)
if MODO in ("generar", "aspecto", "guion"):      # Anuncios Con Precio: los instaladores anteriores lanzan este script para esa seccion; se redirige al motor de precios
    import json, runpy
    try: _lin = (json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8")).get("presets", {}) or {}).get("lineaActiva")
    except Exception: _lin = None
    runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), {"infografias": "infografias_lote.py", "animtexto": "infografias_lote.py", "subtitulado": "subtitulado_lote.py"}.get(_lin, "precios_lote.py")), run_name="__main__"); sys.exit(0)   # la app marca la seccion en presets.lineaActiva
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

# ---------------------------------------------------------------- guiones creados por la app con la API de ChatGPT (dianchi/prompt/guiones_nuevos.json)
GN_F = os.path.join(AG, "dianchi", "prompt", "guiones_nuevos.json")
def _r_de_json(d):
    tp = lambda x: tuple(x) if isinstance(x, list) else x
    r = R(d["slug"], d["rubro"], list(d["titulo"]), d["gancho"], d["guion"], d["cta"], [(tp(e[0]), e[1], e[2]) for e in d["escenas"]], (tp(d["collage"][0]), d["collage"][1], d["collage"][2]),
             A=[(tp(x[0]), x[1]) for x in d["A"]] if d.get("A") else None, hastaA=tp(d.get("hastaA")), bubble=(tp(d["bubble"][0]), d["bubble"][1], d["bubble"][2]) if d.get("bubble") else None, marcar=tuple(d.get("marcar") or ()), cta_tipo=d.get("cta_tipo") or "guardar")
    if d.get("cta_custom"): r["cta_custom"] = True
    return r
def _json_de_r(r):
    return {"slug": r["slug"], "rubro": r["rubro"], "titulo": r["titulo"], "gancho": r["gancho"], "guion": r["guion"], "cta": r["cta"], "escenas": [list(e) for e in r["escenas"]], "collage": list(r["collage"]),
            "A": [list(x) for x in (r["A"] or [])], "hastaA": r["hastaA"], "bubble": list(r["bubble"]) if r["bubble"] else None, "marcar": list(r["marcar"]), "cta_tipo": r["cta_tipo"], "cta_custom": bool(r.get("cta_custom"))}
def _cargar_extra():
    try: arr = json.load(open(GN_F, encoding="utf-8"))
    except Exception: return []
    out = []
    for d in arr:
        try: out.append(_r_de_json(d))
        except Exception: pass
    return out
_ya = {r["slug"] for r in RUBROS}
RUBROS.extend([x for x in _cargar_extra() if x["slug"] not in _ya])

# ---------------------------------------------------------------- NO REPETIR GUIONES: historial de lo ya generado + deteccion de guiones parecidos
HECHOS_F = os.path.join(OPD, "hechos.json")
def hechos_leer():
    """{slug: {fecha, titulo}} de los guiones ya convertidos en video. La primera vez, si ya hay videos en la carpeta de resultados, los guiones existentes se dan por hechos."""
    try: return json.load(open(HECHOS_F, encoding="utf-8"))
    except Exception: pass
    base = {}
    try: carpeta = (json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8")).get("dirs") or {}).get("dianchiResultado")
    except Exception: carpeta = None
    if glob.glob(os.path.join(carpeta or os.path.join(AG, "dianchi", "resultado"), "*.mp4")):
        import datetime; hoy = datetime.date.today().isoformat()
        base = {r["slug"]: {"fecha": hoy, "titulo": " ".join(r["titulo"]).replace("*", ""), "origen": "ya existian"} for r in RUBROS}
        json.dump(base, open(HECHOS_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return base
def hechos_marcar(r):
    import datetime
    h = hechos_leer(); h[r["slug"]] = {"fecha": datetime.date.today().isoformat(), "titulo": " ".join(r["titulo"]).replace("*", "")}
    json.dump(h, open(HECHOS_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
_STOP = set("para pero como cada esto esta estas estos solo mas muy sus tus tiene tienen hace hacen donde cuando porque aunque tambien entre sobre desde hasta una unos unas del los las que con por sin muchas clientas clienta tu su".split())
def _toks(s): return {w for w in re.findall(r"[a-z]{4,}", unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()) if w not in _STOP}
def _jac(a, b): return len(a & b) / max(1, len(a | b))
def parecido(a, b):
    g = _jac(_toks(a["guion"]), _toks(b["guion"])); h = _jac(_toks(a["gancho"]), _toks(b["gancho"])); t_ = _jac(_toks(" ".join(a["titulo"])), _toks(" ".join(b["titulo"])))
    return max(g, h * 0.9, t_ * 0.9), g, h, t_
UMBRAL = 0.5
def verificar_repetidos(nuevos, todos):
    malos = []; vistos = set()
    for v in nuevos:
        for o in todos:
            if o is v: continue
            k = frozenset((v["slug"], o["slug"]))
            if k in vistos: continue
            vistos.add(k)
            if o["slug"] == v["slug"]: malos.append((v["slug"], o["slug"], 1.0, "mismo slug")); continue
            s, g, h, t_ = parecido(v, o)
            if s >= UMBRAL: malos.append((v["slug"], o["slug"], s, "guion %d%% · gancho %d%% · título %d%%" % (g * 100, h * 100, t_ * 100)))
    if malos:
        print("GUIONES REPETIDOS O MUY PARECIDOS:", flush=True)
        for a, b, s, d in malos: print("  · «%s» se parece a «%s» (%d%%: %s)" % (a, b, s * 100, d), flush=True)
        sys.exit("Hay %d guion(es) repetidos o casi iguales a otros. Reescribe esos guiones con otro tema, otro gancho y otro ángulo (o quítalos de la lista) y vuelve a generar." % len(malos))
    print("Guiones: %d nuevos, ninguno repetido." % len(nuevos), flush=True)

def marcado(guion, claves):
    for k in claves: guion = re.sub(r"\b(%s)\b" % re.escape(k), r"*\1*", guion, count=1)
    return guion
an = lambda a: (a, 1) if isinstance(a, str) else a       # ancla -> (palabra, n)
def item(a, t): w, n = an(a); return {"ancla": w, "n": n, "texto": t}

def _solo_subtitulos():
    """Diseño de los videos: «solo subtitulos» (Lato, palabra por palabra) o el diseño completo con titulo, pasos, globo, collage y tarjeta final. Se elige en la app (presets.estiloVideo)."""
    try: return ((json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8")).get("presets") or {}).get("estiloVideo") or "subtitulos") == "subtitulos"
    except Exception: return True

def cta_info(Rr):
    """Datos de la accion final del video: la del tipo elegido (CTAS) o una frase PERSONALIZADA que escribio la persona (Rr["cta_custom"])."""
    if Rr.get("cta_custom"):
        import textwrap
        txt = re.sub(r"\s+", " ", Rr["cta"]).strip(); pal = txt.split(); ancla = re.sub(r"^\W+|\W+$", "", pal[0]) if pal else "Sígueme"
        return dict(ancla=ancla, cinta=textwrap.wrap(txt.rstrip("."), 30)[:2], cierre="|".join(textwrap.wrap(txt.rstrip(".").upper(), 20)[:3]), icono="sig")
    return CTAS.get(Rr.get("cta_tipo") or "guardar", CTAS["guardar"])
def n_cta(Rr):
    """Que aparicion (n-esima) de la palabra de la accion es la del cierre: las que ya hay en el gancho y el guion + 1."""
    previo = [norm(w) for w in (Rr["gancho"] + " " + Rr["guion"]).replace("*", "").split()]
    return previo.count(norm(cta_info(Rr)["ancla"])) + 1

def config(Rr, clips_dir, fotos):
    esc = []
    for i, (a, n, q) in enumerate(Rr["escenas"]):
        e = {"clip": "s%02d.mp4" % i}                       # se reemplaza por el archivo real al descargar
        if a is not None:
            w, nn = an(a)
            if w == "Guarda": w = cta_info(Rr)["ancla"]      # la ultima escena se ancla en la palabra de la accion elegida
            e["ancla"] = w; e["n"] = nn
        esc.append(e)
    cfg = {"slug": Rr["slug"], "rubro": Rr["rubro"], "titulo": Rr["titulo"], "gancho": Rr["gancho"], "guion": marcado(Rr["guion"], Rr["marcar"]), "cta": Rr["cta"], "cinta": cta_info(Rr)["cinta"],
           "clips_dir": clips_dir, "salida": "dianchi/resultado", "operacion": "dianchi/_operacion", "efectos": os.environ.get("CTV_EFECTOS", "1") != "0", "voz": os.environ.get("CTV_VOZ", "es-MX-JorgeNeural"), "titulo_top": 420, "escenas": esc,
           "sfx": [{"tipo": "sparkle", "ancla": an(Rr["collage"][0])[0], "n": an(Rr["collage"][0])[1], "desfase": 0.1}, {"tipo": "ding", "ancla": cta_info(Rr)["ancla"], "n": n_cta(Rr)}],
           "pildoras_top": 380, "pildoras_paso": 108, "cierre": {"ancla": cta_info(Rr)["ancla"], "n": n_cta(Rr), "texto": cta_info(Rr)["cierre"], "icono": cta_info(Rr)["icono"]}}
    w, n = an(Rr["collage"][0]); cfg["collages"] = [{"ancla": w, "n": n, "centro": fotos + "/col-1.png", "izq": fotos + "/col-2.png", "der": fotos + "/col-3.png", "dur": 2.4}]
    if Rr["A"]: cfg["pildoras"] = [item(a, t) for a, t in Rr["A"]]; cfg["pildoras_hasta"] = an(Rr["hastaA"])[0]
    if Rr["B"]: cfg["pildoras2"] = [item(a, t) for a, t in Rr["B"]]; cfg["pildoras2_hasta"] = an(Rr["hastaB"])[0]
    if Rr["bubble"]:
        a, t, h = Rr["bubble"]; w, n = an(a); cfg["pildoras3"] = [{"ancla": w, "n": n, "texto": t}]; cfg["pildoras3_hasta"] = an(h)[0]
    if Rr.get("voz"): cfg["voz"] = Rr["voz"]                          # voz propia del guion (por ejemplo, otro idioma)
    ev = lambda k: os.environ.get("CTV_EV_" + k, "1") != "0"          # eventos del video activables desde la app
    if _solo_subtitulos(): cfg["solo_subtitulos"] = True
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
# ---------------------------------------------------------------- ESCRIBIR LOS GUIONES con la API de ChatGPT y el prompt de Dianchi (modo «guiones»)
# ---------------------------------------------------------------- REVISION DEL ESPAÑOL: segunda pasada (corrector) + lista de formas de voseo
VOSEO = re.compile(r"\b(vos|sos|tenés|querés|podés|sabés|hacés|decís|pensás|necesitás|empezás|ponés|venís|salís|vivís|perdés|perdás|perdas|mirá|escuchá|fijate|ponete|acordate|andá|dejá|cuidá|mostrá|aprendé|comprá|vendé|cobrá|pagá|ahorrá|confiá|che|laburo|laburar|pibe|boludo)\b", re.I)
def _textos_de(o, acum=None):
    acum = [] if acum is None else acum
    if isinstance(o, str): acum.append(o)
    elif isinstance(o, list): [_textos_de(x, acum) for x in o]
    elif isinstance(o, dict): [_textos_de(x, acum) for k, x in o.items() if not str(k).startswith("busqueda") and k not in ("slug", "busquedas")]
    return acum
def _forma(o):
    if isinstance(o, dict): return {k: _forma(v) for k, v in o.items()}
    if isinstance(o, list): return [_forma(x) for x in o]
    return None
def revisar_espanol(d, pedir_rev):
    """Segunda pasada: un corrector arregla voseo, conjugaciones mal escritas («perdas» -> «pierdas»), ortografia y tildes de los textos en español del guion, sin cambiar su sentido ni su estructura."""
    sistema = ("Eres corrector de textos en ESPAÑOL NEUTRO LATINOAMERICANO con tuteo («tú»). Recibes un JSON con un guion de video. Corrige SOLO los textos en español: "
               "(1) voseo y formas rioplatenses → tuteo («tenés»→«tienes», «perdás» o «perdas»→«pierdas», «mirá»→«mira», «vos»→«tú», «sos»→«eres»); "
               "(2) verbos mal conjugados o mal escritos (irregulares: pierdas, tengas, quieras, puedas, vayas, cuentes…), faltas de ortografía y tildes; (3) concordancia de género y número. "
               "NO cambies el sentido, no agregues ni quites ideas, mantén la misma cantidad de palabras (±2) y respeta las mayúsculas y los asteriscos (*palabra*) tal como están. "
               "NO modifiques las claves, los números, los slugs ni los textos en inglés (búsquedas de video). Si algo ya está bien, déjalo igual. Responde SOLO con el MISMO JSON, sin comentarios.")
    try: nuevo = json.loads(pedir_rev([{"role": "system", "content": sistema}, {"role": "user", "content": json.dumps(d, ensure_ascii=False)}]))
    except Exception: return d, []
    if not isinstance(nuevo, dict) or json.dumps(_forma(nuevo), sort_keys=True) != json.dumps(_forma(d), sort_keys=True): return d, []        # cambio la estructura: se descarta la correccion
    a, b = _textos_de(d), _textos_de(nuevo); cambios = []
    if len(a) != len(b): return d, []
    import difflib
    for x, y in zip(a, b):
        if x != y:
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x.split(), y.split()).get_opcodes():
                if op == "replace" and (i2 - i1) == (j2 - j1): cambios += [(" ".join(x.split()[i1:i2]), " ".join(y.split()[j1:j2]))]
    return nuevo, cambios
def voseo_en(d):
    return sorted({m.group(0).lower() for t in _textos_de(d) for m in VOSEO.finditer(t)})
def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()).strip("-")
    return s[:38].strip("-") or "guion"
def norm_acentos(s): return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
def _convertir(d, it, existentes, max_total):
    """Valida lo que devolvio ChatGPT y lo pasa al formato del motor (R). ChatGPT escribe el guion por PARTES (cada parte = una escena con su busqueda de video en ingles) y
    la app calcula sola las palabras ancla: donde cambia cada escena, donde empiezan los pasos, donde aparece el globo y el collage. Devuelve (R, []) o (None, [errores])."""
    err = []
    S_ = lambda x: re.sub(r"\s+", " ", str(x or "")).strip()
    cta_custom = S_(it.get("cta_custom")); gancho = S_(d.get("gancho")); cta = cta_custom or S_(d.get("cta")); partes = [p for p in (d.get("partes") or []) if isinstance(p, dict) and S_(p.get("texto"))]
    if not gancho or not partes: return None, ["faltan el gancho o las partes del guion"]
    if "?" in gancho or "¿" in gancho: err.append("el gancho no puede llevar signos de pregunta")
    if not 5 <= len(partes) <= 12: err.append("el guion debe tener entre 5 y 12 partes (cada una es una escena de unas 8 a 12 palabras)")
    ancla_cta = CTAS.get(it.get("cta_tipo") or "guardar", CTAS["guardar"])["ancla"]
    if not cta_custom and (not cta or norm(cta.split()[0]) != norm(ancla_cta)): err.append("el «cta» debe empezar con la palabra «%s»" % ancla_cta)
    if not re.search(r"[.!]$", cta): cta += "."
    textos = []
    for p in partes:
        x = S_(p["texto"]).replace("*", "")
        if not re.search(r"[.!?,;:]$", x): x += ","
        textos.append(x)
    textos[-1] = re.sub(r"[,;:]$", ".", textos[-1])
    titulo = [S_(x) for x in (d.get("titulo") or []) if S_(x)]
    if not 2 <= len(titulo) <= 3: err.append("el título debe tener 2 o 3 líneas")
    elif not any(re.search(r"\*[^*]+\*", x) for x in titulo):
        ult = titulo[-1].split(); ult[-1] = "*" + norm_acentos(ult[-1]).lower() + "*"; titulo[-1] = " ".join(ult)
    en = lambda q: len(re.findall(r"[A-Za-z]{3,}", str(q or ""))) >= 2 and not re.search(r"[áéíóúñ]", str(q or "").lower())
    q_g, q_c, q_k = S_(d.get("busqueda_gancho")), S_(d.get("busqueda_cta")), S_(d.get("busqueda_collage"))
    qs = [S_(p.get("busqueda")) for p in partes]
    if not all(en(q) for q in [q_g, q_c, q_k] + qs): err.append("todas las búsquedas de video (busqueda_gancho, busqueda de cada parte, busqueda_cta, busqueda_collage) deben estar en inglés y tener 2 a 5 palabras")
    pasos_i = [i for i, p in enumerate(partes) if S_(p.get("paso"))]
    try: o = int(d.get("parte_objecion")) - 1
    except Exception: o = 0
    if not 0 <= o < len(partes) - 2: o = 0                                      # reparacion: la objecion va en la primera parte
    pasos_i = [i for i in pasos_i if i > o and i < len(partes)][:4]
    if len(pasos_i) < 3:                                                       # reparacion: se eligen 3 partes repartidas despues de la objecion como pasos
        resto = [i for i in range(o + 1, len(partes) - 1)] or [len(partes) - 2]
        paso = max(1, len(resto) // 3); elegidos = sorted(set((resto[::paso] + resto)[:3]))
        for i in elegidos:
            if i not in pasos_i: partes[i] = dict(partes[i], paso=" ".join(S_(partes[i]["texto"]).replace("*", "").split()[:3]).upper().strip(",.;:"))
        pasos_i = sorted(set(pasos_i) | set(elegidos))[:4]
    ob = re.sub(r"[“”\"«»]", "", S_(d.get("objecion"))).upper()
    if not ob: ob = " ".join(S_(partes[o]["texto"]).replace("*", "").split()[:4]).upper().strip(",.;:")      # reparacion: sin frase de objecion se usa el inicio de su parte
    toks = [norm(w) for w in gancho.replace("*", "").split()]; n_g = len(toks); ini = []; palabras = []
    for x in textos:
        w = x.split(); ini.append(n_g + len(palabras)); palabras += w
    n_p = len(palabras); toks += [norm(w) for w in palabras]; ini.append(n_g + n_p); cta_w = cta.split(); toks += [norm(w) for w in cta_w]; total = len(toks)
    tope = min(112, int(max_total * 1.3))
    if total > tope: err.append("tiene %d palabras en total (gancho + partes + cta) y el máximo es %d: acorta las partes" % (total, tope))
    if total < max_total * 0.45: err.append("es muy corto (%d palabras): debe acercarse a %d" % (total, max_total))
    if err: return None, err
    todas = gancho.replace("*", "").split() + palabras + cta_w
    pal = lambda i: re.sub(r"^\W+|\W+$", "", todas[i])
    n_de = lambda i: toks[:i + 1].count(toks[i])
    def unica(i0, i1):
        for i in range(i0, i1 + 1):
            if norm(pal(i)) and toks.count(toks[i]) == 1: return pal(i)
        return pal(i0)
    escenas = [(None, 1, q_g)] + [((pal(ini[k]), n_de(ini[k])), 1, qs[k]) for k in range(len(partes))] + [((pal(n_g + n_p), n_de(n_g + n_p)), 1, q_c)]
    # pasos (pildoras): primera palabra de cada parte-paso; terminan al empezar la parte siguiente al ultimo paso
    A = []
    for k, i in enumerate(pasos_i[:4]):
        etq = S_(partes[i].get("paso")).upper(); etq = re.sub(r"^\d+\s*[·.\-)]*\s*", "", etq)
        while len(etq) > 24 and " " in etq: etq = etq.rsplit(" ", 1)[0]
        A.append(((pal(ini[i]), n_de(ini[i])), etq[:24]))
    ult = pasos_i[:4][-1]
    hastaA = unica(ini[ult + 1], ini[ult + 2] - 1) if ult + 1 < len(partes) else unica(ini[ult], ini[ult + 1] - 1)
    # globo con la objecion: palabra mas significativa de su parte; termina al empezar la parte siguiente
    i0, i1 = ini[o], ini[o + 1] - 1; cand = [(len(norm(pal(i))), -i) for i in range(i0, i1 + 1) if len(norm(pal(i))) >= 5 and norm(pal(i)) not in _STOP]
    ia = -max(cand)[1] if cand else i0
    bubble = ((pal(ia), n_de(ia)), "“%s”" % ob[:30], unica(ini[o + 1], ini[o + 2] - 1) if o + 2 <= len(partes) else pal(ini[o + 1]))
    # collage: en la parte que sigue a los pasos (o la ultima antes del cierre)
    c = min(len(partes) - 1, ult + 2 if ult + 2 < len(partes) else ult + 1); ic = ini[c]; ic = next((i for i in range(ini[c], ini[c + 1]) if len(norm(pal(i))) >= 5), ic)
    collage = ((pal(ic), n_de(ic)), 1, q_k)
    guion = " ".join(textos); marc = []
    for w in (d.get("marcar") or [])[:3]:
        w = re.sub(r"^\W+|\W+$", "", str(w))
        m = re.search(r"\b%s\b" % re.escape(w), guion, re.I) if w else None
        if m and m.group(0) not in marc: marc.append(m.group(0))
    slug = _slug(d.get("slug") or (it.get("rubro", "") + " " + " ".join(titulo))); base = slug; k = 2
    while slug in existentes: slug = "%s-%d" % (base, k); k += 1
    rubro = str(it.get("rubro", "")).upper()
    r = R(slug, rubro, titulo, gancho, guion, cta, escenas, collage, A=A, hastaA=hastaA, bubble=bubble, marcar=tuple(marc[:2]), cta_tipo=it.get("cta_tipo") or "guardar")
    if cta_custom: r["cta_custom"] = True
    return r, []

def generar_guiones():
    """Modo «guiones»: por cada combinacion pedida en la app (presets.dianchiPedido) escribe un guion con la API de ChatGPT siguiendo el prompt de Dianchi y lo que el usuario eligio
    (rubro, temática, formato, gancho, acción, problema). Comprueba que sea valido y que no repita a otro; lo guarda en guiones_nuevos.json y deja el lote en lote_actual.txt."""
    import urllib.request, urllib.error
    try: aj = json.load(open(os.environ.get("CTV_AJUSTES") or os.path.join(os.environ.get("APPDATA", ""), "CreaTuVideo", "settings.json"), encoding="utf-8"))
    except Exception: aj = {}
    pedido = (aj.get("presets") or {}).get("dianchiPedido") or []
    if not pedido: sys.exit("No hay nada que escribir: elige al menos un valor en cada opción del paso 1.")
    key = (aj.get("openaiKey") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key: sys.exit("Falta la clave de OpenAI (ChatGPT): pégala en Ajustes → Clave de OpenAI.")
    modelo = (aj.get("openaiModelo") or "gpt-4o-mini").strip()
    leer = lambda f, n: (open(os.path.join(AG, "dianchi", "prompt", f), encoding="utf-8").read()[:n] if os.path.exists(os.path.join(AG, "dianchi", "prompt", f)) else "")
    reglas = leer("dianchi_rubros.md", 9000); ajustes = leer("AJUSTES.md", 9000)
    ejemplo = json.dumps({"slug": "cabello-keratina", "titulo": ["EL ALISADO SE CUIDA", "ANTES Y DESPUÉS DE", "LA *keratina*"],
        "gancho": "Si crees que un alisado con keratina deja el cabello sin vida, depende de cómo se aplica y se cuida.", "busqueda_gancho": "hair straightening salon keratin",
        "partes": [{"texto": "Muchas clientas temen que se vea pesado o acartonado.", "busqueda": "woman touching damaged hair", "paso": ""},
                   {"texto": "Por eso primero lavamos con un shampoo clarificante,", "busqueda": "hairdresser washing hair client salon", "paso": "LAVAMOS A FONDO"},
                   {"texto": "después aplicamos el producto por mechones sin tocar la raíz", "busqueda": "hairdresser applying hair treatment brush", "paso": "POR MECHONES"},
                   {"texto": "y por último sellamos con plancha a la temperatura adecuada.", "busqueda": "hair flat iron straightening", "paso": "SELLAMOS CON PLANCHA"},
                   {"texto": "Luego te enseñamos a cuidarlo en casa.", "busqueda": "woman shiny straight hair", "paso": ""},
                   {"texto": "Si estás embarazada o tu cuero cabelludo es sensible, cuéntanoslo antes.", "busqueda": "hairdresser talking client salon", "paso": ""}],
        "objecion": "SE VERÁ ACARTONADO", "parte_objecion": 1, "cta": "Guarda este audio para recordarlo antes de tu alisado.", "busqueda_cta": "woman smooth hair smiling", "busqueda_collage": "straight shiny hair close up",
        "marcar": ["clarificante", "temperatura"]}, ensure_ascii=False, indent=1)
    sistema = ("Eres especialista en contenido para negocios de belleza y escribes guiones de videos cortos (Reels) para CLIENTAS FINALES, con voz en off, siguiendo estas reglas del prompt de Dianchi:\n\n" + reglas
               + "\n\nAJUSTES ACUMULADOS (se aplican siempre):\n" + ajustes
               + "\n\nFORMATO DE SALIDA (obligatorio). Responde SOLO con un objeto JSON, sin texto antes ni después, con estas claves:\n"
               '{"slug":"servicio-tema-en-minusculas","titulo":["LÍNEA 1","LÍNEA 2","LA *palabra*"],"gancho":"frase de apertura (afirmación, sin signos de pregunta, máximo 16 palabras)","busqueda_gancho":"english pexels search",'
               '"partes":[{"texto":"frase corta del guion","busqueda":"english pexels search","paso":"ETIQUETA CORTA o vacío"}],"objecion":"FRASE DE LA CLIENTA EN MAYÚSCULAS","parte_objecion":1,'
               '"cta":"frase final que empieza con la palabra de la acción","busqueda_cta":"english pexels search","busqueda_collage":"english pexels search","marcar":["palabra","palabra"]}\n'
               "Reglas del formato: (1) La narración completa será: gancho + las partes en orden + cta. NO repitas el gancho dentro de las partes. (2) Cada parte es UNA escena del video: una frase corta de 8 a 12 palabras que se corta bien (termina en coma o punto) y su «busqueda» es una búsqueda de video de stock en INGLÉS de 2 a 5 palabras que muestre exactamente lo que dice esa parte. "
               "(3) Estructura: 1 o 2 partes que plantean el miedo u objeción de la clienta (la «parte_objecion» es el número, desde 1, de la parte que lo nombra), luego 3 o 4 partes que son los PASOS del servicio (cada una con su «paso»: etiqueta en mayúsculas de MÁXIMO 22 caracteres; las demás partes llevan «paso» vacío), "
               "luego 1 o 2 partes de cuidado o cautela real (avisar alergias, embarazo, condición médica, piel sensible… cuando el servicio lo requiera). (4) «objecion»: la frase de la clienta en 2 a 5 palabras, en mayúsculas, que esa parte menciona. "
               "(5) «titulo»: 2 o 3 líneas en MAYÚSCULAS con UNA palabra clave entre *asteriscos* en minúscula y sin tildes ni ñ, sin repetir el gancho. (6) «cta»: debe empezar EXACTAMENTE con la palabra de la acción indicada en el pedido y cerrar con algo concreto del servicio. "
               "(7) «marcar»: 2 palabras técnicas o importantes copiadas tal cual de las partes. (8) Sin cifras ni resultados inventados, sin símbolos decorativos, sin descripciones visuales, español neutro latinoamericano con «tú» (NUNCA voseo ni modismos: «pierdas», no «perdas» ni «perdás»; «tienes», no «tenés»; «mira», no «mirá») y con las conjugaciones, la ortografía y las tildes correctas; no llames «natural» a un servicio con químicos. "
               "(9) Respeta el máximo de palabras del pedido, contando gancho + partes + cta.\n\nEJEMPLO DE UN GUION YA HECHO (imita el nivel de concreción y el formato, NO el tema):\n" + ejemplo)
    usados = {r["slug"] for r in RUBROS}; nuevos = []; guardados = []
    try: guardados = json.load(open(GN_F, encoding="utf-8"))
    except Exception: pass
    historial = lambda: "\n".join("- %s · «%s» · gancho: %s" % (r["slug"], " ".join(r["titulo"]).replace("*", ""), r["gancho"]) for r in RUBROS[-70:])
    def pedir(mensajes, temp=0.9):
        cuerpo = json.dumps({"model": modelo, "temperature": temp, "max_tokens": 2200, "response_format": {"type": "json_object"}, "messages": mensajes}).encode("utf-8")
        rq = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=cuerpo, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try: r = json.loads(urllib.request.urlopen(rq, timeout=150).read().decode("utf-8"))
        except urllib.error.HTTPError as ex:
            try: m = json.loads(ex.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception: m = ""
            sys.exit("La API de ChatGPT respondió con error %s: %s" % (ex.code, (m or ex.reason)[:300].replace(key, "…")))
        except Exception as ex: sys.exit("No se pudo consultar la API de ChatGPT (hace falta internet): %s" % str(ex)[:200].replace(key, "…"))
        return r["choices"][0]["message"]["content"] or ""
    print("Escribiendo %d guion(es) con ChatGPT (%s) y el prompt de Dianchi…" % (len(pedido), modelo), flush=True)
    for i, it in enumerate(pedido, 1):
        dur = max(10, min(30, int(it.get("duracion") or 25))); max_total = int(dur * 3.0)          # voz 1.3x: unas 3 palabras por segundo
        print("CTV_PROGRESO guiones %d %d %s" % (i, len(pedido), _slug((it.get("rubro") or "") + " " + (it.get("tematica") or it.get("problema") or "guion"))), flush=True)
        prob = (it.get("problema") or "").strip(); tipo = it.get("cta_tipo") or "guardar"
        usuario = ("Escribe UN guion nuevo con estos datos del pedido:\n- Rubro / servicio: %s\n- Temática: %s%s\n- Formato: %s → %s\n- Tipo de gancho: %s → %s\n- Acción final: %s → %s (la frase «cta» empieza con la palabra «%s»)\n"
                   % (it.get("rubro", ""), it.get("tematica", ""), (" → " + it["tematica_def"]) if it.get("tematica_def") else "", it.get("formato", ""), it.get("formato_def", ""), it.get("gancho", ""), it.get("gancho_def", ""), it.get("accion", ""), it.get("accion_def", ""), CTAS.get(tipo, CTAS["guardar"])["ancla"]))
        if it.get("cta_custom"): usuario += "- La frase final «cta» es PERSONALIZADA y la pone la app tal cual: «%s». Escribe el último paso o la última parte de modo que lleve naturalmente a ella; no la repitas ni la reescribas.\n" % it["cta_custom"]
        usuario += ("- Problema / miedo a resolver (OBLIGATORIO, el guion trata exactamente de esto): %s\n" % prob) if prob else "- Problema o miedo a resolver: elige tú uno concreto y real de esa temática y servicio, distinto de los guiones ya hechos\n"
        if int(it.get("variaciones") or 1) > 1: usuario += "- Es la variación %s de %s sobre lo mismo: usa un ángulo y un gancho distintos a los otros.\n" % (it.get("variacion", 1), it.get("variaciones"))
        usuario += ("- Longitud: gancho + partes + cta en total, un MÁXIMO de %d palabras (el video dura %d segundos) y no menos de %d.\n\nGUIONES QUE YA EXISTEN (no repitas tema, gancho ni ideas):\n%s" % (max_total, dur, int(max_total * 0.65), historial()))
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]; r = None; errs = []
        for intento in range(3):
            txt = pedir(msgs)
            try: d = json.loads(txt)
            except Exception: d = None
            if not isinstance(d, dict): errs = ["la respuesta no fue un JSON válido"]; r = None
            else:
                d, cambios = revisar_espanol(d, lambda m: pedir(m, 0))
                if cambios: print("  ✎ corrector de español: " + "; ".join("«%s» → «%s»" % c for c in cambios[:8]), flush=True)
                vos = voseo_en(d)
                if vos: errs = ["usas voseo o modismos (%s): escribe en español neutro con «tú»" % ", ".join(vos)]; r = None; d = None
            if isinstance(d, dict):
                r, errs = _convertir(d, it, usados, max_total)
                if r is not None:
                    otro = max(RUBROS, key=lambda o: parecido(r, o)[0]) if RUBROS else None
                    if otro is not None and parecido(r, otro)[0] >= UMBRAL:
                        errs = ["se parece demasiado (%d%%) al guion ya existente «%s»: cambia el tema, el gancho y las ideas" % (parecido(r, otro)[0] * 100, otro["slug"])]; r = None
            if r is not None: break
            print("  intento %d: %s" % (intento + 1, "; ".join(errs)[:300]), flush=True)
            msgs += [{"role": "assistant", "content": txt}, {"role": "user", "content": "Corrige estos problemas y responde de nuevo SOLO con el JSON completo:\n- " + "\n- ".join(errs)}]
        if r is None: print("  ✗ no se pudo crear el guion %d de %d (%s): se omite." % (i, len(pedido), "; ".join(errs)[:200]), flush=True); continue
        usados.add(r["slug"]); RUBROS.append(r); nuevos.append(r); guardados.append(_json_de_r(r))
        os.makedirs(os.path.dirname(GN_F), exist_ok=True); json.dump(guardados, open(GN_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  ✓ %s · «%s» · %d palabras" % (r["slug"], " ".join(r["titulo"]).replace("*", ""), len((r["gancho"] + " " + r["guion"] + " " + r["cta"]).replace("*", "").split())), flush=True)
    if not nuevos: sys.exit("No se pudo crear ningún guion nuevo. Revisa el registro.")
    open(os.path.join(AG, "dianchi", "prompt", "lote_actual.txt"), "w", encoding="utf-8").write("\n".join(r["slug"] for r in nuevos) + "\n")
    print("Guiones nuevos creados: %d de %d (listos para verificar, descargar y generar)." % (len(nuevos), len(pedido)), flush=True)

_LOTE = [] if SOLO or MODO == "listar" else _lote_actual()
if MODO in ("verificar", "descargar", "hoja", "render") and not SOLO:
    _H = hechos_leer()                 # solo se generan los guiones NUEVOS: un guion ya convertido en video no se vuelve a hacer
    SEL = [r for r in RUBROS if (r["slug"] in _LOTE if _LOTE else True) and r["slug"] not in _H]
    if not SEL: sys.exit("No hay guiones nuevos para generar: los %d guiones de la lista ya se convirtieron en video. Escribe guiones nuevos (botón «Escribir guiones (ChatGPT)», con tu clave de OpenAI en Ajustes) y vuelve a generar. Para rehacer uno en concreto, elígelo en «Paso a paso»." % len(RUBROS))
    print("Guiones nuevos por generar: %d (ya hechos: %d)" % (len(SEL), len([1 for r in RUBROS if r["slug"] in _H])), flush=True)
else:
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
    print(json.dumps([{"slug": r["slug"], "rubro": r["rubro"], "titulo": " ".join(r["titulo"]).replace("*", ""), "gancho": r["gancho"], "guion": r["guion"].replace("*", "")[:170]} for r in RUBROS], ensure_ascii=False))

elif MODO == "guiones":
    generar_guiones()

elif MODO == "verificar":
    if not SOLO: verificar_repetidos(SEL, RUBROS)
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
        if r.returncode == 0: hechos_marcar(Rr)

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
