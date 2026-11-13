// Interfaz de CreaTuVideo. Solo habla con el proceso principal mediante window.ctv (ver preload.js).
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
let ajustes = null;
let ocupado = false;

// ---------------------------------------------------------------- navegacion
function ir(v) {
  $$(".vista").forEach((e) => e.classList.toggle("activa", e.id === "v-" + v));
  $$(".nav-b").forEach((b) => b.classList.toggle("activo", b.dataset.v === v));
  if (v === "dianchi" || v === "diegao") cargarLista(v, false);
  if (v === "ajustes") comprobarEntorno();
  if (v === "claude") actualizarCuenta();
}
$$(".nav-b").forEach((b) => b.addEventListener("click", () => ir(b.dataset.v)));
$$("[data-ir]").forEach((b) => b.addEventListener("click", () => ir(b.dataset.ir)));

// ---------------------------------------------------------------- registro
const logEl = $("#log");
function escribir(t) { logEl.textContent += t + "\n"; if (logEl.textContent.length > 120000) logEl.textContent = logEl.textContent.slice(-80000); logEl.scrollTop = logEl.scrollHeight; }
window.ctv.onLog(escribir);
window.ctv.onBusy((b) => {
  ocupado = b;
  $("#ind-busy").classList.toggle("oculto", !b);
  $("#b-cancel").disabled = !b;
  $$("[data-run], #b-upd-ir").forEach((x) => { if (b) x.disabled = true; else if (x.id !== "b-upd-ir") x.disabled = false; });
});
$("#b-limpiar").addEventListener("click", () => (logEl.textContent = ""));
$("#b-cancel").addEventListener("click", () => window.ctv.cancel());

// ---------------------------------------------------------------- listas de videos del lote
const listas = { dianchi: [], diegao: [] };
async function cargarLista(linea, forzar) {
  const cont = $("#lista-" + linea);
  if (listas[linea].length && !forzar) return;
  cont.innerHTML = '<span class="chico">Cargando lista… (la primera vez puede tardar mientras se prepara Python)</span>';
  const r = await window.ctv.listar(linea);
  if (r.error) { cont.innerHTML = '<span class="chico">' + r.error + "</span>"; return; }
  listas[linea] = r.items;
  cont.innerHTML = "";
  for (const it of r.items) {
    const d = document.createElement("label");
    d.className = "item";
    d.innerHTML = '<input type="checkbox" value="' + it.slug + '" checked /><div><b></b><span></span></div>';
    $("b", d).textContent = it.titulo; $("span", d).textContent = it.rubro + " · " + it.slug;
    cont.appendChild(d);
  }
  actualizarContadorLista();
}
$$("[data-acc]").forEach((b) => b.addEventListener("click", () => {
  const l = b.dataset.l;
  if (b.dataset.acc === "recargar") return cargarLista(l, true);
  $$("#lista-" + l + " input").forEach((c) => (c.checked = b.dataset.acc === "seleccionar"));
}));
$$("[data-run]").forEach((b) => b.addEventListener("click", async () => {
  const [linea, modo] = b.dataset.run.split(":");
  const slugs = $$("#lista-" + linea + " input:checked").map((c) => c.value);
  if (!slugs.length) return escribir("Marca al menos un video de la lista.");
  const r = await window.ctv.run({ linea, modo, slugs });
  if (r && r.error) escribir("⚠ " + r.error);
}));
$$("[data-abrir]").forEach((b) => b.addEventListener("click", () => window.ctv.openPath(b.dataset.abrir || (ajustes && ajustes.workspace) || "")));

