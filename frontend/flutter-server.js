const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = process.env.GTEX_FLUTTER_WEB_DIR || "/app/gtex/frontend/build/web";
const PORT = Number(process.env.PORT || 3000);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "application/javascript", ".mjs": "application/javascript", ".json": "application/json",
  ".wasm": "application/wasm", ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
  ".ico": "image/x-icon", ".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2", ".bin": "application/octet-stream", ".frag": "application/octet-stream",
};

http
  .createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
    let file = path.normalize(path.join(ROOT, urlPath));
    if (!file.startsWith(ROOT)) file = path.join(ROOT, "index.html");
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(ROOT, "index.html");
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream", "Cache-Control": file.endsWith("index.html") ? "no-cache" : "public, max-age=3600" });
    fs.createReadStream(file).pipe(res);
  })
  .listen(PORT, "0.0.0.0", () => console.log(`GTEX Flutter web served from ${ROOT} on :${PORT}`));
