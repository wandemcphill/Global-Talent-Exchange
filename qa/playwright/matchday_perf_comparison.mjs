/**
 * GTEX Matchday 3D — Performance Comparison & Quality Tier Benchmark.
 *
 * Compares:
 *   Test A: High Quality WITH video recording enabled (overhead baseline)
 *   Test B: High Quality WITHOUT video recording (pure WebGL baseline)
 *   Test C: Medium Quality WITHOUT video recording
 *   Test D: Low Quality WITHOUT video recording
 *
 * Runs against the demonstration fixture (u2a-006-showcase) at 1920x1080.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.GTEX_ACC_BASE_URL ?? "http://127.0.0.1:3100";
const EMAIL = process.env.GTEX_E2E_EMAIL ?? "seed.fan@gte.local";
const PASSWORD = process.env.GTEX_E2E_PASSWORD ?? "DemoPass123";
const OUT = path.resolve("qa/playwright/perf-comparison-out");
const RUN_SECONDS = Number(process.env.BENCHMARK_SECONDS ?? 45);

fs.mkdirSync(OUT, { recursive: true });

async function runBenchmark(tier, withVideo, label) {
  console.log(`\n=== Running ${label} (tier=${tier}, video=${withVideo}, duration=${RUN_SECONDS}s) ===`);
  const browser = await chromium.launch({
    headless: true,
    args: ["--ignore-gpu-blocklist", "--enable-webgl", "--use-angle=default", "--enable-unsafe-swiftshader"],
  });

  const contextOptions = {
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  };
  if (withVideo) {
    contextOptions.recordVideo = {
      dir: path.join(OUT, `video_${label}`),
      size: { width: 1920, height: 1080 },
    };
  }

  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  // Login
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.locator('input[type="email"], input[name="email"], input[type="text"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASSWORD);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/\/app|\/onboarding/, { timeout: 60000 });

  // Navigate to match with specific tier
  await page.goto(
    `${BASE}/app/match/u2a-006-showcase?live=1&dismissWalkout=1&duration=300&speed=1&tier=${tier}`,
    { waitUntil: "domcontentloaded" }
  );

  await page.waitForSelector('[data-testid="match-pitch-live-scene"] canvas', { timeout: 90000 });
  await page.waitForFunction(
    () => window.__GTEX_BROADCAST_TELEMETRY__ && window.__GTEX_BROADCAST_TELEMETRY__.activeRigCount >= 22,
    null,
    { timeout: 90000 }
  );

  // Setup frame rate and telemetry capture
  await page.evaluate(() => {
    window.__PERF__ = {
      deltas: [],
      samples: [],
      last: performance.now(),
      stalls: [],
      ctxLost: 0,
    };
    const loop = (t) => {
      const d = t - window.__PERF__.last;
      window.__PERF__.last = t;
      window.__PERF__.deltas.push(d);
      if (d > 100) window.__PERF__.stalls.push({ at: Math.round(t), ms: Math.round(d) });
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
    document.querySelector("canvas")?.addEventListener("webglcontextlost", () => window.__PERF__.ctxLost++);
    setInterval(() => {
      const t = window.__GTEX_BROADCAST_TELEMETRY__;
      if (!t) return;
      window.__PERF__.samples.push({
        wall: performance.now(),
        avgFps: t.avgFps,
        p95: t.p95FrameMs,
        drawCalls: t.drawCalls,
        tris: t.triangles,
        geos: t.geometries,
        tex: t.textures,
        heap: t.jsHeapUsedMb,
        tier: t.qualityTier,
      });
    }, 500);
  });

  // Run benchmark duration
  const startTime = Date.now();
  await new Promise((r) => setTimeout(r, RUN_SECONDS * 1000));
  const elapsedSec = (Date.now() - startTime) / 1000;

  // Extract results
  const metrics = await page.evaluate(() => {
    const d = window.__PERF__.deltas.slice(2);
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

    const samples = window.__PERF__.samples;
    const calls = samples.map((x) => x.drawCalls).filter(Boolean);
    const tris = samples.map((x) => x.tris).filter(Boolean);
    const heaps = samples.map((x) => x.heap).filter(Boolean);

    return {
      frames: d.length,
      avgFps: Number((1000 / avg).toFixed(2)),
      p50FrameMs: Number(q(0.5).toFixed(2)),
      p95FrameMs: Number(q(0.95).toFixed(2)),
      p99FrameMs: Number(q(0.99).toFixed(2)),
      worstSustained5sFps: Number(worstFps.toFixed(2)),
      stalls100ms: window.__PERF__.stalls.length,
      contextLost: window.__PERF__.ctxLost,
      drawCallsMin: calls.length ? Math.min(...calls) : 0,
      drawCallsMax: calls.length ? Math.max(...calls) : 0,
      drawCallsAvg: calls.length ? Math.round(calls.reduce((a, b) => a + b, 0) / calls.length) : 0,
      trianglesMin: tris.length ? Math.min(...tris) : 0,
      trianglesMax: tris.length ? Math.max(...tris) : 0,
      heapStartMb: heaps[0] || null,
      heapEndMb: heaps[heaps.length - 1] || null,
      tierReported: samples[samples.length - 1]?.tier || null,
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

  const fullResult = {
    label,
    tier,
    withVideo,
    elapsedSec: Number(elapsedSec.toFixed(2)),
    env,
    metrics,
  };

  console.log(`Results for ${label}:`, JSON.stringify(fullResult, null, 2));

  await context.close();
  await browser.close();
  return fullResult;
}

async function main() {
  console.log("Starting GTEX Performance Benchmark Matrix...");
  const results = {};

  // Test A: High quality WITH video recording
  results.testA_high_with_video = await runBenchmark("high", true, "Test_A_High_Video_On");

  // Test B: High quality WITHOUT video recording
  results.testB_high_no_video = await runBenchmark("high", false, "Test_B_High_Video_Off");

  // Test C: Medium quality WITHOUT video recording
  results.testC_medium_no_video = await runBenchmark("medium", false, "Test_C_Medium_Video_Off");

  // Test D: Low quality WITHOUT video recording
  results.testD_low_no_video = await runBenchmark("low", false, "Test_D_Low_Video_Off");

  const summaryPath = path.join(OUT, "performance_comparison_results.json");
  fs.writeFileSync(summaryPath, JSON.stringify(results, null, 2));
  console.log(`\nAll benchmarks complete! Written to ${summaryPath}`);
}

main().catch((err) => {
  console.error("Benchmark failed:", err);
  process.exit(1);
});