// ---------------------------------------------------------------- formulario de Dianchi (replica de dianchi.creatulink.com)
const OPC = {
  idiomas: [["Español", "es-MX-JorgeNeural"], ["English", "en-US-GuyNeural"], ["Português", "pt-BR-AntonioNeural"], ["Deutsch", "de-DE-ConradNeural"]],
  rubros: ["Barbería", "Cabello", "Cejas", "Cosmetología", "Depilación", "Estética", "Maquillaje", "Masajes", "Micropigmentación", "Pestañas", "Pies", "Podología", "Uñas"],
  formatos: [
    ["Educar — Resuelve dudas", "educativo, informativo, explicación práctica, resolución de dudas"],
    ["Vender sin vender — Despierta interés", "deseo, objeciones, identificación, problema-solución sin venta directa"],
    ["Demostrar — Muestra lo que haces", "caso concreto, procedimiento, transformación observable, antes y después, comparativo, detrás de cámaras"],
    ["Posicionamiento — Muestra tu criterio", "opinión profesional, criterio, decisión experta, punto de vista"],
    ["Promo — Promociona tu servicio", "oferta directa, beneficio principal, motivo para actuar, llamado a la acción"],
    ["Storytelling — Cuenta una experiencia", "Storytelling"],
  ],
  tonos: [
    ["Cercano", "Como hablar con una amiga que entiende perfectamente"], ["Creativo", "Original y fuera de lo común"],
    ["Educativo", "Explica de forma clara, simple y fácil de entender"], ["Emocional", "Conecta con sentimientos y experiencias internas de la clienta"],
    ["Humorístico", "Divertido, relatable y exagerado"], ["Intelectual", "Analítico y basado en criterio"], ["Tranquilizador", "Reduce miedos y genera confianza"],
  ],
  tematicas: [
    ["Aspiraciones", "resultado deseado y estilo de vida que la clienta quiere alcanzar"],
    ["Experiencias", "situaciones, hábitos, pensamientos y cambios cotidianos relacionados con el servicio."],
    ["Frustraciones", "problemas reales, molestias y situaciones repetitivas que vive la clienta"],
    ["Higiene", "confianza, seguridad, protocolos y cuidado profesional"],
    ["Malas experiencias", "errores previos, expectativas incumplidas y consecuencias de decisiones incorrectas"],
    ["Objeciones", "dudas, barreras y razones por las que la clienta aún no toma acción"],
    ["Miedos", "miedos"], ["Procedimientos", "procedimientos"],
  ],
  ganchos: [
    ["Consejo experto — Recomienda como profesional", "recomendación directa basada en el criterio profesional, relacionada con el servicio o situación indicada."],
    ["Error — Muestra un error común", "señalar un error frecuente relacionado con el servicio y explicar brevemente qué conviene hacer o considerar en su lugar."],
    ["Problema — Habla de lo que le pasa", "iniciar desde una situación o dificultad concreta que la clienta reconoce, relacionada con el servicio."],
    ["Reencuadre — Cambia su forma de verlo", "presentar una perspectiva diferente sobre una creencia o situación relacionada con el servicio, de forma natural y concreta."],
    ["Revelación — Descubre algo que no sabía", "presentar un dato, posibilidad o detalle relevante que la audiencia podría desconocer, sin inventar secretos ni afirmar que nadie lo cuenta."],
    ["Verdad directa — Cuestiona una creencia", "comenzar con una afirmación clara que cuestione una creencia, hábito o expectativa común, sin exagerar ni generar incomodidad artificial."],
    ["Miedo — Responde a una preocupación", "iniciar desde un miedo o preocupación real de la clienta y anticipar que el contenido ayudará a entenderlo o resolverlo, sin alarmismo."],
    ["Si yo fuera tu especialista — Aconseja desde tu profesión", "el gancho debe iniciar obligatoriamente con “Si yo fuera tu [profesión del rubro]”, adaptando automáticamente la profesión según el rubro seleccionado. Continuar con una recomendación concreta y relacionada con el servicio."],
    ["Factor clave — Explica qué hace la diferencia", "destacar un factor importante que influye en el procedimiento, la elección del servicio o el resultado deseado, sin afirmar que es el único factor."],
    ["Comparación — Compara dos opciones", "contrastar dos servicios, resultados, decisiones o situaciones para ayudar a entender sus diferencias. Evitar presentar una opción como incorrecta si ambas pueden ser adecuadas."],
  ],
  ctas: [   // [etiqueta, descripcion, cta_tipo del motor, palabra con la que empieza la frase final]
    ["Que comente", "invitar a compartir una experiencia, duda u opinión relacionada con el guion.", "comentar", "Comenta"],
    ["Que me sigan", "invitar a seguir para conocer más contenido relacionado con el tema o servicio.", "seguir", "Sígueme"],
    ["Que comparta", "invitar a enviar el contenido a alguien a quien pueda resultarle útil.", "compartir", "Comparte"],
    ["Que dé like", "invitar a dar like por identificación, acuerdo o interés en el contenido.", "like", "Dale"],
    ["Que lo guarde", "invitar a guardar el contenido para consultarlo o recordarlo después.", "guardar", "Guarda"],
    ["Que escriba un mensaje", "invitar a enviar un mensaje privado con una palabra clave relacionada con el servicio para recibir información o agendar.", "mensaje", "Escríbeme"],
  ],
};
const BRIEF0 = { idioma: "Español", tema: "", rubros: [], formato: OPC.formatos[0][0], tono: "Cercano", tematicas: [], tendencia: "", gancho: OPC.ganchos[0][0], cta: "Que lo guarde", duracion: 25, variaciones: 1 };
function brief() {                               // siempre el MISMO objeto, completando solo lo que falte
  const p = ajustes.presets;
  if (!p.brief) p.brief = { ...BRIEF0, rubros: [], tematicas: [] };
  for (const k of Object.keys(BRIEF0)) if (!(k in p.brief)) p.brief[k] = Array.isArray(BRIEF0[k]) ? [] : BRIEF0[k];
  return p.brief;
}
let tGuardarBrief = null;
function guardarBrief() { clearTimeout(tGuardarBrief); tGuardarBrief = setTimeout(() => window.ctv.saveSettings(ajustes), 500); }
const totalVideos = () => { const b = brief(); return b.rubros.length && b.tematicas.length ? b.rubros.length * b.tematicas.length * Number(b.variaciones) : 0; };

