// Interfaz de CreaTuVideo. Solo habla con el proceso principal mediante window.ctv (ver preload.js).
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
let ajustes = null;
let ocupado = false;
let BL = "dianchi";                                     // linea cuyo formulario/contador esta activo: "dianchi" | "diegao"
const KB = (L = BL) => (L === "diegao" ? "briefDiegao" : "brief");      // donde se guarda el formulario de cada linea
const KD = (L = BL) => (L === "diegao" ? "disenoDiegao" : "diseno");    // y su texto de diseño
function conLinea(L, fn) { const a = BL; BL = L; try { return fn(); } finally { BL = a; } }

// ---------------------------------------------------------------- navegacion
function ir(v) {
  $$(".vista").forEach((e) => e.classList.toggle("activa", e.id === "v-" + v));
  $$(".nav-b").forEach((b) => b.classList.toggle("activo", b.dataset.v === v));
  if (v === "dianchi" || v === "diegao") { BL = v; actualizarContador(); }
  $("#barra-estado").classList.toggle("oculto", v !== "dianchi" && v !== "diegao" && !(gen && !gen.fin));   // el conteo de videos queda fijo al pie, solo en Dianchi y Diegao
  if (v === "ajustes") comprobarEntorno();
  if (v === "claude") { actualizarCuenta(); setTimeout(() => $("#txt-claude").focus(), 50); }
}
$$(".nav-b").forEach((b) => b.addEventListener("click", () => ir(b.dataset.v)));
$$("[data-ir]").forEach((b) => b.addEventListener("click", () => ir(b.dataset.ir)));

// ---------------------------------------------------------------- registro
const logEl = $("#log");
function escribir(t) { logEl.textContent += t + "\n"; if (logEl.textContent.length > 120000) logEl.textContent = logEl.textContent.slice(-80000); logEl.scrollTop = logEl.scrollHeight; }
// progreso de la generacion: el motor imprime "CTV_PROGRESO <modo> <i> <n> <slug>" al empezar cada video
let gen = null;
const FASES_TXT = { preparar: "Preparando voz, tiempos y cortes", verificar: "Verificando tiempos", descargar: "Descargando imágenes y clips", hoja: "Preparando hoja de contacto", render: "Creando los videos" };
function lineaProgreso(l) {
  const m = l.match(/^CTV_PROGRESO (\w+) (\d+) (\d+) (\S+)/); if (!m) return false;
  if (!gen) gen = { plan: 1, render: 0 };
  Object.assign(gen, { modo: m[1], i: Number(m[2]), n: Number(m[3]), slug: m[4], fin: false });
  if (gen.modo === "render") gen.render = Math.max(gen.render, gen.i - 1);
  pintarProgreso(); return true;
}
function pintarProgreso() {
  const el = $("#brief-contador"); if (!el || !gen || !gen.n) return;
  const orden = gen.plan > 1 ? (gen.fases || ["verificar", "descargar", "render"]).indexOf(gen.modo) : 0, fi = Math.max(0, orden);
  const hechasFase = gen.fin && !gen.detenido ? gen.n : gen.i - 1;
  const pct = Math.min(100, Math.round(((fi * gen.n + hechasFase) / (gen.plan * gen.n)) * 100));
  const term = gen.modo === "render" ? (gen.fin && !gen.detenido ? gen.n : gen.render) : (gen.plan > 1 || gen.fin ? gen.render : 0);
  const faltan = Math.max(0, gen.n - term);
  el.className = "contador fijo progreso";
  el.innerHTML = "";
  const f1 = document.createElement("div"); f1.className = "prog-fila";
  const a = document.createElement("span"); a.innerHTML = (gen.fin ? "✔ " : "") + "<b></b>"; a.querySelector("b").textContent = (gen.fin && gen.modo === "render" ? "Listo: videos generados" : (FASES_TXT[gen.modo] || "Procesando") + (gen.plan > 1 ? " (fase " + (fi + 1) + " de " + gen.plan + ")" : ""));
  const b = document.createElement("span"); b.textContent = gen.fin ? "Terminado" : "Video " + Math.min(gen.i, gen.n) + " de " + gen.n + " · " + gen.slug;
  if (gen.detenido) { a.innerHTML = "<b>Proceso detenido</b>"; b.textContent = "Se canceló lo que faltaba"; }
  f1.appendChild(a); f1.appendChild(b);
  if (!gen.fin) { const d = document.createElement("button"); d.type = "button"; d.className = "peligro mini-b"; d.textContent = "■ Detener"; d.addEventListener("click", detener); f1.appendChild(d); }
  const bar = document.createElement("div"); bar.className = "prog-barra"; bar.innerHTML = "<i></i>"; bar.firstChild.style.width = pct + "%";
  const f2 = document.createElement("div"); f2.className = "prog-fila chico"; f2.textContent = "Generados: " + term + " de " + gen.n + " · Faltan: " + faltan + " · " + pct + " %";
  el.appendChild(f1); el.appendChild(bar); el.appendChild(f2);
}
window.ctv.onLog((t) => {
  for (const l of String(t).split(/\r?\n/)) { const m = l.match(/^OK (.+(?:infografia|animtexto)_.+\.mp4)\s*$/); if (m) ifVideoListo(m[1]); }
  const limpias = String(t).split(/\r?\n/).filter((l) => !lineaProgreso(l));
  if (limpias.length) escribir(limpias.join("\n"));
});
window.ctv.onBusy((b) => {
  ocupado = b;
  bloqueoActualizar(b);
  if (!b && gen) { if (gen.plan === 1) { gen.fin = true; gen.detenido = detenido; pintarProgreso(); gen = null; } }
  if (!b) detenido = false;
  $("#ind-busy").classList.toggle("oculto", !b);
  $("#b-cancel").disabled = !b;
  $$("[data-run], .run-pr, #b-upd-ir").forEach((x) => { if (b) x.disabled = true; else if (x.id !== "b-upd-ir") x.disabled = false; });
});
$("#b-limpiar").addEventListener("click", () => (logEl.textContent = ""));
$("#b-cancel").addEventListener("click", () => window.ctv.cancel());

// ---------------------------------------------------------------- iconos (SVG en linea)
const ICO = {
  auto: '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
  carpeta: '<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  guion: '<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></svg>',
  eventos: '<svg viewBox="0 0 24 24"><path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></svg>',
  imagen: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.8"/><path d="m21 16-5-5-9 9"/></svg>',
  video: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/></svg>',
  resultados: '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0-4-4m4 4 4-4M5 19h14"/></svg>',
  diseno: '<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 0 18c1.1 0 2-.9 2-2 0-.6-.2-1-.6-1.4-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2H17a4 4 0 0 0 4-4c0-4-4-7.3-9-7.3z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7" r="1"/></svg>',
  generar: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m10 8.5 5 3.5-5 3.5z"/></svg>',
  aviso: '<svg viewBox="0 0 24 24"><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/></svg>',
  dianchi: '<svg viewBox="0 0 24 24"><circle cx="12" cy="9" r="6"/><path d="M12 15v6M9 21h6M9.5 7a3 3 0 0 1 2-1.5"/></svg>',
  inicio: '<svg viewBox="0 0 24 24"><path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>',
  cortar: '<svg viewBox="0 0 24 24"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/></svg>',
  claude: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/></svg>',
  ajustes: '<svg viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
  animtexto: '<svg viewBox="0 0 24 24"><path d="M4 6V4h12v2M10 4v12M7 16h6"/><path d="M16 12h4M18 12v8M16 20h4"/><path d="m19 4 .5 1.2L20.7 5.7l-1.2.5L19 7.4l-.5-1.2-1.2-.5 1.2-.5z"/></svg>',
  infografia: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 17v-4M12 17V8M17 17v-6"/><path d="m15 5.5.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z"/></svg>',
  precio: '<svg viewBox="0 0 24 24"><path d="M3 10v4a1 1 0 0 0 1 1h3l11 5V4L7 9H4a1 1 0 0 0-1 1z"/><path d="M7 15l1.4 4.2a1 1 0 0 0 1 .8h1a1 1 0 0 0 1-1.2L10.5 16.5M21 9.5v5"/></svg>',
  diegao: '<svg viewBox="0 0 24 24"><path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11.2V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.8M22 9v6"/></svg>',
  clienta: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
  duena: '<svg viewBox="0 0 24 24"><path d="M3 9 5 4h14l2 5"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M5 12v8h14v-8M10 20v-4h4v4"/></svg>',
};
function pintarIconos() {
  $$("[data-ico]").forEach((e) => { e.classList.add("ico"); e.innerHTML = ICO[e.dataset.ico] || ""; });
  const orden = ["guion", "eventos", "imagen", "video", "resultados", "diseno", "generar"];
  $$("#pasos-dianchi li").forEach((li, i) => { if (li.querySelector(".ico")) return; const s = document.createElement("span"); s.className = "ico"; s.innerHTML = ICO[orden[i]]; li.prepend(s); });
  const ordenD = ["guion", "eventos", "imagen", "video", "resultados", "diseno", "generar"];
  $$("#pasos-diegao li").forEach((li, i) => { if (li.querySelector(".ico")) return; const s = document.createElement("span"); s.className = "ico"; s.innerHTML = ICO[ordenD[i]]; li.prepend(s); });
}

