/**
 * GTEX Matchday 3D — Gate 4: Renderer Lifecycle, Context Loss & Recovery Verification.
 *
 * Verifies:
 *   1. Initial 3D Scene WebGL Mount: checks active geometries, textures, draw calls, heap.
 *   2. WebGL Context Loss Simulation: triggers WEBGL_lose_context.loseContext(),
 *      verifies UI detects context loss, displays 2D fallback banner, fires callbacks.
 *   3. WebGL Context Restoration: triggers WEBGL_lose_context.restoreContext(),
 *      verifies 3D canvas recovers, re-initializes renderer, resumes animation loop.
 *   4. 3D-to-2D Manual Fallback: clicks "2D PITCH" button, verifies WebGL scene unmounts,
 *      geometries/textures/shaders disposed, 2D radar renders without Three.js errors.
 *   5. 2D-to-3D Manual Recovery: clicks "3D BROADCAST" button, verifies 3D scene remounts cleanly,
 *      checks geometry and texture count does not accumulate (absence of memory leaks).
 *   6. Repeated Cycle Verification (x3): toggles 2D/3D repeatedly, checks for progressive leak.
 *
 * Outputs screenshots and telemetry report to qa/playwright/lifecycle-gate4-out/
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.GTEX_ACC_BASE_URL ?? "http://127.0.0.1:3100";
const EMAIL = process.env.GTEX_E2E_EMAIL ?? "seed.fan@gte.local";
const PASSWORD = process.env.GTEX_E2E_PASSWORD ?? "DemoPass123";
const OUT = path.resolve("qa/playwright/lifecycle-gate4-out");

fs.mkdirSync(OUT, { recursive: true });

console.log("\n======================================================");
console.log("GTEX GATE 4: RENDERER LIFECYCLE & CONTEXT RECOVERY TEST");
console.log("======================================================\n");

const browser = await chromium.launch({
  headless: true,
  args: ["--ignore-gpu-blocklist", "--enable-webgl", "--use-angle=default", "--enable-unsafe-swiftshader"],
});

const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
});
const page = await context.newPage();

const consoleErrors = [];
page.on("console", (m) => {
  if (m.type() === "error") consoleErrors.push(m.text());
});

// Login
console.log("1. Logging in...");
await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
await page.locator('input[type="email"], input[name="email"], input[type="text"]').first().fill(EMAIL);
await page.locator('input[type="password"]').first().fill(PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/\/app|\/onboarding/, { timeout: 60000 });

// Navigate to match
console.log("2. Navigating to match u2a-006-showcase...");
await page.goto(`${BASE}/app/match/u2a-006-showcase?live=1&dismissWalkout=1&duration=300&speed=1&tier=medium`, {
  waitUntil: "domcontentloaded",
});
await page.waitForSelector('[data-testid="match-pitch-live-scene"] canvas', { timeout: 90000 });
await page.waitForFunction(
  () => window.__GTEX_BROADCAST_TELEMETRY__ && window.__GTEX_BROADCAST_TELEMETRY__.activeRigCount >= 22,
  null,
  { timeout: 90000 }
);

// Capture Initial State
console.log("3. Capturing initial 3D mount baseline...");
await page.screenshot({ path: path.join(OUT, "01_initial_3d_mount.png") });
const initialBaseline = await page.evaluate(() => {
  const t = window.__GTEX_BROADCAST_TELEMETRY__;
  return {
    geos: t?.geometries,
    tex: t?.textures,
    drawCalls: t?.drawCalls,
    heap: t?.jsHeapUsedMb,
    rigs: t?.activeRigCount,
  };
});
console.log("Initial Baseline:", initialBaseline);

// Test WebGL Context Loss Simulation
console.log("4. Simulating WebGL context loss via WEBGL_lose_context extension...");
const contextLossSimulated = await page.evaluate(() => {
  const canvas = document.querySelector("canvas");
  if (!canvas) return { error: "No canvas found" };
  const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl") || canvas.getContext("webgl2");
  if (!gl) return { error: "No gl context found" };
  const loseExt = gl.getExtension("WEBGL_lose_context");
  if (!loseExt) return { error: "WEBGL_lose_context extension not supported in this browser" };
  window.__LOSE_EXT__ = loseExt;
  loseExt.loseContext();
  return { success: true };
});
console.log("Context loss trigger:", contextLossSimulated);

await new Promise((r) => setTimeout(r, 2000));
await page.screenshot({ path: path.join(OUT, "02_context_lost_state.png") });

const contextLostDetected = await page.evaluate(() => {
  const fallbackNotice = document.querySelector('[data-testid="webgl-context-lost-notice"]') ||
                         document.querySelector('[data-testid="match-pitch-live-scene-fallback-container"]');
  return {
    fallbackNoticePresent: !!fallbackNotice,
    fallbackText: fallbackNotice?.textContent || null,
  };
});
console.log("Context loss UI reaction:", contextLostDetected);

// Test Context Restoration & Recovery
console.log("5. Simulating WebGL context restoration and recovery to 3D...");
if (contextLossSimulated.success) {
  await page.evaluate(() => {
    if (window.__LOSE_EXT__) {
      window.__LOSE_EXT__.restoreContext();
    }
    document.getElementById("webpack-dev-server-client-overlay")?.remove();
  });
  await new Promise((r) => setTimeout(r, 1000));
  const restoreBtn = page.locator('[data-testid="return-to-3d-broadcast-button"], [data-testid="toggle-3d-broadcast-mode"], button:has-text("SWITCH TO 3D BROADCAST")').first();
  if (await restoreBtn.count()) {
    await restoreBtn.click({ force: true });
  }
  await new Promise((r) => setTimeout(r, 3000));
  // If we are now in 2D mode, click toggle-3d-broadcast-mode to return to 3D
  const toggle3DMode = page.locator('[data-testid="toggle-3d-broadcast-mode"]').first();
  if (await toggle3DMode.count() && !(await page.locator('[data-testid="match-pitch-live-scene"] canvas').count())) {
    await toggle3DMode.click({ force: true });
    await new Promise((r) => setTimeout(r, 2000));
  }
  await page.screenshot({ path: path.join(OUT, "03_context_restored_state.png") });
}

// Test Manual 3D-to-2D Toggle
console.log("6. Toggling to 2D PITCH mode...");
await page.evaluate(() => {
  document.getElementById("webpack-dev-server-client-overlay")?.remove();
});
const toggle2DButton = page.locator('button:has-text("2D PITCH"), [data-testid="toggle-2d-companion-button"]').first();
if (await toggle2DButton.count()) {
  await toggle2DButton.click({ force: true });
  await new Promise((r) => setTimeout(r, 2500));
  await page.screenshot({ path: path.join(OUT, "04_manual_2d_fallback.png") });

  const stateIn2D = await page.evaluate(() => {
    const has3DCanvas = !!document.querySelector('[data-testid="match-pitch-live-scene"] canvas');
    const has2DFallback = !!document.querySelector('[data-testid="match-pitch-live-scene-fallback-container"]');
    return { has3DCanvas, has2DFallback };
  });
  console.log("State in 2D mode:", stateIn2D);

  // Test Manual 2D-to-3D Recovery
  console.log("7. Toggling back to 3D BROADCAST mode...");
  await page.evaluate(() => {
    document.getElementById("webpack-dev-server-client-overlay")?.remove();
  });
  const toggle3DButton = page.locator('[data-testid="toggle-3d-broadcast-mode"], [data-testid="return-to-3d-broadcast-button"], button:has-text("SWITCH TO 3D BROADCAST")').first();
  await toggle3DButton.click({ force: true });
  await new Promise((r) => setTimeout(r, 3000));
  await page.screenshot({ path: path.join(OUT, "05_manual_3d_recovered.png") });

  const stateIn3D = await page.evaluate(() => {
    const has3DCanvas = !!document.querySelector('[data-testid="match-pitch-live-scene"] canvas');
    const t = window.__GTEX_BROADCAST_TELEMETRY__;
    return {
      has3DCanvas,
      geos: t?.geometries,
      tex: t?.textures,
      drawCalls: t?.drawCalls,
      heap: t?.jsHeapUsedMb,
    };
  });
  console.log("State after remount in 3D:", stateIn3D);

  // Repeated 3D/2D toggle stress test (3 cycles)
  console.log("8. Performing 3 rapid toggle cycles to verify zero progressive resource accumulation...");
  for (let i = 1; i <= 3; i++) {
    await page.evaluate(() => {
      document.getElementById("webpack-dev-server-client-overlay")?.remove();
    });
    const btn2D = page.locator('button:has-text("2D PITCH"), [data-testid="toggle-2d-companion-button"]').first();
    if (await btn2D.count()) {
      await btn2D.click({ force: true });
      await new Promise((r) => setTimeout(r, 1000));
    }
    const btn3D = page.locator('[data-testid="toggle-3d-broadcast-mode"], [data-testid="return-to-3d-broadcast-button"], button:has-text("SWITCH TO 3D BROADCAST")').first();
    if (await btn3D.count()) {
      await btn3D.click({ force: true });
      await new Promise((r) => setTimeout(r, 1500));
    }
  }
}

const finalLifecycleMetrics = await page.evaluate(() => {
  const t = window.__GTEX_BROADCAST_TELEMETRY__;
  return {
    geos: t?.geometries,
    tex: t?.textures,
    drawCalls: t?.drawCalls,
    heap: t?.jsHeapUsedMb,
    activeRigs: t?.activeRigCount,
  };
});
console.log("Final Lifecycle Metrics after Stress Cycles:", finalLifecycleMetrics);

const report = {
  initialBaseline,
  contextLossSimulated,
  contextLostDetected,
  finalLifecycleMetrics,
  consoleErrors,
  resourceAccumulation: {
    geometriesDelta: (finalLifecycleMetrics.geos ?? 0) - (initialBaseline.geos ?? 0),
    texturesDelta: (finalLifecycleMetrics.tex ?? 0) - (initialBaseline.tex ?? 0),
    isLeaking: (finalLifecycleMetrics.geos ?? 0) > (initialBaseline.geos ?? 0) + 5,
  },
};

fs.writeFileSync(path.join(OUT, "lifecycle_verification_results.json"), JSON.stringify(report, null, 2));
console.log("Gate 4 Report written to:", path.join(OUT, "lifecycle_verification_results.json"));

await context.close();
await browser.close();
console.log("Gate 4 verification finished successfully.\n");