function actualizarContador() {
  const b = brief(), el = $("#brief-contador"), n = totalVideos();
  el.className = "contador" + (n ? "" : " vacio");
  if (!n) { el.textContent = "Elige al menos un rubro y una temática para ver cuántos videos se procesarán."; return resumenDianchi(); }
  const min = n * 5;
  el.innerHTML = "Se procesarán <b>" + n + "</b> video" + (n === 1 ? "" : "s") + " — " + b.rubros.length + " rubro" + (b.rubros.length === 1 ? "" : "s") + " × " + b.tematicas.length + " temática" + (b.tematicas.length === 1 ? "" : "s") + " × " + b.variaciones + (Number(b.variaciones) === 1 ? " variación" : " variaciones")
    + "<br><span class='chico'>Tiempo estimado: unos " + (min >= 60 ? Math.floor(min / 60) + " h " + (min % 60) + " min" : min + " min") + " (≈ 5 min por video)." + (ajustes.presets.rellenoLocal ? "" : " Descarga ≈ " + n * 80 + " solicitudes de Pexels (cupo: 20.000 al mes).") + "</span>"
    + (n > 16 ? "<br><span class='aviso-n'>⚠ Son muchos videos: conviene hacerlos en lotes de 16 o menos.</span>" : "");
  resumenDianchi();
}
function campo(num, titulo, ayuda, nodo, ancho) {
  const d = document.createElement("div"); d.className = "campo" + (ancho ? " ancho" : "");
  const l = document.createElement("label"); l.className = "et"; l.textContent = (num ? num + ". " : "") + titulo.toUpperCase(); d.appendChild(l);
  if (ayuda) { const a = document.createElement("div"); a.className = "ayuda"; a.textContent = ayuda; d.appendChild(a); }
  d.appendChild(nodo); return d;
}
function selector(pares, valor, alCambiar) {
  const s = document.createElement("select");
  for (const p of pares) { const o = document.createElement("option"); o.value = p[0]; o.textContent = p[0]; s.appendChild(o); }
  s.value = valor; s.addEventListener("change", () => alCambiar(s.value)); return s;
}
function chipsMulti(lista, sel, alCambiar, titulo) {
  const cont = document.createElement("div"); cont.className = "chips-multi";
  const pintar = () => $$(".chip", cont).forEach((c) => c.classList.toggle("on", sel.includes(c.dataset.v)));
  for (const nom of lista) {
    const c = document.createElement("button"); c.type = "button"; c.className = "chip"; c.dataset.v = nom; c.textContent = nom;
    c.addEventListener("click", () => { const i = sel.indexOf(nom); if (i >= 0) sel.splice(i, 1); else sel.push(nom); pintar(); alCambiar(); });
    cont.appendChild(c);
  }
  pintar(); return { cont, todos: () => { sel.splice(0, sel.length, ...lista); pintar(); alCambiar(); }, ninguno: () => { sel.splice(0, sel.length); pintar(); alCambiar(); } };
}
function pintarBrief() {
  const cont = $("#brief-dianchi"); if (!cont || !ajustes) return;
  const b = brief(); cont.innerHTML = "";
  const cambio = () => { guardarBrief(); actualizarContador(); };
  cont.appendChild(campo(1, "Idioma", "", selector(OPC.idiomas, b.idioma, (v) => { b.idioma = v; cambio(); })));
  const ta = document.createElement("textarea"); ta.rows = 3; ta.value = b.tema; ta.placeholder = "Ej: Lifting de pestañas + Tinte, Diseño de cejas con henna…";
  ta.addEventListener("input", () => { b.tema = ta.value; guardarBrief(); });
  cont.appendChild(campo(2, "¿De qué quieres hablar?", "Escribe el servicio, producto o tema principal de tu contenido.", ta));
  const rb = chipsMulti(OPC.rubros, b.rubros, cambio);
  const fr = campo(3, "Rubro (uno o varios)", "", rb.cont, true);
  for (const [txt, fn] of [["Todos", rb.todos], ["Ninguno", rb.ninguno]]) { const m = document.createElement("button"); m.className = "mini"; m.type = "button"; m.textContent = txt; m.addEventListener("click", fn); $("label", fr).appendChild(m); }
  cont.appendChild(fr);
  cont.appendChild(campo(4, "Formato", "", selector(OPC.formatos, b.formato, (v) => { b.formato = v; cambio(); })));
  cont.appendChild(campo(5, "Emoción que quieres proyectar", "", selector(OPC.tonos, b.tono, (v) => { b.tono = v; cambio(); })));
  const tm = chipsMulti(OPC.tematicas.map((t) => t[0]), b.tematicas, cambio);
  const ft = campo(6, "Temática (una o varias)", "", tm.cont, true);
  for (const [txt, fn] of [["Todas", tm.todos], ["Ninguna", tm.ninguno]]) { const m = document.createElement("button"); m.className = "mini"; m.type = "button"; m.textContent = txt; m.addEventListener("click", fn); $("label", ft).appendChild(m); }
  cont.appendChild(ft);
  const tn = document.createElement("input"); tn.value = b.tendencia; tn.placeholder = "Escribe la tendencia o temática específica que quieres tratar…";
  tn.addEventListener("input", () => { b.tendencia = tn.value; guardarBrief(); });
  cont.appendChild(campo(7, "Tendencia (opcional)", "", tn));
  cont.appendChild(campo(8, "Gancho", "", selector(OPC.ganchos, b.gancho, (v) => { b.gancho = v; cambio(); })));
  cont.appendChild(campo(9, "¿Qué quieres que haga el usuario?", "", selector(OPC.ctas, b.cta, (v) => { b.cta = v; cambio(); })));
  const rg = document.createElement("div"); rg.className = "rango";
  const ir_ = document.createElement("input"); ir_.type = "range"; ir_.min = 10; ir_.max = 30; ir_.value = b.duracion;
  const bd = document.createElement("span"); bd.className = "badge"; bd.textContent = b.duracion + " seg";
  ir_.addEventListener("input", () => { b.duracion = Number(ir_.value); bd.textContent = b.duracion + " seg"; guardarBrief(); });
  rg.appendChild(ir_); rg.appendChild(bd);
  cont.appendChild(campo("", "Duración", "Dianchi limita los videos a 30 segundos.", rg));
  const vs = selector([["1"], ["2"], ["3"], ["4"], ["5"]], String(b.variaciones), (v) => { b.variaciones = Number(v); cambio(); });
  cont.appendChild(campo("", "Variaciones por combinación", "Cuántos guiones distintos (otro gancho y otro ángulo) por cada rubro × temática.", vs));
  actualizarContador();
}
function textoBrief() {
  const b = brief(), n = totalVideos();
  const g = OPC.ganchos.find((x) => x[0] === b.gancho), f = OPC.formatos.find((x) => x[0] === b.formato), t = OPC.tonos.find((x) => x[0] === b.tono), ct = OPC.ctas.find((x) => x[0] === b.cta);
  const voz = OPC.idiomas.find((x) => x[0] === b.idioma)[1];
  const combos = []; for (const r of b.rubros) for (const tm of b.tematicas) for (let v = 1; v <= b.variaciones; v++) combos.push("- " + r + " · " + tm + (b.variaciones > 1 ? " · variación " + v : ""));
  return "Crea " + n + " guion" + (n === 1 ? "" : "es") + " nuevo" + (n === 1 ? "" : "s") + " para Dianchi y agrégalos a la lista RUBROS de scripts/dianchi_lote.py, con el mismo formato que los existentes (escenas con consultas de Pexels, collage, píldoras de pasos, globo de objeción, marcar). "
    + "Antes lee prompt/AJUSTES.md y prompt/rubros_hechos.md y no repitas lo ya hecho.\n\nOPCIONES (las mismas del formulario de Dianchi):\n"
    + "- Idioma: " + b.idioma + (b.idioma === "Español" ? "" : " (usa el parámetro voz=\"" + voz + "\" en cada entrada)") + "\n"
    + (b.tema.trim() ? "- De qué hablar: " + b.tema.trim() + "\n" : "")
    + "- Rubros: " + b.rubros.join(", ") + "\n"
    + "- Temáticas: " + b.tematicas.map((x) => x + " (" + OPC.tematicas.find((y) => y[0] === x)[1] + ")").join("; ") + "\n"
    + "- Formato: " + f[0] + " → " + f[1] + "\n- Emoción: " + t[0] + " → " + t[1] + "\n"
    + (b.tendencia.trim() ? "- Tendencia: " + b.tendencia.trim() + "\n" : "")
    + "- Gancho: " + g[0] + " → " + g[1] + "\n"
    + "- Acción del usuario: " + ct[0] + " → " + ct[1] + " Usa cta_tipo=\"" + ct[2] + "\" y haz que la frase final del guion EMPIECE con «" + ct[3] + "».\n"
    + "- Duración objetivo: " + b.duracion + " segundos (máximo 30; unas 2,5 palabras por segundo).\n"
    + "- Variaciones por combinación: " + b.variaciones + (b.variaciones > 1 ? " (cada una con otro gancho y otro ángulo)" : "") + "\n\n"
    + "Genera una entrada por combinación (" + n + " en total):\n" + (n <= 40 ? combos.join("\n") : combos.slice(0, 40).join("\n") + "\n… (y el resto del producto cartesiano)") + "\n\n"
    + "Al terminar: agrega los slugs nuevos a prompt/rubros_hechos.md, ejecuta la verificación (dianchi_lote.py … verificar) para comprobar tiempos y choques, y avísame para que los marque en la app (botón «Recargar lista»).";
}
$("#b-crear-guiones").addEventListener("click", () => {
  if (!totalVideos()) return escribir("Elige al menos un rubro y una temática para crear guiones.");
  enviarClaude("dianchi", textoBrief());
});
function actualizarContadorLista() {
  const el = $("#contador-lista"); if (!el) return;
  const n = $$("#lista-dianchi input:checked").length, tot = $$("#lista-dianchi input").length;
  el.className = "contador" + (n ? "" : " vacio");
  el.innerHTML = n ? "Se generarán <b>" + n + "</b> de " + tot + " video" + (tot === 1 ? "" : "s") + " de la lista (≈ " + n * 5 + " min)." : "Marca los guiones que quieres convertir en video.";
}