// ---------------------------------------------------------------- listas de videos del lote
const listas = { dianchi: [], diegao: [] };
async function cargarLista(linea, forzar) {
  const cont = $("#lista-" + linea); if (!cont) return;
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
}
$$("[data-acc]").forEach((b) => b.addEventListener("click", () => {
  const l = b.dataset.l;
  if (b.dataset.acc === "recargar") return cargarLista(l, true);
  $$("#lista-" + l + " input").forEach((c) => (c.checked = b.dataset.acc === "seleccionar"));
}));
$$("[data-run]").forEach((b) => b.addEventListener("click", async () => {
  if (!(await exigirUltimaVersion())) return;
  const [linea, modo] = b.dataset.run.split(":");
  const slugs = $$("#lista-" + linea + " input:checked").map((c) => c.value);
  gen = { plan: 1, render: 0 };
  const r = await window.ctv.run({ linea, modo, slugs });
  if (r && r.error) escribir("⚠ " + r.error);
}));
const DIR_RESULTADOS = { "dianchi/resultado": "dianchiResultado", "diegao/resultado": "diegaoResultado", "precios/resultado": "preciosResultado", "infografias/resultado": "infografiasResultado", "animtexto/resultado": "animtextoResultado", "por-cortar/resultado": "cortarResultado" };
// "Abrir resultados" abre la carpeta que el usuario eligio (si no eligio ninguna, la predeterminada dentro de la carpeta de trabajo)
$$("[data-abrir]").forEach((b) => b.addEventListener("click", () => window.ctv.openPath((ajustes && ajustes.dirs && ajustes.dirs[DIR_RESULTADOS[b.dataset.abrir]]) || b.dataset.abrir || (ajustes && ajustes.workspace) || "")));

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
// temáticas de Diegao (para dueñas de salón); las de Dianchi (para clientas) están en OPC.tematicas
OPC.tematicasDuenas = [
  ["Finanzas", "dinero del salón: precios, costos, ganancia, ahorro, cobros y deudas"],
  ["Administración", "orden del negocio: control, registros, tiempos, inventario, agenda y organización diaria"],
  ["Estrategia", "rumbo del negocio: posicionamiento, oferta, crecimiento, decisiones y diferenciación"],
  ["Fidelización", "lograr que las clientas vuelvan: seguimiento, recompra, membresías y relación a largo plazo"],
  ["Atención al cliente", "cómo tratar y escuchar a la clienta, resolver quejas y dar una experiencia memorable"],
  ["Protocolos", "procesos y estándares del salón: pasos fijos de atención, higiene, cierre y puesta en marcha"],
  ["Estructura", "cómo se arma el negocio: roles, equipo, delegación, horarios y organización interna"],
  ["Espiritualidad", "propósito, fe, gratitud, energía y sentido de lo que hace la dueña con su negocio"],
  ["Mentalidad", "creencias, miedos, disciplina y hábitos mentales de la dueña como emprendedora"],
];
OPC.rubrosDuenas = ["Salones de belleza", "Peluquería", "Estéticas", "Clínicas", "Independientes", "Servicio a domicilio"];   // tipo de negocio de la dueña (Diegao)
const RUBROS_L = (L = BL) => (L === "diegao" ? OPC.rubrosDuenas : OPC.rubros);
const TEMAS = (L = BL) => (L === "diegao" ? OPC.tematicasDuenas : OPC.tematicas);
const BRIEF0 = { idioma: "Español", problemasAuto: true, rubros: [], formatos: [OPC.formatos[0][0]], tonos: ["Cercano"], tematicas: [], problemas: [], ganchos: [OPC.ganchos[0][0]], ctas: ["Que lo guarde"], duracion: 25, variaciones: 1 };
// dimensiones que se combinan: [clave, singular, plural]
const DIMS = [["rubros", "rubro", "rubros"], ["tematicas", "temática", "temáticas"], ["formatos", "formato", "formatos"], ["ganchos", "gancho", "ganchos"], ["ctas", "acción", "acciones"]];
function brief() {                               // siempre el MISMO objeto, completando solo lo que falte
  const p = ajustes.presets;
  const kb = KB();
  if (!p[kb]) p[kb] = { ...BRIEF0, rubros: [], tematicas: [], formatos: [...BRIEF0.formatos], tonos: [...BRIEF0.tonos], ganchos: [...BRIEF0.ganchos], ctas: [...BRIEF0.ctas] };
  const b = p[kb];
  for (const [nuevo, viejo] of [["formatos", "formato"], ["tonos", "tono"], ["ganchos", "gancho"], ["ctas", "cta"]])   // version anterior: un solo valor
    if (!Array.isArray(b[nuevo]) && typeof b[viejo] === "string" && b[viejo]) b[nuevo] = [b[viejo]];
  if (!Array.isArray(b.problemas)) b.problemas = [];
  { const okR = RUBROS_L(); const vr = b.rubros.filter((x) => okR.includes(x)); if (vr.length !== b.rubros.length) b.rubros.splice(0, b.rubros.length, ...vr); }
  { const ok = TEMAS().map((x) => x[0]); const v = b.tematicas.filter((x) => ok.includes(x)); if (v.length !== b.tematicas.length) b.tematicas.splice(0, b.tematicas.length, ...v); }   // quita temáticas que ya no existen en la lista de esta línea
  if (typeof b.tema === "string" && b.tema.trim() && !b.problemas.includes(b.tema.trim())) { b.problemas.push(b.tema.trim()); b.tema = ""; }   // el antiguo "de qué hablar" pasa a ser un problema
  if (!("problemasAuto" in b)) b.problemasAuto = !b.problemas.length;
  if (!Array.isArray(b.problemas) && typeof b.tendencia === "string" && b.tendencia.trim()) b.problemas = [b.tendencia.trim()];
  for (const k of Object.keys(BRIEF0)) if (!(k in b)) b[k] = Array.isArray(BRIEF0[k]) ? [...BRIEF0[k]] : BRIEF0[k];
  return b;
}
let tGuardarBrief = null;
function guardarBrief() { clearTimeout(tGuardarBrief); tGuardarBrief = setTimeout(() => window.ctv.saveSettings(ajustes), 500); }
const problemasEf = (b) => (b.problemasAuto ? [] : b.problemas);
const totalVideos = () => { const b = brief(); let n = (Number(b.variaciones) || 1) * (b.problemasAuto ? 1 : b.problemas.length); for (const [k] of DIMS) { if (!b[k].length) return 0; n *= b[k].length; } return n; };
function desgloseBrief() {
  const b = brief(), partes = DIMS.filter(([k]) => b[k].length > 1).map(([k, s, p]) => b[k].length + " " + p);
  if (!b.problemasAuto && b.problemas.length > 1) partes.push(b.problemas.length + " problemas");
  if (Number(b.variaciones) > 1) partes.push(b.variaciones + " variaciones");
  return partes.length ? partes.join(" × ") : "una sola combinación";
}
const FALTA = () => { const b = brief(), f = DIMS.filter(([k]) => !b[k].length).map(([k, s]) => s); if (!b.problemasAuto && !b.problemas.length) f.push("temática o problema (o activa Automático)"); return f.length ? "Elige al menos un valor en: " + f.join(", ") + "." : ""; };

