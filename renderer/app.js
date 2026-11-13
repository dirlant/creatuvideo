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
  dianchi: ["dianchiResultado", "imagenes", "relleno"],
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
  $$(".sel-voz").forEach((s) => (s.value = ajustes.presets.voz));
}
$("#pr-efectos").addEventListener("change", (e) => { ajustes.presets.efectos = e.target.checked; guardarAuto(); });
$("#pr-relleno").addEventListener("change", (e) => { ajustes.presets.rellenoLocal = e.target.checked; guardarAuto(); });
$$(".sel-voz").forEach((s) => s.addEventListener("change", (e) => { ajustes.presets.voz = e.target.value; guardarAuto(); }));

function pintarAjustes() {
  pintarSecciones();
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
async function iniciarSesion() {
  const r = await window.ctv.claudeLogin();
  if (!r.ok) return escribir("⚠ " + r.error);
  escribir("Se abrió el inicio de sesión de Claude: complétalo en el navegador. La app lo detecta sola.");
  if (esperandoLogin) clearInterval(esperandoLogin);
  let n = 0;
  esperandoLogin = setInterval(async () => {
    n++; const cs = await window.ctv.claudeStatus();
    if (cs.sesion || n > 60) { clearInterval(esperandoLogin); esperandoLogin = null; actualizarCuenta(); comprobarEntorno(); if (cs.sesion) escribir("Sesión de Claude iniciada ✔"); }
  }, 4000);
}
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