// ---------------------------------------------------------------- asistente de Dianchi
let pasoDianchi = 1;
const TOTAL_PASOS = 6;
function irPasoDianchi(n) {
  if (n > pasoDianchi && pasoDianchi === 1 && !$$("#lista-dianchi input:checked").length) return escribir("Marca al menos un guion para continuar.");
  pasoDianchi = Math.max(1, Math.min(TOTAL_PASOS, n));
  $$("#v-dianchi .paso").forEach((p) => p.classList.toggle("oculto", Number(p.dataset.p) !== pasoDianchi));
  $$("#pasos-dianchi li").forEach((li) => { const k = Number(li.dataset.p); li.classList.toggle("act", k === pasoDianchi); li.classList.toggle("hecho", k < pasoDianchi); });
  $("#w-atras").classList.toggle("oculto", pasoDianchi === 1);
  $("#w-sig").classList.toggle("oculto", pasoDianchi === TOTAL_PASOS);
  if (pasoDianchi === TOTAL_PASOS) resumenDianchi();
}
function resumenDianchi() {
  const r = $("#resumen-dianchi"); if (!r || !ajustes) return;
  const sel = $$("#lista-dianchi input:checked").length, p = ajustes.presets, d = ajustes.dirs, ev = p.eventos;
  const voz = (VOCES.find((v) => v[0] === p.voz) || [0, p.voz])[1];
  const si = (b) => (b ? "sí" : "no");
  const carpeta = (x) => x || "dentro de la carpeta de trabajo";
  r.innerHTML = "";
  for (const [k, v] of [
    ["Guiones", sel + " de la lista marcado(s) · voz " + voz + (totalVideos() ? " · " + totalVideos() + " por crear con Claude (" + brief().rubros.length + " rubros × " + brief().tematicas.length + " temáticas × " + brief().variaciones + " variaciones)" : "")],
    ["Eventos", "efectos " + si(p.efectos) + " · objeción " + si(ev.burbuja) + " · pasos " + si(ev.pasos) + " · collage " + si(ev.collage) + " · sonidos " + si(ev.sfx) + " · tarjeta final " + si(ev.cierre)],
    ["Imágenes", carpeta(d.imagenes) + (p.imagenesCollage ? " (se usan en el collage)" : "")],
    ["Videos", carpeta(d.relleno) + (p.rellenoLocal ? " (se usan como relleno)" : " (se descargan de Pexels)")],
    ["Resultados", carpeta(d.dianchiResultado)],
  ]) { const f = document.createElement("div"); f.innerHTML = "<b></b>: <span></span>"; $("b", f).textContent = v === undefined ? "" : k; $("span", f).textContent = v; r.appendChild(f); }
}
$("#w-sig").addEventListener("click", () => irPasoDianchi(pasoDianchi + 1));
$("#w-atras").addEventListener("click", () => irPasoDianchi(pasoDianchi - 1));
$$("#pasos-dianchi li").forEach((li) => li.addEventListener("click", () => irPasoDianchi(Number(li.dataset.p))));
$("#lista-dianchi").addEventListener("change", () => { resumenDianchi(); actualizarContadorLista(); });
$("#b-generar-todo").addEventListener("click", async () => {
  const slugs = $$("#lista-dianchi input:checked").map((c) => c.value);
  if (!slugs.length) return escribir("Marca al menos un guion en el paso 1.");
  for (const modo of ["verificar", "descargar", "render"]) {
    const r = await window.ctv.run({ linea: "dianchi", modo, slugs });
    if (!r || !r.ok) return escribir("⚠ Se detuvo en «" + modo + "»" + (r && r.error ? ": " + r.error : ". Revisa el registro."));
  }
  escribir("✔ Videos de Dianchi generados. Revisa la carpeta de resultados.");
});