function actualizarContador() {
  if (gen && !gen.fin) return;
  const b = brief(), el = $("#brief-contador"), n = totalVideos();
  el.className = "contador" + (n ? "" : " vacio");
  const pexels = BL === "dianchi";
  el.classList.toggle("clic", !n); el.title = n ? "" : "Ir al paso 1";
  if (!n) { el.innerHTML = '<span class="ico">' + ICO.aviso + "</span>"; el.appendChild(document.createTextNode("Falta completar el paso 1. " + FALTA().replace("Elige al menos un valor en: ", "Elige al menos uno en: ") + " Así se calcula cuántos videos se procesarán.")); return resumenDianchi(); }
  const min = n * 5;
  el.innerHTML = "Se procesarán <b>" + n + "</b> video" + (n === 1 ? "" : "s") + " — " + desgloseBrief()
    + "<br><span class='chico'>Tiempo estimado: unos " + (min >= 60 ? Math.floor(min / 60) + " h " + (min % 60) + " min" : min + " min") + " (≈ 5 min por video)." + (!pexels || ajustes.presets.rellenoLocal ? "" : " Descarga ≈ " + n * 80 + " solicitudes de Pexels (cupo: 20.000 al mes).") + "</span>"
    + (n > 16 ? "<br><span class='aviso-n'>⚠ Son muchos videos: conviene hacerlos en lotes de 16 o menos.</span>" : "");
  resumenDianchi();
}
let nCampo = 0;
function campo(num, titulo, ayuda, nodo, ancho) {
  if (num) num = ++nCampo;
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
function campoMulti(num, titulo, nombres, sel, cambio, plural) {
  const m = chipsMulti(nombres, sel, cambio);
  const f = campo(num, titulo, "", m.cont, true);
  for (const [txt, fn] of [["Todos", m.todos], ["Ninguno", m.ninguno]]) { const x = document.createElement("button"); x.className = "mini"; x.type = "button"; x.textContent = txt; x.addEventListener("click", fn); $("label", f).appendChild(x); }
  return f;
}
function pintarBrief() {
  const cont = $("#brief-" + BL); if (!cont || !ajustes) return;
  const b = brief(); cont.innerHTML = ""; nCampo = 0;
  const cambio = () => { guardarBrief(); actualizarContador(); };
  cont.appendChild(campo(1, "Idioma", "", selector(OPC.idiomas, b.idioma, (v) => { b.idioma = v; cambio(); })));
  const rb = chipsMulti(RUBROS_L(), b.rubros, cambio);
  const fr = campo(3, "Rubro (uno o varios)", "", rb.cont, true);
  for (const [txt, fn] of [["Todos", rb.todos], ["Ninguno", rb.ninguno]]) { const m = document.createElement("button"); m.className = "mini"; m.type = "button"; m.textContent = txt; m.addEventListener("click", fn); $("label", fr).appendChild(m); }
  cont.appendChild(fr);
  cont.appendChild(campoMulti(4, "Formato (uno o varios)", OPC.formatos.map((x) => x[0]), b.formatos, cambio));
  const tm = chipsMulti(TEMAS().map((t) => t[0]), b.tematicas, cambio);
  const ft = campo(6, "Temática (una o varias)", "", tm.cont, true);
  for (const [txt, fn] of [["Todas", tm.todos], ["Ninguna", tm.ninguno]]) { const m = document.createElement("button"); m.className = "mini"; m.type = "button"; m.textContent = txt; m.addEventListener("click", fn); $("label", ft).appendChild(m); }
  cont.appendChild(ft);
  const pb = document.createElement("div"); pb.className = "problemas";
  const auto = document.createElement("button"); auto.type = "button"; auto.className = "chip auto";
  const fila = document.createElement("div"); fila.className = "fila";
  const tn = document.createElement("input"); tn.placeholder = "Escribe una temática o problema a resolver y pulsa Enter…";
  const ad = document.createElement("button"); ad.type = "button"; ad.textContent = "Agregar";
  const et = document.createElement("div"); et.className = "etiquetas";
  const pintarEt = () => {
    auto.classList.toggle("on", !!b.problemasAuto); auto.textContent = (b.problemasAuto ? "✓ " : "") + "Automático: la app elige temáticas del rubro al azar";
    tn.disabled = ad.disabled = !!b.problemasAuto; pb.classList.toggle("apagado", !!b.problemasAuto);
    et.innerHTML = ""; b.problemas.forEach((p, i) => { const e = document.createElement("span"); e.className = "etiqueta"; e.appendChild(document.createTextNode(p)); const x = document.createElement("button"); x.type = "button"; x.title = "Quitar"; x.textContent = "×"; x.addEventListener("click", () => { b.problemas.splice(i, 1); pintarEt(); cambio(); }); e.appendChild(x); et.appendChild(e); });
  };
  const agregar = () => { const v = tn.value.trim(); if (!v) return; if (!b.problemas.includes(v)) b.problemas.push(v); tn.value = ""; pintarEt(); cambio(); tn.focus(); };
  auto.addEventListener("click", () => { b.problemasAuto = !b.problemasAuto; pintarEt(); cambio(); });
  ad.addEventListener("click", agregar); tn.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); agregar(); } });
  fila.appendChild(tn); fila.appendChild(ad); pb.appendChild(auto); pb.appendChild(fila); pb.appendChild(et); pintarEt();
  cont.appendChild(campo(7, "Temática o problema a resolver", "Automático, o agrega los tuyos de uno en uno: cada uno se convierte en un guion distinto.", pb, true));
  cont.appendChild(campoMulti(8, "Gancho (uno o varios)", OPC.ganchos.map((x) => x[0]), b.ganchos, cambio));
  cont.appendChild(campoMulti(9, "¿Qué quieres que haga el usuario? (una o varias)", OPC.ctas.map((x) => x[0]), b.ctas, cambio));
  const rg = document.createElement("div"); rg.className = "rango";
  const ir_ = document.createElement("input"); ir_.type = "range"; ir_.min = 10; ir_.max = 30; ir_.value = b.duracion;
  const bd = document.createElement("span"); bd.className = "badge"; bd.textContent = b.duracion + " seg";
  ir_.addEventListener("input", () => { b.duracion = Number(ir_.value); bd.textContent = b.duracion + " seg"; guardarBrief(); });
  rg.appendChild(ir_); rg.appendChild(bd);
  cont.appendChild(campo("", "Duración", "Dianchi limita los videos a 30 segundos.", rg));
  const vs = selector([["1"], ["2"], ["3"], ["4"], ["5"]], String(b.variaciones), (v) => { b.variaciones = Number(v); cambio(); });
  cont.appendChild(campo("", "Variaciones por combinación", "Cuántos guiones distintos (otro ángulo) por cada combinación de lo que elegiste arriba.", vs));
  const td = $(BL === "diegao" ? "#txt-diseno-d" : "#txt-diseno"); if (td && document.activeElement !== td) td.value = ajustes.presets[KD()] || "";
  actualizarContador();
}
const disenoTexto = (L = BL) => ((ajustes && ajustes.presets[KD(L)]) || "").trim();
const NOM_L = { dianchi: "Dianchi", diegao: "Diegao" };
function textoBrief() {
  const L = BL, b = brief(), n = totalVideos();
  const busca = (lista, nombre) => lista.find((x) => x[0] === nombre) || [nombre, ""];
  const voz = OPC.idiomas.find((x) => x[0] === b.idioma)[1];
  const defs = (lista, sel) => sel.map((s) => "  · " + s + " → " + busca(lista, s)[1]).join("\n");
  // una entrada por cada combinacion de las dimensiones elegidas
  let combos = [[]];
  const listas = [b.rubros, b.tematicas, b.formatos, b.ganchos, b.ctas];
  if (!b.problemasAuto) listas.push(b.problemas);
  for (const l of listas) combos = combos.flatMap((c) => l.map((x) => [...c, x]));
  const lineas = [];
  for (const c of combos) for (let v = 1; v <= b.variaciones; v++) {
    const ct = busca(OPC.ctas, c[4]);
    lineas.push("- " + c[0] + " · " + c[1] + " · formato " + c[2] + " · gancho " + c[3] + " · acción " + c[4] + (!b.problemasAuto ? " · problema/temática a resolver: «" + c[5] + "»" : " · temática a resolver: elígela tú al azar, propia del rubro y distinta en cada guion") + " (cta_tipo=\"" + ct[2] + "\", la frase final empieza con «" + ct[3] + "»)" + (b.variaciones > 1 ? " · variación " + v : ""));
  }
  const dg = L === "diegao";
  const intro = dg
    ? "Crea " + n + " guion" + (n === 1 ? "" : "es") + " nuevo" + (n === 1 ? "" : "s") + " para Diegao (videos de mentor PARA DUEÑAS de salón, hablándoles de tú a tú; no es para clientas) y agrégalos a la lista V de scripts/diegao_lote.py, con el mismo formato que los existentes (slug, buenas/malas, rubro, titulo, gancho, guion, burbuja, pasos, pasos_hasta). "
      + "Antes lee diegao/prompt/diegao_mentor.md y diegao/prompt/AJUSTES.md y no repitas los guiones que ya existen.\n\nOPCIONES (las mismas del formulario; cada guion usa UNA combinación de ellas):\n"
    : "Crea " + n + " guion" + (n === 1 ? "" : "es") + " nuevo" + (n === 1 ? "" : "s") + " para Dianchi (videos PARA CLIENTAS) y agrégalos a la lista RUBROS de scripts/dianchi_lote.py, con el mismo formato que los existentes (escenas con consultas de Pexels, collage, píldoras de pasos, globo de objeción, marcar). "
      + "Antes lee prompt/AJUSTES.md y prompt/rubros_hechos.md y no repitas lo ya hecho.\n\nOPCIONES (las mismas del formulario de Dianchi; cada guion usa UNO de cada combinación de ellas):\n";
  const cierre = dg
    ? "Al terminar: escribe SOLO los slugs nuevos (uno por línea, reemplazando el contenido) en diegao/prompt/lote_actual.txt — la app genera los videos de ese archivo — y ejecuta «diegao_lote.py … preparar» con ellos para comprobar tiempos y choques."
    : "Al terminar: agrega los slugs nuevos a prompt/rubros_hechos.md, escribe SOLO esos slugs nuevos (uno por línea, reemplazando el contenido) en prompt/lote_actual.txt — la app genera los videos de ese archivo — y ejecuta la verificación (dianchi_lote.py … verificar) para comprobar tiempos y choques.";
  return intro
    + "- Idioma: " + b.idioma + (b.idioma === "Español" ? "" : " (usa el parámetro voz=\"" + voz + "\" en cada entrada)") + "\n"
    + "- Rubros" + (dg ? " (tipo de salón de la dueña)" : "") + ": " + b.rubros.join(", ") + "\n"
    + "- Temáticas:\n" + defs(TEMAS(), b.tematicas) + "\n"
    + "- Formatos:\n" + defs(OPC.formatos, b.formatos) + "\n"
    + (b.problemasAuto ? "- Temática o problema a resolver: AUTOMÁTICO. Elige tú, al azar, un problema o tema concreto y real " + (dg ? "de una dueña de salón (administración, finanzas, agenda, precios, equipo…)" : "del rubro") + " para cada guion, sin repetir entre guiones" + (dg ? " ni con los que ya existen.\n" : " ni con prompt/rubros_hechos.md.\n") : "- Temáticas o problemas a resolver (cada guion trata UNO): " + b.problemas.map((p) => "«" + p + "»").join("; ") + "\n")
    + "- Ganchos:\n" + defs(OPC.ganchos, b.ganchos) + "\n"
    + "- Acciones del usuario:\n" + defs(OPC.ctas, b.ctas) + "\n"
    + "- Duración objetivo: " + b.duracion + " segundos (máximo 30; unas 2,5 palabras por segundo).\n"
    + "- Variaciones por combinación: " + b.variaciones + (b.variaciones > 1 ? " (cada una con otro ángulo)" : "") + "\n\n"
    + "Genera una entrada por combinación (" + n + " en total), cada una con su propio gancho, formato y cta_tipo:\n" + (n <= 40 ? lineas.join("\n") : lineas.slice(0, 40).join("\n") + "\n… (y el resto de las combinaciones, hasta " + n + ")") + "\n\n"
    + (disenoTexto() ? "\n\nDISEÑO PERSONALIZADO (aplícalo a los videos de este lote): " + disenoTexto() + "\n\n" : "")
    + cierre;
}
// diseño: se guarda por linea y se manda a Claude (aplicar al motor / corregir lo ya generado)
for (const [L, sfx] of [["dianchi", ""], ["diegao", "-d"]]) {
  const nom = NOM_L[L], motor = "scripts/" + L + "_lote.py";
  $("#txt-diseno" + sfx).addEventListener("input", (e) => { ajustes.presets[KD(L)] = e.target.value; guardarBrief(); });
  $("#b-diseno-aplicar" + sfx).addEventListener("click", () => {
    const d = disenoTexto(L); if (!d) return escribir("Escribe primero cómo quieres el diseño.");
    enviarClaude(L, "Quiero PERSONALIZAR EL DISEÑO de los videos de " + nom + ". Esto es lo que pido:\n\n" + d + "\n\nAplícalo en el motor (" + motor + " y los archivos de estilo que use: colores, tipografías, titulares, globo de objeción, píldoras de pasos, collage, subtítulos) de forma que valga para los próximos videos. No borres ni sobrescribas los prompts existentes. Al terminar genera un video de prueba y dime qué cambiaste.");
  });
  $("#b-diseno-modificar" + sfx).addEventListener("click", () => {
    const d = disenoTexto(L); if (!d) return escribir("Escribe primero qué quieres cambiar del resultado.");
    enviarClaude(L, "Modifica el RESULTADO ya generado de " + nom + " (los videos de la carpeta de resultados) según esto:\n\n" + d + "\n\nAjusta el diseño en el motor y vuelve a renderizar solo los videos afectados, sin rehacer los guiones ni volver a descargar material. Conserva los originales (guarda los nuevos con otro nombre o versión) y dime qué cambió.");
  });
}
// ---------------------------------------------------------------- asistentes (Dianchi y Diegao)
const PASO = { dianchi: 1, diegao: 1 };
const TOTAL_PASOS = { dianchi: 7, diegao: 7 };
const SFX_NAV = { dianchi: "w", diegao: "wd" };
function irPasoWiz(L, n) {
  PASO[L] = Math.max(1, Math.min(TOTAL_PASOS[L], n));
  $$("#v-" + L + " .paso").forEach((p) => p.classList.remove("oculto"));         // todos los pasos se ven en una sola pantalla, como un historial
  const pasoEl = $("#v-" + L + ' .paso[data-p="' + PASO[L] + '"]'); if (pasoEl) pasoEl.scrollIntoView({ behavior: "smooth", block: "start" });
  $$("#pasos-" + L + " li").forEach((li) => { const k = Number(li.dataset.p); li.classList.toggle("act", k === PASO[L]); li.classList.toggle("hecho", k < PASO[L]); });
  $("#" + SFX_NAV[L] + "-atras").classList.toggle("oculto", PASO[L] === 1);
  $("#" + SFX_NAV[L] + "-sig").classList.toggle("oculto", PASO[L] === TOTAL_PASOS[L]);
  if (PASO[L] === TOTAL_PASOS[L]) resumenWiz(L);
}
const irPasoDianchi = (n) => irPasoWiz("dianchi", n);
function resumenWiz(L) {
  const r = $("#resumen-" + L); if (!r || !ajustes) return;
  const p = ajustes.presets, d = ajustes.dirs, ev = p.eventos;
  const voz = (VOCES.find((v) => v[0] === p.voz) || [0, p.voz])[1];
  const si = (b) => (b ? "sí" : "no");
  const carpeta = (x) => x || "dentro de la carpeta de trabajo";
  const dis = (p[KD(L)] || "").trim();
  const total = conLinea(L, totalVideos), desg = conLinea(L, desgloseBrief);
  const guiones = ["Guiones", (total ? total + " video" + (total === 1 ? "" : "s") + " según el formulario (" + desg + ")" : "los del último lote creado con Claude") + " · voz " + voz];
  const diseno = ["Diseño", dis ? dis.slice(0, 140) + (dis.length > 140 ? "…" : "") : "el de siempre (sin cambios; puedes escribir correcciones en el paso " + 6 + ")"];
  const filas = L === "diegao"
    ? [guiones, ["Imágenes", p.imagenesCollageDiegao ? "de la carpeta " + (d.diegaoImagenes || "(sin elegir: elige una en el paso 3)") : "automático (fotogramas de los videos)"],
      ["Videos", p.rellenoLocalDiegao === false ? "automático (se descargan de Pexels)" : "de la carpeta " + (d.diegaoFuente || "de videos del evento (la predeterminada)")], diseno, ["Resultados", carpeta(d.diegaoResultado)]]
    : [guiones,
      ["Eventos", "efectos " + si(p.efectos) + " · objeción " + si(ev.burbuja) + " · pasos " + si(ev.pasos) + " · collage " + si(ev.collage) + " · sonidos " + si(ev.sfx) + " · tarjeta final " + si(ev.cierre)],
      ["Imágenes", p.imagenesCollage ? "de la carpeta " + (d.imagenes || "(sin elegir: elige una en el paso 3)") : "automático (fotogramas de los videos descargados)"],
      ["Videos", p.rellenoLocal ? "de la carpeta " + (d.relleno || "(sin elegir: elige una en el paso 4)") : "automático (se descargan de Pexels)"],
      diseno, ["Resultados", carpeta(d.dianchiResultado)]];
  r.innerHTML = "";
  for (const [k, v] of filas) { const f = document.createElement("div"); f.innerHTML = "<b></b>: <span></span>"; $("b", f).textContent = k; $("span", f).textContent = v; r.appendChild(f); }
}
const resumenDianchi = () => { resumenWiz("dianchi"); resumenWiz("diegao"); };
$("#brief-contador").addEventListener("click", () => { if (!totalVideos()) irPasoWiz(BL, 1); });
for (const L of ["dianchi", "diegao"]) {
  $("#" + SFX_NAV[L] + "-sig").addEventListener("click", () => irPasoWiz(L, PASO[L] + 1));
  $("#" + SFX_NAV[L] + "-atras").addEventListener("click", () => irPasoWiz(L, PASO[L] - 1));
  $$("#pasos-" + L + " li").forEach((li) => li.addEventListener("click", () => irPasoWiz(L, Number(li.dataset.p))));
}
// "Generar todo": Dianchi = verificar -> descargar -> render; Diegao = preparar -> render
async function generarTodo(L) {
  if (!(await exigirUltimaVersion())) return;
  const fases = L === "diegao" ? ["preparar", "render"] : ["verificar", "descargar", "render"];
  gen = { plan: fases.length, fases, render: 0 };
  for (const modo of fases) {
    const r = await window.ctv.run({ linea: L, modo, slugs: [] });   // sin slugs: el motor usa el ultimo lote creado con Claude
    if (!r || !r.ok) { if (detenido && gen) { gen.fin = true; gen.detenido = true; pintarProgreso(); gen = null; return escribir("■ Proceso detenido."); } gen = null; actualizarContador(); return escribir("⚠ Se detuvo en «" + modo + "»" + (r && r.error ? ": " + r.error : ". Revisa el registro.")); }
  }
  if (gen) { gen.fin = true; gen.modo = "render"; pintarProgreso(); gen = null; }
  escribir("✔ Videos de " + NOM_L[L] + " generados. Revisa la carpeta de resultados.");
}
$("#b-generar-todo").addEventListener("click", () => generarTodo("dianchi"));
$("#b-generar-todo-d").addEventListener("click", () => generarTodo("diegao"));

