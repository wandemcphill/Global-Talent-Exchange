/**
 * GTEX Matchday 3D — Gate 2: 300-Second Sustained Performance Benchmark.
 *
 * Runs a continuous 300-second (full 90' match) benchmark for a specified tier and video mode.
 *
 * Usage:
 *   node sustained_perf_gate2.mjs <configKey> [durationSec]
 *
 * Available configs:
 *   high_no_video       -> tier=high, video=false
 *   medium_no_video     -> tier=medium, video=false
 *   low_no_video        -> tier=low, video=false
 *   medium_with_video   -> tier=medium, video=true
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const CONFIGS = {
  high_no_video: { tier: "high", video: false, label: "High_Quality_Video_Off" },
  medium_no_video: { tier: "medium", video: false, label: "Medium_Quality_Video_Off" },
  low_no_video: { tier: "low", video: false, label: "Low_Quality_Video_Off" },
  medium_with_video: { tier: "medium", video: true, label: "Medium_Quality_Video_On" },
};

const configKey = process.argv[2] ?? "medium_no_video";
const config = CONFIGS[configKey];
if (!config) {
  console.error(`Unknown config: ${configKey}. Available: ${Object.keys(CONFIGS).join(", ")}`);
  process.exit(1);
}

const DURATION = Number(process.argv[3] ?? 300);
const BASE = process.env.GTEX_ACC_BASE_URL ?? "http://127.0.0.1:3100";
const EMAIL = process.env.GTEX_E2E_EMAIL ?? "seed.fan@gte.local";
const PASSWORD = process.env.GTEX_E2E_PASSWORD ?? "DemoPass123";
const OUT = path.resolve("qa/playwright/sustained-perf-out");

fs.mkdirSync(OUT, { recursive: true });

console.log(`\n======================================================`);
console.log(`GTEX GATE 2 SUSTAINED BENCHMARK: ${config.label}`);
console.log(`Tier: ${config.tier} | Video: ${config.video} | Duration: ${DURATION}s`);
console.log(`======================================================\n`);

const browser = await chromium.launch({
  headless: true,
  args: ["--ignore-gpu-blocklist", "--enable-webgl", "--use-angle=default", "--enable-unsafe-swiftshader"],
});

const contextOptions = {
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
};
if (config.video) {
  contextOptions.recordVideo = {
    dir: path.join(OUT, `video_${configKey}`),
    size: { width: 1920, height: 1080 },
  };
}

const context = await browser.newContext(contextOptions);
const page = await context.newPage();

// 1. Real Login
console.log(`Logging in via ${BASE}/login...`);
await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
await page.locator('input[type="email"], input[name="email"], input[type="text"]').first().fill(EMAIL);
await page.locator('input[type="password"]').first().fill(PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/\/app|\/onboarding/, { timeout: 60000 });
console.log(`Login successful: ${page.url()}`);

// 2. Load Match Center
console.log(`Navigating to match u2a-006-showcase with tier=${config.tier}...`);
await page.goto(
  `${BASE}/app/match/u2a-006-showcase?live=1&dismissWalkout=1&duration=${DURATION}&speed=1&tier=${config.tier}`,
  { waitUntil: "domcontentloaded" }
);

await page.waitForSelector('[data-testid="match-pitch-live-scene"] canvas', { timeout: 90000 });
await page.waitForFunction(
  () => window.__GTEX_BROADCAST_TELEMETRY__ && window.__GTEX_BROADCAST_TELEMETRY__.activeRigCount >= 22,
  null,
  { timeout: 90000 }
);
console.log(`3D pitch canvas ready and 22 rigs active.`);

// 3. Attach In-Page Telemetry Recorder
await page.evaluate(() => {
  window.__GATE2__ = {
    deltas: [],
    samples: [],
    last: performance.now(),
    stalls: [],
    ctxLost: 0,
  };
  const loop = (t) => {
    const d = t - window.__GATE2__.last;
    window.__GATE2__.last = t;
    window.__GATE2__.deltas.push(d);
    if (d > 100) window.__GATE2__.stalls.push({ at: Math.round(t), ms: Math.round(d) });
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  document.querySelector("canvas")?.addEventListener("webglcontextlost", () => window.__GATE2__.ctxLost++);

  setInterval(() => {
    const t = window.__GTEX_BROADCAST_TELEMETRY__;
    if (!t) return;
    window.__GATE2__.samples.push({
      wall: performance.now(),
      currentTime: t.currentTime,
      clock: t.clockLabel,
      score: t.score,
      avgFps: t.avgFps,
      p95: t.p95FrameMs,
      drawCalls: t.drawCalls,
      tris: t.triangles,
      geos: t.geometries,
      tex: t.textures,
      heap: t.jsHeapUsedMb,
      tier: t.qualityTier,
    });
  }, 1000);
});

// 4. Progress Logging Loop
const startTime = Date.now();
const intervalSec = 30;
for (let elapsed = 0; elapsed < DURATION; elapsed += intervalSec) {
  await new Promise((r) => setTimeout(r, intervalSec * 1000));
  const snap = await page.evaluate(() => {
    const d = window.__GATE2__.deltas;
    const recent = d.slice(-300);
    const avgRecent = recent.length ? 1000 / (recent.reduce((a, b) => a + b, 0) / recent.length) : 0;
    const t = window.__GTEX_BROADCAST_TELEMETRY__ || {};
    return {
      frames: d.length,
      recentFps: Number(avgRecent.toFixed(1)),
      telemetryFps: t.avgFps,
      drawCalls: t.drawCalls,
      clock: t.clockLabel,
      score: t.score,
      stalls: window.__GATE2__.stalls.length,
    };
  });
  console.log(`[${new Date().toISOString()}] Progress ${elapsed + intervalSec}/${DURATION}s | clock: ${snap.clock} | score: ${snap.score} | frames: ${snap.frames} | recentFps: ${snap.recentFps} | drawCalls: ${snap.drawCalls} | stalls: ${snap.stalls}`);
}

const totalWallSec = (Date.now() - startTime) / 1000;

// 5. Gather Final Metrics
const results = await page.evaluate(() => {
  const d = window.__GATE2__.deltas.slice(2);
  const s = d.slice().sort((a, b) => a - b);
  const q = (p) => s[Math.min(s.length - 1, Math.floor(s.length * p))];
  const avg = d.reduce((a, b) => a + b, 0) / d.length;

  let worstFps = Infinity;
  let acc = 0;
  const win = [];
  for (const x of d) {
    win.push(x);
    acc += x;
    while (acc > 5000) acc -= win.shift();
    if (acc >= 4900) worstFps = Math.min(worstFps, win.length / (acc / 1000));
  }

  const S = window.__GATE2__.samples;
  const calls = S.map((x) => x.drawCalls).filter(Boolean);
  const tris = S.map((x) => x.tris).filter(Boolean);
  const heaps = S.map((x) => x.heap).filter(Boolean);

  return {
    frames: d.length,
    avgFps: Number((1000 / avg).toFixed(2)),
    p50FrameMs: Number(q(0.5).toFixed(2)),
    p95FrameMs: Number(q(0.95).toFixed(2)),
    p99FrameMs: Number(q(0.99).toFixed(2)),
    maxFrameMs: Number(s[s.length - 1].toFixed(2)),
    worstSustained5sFps: Number(worstFps.toFixed(2)),
    stalls100ms: window.__GATE2__.stalls.length,
    stallsList: window.__GATE2__.stalls.slice(0, 20),
    contextLost: window.__GATE2__.ctxLost,
    drawCallsMin: calls.length ? Math.min(...calls) : 0,
    drawCallsMax: calls.length ? Math.max(...calls) : 0,
    drawCallsAvg: calls.length ? Math.round(calls.reduce((a, b) => a + b, 0) / calls.length) : 0,
    trianglesMin: tris.length ? Math.min(...tris) : 0,
    trianglesMax: tris.length ? Math.max(...tris) : 0,
    heapStartMb: heaps[0] || null,
    heapEndMb: heaps[heaps.length - 1] || null,
    heapMaxMb: heaps.length ? Math.max(...heaps) : null,
    tierReported: S[S.length - 1]?.tier || null,
    sampleCount: S.length,
  };
});

const env = await page.evaluate(() => {
  const t = window.__GTEX_BROADCAST_TELEMETRY__;
  return {
    gpuVendor: t?.gpuVendor,
    gpuRenderer: t?.gpuRenderer,
    canvas: [t?.canvasWidth, t?.canvasHeight],
  };
});

const finalOutput = {
  configKey,
  ...config,
  durationRequestedSec: DURATION,
  durationActualSec: Number(totalWallSec.toFixed(2)),
  env,
  metrics: results,
};

const resultPath = path.join(OUT, `${configKey}.json`);
fs.writeFileSync(resultPath, JSON.stringify(finalOutput, null, 2));
console.log(`\nFinal metrics written to: ${resultPath}`);
console.log(JSON.stringify(finalOutput, null, 2));

const videoPath = await page.video()?.path();
await context.close();
await browser.close();
if (videoPath) console.log(`Video recorded to: ${videoPath}`);
console.log(`\nFinished benchmark: ${configKey}`);