// ---------------------------------------------------------------- Claude Code
$$(".chip").forEach((c) => c.addEventListener("click", () => { $("#txt-claude").value = c.dataset.p; $("#txt-claude").focus(); }));
async function enviarClaude(linea, texto) {
  if (!texto.trim()) return escribir("Escribe una instrucción primero.");
  const cs = await window.ctv.claudeStatus();
  if (cs.instalado && !cs.sesion) { ir("claude"); actualizarCuenta(); return escribir("⚠ Primero inicia sesión en Claude con tu cuenta (botón «Iniciar sesión» arriba)."); }
  const r = await window.ctv.openClaude({ linea, instruccion: texto });
  escribir(r.ok ? "Claude Code abierto en una ventana nueva." : "⚠ " + r.error);
}
$("#b-claude").addEventListener("click", () => enviarClaude($("#sel-linea").value, $("#txt-claude").value));
$("#b-cortar").addEventListener("click", () => enviarClaude("por-cortar", $("#txt-cortar").value));

// ---------------------------------------------------------------- ajustes
// Las carpetas y opciones se eligen en la misma pantalla de cada tipo de edicion y se guardan solas.
const NOMBRES_DIRS = {
  dianchiResultado: "Resultados de Dianchi", imagenes: "Carpeta de imágenes", relleno: "Videos de relleno",
  diegaoResultado: "Resultados de Diegao", diegaoFuente: "Videos fuente (evento)",
  cortarEntrada: "Video a cortar (entrada)", cortarResultado: "Resultados de los cortes",
};
const SECCIONES = {
  "dianchi-imagenes": ["imagenes"],
  "dianchi-videos": ["relleno"],
  "dianchi-resultados": ["dianchiResultado"],
  diegao: ["diegaoResultado", "diegaoFuente"],
  cortar: ["cortarEntrada", "cortarResultado"],
};
const VOCES = [["es-MX-JorgeNeural", "Jorge (México, hombre)"], ["es-MX-DaliaNeural", "Dalia (México, mujer)"], ["es-CO-GonzaloNeural", "Gonzalo (Colombia, hombre)"], ["es-CO-SalomeNeural", "Salomé (Colombia, mujer)"], ["es-ES-AlvaroNeural", "Álvaro (España, hombre)"]];
$$(".sel-voz").forEach((s) => { for (const [v, n] of VOCES) { const o = document.createElement("option"); o.value = v; o.textContent = n; s.appendChild(o); } });
async function guardarAuto() {
  ajustes = await window.ctv.saveSettings(ajustes);
  pintarSecciones();
}
function pintarSecciones() {
  for (const [sec, claves] of Object.entries(SECCIONES)) {
    const c = $("#cfg-" + sec); c.innerHTML = "";
    for (const k of claves) {
      const f = document.createElement("div"); f.className = "fila";
      f.innerHTML = '<span class="et-f"></span><input readonly placeholder="(carpeta predeterminada dentro de la carpeta de trabajo)" /><button data-k="' + k + '">Elegir</button><button data-x="' + k + '">Quitar</button>';
      $(".et-f", f).textContent = NOMBRES_DIRS[k]; $("input", f).value = ajustes.dirs[k] || "";
      c.appendChild(f);
    }
    $$("[data-k]", c).forEach((b) => b.addEventListener("click", async () => {
      const p = await window.ctv.pickFolder(NOMBRES_DIRS[b.dataset.k]); if (!p) return;
      ajustes.dirs[b.dataset.k] = p; guardarAuto();
    }));
    $$("[data-x]", c).forEach((b) => b.addEventListener("click", () => { ajustes.dirs[b.dataset.x] = ""; guardarAuto(); }));
  }
  $("#pr-efectos").checked = !!ajustes.presets.efectos;
  $("#pr-relleno").checked = !!ajustes.presets.rellenoLocal;
  $("#pr-imagenes").checked = !!ajustes.presets.imagenesCollage;
  for (const k of ["burbuja", "pasos", "collage", "sfx", "cierre"]) $("#ev-" + k).checked = ajustes.presets.eventos[k] !== false;
  resumenDianchi();
  $$(".sel-voz").forEach((s) => (s.value = ajustes.presets.voz));
}
$("#pr-imagenes").addEventListener("change", (e) => { ajustes.presets.imagenesCollage = e.target.checked; guardarAuto(); });
for (const k of ["burbuja", "pasos", "collage", "sfx", "cierre"]) $("#ev-" + k).addEventListener("change", (e) => { ajustes.presets.eventos[k] = e.target.checked; guardarAuto(); });
$("#pr-efectos").addEventListener("change", (e) => { ajustes.presets.efectos = e.target.checked; guardarAuto(); });
$("#pr-relleno").addEventListener("change", (e) => { ajustes.presets.rellenoLocal = e.target.checked; guardarAuto(); });
$$(".sel-voz").forEach((s) => s.addEventListener("change", (e) => { ajustes.presets.voz = e.target.value; guardarAuto(); }));