// ---------------------------------------------------------------- Claude Code
$$(".chip").forEach((c) => c.addEventListener("click", () => { $("#txt-claude").value = c.dataset.p; $("#txt-claude").focus(); }));
async function enviarClaude(linea, texto) {
  if (!texto.trim()) return escribir("Escribe una instrucción primero.");
  const cs = await window.ctv.claudeStatus();
  if (cs.instalado && !cs.sesion) { ir("claude"); actualizarCuenta(); return escribir("⚠ Primero inicia sesión en Claude con tu cuenta (botón «Iniciar sesión» arriba)."); }
  const r = await window.ctv.openClaude({ linea, instruccion: texto });
  escribir(r.ok ? "Claude Code abierto en una ventana nueva." : "⚠ " + r.error);
}
$("#b-claude").addEventListener("click", () => {
  const texto = $("#txt-claude").value; if (!texto.trim()) return escribir("Escribe una instrucción primero.");
  const d = ajustes.dirs, carpetas = [["Carpeta de videos", d.claudeVideos], ["Carpeta de imágenes", d.claudeImagenes], ["Carpeta de salida (deja aquí los videos terminados)", d.claudeSalida]].filter((c) => c[1]);
  const pre = carpetas.length ? "Carpetas que debes usar en este trabajo:\n" + carpetas.map((c) => "- " + c[0] + ": " + c[1]).join("\n") + "\n\n" : "";
  enviarClaude($("#sel-linea").value, pre + texto);
});
// ---------------------------------------------------------------- Cortar: patrón de interrupción, tipos de plano y efectos cinematográficos
const CX_RITMOS = [["fijo", "Fijo: siempre cada X segundos"], ["variable", "Variable: entre X−1 y X+1 segundos"], ["acelerado", "Acelerado: empieza en X s y se acorta hacia el final"], ["contenido", "Por contenido: en cada frase o idea (X es el máximo)"]];
const CX_PLANOS = [["Primer plano", "close-up del rostro"], ["Plano medio", "de la cintura hacia arriba"], ["Plano general", "cuerpo entero o la escena completa"], ["Plano detalle", "manos, objeto o pizarra de cerca"], ["Plano americano", "de las rodillas hacia arriba"], ["Plano de apoyo", "público, entorno o la sala"], ["B-roll", "imágenes o videos de apoyo sobre la voz"]];
const CX_EFECTOS = [
  ["Zoom in suave", "push-in lento de 100 % a 108 % durante el plano, para dar vida a la imagen quieta"],
  ["Zoom out", "alejamiento lento de 110 % a 100 % durante el plano"],
  ["Punch-in", "zoom seco de 100 % a 115 % en 0,15 s al empezar el plano, para enfatizar una frase"],
  ["Paneo rápido", "desplazamiento lateral veloz con desenfoque de movimiento entre dos planos (whip pan)"],
  ["Flash blanco", "destello blanco de 2 a 3 fotogramas justo en el corte"],
  ["Glitch RGB", "separación de canales de color y ruido digital de unos 0,2 s en el corte"],
  ["Sacudida de cámara", "vibración corta (shake) al inicio del plano para dar impacto"],
  ["Fundido a negro", "caída rápida a negro de 0,2 s entre planos importantes"],
  ["Desenfoque de transición", "desenfoque que sube y baja alrededor del corte"],
  ["Cámara lenta", "velocidad al 50–70 % solo en planos de apoyo sin voz importante, o con el audio compensado"],
  ["Rampa de velocidad", "acelerar y frenar el video dentro de un mismo plano en momentos clave"],
  ["Congelar cuadro", "imagen congelada de 0,3 s para remarcar una palabra o idea"],
  ["Look cinematográfico", "gradación de color (sombras frías, luces cálidas), viñeta suave y grano fino en todo el clip"],
  ["Subtítulos dinámicos", "subtítulos palabra por palabra con la palabra clave resaltada"],
  ["Sonido whoosh", "sonido breve de transición o impacto en cada cambio de plano"],
];
const CX_PRESETS = {
  suave: { n: "Suave", d: "Cambio cada 6 s, pocos efectos. Para charlas tranquilas o contenido educativo.", cada: 6, ritmo: "fijo", planos: ["Plano medio", "Plano general"], efectos: ["Zoom in suave", "Fundido a negro"], intensidad: "sutil" },
  equilibrado: { n: "Equilibrado", d: "Cambio cada 4 s con zoom suave y sonido. Es el patrón de siempre.", cada: 4, ritmo: "fijo", planos: ["Plano medio", "Primer plano", "Plano general"], efectos: ["Zoom in suave", "Sonido whoosh"], intensidad: "media" },
  dinamico: { n: "Dinámico", d: "Cambio cada 3 s, variable, con punch-in, flash y sonido.", cada: 3, ritmo: "variable", planos: ["Primer plano", "Plano medio", "Plano general", "Plano detalle"], efectos: ["Punch-in", "Flash blanco", "Sonido whoosh", "Subtítulos dinámicos"], intensidad: "media" },
  viral: { n: "Viral / Intenso", d: "Cambio cada 2 s, acelerado, con glitch, sacudida y subtítulos. Para Reels y TikTok de alto ritmo.", cada: 2, ritmo: "acelerado", planos: ["Primer plano", "Plano medio", "Plano detalle", "Plano de apoyo", "B-roll"], efectos: ["Punch-in", "Glitch RGB", "Sacudida de cámara", "Flash blanco", "Rampa de velocidad", "Subtítulos dinámicos", "Sonido whoosh"], intensidad: "fuerte" },
  cine: { n: "Cinematográfico", d: "Cambio cada 5 s, variable, con paneos, desenfoques, cámara lenta y gradación de color.", cada: 5, ritmo: "variable", planos: ["Plano general", "Plano medio", "Primer plano", "Plano detalle", "Plano americano"], efectos: ["Zoom in suave", "Paneo rápido", "Desenfoque de transición", "Cámara lenta", "Fundido a negro", "Look cinematográfico"], intensidad: "sutil" },
};
const CX0 = { preset: "equilibrado", cada: 4, ritmo: "fijo", planos: [...CX_PRESETS.equilibrado.planos], efectos: [...CX_PRESETS.equilibrado.efectos], intensidad: "media", clipMin: 20, clipMax: 40 };
function cxp() { const p = ajustes.presets.cortar || (ajustes.presets.cortar = {}); for (const k of Object.keys(CX0)) if (p[k] === undefined) p[k] = Array.isArray(CX0[k]) ? [...CX0[k]] : CX0[k]; return p; }
const cxNum = (n) => String(n).replace(".", ",");
function cxEspecificacion() {
  const p = cxp(), X = p.cada;
  const ritmo = { fijo: "cambia de plano o de encuadre exactamente cada " + cxNum(X) + " segundos", variable: "cambia de plano en intervalos irregulares, entre " + cxNum(Math.max(1, X - 1)) + " y " + cxNum(X + 1) + " segundos (promedio " + cxNum(X) + " s), para que no se sienta mecánico", acelerado: "empieza cambiando cada " + cxNum(X) + " segundos y va acortando el intervalo hasta cerca de " + cxNum(Math.max(1, X / 2)) + " s hacia el final del clip", contenido: "cambia de plano en cada frase o idea nueva, con un máximo de " + cxNum(X) + " segundos sin cambio" }[p.ritmo];
  const L = ["PATRÓN DE INTERRUPCIÓN Y EFECTOS (estos valores mandan sobre los predeterminados de prompt/PROMPT_cortar.md):",
    "- Cambios de escena: " + ritmo + ". Nunca dejes un plano quieto más de " + cxNum(Math.max(X + 1, 2)) + " s.",
    "- Duración de cada clip: de " + p.clipMin + " a " + Math.max(p.clipMax, p.clipMin) + " segundos."];
  if (p.planos.length) L.push("- Tipos de plano que debes alternar (no repitas el mismo dos veces seguidas): " + p.planos.map((n) => n.toLowerCase() + " (" + CX_PLANOS.find((x) => x[0] === n)[1] + ")").join("; ") + ".");
  else L.push("- Tipos de plano: elige tú los más adecuados para cada momento.");
  if (p.efectos.length) L.push("- Efectos cinematográficos permitidos, con intensidad " + p.intensidad + " (" + { sutil: "discretos, casi imperceptibles", media: "claros pero elegantes", fuerte: "marcados y llamativos" }[p.intensidad] + "): " + p.efectos.map((n) => n + " = " + CX_EFECTOS.find((x) => x[0] === n)[1]).join("; ") + ". Reparte los efectos entre los cambios de plano según lo que se dice (énfasis, remate, transición); no repitas el mismo efecto dos veces seguidas ni uses efectos que no están en esta lista.");
  else L.push("- Efectos: ninguno; solo cortes limpios entre planos.");
  L.push("- SIN hook de mentor, SIN título gancho, SIN etiqueta de categoría y SIN hook de por-cortar/hook: aquí solo se cortan los silencios (y muletillas) y se aplica lo elegido arriba. Ignora esos pasos de prompt/PROMPT_cortar.md. El clip empieza directamente con el contenido.");
  L.push("Implementa los efectos con ffmpeg o con los scripts de scripts/ sin romper lo existente, y antes de dar los clips por listos revisa cuadros reales de cada uno para comprobar que los cambios y efectos se ven bien.");
  return L.join("\n");
}
let cxListo = false;
function construirCortar() {
  if (cxListo) return; cxListo = true;
  const pr = $("#cx-presets");
  for (const [k, v] of Object.entries(CX_PRESETS)) { const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.dataset.v = k; b.textContent = v.n; b.title = v.d; b.addEventListener("click", () => { const p = cxp(), s = CX_PRESETS[k]; Object.assign(p, { preset: k, cada: s.cada, ritmo: s.ritmo, intensidad: s.intensidad, planos: [...s.planos], efectos: [...s.efectos] }); guardarAuto(); }); pr.appendChild(b); }
  { const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.dataset.v = "personalizado"; b.textContent = "Personalizado"; b.title = "Tus propios valores"; b.addEventListener("click", () => { cxp().preset = "personalizado"; guardarAuto(); }); pr.appendChild(b); }
  const chips = (cont, lista, clave, ayuda) => { for (const [n, d] of lista) { const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.dataset.v = n; b.textContent = n; b.title = d; b.addEventListener("click", () => { const p = cxp(), i = p[clave].indexOf(n); if (i >= 0) p[clave].splice(i, 1); else p[clave].push(n); p.preset = "personalizado"; guardarAuto(); }); if (ayuda) b.addEventListener("mouseenter", () => { $(ayuda).textContent = n + ": " + d + "."; }); cont.appendChild(b); } };
  chips($("#cx-planos"), CX_PLANOS, "planos"); chips($("#cx-efectos"), CX_EFECTOS, "efectos", "#cx-efectos-d");
  for (const [v, n] of CX_RITMOS) { const o = document.createElement("option"); o.value = v; o.textContent = n; $("#cx-ritmo").appendChild(o); }
  for (const [v, n] of [["sutil", "Sutil (discretos)"], ["media", "Media (claros pero elegantes)"], ["fuerte", "Fuerte (marcados)"]]) { const o = document.createElement("option"); o.value = v; o.textContent = n; $("#cx-int").appendChild(o); }
  $("#cx-cada").addEventListener("input", (ev) => { const p = cxp(); p.cada = Number(ev.target.value); p.preset = "personalizado"; $("#cx-cada-v").textContent = cxNum(p.cada) + " s"; $("#cx-previa").textContent = cxEspecificacion(); });
  $("#cx-cada").addEventListener("change", () => guardarAuto());
  $("#cx-ritmo").addEventListener("change", (ev) => { const p = cxp(); p.ritmo = ev.target.value; p.preset = "personalizado"; guardarAuto(); });
  $("#cx-int").addEventListener("change", (ev) => { const p = cxp(); p.intensidad = ev.target.value; p.preset = "personalizado"; guardarAuto(); });
  for (const [id, k] of [["cx-min", "clipMin"], ["cx-max", "clipMax"]]) $("#" + id).addEventListener("change", (ev) => { const v = Math.max(5, Math.min(180, Number(ev.target.value) || CX0[k])); cxp()[k] = v; if (cxp().clipMax < cxp().clipMin) cxp().clipMax = cxp().clipMin; guardarAuto(); });
}
function pintarCortar() {
  construirCortar(); const p = cxp();
  $$("#cx-presets .chip").forEach((c) => c.classList.toggle("on", c.dataset.v === p.preset));
  $("#cx-presets-d").textContent = CX_PRESETS[p.preset] ? CX_PRESETS[p.preset].d : "Combina tus propios valores: cada cuánto cambia, qué planos y qué efectos.";
  $$("#cx-planos .chip").forEach((c) => c.classList.toggle("on", p.planos.includes(c.dataset.v)));
  $$("#cx-efectos .chip").forEach((c) => c.classList.toggle("on", p.efectos.includes(c.dataset.v)));
  $("#cx-cada").value = p.cada; $("#cx-cada-v").textContent = cxNum(p.cada) + " s"; $("#cx-ritmo").value = p.ritmo; $("#cx-int").value = p.intensidad;
  if (document.activeElement !== $("#cx-min")) $("#cx-min").value = p.clipMin;
  if (document.activeElement !== $("#cx-max")) $("#cx-max").value = p.clipMax;
  $("#cx-clip-v").textContent = p.clipMin + " a " + Math.max(p.clipMax, p.clipMin) + " s";
  $("#cx-previa").textContent = cxEspecificacion();
}
$("#b-cortar").addEventListener("click", () => enviarClaude("por-cortar", $("#txt-cortar").value.trim() + "\n\n" + cxEspecificacion()));

