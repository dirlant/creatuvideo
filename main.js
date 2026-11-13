// CreaTuVideo - proceso principal (Electron)
// - Muestra el panel (renderer/), guarda la configuracion y prepara la "carpeta de trabajo" con el motor (engine/).
// - Ejecuta los scripts del motor con uv/ffmpeg y reenvia el registro a la interfaz.
// - Se actualiza desde el repositorio de GitHub (engine/ y renderer/ se descargan a una carpeta "overlay").
const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { spawn, spawnSync } = require("child_process");

const REPO = "dirlant/creatuvideo";
const BRANCH = "main";
const LINEAS = ["dianchi", "diegao", "por-cortar", "ads"];

let win = null;
let hijo = null; // proceso en ejecucion (uno a la vez)

// ------------------------------------------------------------------ configuracion
const SETTINGS_FILE = () => path.join(app.getPath("userData"), "settings.json");
const DEFAULTS = () => ({
  workspace: path.join(app.getPath("documents"), "CreaTuVideo"),
  dirs: { dianchiResultado: "", diegaoResultado: "", cortarResultado: "", imagenes: "", relleno: "", diegaoFuente: "", cortarEntrada: "" },
  pexelsKey: "",
  githubToken: "",
  autoUpdate: true,
  presets: { efectos: true, voz: "es-MX-JorgeNeural", rellenoLocal: false },
});
function getSettings() {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(SETTINGS_FILE(), "utf8")); } catch {}
  const d = DEFAULTS();
  return { ...d, ...s, dirs: { ...d.dirs, ...(s.dirs || {}) }, presets: { ...d.presets, ...(s.presets || {}) } };
}
function saveSettings(s) {
  fs.mkdirSync(path.dirname(SETTINGS_FILE()), { recursive: true });
  fs.writeFileSync(SETTINGS_FILE(), JSON.stringify(s, null, 2));
}

// ------------------------------------------------------------------ motor y overlay (actualizaciones)
const OVERLAY = () => path.join(app.getPath("userData"), "overlay");
function metaOverlay() { try { return JSON.parse(fs.readFileSync(path.join(OVERLAY(), "meta.json"), "utf8")); } catch { return null; } }
function overlayValido() {
  const m = metaOverlay();
  return !!m && m.base === app.getVersion() && fs.existsSync(path.join(OVERLAY(), "engine"));   // un instalador nuevo descarta overlays viejos
}
function engineDir() {
  if (overlayValido()) return path.join(OVERLAY(), "engine");
  return app.isPackaged ? path.join(process.resourcesPath, "engine") : path.join(__dirname, "engine");
}
function rendererDir() {
  if (overlayValido() && fs.existsSync(path.join(OVERLAY(), "renderer", "index.html"))) return path.join(OVERLAY(), "renderer");
  return path.join(__dirname, "renderer");
}

// ------------------------------------------------------------------ utilidades
function log(msg) { if (win && !win.isDestroyed()) win.webContents.send("log", String(msg)); }
function busy(b) { if (win && !win.isDestroyed()) win.webContents.send("busy", b); }
function where(nombre) {
  const r = spawnSync("where", [nombre], { encoding: "utf8", windowsHide: true });
  return r.status === 0 ? (r.stdout.split(/\r?\n/)[0] || "").trim() || null : null;
}
function buscarEn(dir, archivo, prof = 5) {
  try {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isFile() && e.name.toLowerCase() === archivo) return p;
      if (e.isDirectory() && prof > 0) { const r = buscarEn(p, archivo, prof - 1); if (r) return r; }
    }
  } catch {}
  return null;
}
function winget(prefijo, archivo) {
  const base = path.join(process.env.LOCALAPPDATA || "", "Microsoft", "WinGet", "Packages");
  try {
    for (const d of fs.readdirSync(base)) if (d.toLowerCase().startsWith(prefijo.toLowerCase())) { const r = buscarEn(path.join(base, d), archivo); if (r) return r; }
  } catch {}
  return null;
}
const findUv = () => where("uv") || winget("astral-sh.uv", "uv.exe") || (fs.existsSync(path.join(os.homedir(), ".local", "bin", "uv.exe")) ? path.join(os.homedir(), ".local", "bin", "uv.exe") : null);
const findFfmpeg = () => where("ffmpeg") || winget("Gyan.FFmpeg", "ffmpeg.exe");
const findNode = () => where("node");
const findClaude = () => where("claude");

