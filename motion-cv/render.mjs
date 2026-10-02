// Renders index.html frame by frame with headless Chromium and pipes PNGs into ffmpeg.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
const require = createRequire("/opt/node-tools/node_modules/");
const { chromium } = require("playwright");

const root = path.dirname(new URL(import.meta.url).pathname);
const stills = process.argv.slice(2).map(Number);
const types = { ".html": "text/html", ".woff2": "font/woff2" };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  fs.readFile(f, (e, d) => e ? (res.writeHead(404), res.end()) : (res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }), res.end(d)));
}).listen(0);
const port = server.address().port;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(`http://localhost:${port}/index.html?render`);
await page.evaluate(() => window.ready);
const grab = async f => Buffer.from(await page.evaluate(f => { renderFrame(f); return document.getElementById("c").toDataURL("image/png").split(",")[1]; }, f), "base64");

if (stills.length) {
  fs.mkdirSync(path.join(root, "stills"), { recursive: true });
  for (const s of stills) fs.writeFileSync(path.join(root, "stills", `t${s}.png`), await grab(Math.round(s * 60)));
} else {
  const total = await page.evaluate(() => TOTAL_FRAMES);
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", "60", "-i", "-",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    path.join(root, "claude-motion-reel.mp4")], { stdio: ["pipe", "inherit", "inherit"] });
  for (let f = 0; f < total; f++) {
    const png = await grab(f);
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once("drain", r));
    if (f % 60 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on("close", r));
}
await browser.close(); server.close();