// ---------------------------------------------------------------- ajustes
// Las carpetas y opciones se eligen en la misma pantalla de cada tipo de edicion y se guardan solas.
const NOMBRES_DIRS = {
  dianchiResultado: "Resultados de Dianchi", imagenes: "Carpeta de imágenes", relleno: "Videos de relleno",
  diegaoResultado: "Resultados de Diegao", diegaoFuente: "Videos fuente (evento)", diegaoImagenes: "Carpeta de imágenes (Diegao)",
  preciosVideos: "Videos de fondo (Precios)", preciosImagenes: "Carpeta de imágenes (Precios)", preciosResultado: "Resultados de Anuncios Con Precio", infografiasResultado: "Resultados de Infografías Animadas", animtextoResultado: "Resultados de Animación de Texto",
  claudeVideos: "Carpeta de videos", claudeImagenes: "Carpeta de imágenes", claudeSalida: "Carpeta de salida",
  cortarEntrada: "Video a cortar (entrada)", cortarResultado: "Resultados de los cortes",
};
const SECCIONES = {
  "dianchi-imagenes": ["imagenes"],
  "dianchi-videos": ["relleno"],
  "dianchi-resultados": ["dianchiResultado"],
  "diegao-fuente": ["diegaoFuente"],
  "diegao-imagenes": ["diegaoImagenes"],
  "diegao-resultados": ["diegaoResultado"],
  "precios-videos": ["preciosVideos"],
  "precios-imagenes": ["preciosImagenes"],
  "precios-resultados": ["preciosResultado"],
  "infografias-resultados": ["infografiasResultado"],
  "animtexto-resultados": ["animtextoResultado"],
  claude: ["claudeVideos", "claudeImagenes", "claudeSalida"],
  cortar: ["cortarEntrada", "cortarResultado"],
};
const VOCES = [["es-MX-JorgeNeural", "Jorge (México, hombre)"], ["es-MX-DaliaNeural", "Dalia (México, mujer)"], ["es-CO-GonzaloNeural", "Gonzalo (Colombia, hombre)"], ["es-CO-SalomeNeural", "Salomé (Colombia, mujer)"], ["es-ES-AlvaroNeural", "Álvaro (España, hombre)"]];
// ---------------------------------------------------------------- Anuncios Con Precio (video de 15 s, formato Reels)
const PR_IDIOMAS = [["es", "Español"], ["en", "English"], ["pt", "Português"], ["de", "Deutsch"]];
const PR_VOCES = {
  es: VOCES,
  en: [["en-US-GuyNeural", "Guy (EE. UU., hombre)"], ["en-US-JennyNeural", "Jenny (EE. UU., mujer)"]],
  pt: [["pt-BR-AntonioNeural", "Antonio (Brasil, hombre)"], ["pt-BR-FranciscaNeural", "Francisca (Brasil, mujer)"]],
  de: [["de-DE-ConradNeural", "Conrad (Alemania, hombre)"], ["de-DE-KatjaNeural", "Katja (Alemania, mujer)"]],
};
const PR0 = { idioma: "es", voz: "es-MX-JorgeNeural", rubro: "", servicio: "", ubicacion: "", titulo: "", incluye: "", precio: "", cta: "me", videos: "auto", imagenes: "auto", generado: false };
const ES0 = { tarjeta: "#1c1030", opacidad: 0.8, amarillo: "#FFD400", letras: "#FFFFFF", chip: "#D61480", escala: 1, posicion: "centro", diseno: "modelo", oscuro: 0.28 };
function prp() { const p = ajustes.presets.precios || (ajustes.presets.precios = {}); for (const k of Object.keys(PR0)) if (p[k] === undefined) p[k] = PR0[k]; return p; }
function esp() { const p = ajustes.presets.preciosEstilo || (ajustes.presets.preciosEstilo = {}); for (const k of Object.keys(ES0)) if (p[k] === undefined) p[k] = ES0[k]; return p; }
function llenarSelect(sel, pares, valor) {
  sel.innerHTML = "";
  for (const [v, n] of pares) { const o = document.createElement("option"); o.value = v; o.textContent = n; sel.appendChild(o); }
  sel.value = valor;
}
function pintarPrecios() {
  if (!ajustes || !$("#pr-idioma")) return;
  const p = prp(), e = esp();
  llenarSelect($("#pr-idioma"), PR_IDIOMAS, p.idioma);
  llenarSelect($("#pr-rubro"), [["", "Elige un rubro…"], ...OPC.rubros.map((r) => [r, r])], p.rubro);
  const voces = PR_VOCES[p.idioma] || VOCES;
  if (!voces.some((v) => v[0] === p.voz)) p.voz = voces[0][0];
  llenarSelect($("#pr-voz"), voces, p.voz);
  for (const [id, k] of [["pr-servicio", "servicio"], ["pr-ubicacion", "ubicacion"], ["pr-titulo", "titulo"], ["pr-incluye", "incluye"], ["pr-precio", "precio"]]) if (document.activeElement !== $("#" + id)) $("#" + id).value = p[k];
  for (const [nombre, valor] of [["pr-videos", p.videos], ["pr-imagenes", p.imagenes], ["pr-cta", p.cta]]) $$('input[name="' + nombre + '"]').forEach((r) => (r.checked = r.value === valor));
  $("#caja-pr-videos").classList.toggle("oculto", p.videos !== "carpeta");
  $("#caja-pr-imagenes").classList.toggle("oculto", p.imagenes !== "carpeta");
  $("#pr-aspecto").classList.toggle("oculto", !p.generado);
  for (const k of ["tarjeta", "amarillo", "letras", "chip"]) $("#es-" + k).value = e[k];
  $("#es-opacidad").value = Math.round(e.opacidad * 100); $("#es-opacidad-v").textContent = Math.round(e.opacidad * 100) + " %";
  $("#es-escala").value = Math.round(e.escala * 100); $("#es-escala-v").textContent = Math.round(e.escala * 100) + " %";
  $("#es-posicion").value = e.posicion;
  $("#pr-diseno").value = e.diseno; $("#es-oscuro").value = Math.round(e.oscuro * 100); $("#es-oscuro-v").textContent = Math.round(e.oscuro * 100) + " %";
  $("#pr-aspecto").dataset.d = e.diseno; $("#sec-pr-imagenes").classList.toggle("oculto", e.diseno === "modelo");
}
function cambioPrecios(fn) { return (ev) => { fn(ev.target.value, ev.target); guardarAuto(); }; }
$("#pr-idioma").addEventListener("change", cambioPrecios((v) => { const p = prp(); p.idioma = v; p.voz = PR_VOCES[v][0][0]; }));
$("#pr-rubro").addEventListener("change", cambioPrecios((v) => { prp().rubro = v; }));
$("#pr-voz").addEventListener("change", cambioPrecios((v) => { prp().voz = v; }));
for (const [id, k] of [["pr-servicio", "servicio"], ["pr-ubicacion", "ubicacion"], ["pr-titulo", "titulo"], ["pr-incluye", "incluye"], ["pr-precio", "precio"]]) {
  $("#" + id).addEventListener("input", (ev) => { prp()[k] = ev.target.value; });
  $("#" + id).addEventListener("change", () => guardarAuto());
}
for (const [nombre, k] of [["pr-videos", "videos"], ["pr-imagenes", "imagenes"], ["pr-cta", "cta"]]) $$('input[name="' + nombre + '"]').forEach((r) => r.addEventListener("change", (ev) => { prp()[k] = ev.target.value; guardarAuto(); }));
for (const k of ["tarjeta", "amarillo", "letras", "chip"]) $("#es-" + k).addEventListener("change", (ev) => { esp()[k] = ev.target.value; guardarAuto(); });
$("#es-opacidad").addEventListener("input", (ev) => { esp().opacidad = Number(ev.target.value) / 100; $("#es-opacidad-v").textContent = ev.target.value + " %"; });
$("#es-escala").addEventListener("input", (ev) => { esp().escala = Number(ev.target.value) / 100; $("#es-escala-v").textContent = ev.target.value + " %"; });
for (const id of ["es-opacidad", "es-escala"]) $("#" + id).addEventListener("change", () => guardarAuto());
$("#pr-diseno").addEventListener("change", (ev) => { esp().diseno = ev.target.value; guardarAuto(); });
$("#es-oscuro").addEventListener("input", (ev) => { esp().oscuro = Number(ev.target.value) / 100; $("#es-oscuro-v").textContent = ev.target.value + " %"; });
$("#es-oscuro").addEventListener("change", () => guardarAuto());
$("#es-posicion").addEventListener("change", (ev) => { esp().posicion = ev.target.value; guardarAuto(); });
$("#b-precios-restablecer").addEventListener("click", () => { ajustes.presets.preciosEstilo = { ...ES0 }; guardarAuto(); });
async function correrPrecios(modo) {
  const p = prp(), st = $("#pr-estado");
  st.textContent = "Comprobando que tengas la última versión…";
  if (!(await exigirUltimaVersion())) { st.textContent = "⚠ Primero hay que actualizar a la última versión."; return; }
  st.textContent = "";
  if (modo === "generar") {
    const falta = !p.rubro ? "el rubro" : !p.servicio.trim() ? "el servicio" : !p.titulo.trim() ? "el título" : !p.incluye.trim() ? "lo que incluye el servicio" : !p.precio.trim() ? "el precio promocional" : "";
    if (falta) { st.textContent = "⚠ Falta " + falta + "."; return; }
  }
  st.textContent = modo === "generar" ? "Generando el video… (voz, videos y montaje; puede tardar 1–3 minutos)" : "Montando con el nuevo aspecto…";
  ajustes.presets.lineaActiva = "precios"; await guardarAuto();
  const r = await window.ctv.run({ linea: "precios", modo, slugs: [] });
  if (r && r.error) { st.textContent = "⚠ " + r.error; return; }
  if (r && r.ok) { p.generado = true; st.textContent = "✔ Listo. Está en la carpeta de resultados."; await guardarAuto(); }
  else st.textContent = "⚠ No se pudo terminar; revisa el registro de abajo.";
}
$("#b-precios-generar").addEventListener("click", () => correrPrecios("generar"));
$("#b-precios-aspecto").addEventListener("click", () => correrPrecios("aspecto"));
const ESTILOS = [
  ["minimalista", "Minimalista", "Poco contenido, mucho espacio en blanco y un solo acento.", "v"],
  ["flat", "Flat design", "Colores planos, sin sombras ni texturas.", "v"],
  ["skeuo", "Skeuomorfismo", "Imita objetos reales, con brillos, relieve y materiales.", "v"],
  ["neumorfismo", "Neumorfismo", "Elementos suaves que parecen salir del fondo.", "v"],
  ["glass", "Glassmorphism", "Transparencia y desenfoque tipo vidrio esmerilado.", "v"],
  ["clay", "Claymorphism", "Formas infladas y redondeadas, tipo plastilina.", "v"],
  ["neobrutalismo", "Neobrutalismo", "Bordes negros gruesos, colores vivos y sombras duras.", "v"],
  ["bento", "Bento grid", "Contenido en cajas de distintos tamaños, como un bento.", "v"],
  ["neon", "Oscuro y neón (cyberpunk)", "Fondo oscuro con acentos luminosos.", "v"],
  ["aurora", "Gradientes y aurora", "Degradados fluidos y fondos de color en malla.", "v"],
  ["retro", "Retro, Y2K y vaporwave", "Nostalgia de los 80, 90 y 2000.", "v"],
  ["isometrico", "Isométrico y 3D", "Objetos en perspectiva o con volumen.", "v"],
  ["ilustrado", "Ilustrado y hecho a mano", "Trazos orgánicos, garabatos y texturas.", "v"],
  ["editorial", "Tipográfico y editorial", "El texto es el protagonista, estilo revista.", "v"],
  ["memphis", "Maximalismo y Memphis", "Muchos colores, patrones y formas geométricas.", "v"],
  ["material", "Material design (Google)", "Capas, elevación y componentes estandarizados.", "f"],
  ["apple", "Human Interface (Apple)", "El estilo de iOS y macOS, con su vidrio líquido.", "f"],
  ["fluent", "Fluent (Microsoft)", "Profundidad, luz y materiales en Windows.", "f"],
  ["responsivo", "Responsivo y mobile-first", "Se adapta a cualquier pantalla, empezando por el celular.", "f"],
  ["accesible", "Accesible e inclusivo", "Contraste, tamaños y lectura pensados para todas las personas.", "f"],
  ["atomico", "Atomic design y design systems", "Componentes reutilizables que mantienen la coherencia de una marca.", "f"],
  ["oscuro", "Modo oscuro", "Nació por legibilidad y ahorro de batería.", "f"],
];
const IF_DEMO = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 110"><rect width="90" height="110" fill="#fff"/><circle cx="45" cy="26" r="13" fill="#d61480"/><rect x="42" y="19" width="6" height="14" rx="2" fill="#fff"/><rect x="18" y="50" width="54" height="8" rx="3" fill="#2a2a3a"/><rect x="12" y="68" width="66" height="5" rx="2" fill="#aaa"/><rect x="12" y="79" width="66" height="5" rx="2" fill="#aaa"/><rect x="24" y="90" width="42" height="5" rx="2" fill="#aaa"/></svg>');
const IF0 = { imagen: "", estilos: [], titulo: "", subtitulo: "", duracion: 0, idioma: "", voz: "", formato: "reels" };
let ifMini = "", ifMiniRuta = "", ifConstruido = false;
function ifp() { const p = ajustes.presets.infografias || (ajustes.presets.infografias = {}); for (const k of Object.keys(IF0)) if (p[k] === undefined) p[k] = Array.isArray(IF0[k]) ? [] : IF0[k]; return p; }
function pintarInfografias() {
  if (!ajustes || !$("#if-est-v")) return;
  const p = ifp(), v = $("#v-infografias");
  if (p.imagenB64 && ifMiniRuta !== p.imagen) { ifMiniRuta = p.imagen; ifMini = p.imagenB64; }
  if (!p.imagen) { ifMini = ""; ifMiniRuta = ""; }
  v.style.setProperty("--img", 'url("' + IF_DEMO + '")');                     // las vistas previas son genericas: no usan la imagen del usuario
  $("#if-miniatura").style.backgroundImage = ifMini ? 'url("' + ifMini + '")' : "none"; $("#if-miniatura").classList.toggle("demo", !ifMini);
  $("#if-nombre").textContent = p.imagen ? p.imagen.split(/[\\/]/).pop() + (ifMini ? "" : " (no se pudo mostrar la miniatura)") : "Aún no has elegido una imagen. Abajo, las vistas previas usan una imagen de ejemplo.";
  if (!ifConstruido) {
    ifConstruido = true;
    for (const [clave, nombre, desc, g] of ESTILOS) {
      const l = document.createElement("label"); l.className = "est"; l.dataset.e = clave;
      l.innerHTML = '<div class="pv pv-' + clave + '"><i class="pv-t"></i><div class="pv-c"></div><i class="pv-s"></i></div><b></b><span class="d"></span><span class="ok">✓</span><input type="checkbox" />';
      $("b", l).textContent = nombre; $(".d", l).textContent = desc;
      $("input", l).addEventListener("change", (ev) => { const q = ifp(), s = new Set(q.estilos); if (ev.target.checked) s.add(clave); else s.delete(clave); q.estilos = ESTILOS.map((e) => e[0]).filter((k) => s.has(k)); guardarAuto(); });
      $(g === "v" ? "#if-est-v" : "#if-est-f").appendChild(l);
    }
  }
  $$(".est", v).forEach((l) => { const on = p.estilos.includes(l.dataset.e); l.classList.toggle("sel", on); $("input", l).checked = on; });
  $("#if-cuenta").textContent = p.estilos.length ? p.estilos.length + (p.estilos.length === 1 ? " estilo elegido" : " estilos elegidos") : "Ninguno elegido todavía";
  for (const [id, k] of [["if-titulo", "titulo"], ["if-subtitulo", "subtitulo"]]) if (document.activeElement !== $("#" + id)) $("#" + id).value = p[k];
  $("#if-formato").value = p.formato; $("#if-duracion").value = String([10, 15, 20, 30].includes(Number(p.duracion)) ? p.duracion : 0); $("#if-idioma").value = p.idioma || "";
  if (!$("#if-voz").options.length) llenarSelect($("#if-voz"), [["", "Automática (según el idioma del texto)"], ["none", "Sin voz (solo animación)"], ...VOCES, ...PR_VOCES.en, ...PR_VOCES.pt, ...PR_VOCES.de], p.voz || "");
  $("#if-voz").value = p.voz || "";
}
// La imagen se elige con el selector del sistema y se guarda dentro de los ajustes (reducida a 2200 px): no depende de la version del instalador.
$("#b-if-imagen").addEventListener("click", () => $("#if-archivo").click());
$("#if-archivo").addEventListener("change", (ev) => {
  const f = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (!f) return;
  const msg = (t) => { $("#if-nombre").textContent = t; $("#if-estado").textContent = t.startsWith("⚠") ? t : ""; };
  const url = URL.createObjectURL(f), im = new Image();
  im.onerror = () => { URL.revokeObjectURL(url); msg("⚠ No se pudo leer esa imagen. Prueba con un PNG o JPG."); };
  im.onload = async () => {
    const k = Math.min(1, 2200 / Math.max(im.naturalWidth, im.naturalHeight)), c = document.createElement("canvas");
    c.width = Math.round(im.naturalWidth * k); c.height = Math.round(im.naturalHeight * k);
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(im, 0, 0, c.width, c.height); URL.revokeObjectURL(url);
    const p = ifp(); p.imagenB64 = c.toDataURL("image/jpeg", 0.92); p.imagen = f.name; ifMini = c.toDataURL("image/jpeg", 0.6); ifMiniRuta = f.name;
    $("#if-estado").textContent = ""; await guardarAuto();
  };
  im.src = url;
});
const ifListos = [];
function ifVideoListo(ruta) {
  const r = ruta.replace(/\\/g, "/"), nombre = r.split("/").pop(); if (ifListos.includes(r)) return; ifListos.push(r);
  const url = "file:///" + r.replace(/^\/+/, "").split("/").map((s, i) => (i === 0 ? s : encodeURIComponent(s))).join("/");
  const d = document.createElement("div"); d.className = "if-res";
  d.innerHTML = '<video controls loop preload="metadata"></video><div><b></b><a class="boton-a" download>Descargar video</a></div>';
  $("video", d).src = url; $("b", d).textContent = nombre; const a = $("a", d); a.href = url; a.download = nombre;
  const px = nombre.startsWith("animtexto_") ? "at" : "if";
  $("#" + px + "-lista").prepend(d); $("#" + px + "-resultados").classList.remove("oculto");
}
for (const [id, k] of [["if-titulo", "titulo"], ["if-subtitulo", "subtitulo"]]) {
  $("#" + id).addEventListener("input", (ev) => { ifp()[k] = ev.target.value; });
  $("#" + id).addEventListener("change", () => guardarAuto());
}
$("#if-formato").addEventListener("change", (ev) => { ifp().formato = ev.target.value; guardarAuto(); });
$("#if-voz").addEventListener("change", (ev) => { ifp().voz = ev.target.value; guardarAuto(); });
$("#if-idioma").addEventListener("change", (ev) => { ifp().idioma = ev.target.value; guardarAuto(); });
$("#if-duracion").addEventListener("change", (ev) => { ifp().duracion = Number(ev.target.value); guardarAuto(); });
$("#b-if-todos").addEventListener("click", () => { ifp().estilos = ESTILOS.map((e) => e[0]); guardarAuto(); });
$("#b-if-ninguno").addEventListener("click", () => { ifp().estilos = []; guardarAuto(); });
$("#b-if-generar").addEventListener("click", async () => {
  const p = ifp(), st = $("#if-estado");
  if (!p.imagen || !p.imagenB64) { p.imagen = ""; $("#if-nombre").textContent = "⚠ Primero sube la imagen."; }
  if (!p.imagen) { st.textContent = "⚠ Primero sube la imagen."; return; }
  if (!p.estilos.length) { st.textContent = "⚠ Elige al menos un estilo de diseño."; return; }
  st.textContent = "Comprobando que tengas la última versión…";
  if (!(await exigirUltimaVersion())) { st.textContent = "⚠ Primero hay que actualizar a la última versión."; return; }
  st.textContent = "Generando " + p.estilos.length + (p.estilos.length === 1 ? " video" : " videos") + "… primero Claude Code lee e interpreta la imagen (unos segundos), luego se genera la voz y se anima cada estilo (alrededor de 1 minuto cada uno)";
  ajustes.presets.lineaActiva = "infografias"; await guardarAuto();
  const r = await window.ctv.run({ linea: "infografias", modo: "generar", slugs: [] });
  if (r && r.ok && !ifListos.length && !$("#if-lista").children.length) { st.textContent = "⚠ Terminó pero no se creó ningún video. Revisa el registro de abajo."; return; }
  if (r && r.error) { st.textContent = "⚠ " + r.error; return; }
  st.textContent = r && r.ok ? "✔ Listo. Tus videos aparecen abajo para verlos y descargarlos." : "⚠ No se pudo terminar; revisa el registro de abajo.";
});