function pintarAjustes() {
  pintarSecciones();
  pintarBrief();
  $("#in-ws").value = ajustes.workspace;
  $("#in-pexels").value = ajustes.pexelsKey || "";
  const inc = ajustes.incluidas || {};                       // claves que vienen incluidas: ni se muestran ni se piden
  $("#bloque-pexels").classList.toggle("oculto", !!inc.pexels);
  $("#bloque-gh").classList.toggle("oculto", !!inc.github);
  $("#bloque-claves").classList.toggle("oculto", !!inc.pexels && !!inc.github);
  $("#in-gh").value = ajustes.githubToken || "";
  $("#pr-auto").checked = ajustes.autoUpdate !== false;
}
$("[data-ws]").addEventListener("click", async () => { const p = await window.ctv.pickFolder("Carpeta de trabajo"); if (p) { ajustes.workspace = p; $("#in-ws").value = p; } });
$("#b-guardar").addEventListener("click", async () => {
  ajustes.pexelsKey = $("#in-pexels").value.trim(); ajustes.githubToken = $("#in-gh").value.trim(); ajustes.autoUpdate = $("#pr-auto").checked;
  ajustes = await window.ctv.saveSettings(ajustes);
  $("#msg-guardar").textContent = "Guardado ✔";
  setTimeout(() => ($("#msg-guardar").textContent = ""), 2500);
});

