// Pone el icono en el .exe despues de empaquetar (electron-builder no lo hace con signAndEditExecutable:false).
const path = require("path");
exports.default = async function (context) {
  const { rcedit } = await import("rcedit");
  const exe = path.join(context.appOutDir, context.packager.appInfo.productFilename + ".exe");
  await rcedit(exe, { icon: path.join(__dirname, "icon.ico") });
  console.log("  • icono aplicado a " + path.basename(exe));
};