// ---------------------------------------------------------------- Animación de Texto: el texto lo escribe la persona; mismo motor y mismos estilos que Infografías
const AT0 = { texto: "", estilos: [], titulo: "", subtitulo: "", duracion: 0, idioma: "", voz: "", formato: "reels" };
function atp() { const p = ajustes.presets.animtexto || (ajustes.presets.animtexto = {}); for (const k of Object.keys(AT0)) if (p[k] === undefined) p[k] = Array.isArray(AT0[k]) ? [] : AT0[k]; return p; }
let atConstruido = false;
function atCuentaTexto() {
  const t = ($("#at-texto").value || "").trim(), pal = t ? t.split(/\s+/).length : 0, seg = Math.round(pal / 2.5);
  $("#at-cuenta-t").textContent = pal ? pal + " palabras · narración de unos " + (seg >= 60 ? Math.floor(seg / 60) + " min " + (seg % 60) + " s" : seg + " s") : "";
}
function pintarAnimTexto() {
  if (!ajustes || !$("#at-est-v")) return;
  const p = atp(), v = $("#v-animtexto");
  v.style.setProperty("--img", 'url("' + IF_DEMO + '")');
  if (!atConstruido) {
    atConstruido = true;
    for (const [clave, nombre, desc, g] of ESTILOS) {
      const l = document.createElement("label"); l.className = "est"; l.dataset.e = clave;
      l.innerHTML = '<div class="pv pv-' + clave + '"><i class="pv-t"></i><div class="pv-c"></div><i class="pv-s"></i></div><b></b><span class="d"></span><span class="ok">✓</span><input type="checkbox" />';
      $("b", l).textContent = nombre; $(".d", l).textContent = desc;
      $("input", l).addEventListener("change", (ev) => { const q = atp(), s = new Set(q.estilos); if (ev.target.checked) s.add(clave); else s.delete(clave); q.estilos = ESTILOS.map((e) => e[0]).filter((k) => s.has(k)); guardarAuto(); });
      $(g === "v" ? "#at-est-v" : "#at-est-f").appendChild(l);
    }
  }
  $$(".est", v).forEach((l) => { const on = p.estilos.includes(l.dataset.e); l.classList.toggle("sel", on); $("input", l).checked = on; });
  $("#at-cuenta").textContent = p.estilos.length ? p.estilos.length + (p.estilos.length === 1 ? " estilo elegido" : " estilos elegidos") : "Ninguno elegido todavía";
  for (const [id, k] of [["at-texto", "texto"], ["at-titulo", "titulo"], ["at-subtitulo", "subtitulo"]]) if (document.activeElement !== $("#" + id)) $("#" + id).value = p[k];
  atCuentaTexto();
  $("#at-formato").value = p.formato; $("#at-duracion").value = String([10, 15, 20, 30].includes(Number(p.duracion)) ? p.duracion : 0); $("#at-idioma").value = p.idioma || "";
  if (!$("#at-voz").options.length) llenarSelect($("#at-voz"), [["", "Automática (según el idioma del texto)"], ["none", "Sin voz (solo animación)"], ...VOCES, ...PR_VOCES.en, ...PR_VOCES.pt, ...PR_VOCES.de], p.voz || "");
  $("#at-voz").value = p.voz || "";
}
for (const [id, k] of [["at-texto", "texto"], ["at-titulo", "titulo"], ["at-subtitulo", "subtitulo"]]) {
  $("#" + id).addEventListener("input", (ev) => { atp()[k] = ev.target.value; if (k === "texto") atCuentaTexto(); });
  $("#" + id).addEventListener("change", () => guardarAuto());
}
$("#b-at-archivo").addEventListener("click", () => $("#at-archivo").click());
$("#at-archivo").addEventListener("change", async (ev) => {
  const f = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (!f) return;
  const txt = (await f.text()).replace(/^\uFEFF/, "").trim(); atp().texto = txt.slice(0, 6000); $("#at-estado").textContent = txt.length > 6000 ? "⚠ El archivo es largo: se usarán los primeros 6000 caracteres." : ""; await guardarAuto();
});
$("#b-at-limpiar").addEventListener("click", () => { atp().texto = ""; $("#at-texto").value = ""; atCuentaTexto(); guardarAuto(); });
$("#at-formato").addEventListener("change", (ev) => { atp().formato = ev.target.value; guardarAuto(); });
$("#at-voz").addEventListener("change", (ev) => { atp().voz = ev.target.value; guardarAuto(); });
$("#at-idioma").addEventListener("change", (ev) => { atp().idioma = ev.target.value; guardarAuto(); });
$("#at-duracion").addEventListener("change", (ev) => { atp().duracion = Number(ev.target.value); guardarAuto(); });
$("#b-at-todos").addEventListener("click", () => { atp().estilos = ESTILOS.map((e) => e[0]); guardarAuto(); });
$("#b-at-ninguno").addEventListener("click", () => { atp().estilos = []; guardarAuto(); });
$("#b-at-generar").addEventListener("click", async () => {
  const p = atp(), st = $("#at-estado");
  p.texto = $("#at-texto").value;
  if (p.texto.trim().length < 15) { st.textContent = "⚠ Escribe primero el texto que quieres animar."; return; }
  if (!p.estilos.length) { st.textContent = "⚠ Elige al menos un estilo de diseño."; return; }
  st.textContent = "Comprobando que tengas la última versión…";
  if (!(await exigirUltimaVersion())) { st.textContent = "⚠ Primero hay que actualizar a la última versión."; return; }
  st.textContent = "Generando " + p.estilos.length + (p.estilos.length === 1 ? " video" : " videos") + "… primero Claude Code interpreta tu texto (unos segundos), luego se genera la voz y se anima cada estilo (alrededor de 1 minuto cada uno)";
  ajustes.presets.lineaActiva = "animtexto"; await guardarAuto();
  const antes = $("#at-lista").children.length;
  const r = await window.ctv.run({ linea: "infografias", modo: "generar", slugs: [] });
  if (r && r.ok && $("#at-lista").children.length === antes) { st.textContent = "⚠ Terminó pero no se creó ningún video. Revisa el registro de abajo."; return; }
  if (r && r.error) { st.textContent = "⚠ " + r.error; return; }
  st.textContent = r && r.ok ? "✔ Listo. Tus videos aparecen abajo para verlos y descargarlos." : "⚠ No se pudo terminar; revisa el registro de abajo.";
});