// ---------------------------------------------------------------- entorno
const ITEMS_ENTORNO = [
  ["uv", "uv (Python)", "ffmpeg-uv", "uv"],
  ["ffmpeg", "FFmpeg", "ffmpeg", "ffmpeg"],
  ["node", "Node.js (hyperframes)", "node", "node"],
  ["claude", "Claude Code", null, null],
  ["pexels", "Clave de Pexels", null, null],
];
async function instalarTodo() {
  const r = await window.ctv.installAll();
  if (r && r.error) escribir("⚠ " + r.error);
  comprobarEntorno();
}
$("#b-instalar-todo").addEventListener("click", instalarTodo);
$("#b-instalar-todo2").addEventListener("click", instalarTodo);
async function comprobarEntorno() {
  const e = await window.ctv.checkEnv();
  const cs = await window.ctv.claudeStatus();
  const faltan = [["uv", "uv (Python)"], ["ffmpeg", "FFmpeg"], ["node", "Node.js"], ["claude", "Claude Code"]].filter(([k]) => !e[k]).map(([, n]) => n);
  $("#banner-falta").classList.toggle("oculto", !faltan.length);
  $("#txt-faltan").textContent = faltan.length ? "Falta: " + faltan.join(", ") + "." : "";
  for (const cont of [$("#lista-entorno"), $("#estado-entorno")]) {
    cont.innerHTML = "";
    for (const [k, nombre, , instalar] of ITEMS_ENTORNO) {
      if (k === "pexels" && ajustes && ajustes.incluidas && ajustes.incluidas.pexels) continue;
      const ok = !!e[k]; const f = document.createElement("div"); f.className = "estado" + (ok ? " ok" : "");
      f.innerHTML = '<span class="pt"></span><span class="n"></span><span class="r"></span>';
      $(".n", f).textContent = nombre;
      $(".r", f).textContent = ok ? (typeof e[k] === "string" ? e[k] : "listo") : k === "claude" ? "No instalado: instálalo desde claude.com/claude-code e inicia sesión" : k === "pexels" ? "Pégala en Ajustes → Claves" : "Falta";
      if (!ok && instalar && cont.id === "lista-entorno") {
        const b = document.createElement("button"); b.textContent = "Instalar"; b.addEventListener("click", async () => { await window.ctv.installDep(instalar); comprobarEntorno(); }); f.appendChild(b);
      }
      if (!ok && k === "claude" && cont.id === "lista-entorno") {
        const b = document.createElement("button"); b.textContent = "Ver cómo"; b.addEventListener("click", () => window.ctv.openUrl("https://docs.claude.com/en/docs/claude-code/setup")); f.appendChild(b);
      }
      cont.appendChild(f);
    }
    if (cs.instalado) {                                         // sesion de Claude Code
      const f = document.createElement("div"); f.className = "estado" + (cs.sesion ? " ok" : "");
      f.innerHTML = '<span class="pt"></span><span class="n">Sesión de Claude</span><span class="r"></span>';
      $(".r", f).textContent = cs.sesion ? "Iniciada" + (cs.email ? " (" + cs.email + ")" : "") : "Sin iniciar sesión";
      if (!cs.sesion) { const b = document.createElement("button"); b.textContent = "Iniciar sesión"; b.addEventListener("click", iniciarSesion); f.appendChild(b); }
      cont.appendChild(f);
    }
  }
}
$("#b-entorno").addEventListener("click", comprobarEntorno);