// ------------------------------------------------------------------ carpeta de trabajo (workspace)
function copiar(src, dst) { if (fs.existsSync(src)) fs.cpSync(src, dst, { recursive: true, force: true }); }
function copiarSiFalta(src, dst, avisar) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) { copiarSiFalta(s, d, avisar); continue; }
    if (!fs.existsSync(d)) fs.copyFileSync(s, d);
    else if (avisar && fs.readFileSync(s, "utf8") !== fs.readFileSync(d, "utf8")) {        // el usuario/Claude ya cambio este archivo: no se pisa, se deja la version nueva al lado
      const alt = d.replace(/(\.[^.]+)$/, ".actualizado$1");
      fs.copyFileSync(s, alt); log("Prompt con cambios del repositorio guardado como " + path.relative(getSettings().workspace, alt));
    }
  }
}
function normRuta(p) { return path.resolve(String(p).replace(/^\\\\\?\\/, "")).replace(/[\\/]+$/, "").toLowerCase(); }
function asegurarEnlace(ws, rel, destino) {
  const p = path.join(ws, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  let st = null; try { st = fs.lstatSync(p); } catch {}
  if (!destino) {                                  // sin carpeta elegida: carpeta normal dentro de la carpeta de trabajo
    if (st && st.isSymbolicLink()) fs.rmdirSync(p);
    fs.mkdirSync(p, { recursive: true }); return;
  }
  fs.mkdirSync(destino, { recursive: true });
  if (st) {
    if (st.isSymbolicLink()) { if (normRuta(fs.readlinkSync(p)) === normRuta(destino)) return; fs.rmdirSync(p); }
    else if (st.isDirectory()) {
      if (fs.readdirSync(p).length === 0) fs.rmdirSync(p);
      else { log("AVISO: " + rel + " ya tiene archivos dentro de la carpeta de trabajo; no se enlaza a " + destino + ". Muevelos y vuelve a guardar."); return; }
    }
  }
  fs.symlinkSync(destino, p, "junction");
}
function syncWorkspace(actualizando = false) {
  const s = getSettings(), ws = s.workspace, eng = engineDir();
  fs.mkdirSync(ws, { recursive: true });
  copiar(path.join(eng, "scripts"), path.join(ws, "scripts"));
  copiar(path.join(eng, "assets"), path.join(ws, "_operacion", "_work"));
  fs.mkdirSync(path.join(ws, "_operacion", "_trabajo"), { recursive: true });
  for (const l of LINEAS) {
    fs.mkdirSync(path.join(ws, l, "_operacion"), { recursive: true });
    copiarSiFalta(path.join(eng, "prompts", l), path.join(ws, l), actualizando);
  }
  copiarSiFalta(path.join(eng, "prompts"), ws, false);                     // CLAUDE.md de la raiz si existe
  const d = s.dirs;
  asegurarEnlace(ws, "dianchi/resultado", d.dianchiResultado);
  asegurarEnlace(ws, "diegao/resultado", d.diegaoResultado);
  asegurarEnlace(ws, "por-cortar/resultado", d.cortarResultado);
  asegurarEnlace(ws, "dianchi/entrada/imagenes", d.imagenes);
  asegurarEnlace(ws, "dianchi/entrada/videos", d.relleno);
  asegurarEnlace(ws, "diegao/entrada/evento-receta", d.diegaoFuente);
  asegurarEnlace(ws, "por-cortar/entrada", d.cortarEntrada);
  return ws;
}

// ------------------------------------------------------------------ ejecucion de procesos
function entorno(extra = {}) {
  const s = getSettings(), ff = findFfmpeg();
  const env = { ...process.env, PYTHONIOENCODING: "utf-8", ...extra };
  if (s.pexelsKey) env.PEXELS_API_KEY = s.pexelsKey;
  env.CTV_EFECTOS = s.presets.efectos ? "1" : "0";
  env.CTV_VOZ = s.presets.voz || "es-MX-JorgeNeural";
  if (ff) env.PATH = path.dirname(ff) + path.delimiter + (env.PATH || env.Path || "");
  return env;
}
function correr(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    log("> " + [path.basename(cmd), ...args].join(" "));
    const p = spawn(cmd, args, { cwd: opts.cwd, env: opts.env || entorno(), windowsHide: true });
    hijo = p; busy(true);
    p.stdout.setEncoding("utf8"); p.stderr.setEncoding("utf8");
    const emitir = (b) => String(b).split(/\r?\n/).filter(Boolean).forEach(log);
    p.stdout.on("data", emitir); p.stderr.on("data", emitir);
    p.on("error", (e) => { log("ERROR: " + e.message); hijo = null; busy(false); resolve(-1); });
    p.on("close", (c) => { hijo = null; busy(false); resolve(c); });
  });
}
function capturar(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    let out = "", err = "";
    const p = spawn(cmd, args, { cwd: opts.cwd, env: opts.env || entorno(), windowsHide: true });
    p.stdout.setEncoding("utf8"); p.stderr.setEncoding("utf8");
    p.stdout.on("data", (b) => (out += b)); p.stderr.on("data", (b) => (err += b));
    p.on("error", (e) => resolve({ code: -1, out, err: e.message }));
    p.on("close", (c) => resolve({ code: c, out, err }));
  });
}
function recodificarHevc(dir) {      // hyperframes entrega HEVC 10 bits: se pasa a H.264 para que se vea en cualquier telefono
  const ff = findFfmpeg(); if (!ff || !fs.existsSync(dir)) return;
  const fp = ff.replace(/ffmpeg\.exe$/i, "ffprobe.exe");
  for (const f of fs.readdirSync(dir)) {
    if (!/\.mp4$/i.test(f)) continue;
    const p = path.join(dir, f);
    const c = spawnSync(fp, ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", p], { encoding: "utf8", windowsHide: true }).stdout || "";
    if (!/hevc/i.test(c)) continue;
    log("Pasando a H.264: " + f);
    const tmp = p + ".tmp.mp4";
    const r = spawnSync(ff, ["-nostdin", "-y", "-v", "error", "-i", p, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp], { windowsHide: true });
    if (r.status === 0) fs.renameSync(tmp, p); else { try { fs.unlinkSync(tmp); } catch {} }
  }
}

// ------------------------------------------------------------------ IPC
ipcMain.handle("version", () => {
  const m = overlayValido() ? metaOverlay() : null;
  return { app: app.getVersion(), motor: m ? (m.version || "") + " (" + String(m.sha || "").slice(0, 7) + ")" : "incluido en el instalador", workspace: getSettings().workspace };
});
ipcMain.handle("settings:get", () => getSettings());
ipcMain.handle("settings:save", (_e, s) => { saveSettings(s); try { syncWorkspace(); } catch (e) { log("ERROR al preparar carpetas: " + e.message); } return getSettings(); });
ipcMain.handle("pick-folder", async (_e, titulo) => {
  const r = await dialog.showOpenDialog(win, { title: titulo || "Elegir carpeta", properties: ["openDirectory", "createDirectory"] });
  return r.canceled ? null : r.filePaths[0];
});
ipcMain.handle("pick-file", async (_e, titulo) => {
  const r = await dialog.showOpenDialog(win, { title: titulo || "Elegir archivo", properties: ["openFile"], filters: [{ name: "Video", extensions: ["mp4", "mov", "mkv", "webm"] }] });
  return r.canceled ? null : r.filePaths[0];
});
ipcMain.handle("open-path", async (_e, p) => { const s = getSettings(); const ruta = path.isAbsolute(p) ? p : path.join(s.workspace, p); fs.mkdirSync(ruta, { recursive: true }); return shell.openPath(ruta); });
ipcMain.handle("open-url", (_e, u) => { if (/^https:\/\//.test(u)) shell.openExternal(u); });

ipcMain.handle("env:check", () => {
  const s = getSettings();
  return { uv: findUv(), ffmpeg: findFfmpeg(), node: findNode(), claude: findClaude(), winget: where("winget"), pexels: !!s.pexelsKey, workspace: s.workspace };
});
const WINGET_IDS = { ffmpeg: "Gyan.FFmpeg", uv: "astral-sh.uv", node: "OpenJS.NodeJS.LTS" };
ipcMain.handle("env:install", async (_e, que) => {
  const id = WINGET_IDS[que]; if (!id) return { ok: false, error: "Desconocido" };
  if (!where("winget")) return { ok: false, error: "No se encontro winget. Instala manualmente " + que + "." };
  const c = await correr("winget", ["install", "--id", id, "-e", "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"]);
  return { ok: c === 0 };
});

ipcMain.handle("lote:listar", async (_e, linea) => {
  const uv = findUv(); if (!uv) return { error: "Falta uv (Ajustes > Comprobar entorno)." };
  const ws = syncWorkspace(); const script = linea === "diegao" ? "diegao_lote.py" : "dianchi_lote.py";
  const r = await capturar(uv, ["run", "--python", "3.12", "--with", "pillow", "python", path.join("scripts", script), findFfmpeg() || "ffmpeg.exe", "listar"], { cwd: ws });
  try { return { items: JSON.parse(r.out.trim().split(/\r?\n/).pop()) }; } catch { return { error: "No se pudo leer la lista: " + (r.err || r.out).slice(-300) }; }
});
ipcMain.handle("lote:run", async (_e, { linea, modo, slugs }) => {
  if (hijo) return { ok: false, error: "Ya hay un proceso en marcha." };
  const uv = findUv(), ff = findFfmpeg();
  if (!uv || !ff) return { ok: false, error: "Falta " + (!uv ? "uv" : "FFmpeg") + ". Ve a Ajustes > Comprobar entorno." };
  const s = getSettings();
  if (modo === "descargar" && !s.pexelsKey && !s.presets.rellenoLocal) return { ok: false, error: "Falta la clave de Pexels (Ajustes) o activa \"usar mis videos de relleno\"." };
  const ws = syncWorkspace();
  const script = linea === "diegao" ? "diegao_lote.py" : "dianchi_lote.py";
  const env = entorno({ CTV_RELLENO_LOCAL: s.presets.rellenoLocal ? "1" : "0" });
  const args = ["run", "--python", "3.12", "--with", "edge-tts", "--with", "pillow", "--with", "numpy", "python", path.join("scripts", script), ff, modo, ...(slugs || [])];
  log("=== " + linea + " / " + modo + (slugs && slugs.length ? " / " + slugs.join(", ") : "") + " ===");
  const c = await correr(uv, args, { cwd: ws, env });
  if (modo === "render") recodificarHevc(path.join(ws, linea, "resultado"));
  log(c === 0 ? "=== Terminado ===" : "=== Termino con codigo " + c + " ===");
  return { ok: c === 0 };
});
ipcMain.handle("lote:cancel", () => {
  if (!hijo) return false;
  spawnSync("taskkill", ["/pid", String(hijo.pid), "/T", "/F"], { windowsHide: true });
  log("Proceso cancelado."); return true;
});

ipcMain.handle("claude:open", (_e, { linea, instruccion }) => {
  const claude = findClaude();
  if (!claude) return { ok: false, error: "No se encontro Claude Code. Instalalo (Ajustes > Claude Code) e inicia sesion con tu cuenta." };
  const ws = syncWorkspace();
  const pre = linea && linea !== "general" ? "Trabaja en la carpeta ./" + linea + ". Antes de empezar lee ./" + linea + "/CLAUDE.md y ./" + linea + "/prompt/AJUSTES.md.\n\n" : "";
  const archivo = path.join(ws, "_instruccion.txt");
  fs.writeFileSync(archivo, pre + instruccion + "\n\nLa app CreaTuVideo usa los scripts de ./scripts y las carpetas de entrada/resultado de cada linea; si cambias una regla que deba valer a futuro, anotala en prompt/AJUSTES.md.", "utf8");
  const cmd = "claude 'Lee el archivo _instruccion.txt de esta carpeta y haz lo que pide.'";
  const p = spawn("powershell.exe", ["-NoExit", "-NoProfile", "-Command", cmd], { cwd: ws, detached: true, stdio: "ignore", windowsHide: false });
  p.unref();
  return { ok: true };
});

// ------------------------------------------------------------------ actualizacion desde GitHub
function ghToken() {
  const s = getSettings();
  if (s.githubToken) return s.githubToken;
  if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN;
  const gh = where("gh");
  if (gh) { const r = spawnSync(gh, ["auth", "token"], { encoding: "utf8", windowsHide: true }); if (r.status === 0 && r.stdout.trim()) return r.stdout.trim(); }
  return "";
}
function cabeceras() {
  const h = { Accept: "application/vnd.github+json", "User-Agent": "CreaTuVideo", "X-GitHub-Api-Version": "2022-11-28" };
  const t = ghToken(); if (t) h.Authorization = "Bearer " + t;
  return h;
}
async function comprobarActualizacion() {
  try {
    const res = await fetch("https://api.github.com/repos/" + REPO + "/commits/" + BRANCH, { headers: cabeceras() });
    if (res.status === 404 || res.status === 401 || res.status === 403) return { ok: false, motivo: "Sin acceso al repositorio (es privado). Agrega un token de GitHub en Ajustes." };
    if (res.status === 409 || res.status === 422) return { ok: false, motivo: "El repositorio todavia no tiene versiones publicadas." };
    if (!res.ok) return { ok: false, motivo: "GitHub respondio " + res.status };
    const j = await res.json(); const m = metaOverlay();
    const local = overlayValido() && m ? m.sha : null;
    return { ok: true, sha: j.sha, corto: j.sha.slice(0, 7), actual: local ? local.slice(0, 7) : "instalada", hay: j.sha !== local, mensaje: String(j.commit.message || "").split("\n")[0] };
  } catch (e) { return { ok: false, motivo: "Sin conexion: " + e.message }; }
}
async function aplicarActualizacion() {
  const info = await comprobarActualizacion();
  if (!info.ok) return info;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ctv-upd-"));
  try {
    log("Descargando version " + info.corto + "...");
    const res = await fetch("https://api.github.com/repos/" + REPO + "/zipball/" + BRANCH, { headers: cabeceras(), redirect: "follow" });
    if (!res.ok) return { ok: false, motivo: "No se pudo descargar (" + res.status + ")" };
    const zip = path.join(tmp, "repo.zip"); fs.writeFileSync(zip, Buffer.from(await res.arrayBuffer()));
    const x = spawnSync("powershell.exe", ["-NoProfile", "-Command", "Expand-Archive -LiteralPath '" + zip.replace(/'/g, "''") + "' -DestinationPath '" + path.join(tmp, "x").replace(/'/g, "''") + "' -Force"], { windowsHide: true, encoding: "utf8" });
    if (x.status !== 0) return { ok: false, motivo: "No se pudo descomprimir: " + (x.stderr || "").slice(0, 200) };
    const raiz = fs.readdirSync(path.join(tmp, "x"))[0]; const src = path.join(tmp, "x", raiz);
    if (!fs.existsSync(path.join(src, "engine"))) return { ok: false, motivo: "La version descargada no trae la carpeta engine/." };
    fs.rmSync(OVERLAY(), { recursive: true, force: true }); fs.mkdirSync(OVERLAY(), { recursive: true });
    copiar(path.join(src, "engine"), path.join(OVERLAY(), "engine"));
    if (fs.existsSync(path.join(src, "renderer"))) copiar(path.join(src, "renderer"), path.join(OVERLAY(), "renderer"));
    let version = ""; try { version = JSON.parse(fs.readFileSync(path.join(src, "package.json"), "utf8")).version; } catch {}
    fs.writeFileSync(path.join(OVERLAY(), "meta.json"), JSON.stringify({ sha: info.sha, base: app.getVersion(), version, fecha: new Date().toISOString() }, null, 2));
    syncWorkspace(true);
    log("Actualizado a " + info.corto + (version ? " (v" + version + ")" : "") + ". Reiniciando...");
    setTimeout(() => { app.relaunch(); app.exit(0); }, 1200);
    return { ok: true, corto: info.corto };
  } catch (e) { return { ok: false, motivo: e.message }; }
  finally { try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {} }
}
ipcMain.handle("update:check", () => comprobarActualizacion());
ipcMain.handle("update:apply", () => aplicarActualizacion());

// ------------------------------------------------------------------ ventana
function crearVentana() {
  const area = require("electron").screen.getPrimaryDisplay().workAreaSize;
  win = new BrowserWindow({
    width: Math.min(1280, area.width), height: Math.min(860, area.height), minWidth: 980, minHeight: 640, title: "CreaTuVideo", backgroundColor: "#14111c",
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false, sandbox: false },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(path.join(rendererDir(), "index.html"));
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https:\/\//.test(url)) shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("did-finish-load", async () => {
    try { syncWorkspace(); } catch (e) { log("ERROR al preparar la carpeta de trabajo: " + e.message); }
    if (getSettings().autoUpdate) setTimeout(async () => { const i = await comprobarActualizacion(); if (win && !win.isDestroyed()) win.webContents.send("update:info", i); }, 3000);
  });
}
app.whenReady().then(crearVentana);
app.on("window-all-closed", () => app.quit());