$$(".sel-voz").forEach((s) => { for (const [v, n] of VOCES) { const o = document.createElement("option"); o.value = v; o.textContent = n; s.appendChild(o); } });
async function guardarAuto() {
  ajustes = await window.ctv.saveSettings(ajustes);
  pintarSecciones();
  repintarBriefs();   // los botones de rubro, temática, etc. guardan sus listas dentro del objeto de ajustes: al cambiar ese objeto hay que volver a enlazarlos o el conteo se queda pegado
}
function repintarBriefs() {
  for (const l of ["dianchi", "diegao"]) conLinea(l, pintarBrief);
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
  for (const [nombre, preset, caja] of [["fuente-imagenes", "imagenesCollage", "#caja-imagenes"], ["fuente-videos", "rellenoLocal", "#caja-videos"]]) {
    const v = ajustes.presets[preset] ? "carpeta" : "auto";
    $$('input[name="' + nombre + '"]').forEach((r) => (r.checked = r.value === v));
    $(caja).classList.toggle("oculto", v !== "carpeta");
  }
  for (const [nombre, valor, caja] of [["fuente-imagenes-d", ajustes.presets.imagenesCollageDiegao ? "carpeta" : "auto", "#caja-imagenes-d"], ["fuente-videos-d", ajustes.presets.rellenoLocalDiegao === false ? "auto" : "carpeta", "#caja-videos-d"]]) {
    $$('input[name="' + nombre + '"]').forEach((r) => (r.checked = r.value === valor));
    $(caja).classList.toggle("oculto", valor !== "carpeta");
  }
  for (const k of ["burbuja", "pasos", "collage", "sfx", "cierre"]) $("#ev-" + k).checked = ajustes.presets.eventos[k] !== false;
  resumenDianchi();
  pintarPrecios();
  pintarInfografias();
  pintarAnimTexto();
  pintarCortar();
  $$(".sel-voz").forEach((s) => (s.value = ajustes.presets.voz));
}
$$('input[name="fuente-imagenes"]').forEach((r) => r.addEventListener("change", (e) => { ajustes.presets.imagenesCollage = e.target.value === "carpeta"; guardarAuto(); }));
for (const k of ["burbuja", "pasos", "collage", "sfx", "cierre"]) $("#ev-" + k).addEventListener("change", (e) => { ajustes.presets.eventos[k] = e.target.checked; guardarAuto(); });
$("#pr-efectos").addEventListener("change", (e) => { ajustes.presets.efectos = e.target.checked; guardarAuto(); });
$$('input[name="fuente-imagenes-d"]').forEach((r) => r.addEventListener("change", (e) => { ajustes.presets.imagenesCollageDiegao = e.target.value === "carpeta"; guardarAuto(); }));
$$('input[name="fuente-videos-d"]').forEach((r) => r.addEventListener("change", (e) => { ajustes.presets.rellenoLocalDiegao = e.target.value === "carpeta"; guardarAuto(); }));
$$('input[name="fuente-videos"]').forEach((r) => r.addEventListener("change", (e) => { ajustes.presets.rellenoLocal = e.target.value === "carpeta"; guardarAuto(); }));
$$(".sel-voz").forEach((s) => s.addEventListener("change", (e) => { ajustes.presets.voz = e.target.value; guardarAuto(); }));