// ---------------------------------------------------------------- cuenta de Claude
async function actualizarCuenta() {
  const cs = await window.ctv.claudeStatus();
  const t = $("#txt-cuenta");
  $("#b-login").classList.toggle("oculto", !cs.instalado || cs.sesion);
  $("#b-logout").classList.toggle("oculto", !cs.sesion);
  t.textContent = !cs.instalado ? "Claude Code no está instalado (usa «Instalar todo lo que falta» en Ajustes)." : cs.sesion ? "● Sesión iniciada" + (cs.email ? " como " + cs.email : "") : "● Sin sesión iniciada";
  return cs;
}
let esperandoLogin = null;
let urlLogin = "";
async function iniciarSesion() {
  ir("claude");
  const r = await window.ctv.claudeLogin();
  if (!r.ok) return escribir("⚠ " + r.error);
  escribir("Iniciando sesión de Claude… se abrirá el navegador; si no, usa el enlace que aparece en esta pantalla.");
  if (esperandoLogin) clearInterval(esperandoLogin);
  let n = 0;
  esperandoLogin = setInterval(async () => {
    n++; const cs = await window.ctv.claudeStatus();
    if (cs.sesion || n > 90) {
      clearInterval(esperandoLogin); esperandoLogin = null;
      $("#login-ayuda").classList.add("oculto"); actualizarCuenta(); comprobarEntorno();
      if (cs.sesion) escribir("Sesión de Claude iniciada ✔");
    }
  }, 4000);
}
window.ctv.onLoginUrl(({ url }) => { urlLogin = url; $("#login-url").value = url; $("#login-ayuda").classList.remove("oculto"); });
window.ctv.onLoginFin(({ ventana }) => { if (ventana) escribir("Se abrió una ventana de comandos para iniciar sesión: sigue sus instrucciones."); });
$("#b-url-abrir").addEventListener("click", () => urlLogin && window.ctv.openUrl(urlLogin));
$("#b-url-copiar").addEventListener("click", async () => { if (urlLogin) { await window.ctv.copiar(urlLogin); escribir("Enlace copiado: pégalo en tu navegador."); } });
$("#b-codigo").addEventListener("click", async () => { const v = $("#login-codigo").value.trim(); if (!v) return; await window.ctv.claudeLoginCode(v); $("#login-codigo").value = ""; escribir("Código enviado."); });
$("#b-login-ventana").addEventListener("click", () => window.ctv.claudeLoginVentana());
$("#b-login").addEventListener("click", iniciarSesion);
$("#b-logout").addEventListener("click", async () => { await window.ctv.claudeLogout(); actualizarCuenta(); comprobarEntorno(); });
$("#b-cuenta").addEventListener("click", () => { actualizarCuenta(); comprobarEntorno(); });

// ---------------------------------------------------------------- actualizaciones
let ultimaInfo = null;
function mostrarUpd(i) {
  ultimaInfo = i;
  const aviso = $("#aviso-upd"), txt = $("#txt-upd"), btn = $("#b-upd-ir");
  if (!i.ok) { txt.textContent = i.motivo; aviso.classList.add("oculto"); btn.disabled = true; return; }
  if (i.hay) {
    txt.textContent = "Hay una versión nueva (" + i.corto + "): " + i.mensaje;
    aviso.textContent = "Actualización disponible (" + i.corto + "). Clic para ver."; aviso.classList.remove("oculto"); btn.disabled = false;
  } else { txt.textContent = "Estás al día (" + i.actual + ")."; aviso.classList.add("oculto"); btn.disabled = true; }
}
window.ctv.onUpdate(mostrarUpd);
$("#aviso-upd").addEventListener("click", () => ir("ajustes"));
$("#b-upd").addEventListener("click", async () => { $("#txt-upd").textContent = "Buscando…"; mostrarUpd(await window.ctv.checkUpdate()); });
$("#b-upd-ir").addEventListener("click", async () => {
  $("#b-upd-ir").disabled = true; $("#txt-upd").textContent = "Actualizando…";
  const r = await window.ctv.applyUpdate();
  if (!r.ok) { $("#txt-upd").textContent = r.motivo || "No se pudo actualizar."; $("#b-upd-ir").disabled = false; }
});

// ---------------------------------------------------------------- inicio
(async function init() {
  ajustes = await window.ctv.getSettings();
  pintarAjustes();
  const v = await window.ctv.version();
  $("#v-app").textContent = "v" + v.app;
  $("#txt-version").textContent = "App v" + v.app + " · motor: " + v.motor + " · carpeta de trabajo: " + v.workspace;
  comprobarEntorno();
})();