function pintarAjustes() {
  pintarSecciones();
  for (const L of ["dianchi", "diegao"]) conLinea(L, pintarBrief);
  actualizarContador();
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
  repintarBriefs();
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
  if (ocupado) return bloqueoActualizar(true);   // mientras trabaja se muestra el motivo del bloqueo, no el resultado de la busqueda
  const aviso = $("#aviso-upd"), txt = $("#txt-upd"), btn = $("#b-upd-ir");
  if (!i.ok) { txt.textContent = i.motivo; aviso.classList.add("oculto"); btn.disabled = true; return; }
  if (i.hay) {
    txt.textContent = "";
    aviso.textContent = "Actualización disponible (" + i.corto + "). Clic para descargar e instalar."; aviso.classList.remove("oculto"); btn.disabled = false;
  } else { txt.textContent = "Estás al día (" + i.actual + ")."; aviso.classList.add("oculto"); btn.disabled = true; }
}
window.ctv.onUpdate(mostrarUpd);
const MOTIVO_BLOQUEO = "No se puede actualizar mientras la app está trabajando: al actualizar se reinicia y se cortaría lo que se está generando. Espera a que termine o detén el proceso.";
let detenido = false;
function detener() { detenido = true; window.ctv.cancel(); escribir("■ Deteniendo el proceso…"); }
$("#b-detener").addEventListener("click", detener);
function bloqueoActualizar(b) {
  $("#b-detener").classList.toggle("oculto", !b);
  const btn = $("#b-upd"), txt = $("#txt-upd"), aviso = $("#aviso-upd");
  btn.disabled = b; btn.title = b ? MOTIVO_BLOQUEO : "";
  aviso.classList.toggle("bloqueado", b); aviso.title = b ? MOTIVO_BLOQUEO : "";
  if (b) txt.textContent = "Actualizar está bloqueado: la app está trabajando. Se podrá cuando termine o si detienes el proceso.";
  else if (ultimaInfo) mostrarUpd(ultimaInfo); else txt.textContent = "";
}
let actualizando = false;
async function actualizarAhora() {
  if (actualizando) return;
  if (ocupado) return escribir("⚠ " + MOTIVO_BLOQUEO);
  actualizando = true;
  const aviso = $("#aviso-upd");
  $("#b-upd-ir").disabled = true; $("#txt-upd").textContent = "Descargando la actualización…";
  aviso.textContent = "Descargando la actualización… la app se reiniciará sola."; aviso.classList.remove("oculto");
  const r = await window.ctv.applyUpdate();
  if (!r.ok) {
    actualizando = false;
    $("#txt-upd").textContent = r.motivo || "No se pudo actualizar."; $("#b-upd-ir").disabled = false;
    aviso.textContent = "No se pudo actualizar: " + (r.motivo || "error") + ". Clic para reintentar.";
  } else { aviso.textContent = "Actualización lista (" + r.corto + "). Reiniciando…"; $("#txt-upd").textContent = "Reiniciando…"; }
}
$("#aviso-upd").addEventListener("click", actualizarAhora);   // un clic en el aviso descarga e instala
$("#b-upd").addEventListener("click", async () => { if (ocupado) return escribir("⚠ " + MOTIVO_BLOQUEO); $("#txt-upd").textContent = "Buscando…"; mostrarUpd(await window.ctv.checkUpdate()); });
$("#b-upd-ir").addEventListener("click", actualizarAhora);

// Antes de generar videos hay que tener la ultima version: si hay una nueva, se descarga e instala (la app se reinicia) y la generacion no arranca.
let forzandoUpd = false;
function modalUpd(titulo, texto, cerrable) {
  let m = $("#modal-upd");
  if (!m) { m = document.createElement("div"); m.id = "modal-upd"; m.className = "modal-upd"; m.innerHTML = '<div class="modal-caja"><h2></h2><p></p><div class="barra"><button class="p fuerte" id="modal-upd-cerrar">Entendido</button></div></div>'; document.body.appendChild(m); $("#modal-upd-cerrar").addEventListener("click", () => m.classList.add("oculto")); }
  $("h2", m).textContent = titulo; $("p", m).textContent = texto; $("#modal-upd-cerrar").classList.toggle("oculto", !cerrable); m.classList.remove("oculto");
}
async function exigirUltimaVersion() {
  if (forzandoUpd) return false;
  let i; try { i = await window.ctv.checkUpdate(); } catch { i = null; }
  if (!i || !i.ok) { escribir("⚠ No se pudo comprobar si tienes la última versión (" + ((i && i.motivo) || "sin respuesta") + "). Se continúa con la versión actual."); return true; }
  if (!i.hay) return true;
  forzandoUpd = true;
  modalUpd("Hay una versión nueva (" + i.corto + ")", "Para generar videos necesitas tener la última versión. Se está descargando e instalando; la app se reiniciará sola. Cuando vuelva a abrir, pulsa «Generar» otra vez.", false);
  const r = await window.ctv.applyUpdate();
  if (!r || !r.ok) { forzandoUpd = false; modalUpd("No se pudo actualizar", ((r && r.motivo) || "Error desconocido") + ". Revisa tu conexión e inténtalo de nuevo: no se puede generar sin la última versión.", true); }
  return false;
}

// ---------------------------------------------------------------- inicio
pintarIconos();
(async function init() {
  ajustes = await window.ctv.getSettings();
  pintarAjustes();
  const v = await window.ctv.version();
  $("#v-app").textContent = "v" + v.app;
  $("#txt-version").textContent = "App v" + v.app + " · motor: " + v.motor + " · carpeta de trabajo: " + v.workspace;
  comprobarEntorno();
})();

// ---------------------------------------------------------------- prompt nuevo (los existentes no se editan)
const NOMBRE_LINEA = { dianchi: "Dianchi", diegao: "Diegao", "por-cortar": "Cortar y silencios" };
$$("[data-nuevo-prompt]").forEach((b) => b.addEventListener("click", () => {
  const l = b.dataset.nuevoPrompt;
  enviarClaude(l, "Quiero un PROMPT NUEVO para la línea " + NOMBRE_LINEA[l] + ". No modifiques ni sobrescribas ningún archivo de prompt existente (ni AJUSTES.md): crea uno nuevo, por ejemplo prompt/prompt-nuevo-" + new Date().toISOString().slice(0, 10) + ".md. "
    + "Antes léete el prompt actual solo como referencia y hazme las preguntas que necesites (público, tono, tipo de negocio, estilo) para que el nuevo prompt quede hecho a mi medida. "
    + "Al terminar dime cómo usarlo para generar con él.");
}));

// ---------------------------------------------------------------- compartir el enlace de descarga
const LINK_DESCARGA = "https://github.com/dirlant/creatuvideo/releases/latest";
$("#b-compartir").addEventListener("click", async () => {
  let ok = false;
  try { await navigator.clipboard.writeText(LINK_DESCARGA); ok = true; } catch {}
  if (!ok) { const ta = document.createElement("textarea"); ta.value = LINK_DESCARGA; document.body.appendChild(ta); ta.select(); try { ok = document.execCommand("copy"); } catch {} ta.remove(); }
  const b = $("#b-compartir"), t0 = "Compartir enlace de descarga";
  b.textContent = ok ? "✔ Enlace copiado" : "No se pudo copiar"; setTimeout(() => (b.textContent = t0), 2500);
  escribir((ok ? "✔ Enlace de descarga copiado: " : "Enlace de descarga: ") + LINK_DESCARGA);
});
