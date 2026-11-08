/**
 * GTEX Matchday 3D — continuous 300-second browser acceptance run (1920x1080).
 *
 * Drives the real React/WebGL MatchCenter route in one continuous browser session,
 * logs in through the real login UI against a locally running GTEX API with a
 * documented seeded account, and records video, screenshots and measured telemetry.
 *
 * Match data: the `u2a-006-showcase` demonstration fixture (flagged DEMONSTRATION FIXTURE
 * in the HUD). No backend-authoritative live match is used in this run.
 *
 * Usage (from qa/playwright):
 *   $env:GTEX_ACC_BASE_URL='http://127.0.0.1:3100'
 *   $env:GTEX_E2E_EMAIL='seed.fan@gte.local'; $env:GTEX_E2E_PASSWORD='DemoPass123'
 *   node matchday_3d_acceptance.mjs [outDir] [durationSec]
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.GTEX_ACC_BASE_URL ?? "http://127.0.0.1:3100";
const EMAIL = process.env.GTEX_E2E_EMAIL ?? "seed.fan@gte.local";
const PASSWORD = process.env.GTEX_E2E_PASSWORD ?? "DemoPass123"; // pragma: allowlist secret
const OUT = path.resolve(process.argv[2] ?? "matchday-acceptance-out");
const DURATION = Number(process.argv[3] ?? 300);
fs.mkdirSync(OUT, { recursive: true });

const log = [];
const note = (m) => {
  const line = `[${new Date().toISOString()}] ${m}`;
  console.log(line);
  log.push(line);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  headless: true,
  args: [
    "--ignore-gpu-blocklist",
    "--enable-webgl",
    "--use-angle=default",
    "--enable-unsafe-swiftshader",
  ],
});
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: path.join(OUT, "video"), size: { width: 1920, height: 1080 } },
});
const page = await context.newPage();
const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];
page.on("console", (m) => {
  if (m.type() === "error") consoleErrors.push(m.text().slice(0, 300));
});
page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 300)));
page.on("requestfailed", (r) =>
  failedRequests.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`),
);
const apiHits = [];
page.on("response", (r) => {
  const u = r.url();
  if (/\/api\/(public\/ads|sponsorship|matches\/)/.test(u))
    apiHits.push(`${r.status()} ${r.request().method()} ${u}`);
});

// --- real login through the UI ---
await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
await page
  .locator('input[type="email"], input[name="email"], input[type="text"]')
  .first()
  .fill(EMAIL);
await page.locator('input[type="password"]').first().fill(PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/\/app|\/onboarding/, { timeout: 60000 });
note(`login ok -> ${page.url()}`);

await page.goto(
  `${BASE}/app/match/u2a-006-showcase?live=1&dismissWalkout=1&duration=${DURATION}&speed=1&tier=high`,
  {
    waitUntil: "domcontentloaded",
  },
);
await page.waitForSelector('[data-testid="match-pitch-live-scene"] canvas', { timeout: 90000 });
await page.waitForFunction(
  () =>
    window.__GTEX_BROADCAST_TELEMETRY__ && window.__GTEX_BROADCAST_TELEMETRY__.activeRigCount >= 22,
  null,
  { timeout: 90000 },
);
note("3D scene up, 22 rigs active");

// in-page independent frame recorder (rAF deltas) + telemetry sampler
await page.evaluate(() => {
  window.__ACC__ = { deltas: [], samples: [], last: performance.now(), stalls: [], ctxLost: 0 };
  const loop = (t) => {
    const d = t - window.__ACC__.last;
    window.__ACC__.last = t;
    window.__ACC__.deltas.push(d);
    if (d > 100) window.__ACC__.stalls.push({ at: Math.round(t), ms: Math.round(d) });
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  document
    .querySelector("canvas")
    ?.addEventListener("webglcontextlost", () => window.__ACC__.ctxLost++);
  setInterval(() => {
    const t = window.__GTEX_BROADCAST_TELEMETRY__;
    if (!t) return;
    window.__ACC__.samples.push({
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
      cam: t.cameraPreset,
      rigs: t.activeRigCount,
      rot: t.adRotationCount,
      imp: t.adImpressionCount,
      crowd: t.crowdReaction?.type,
      ads: (t.activeAdCampaigns || []).map((c) => c.brandName + "/" + c.source),
    });
  }, 1000);
});

const env = await page.evaluate(() => {
  const t = window.__GTEX_BROADCAST_TELEMETRY__;
  const c = document.createElement("canvas");
  const gl2 = !!c.getContext("webgl2");
  return {
    ua: navigator.userAgent,
    gpuVendor: t.gpuVendor,
    gpuRenderer: t.gpuRenderer,
    webgl2: gl2,
    dpr: devicePixelRatio,
    vw: innerWidth,
    vh: innerHeight,
    canvas: [t.canvasWidth, t.canvasHeight],
    tier: t.qualityTier,
  };
});
env.browserVersion = browser.version();
note("env " + JSON.stringify(env));
fs.writeFileSync(path.join(OUT, "environment.json"), JSON.stringify(env, null, 2));

const shots = [];
const shot = async (name, desc) => {
  const file = `${String(shots.length + 1).padStart(2, "0")}_${name}.png`;
  await page.screenshot({ path: path.join(OUT, file) });
  const st = await page.evaluate(() => {
    const t = window.__GTEX_BROADCAST_TELEMETRY__ || {};
    return {
      matchTime: t.currentTime,
      clock: t.clockLabel,
      score: t.score,
      cam: t.cameraPreset,
      fps: t.avgFps,
    };
  });
  shots.push({ file, desc, ...st });
  note(`screenshot ${file}: ${desc} ${JSON.stringify(st)}`);
};
const matchTime = () => page.evaluate(() => window.__GTEX_BROADCAST_TELEMETRY__?.currentTime ?? -1);
const waitMatchTime = async (sec) => {
  const deadline = Date.now() + 120000;
  while ((await matchTime()) < sec && Date.now() < deadline) await sleep(250);
};
const events = [];
const ev = (m) => {
  events.push({ wall: new Date().toISOString(), m });
  note(m);
};

const t0 = Date.now();
await shot("initial_broadcast_view", "Initial broadcast view");
await waitMatchTime(15);
await shot("early_live_gameplay", "Early live gameplay");

await waitMatchTime(30);
await page.locator('[data-testid="camera-mode-tactical_high"]').click();
ev("camera -> tactical_high");
await sleep(2500);
await shot("tactical_wide_camera", "First camera transition: tactical_high wide view");
await page.locator('[data-testid="camera-mode-broadcast_main"]').click();
ev("camera -> broadcast_main");

await waitMatchTime(45);
await sleep(1500);
await shot("stadium_led_ads_full", "Stadium advertising, broadcast camera");
const adShot = `${String(shots.length + 1).padStart(2, "0")}_stadium_led_ads_closeup.png`;
await page.screenshot({
  path: path.join(OUT, adShot),
  clip: { x: 0, y: 540, width: 1920, height: 540 },
});
shots.push({
  file: adShot,
  desc: "Stadium LED advertising close inspection (lower half crop of the same live frame)",
});
note("screenshot ad closeup crop");
const adsBefore = await page.evaluate(() =>
  window.__GTEX_BROADCAST_CONTROL__.getAdvertisingSummary(),
);
fs.writeFileSync(path.join(OUT, "ads_summary_t45.json"), JSON.stringify(adsBefore, null, 2));

// campaign change during the match (HARNESS TEST DATA, not a real booking)
await waitMatchTime(100);
const nowMs = Date.now();
await page.evaluate((now) => {
  window.__GTEX_BROADCAST_CONTROL__.setStadiumCampaigns([
    {
      id: "harness-valid",
      brandName: "HARNESS PARTNER A",
      headline: "TEST CAMPAIGN ACTIVE",
      source: "club_sponsor",
      priority: 500,
      isApproved: true,
      isActive: true,
      status: "active",
      startAt: now - 3600e3,
      endAt: now + 3600e3,
      primaryColor: "#0b3d91",
      accentColor: "#ffd166",
      textColor: "#ffffff",
    },
    {
      id: "harness-expired",
      brandName: "HARNESS EXPIRED",
      headline: "SHOULD NEVER SHOW",
      source: "club_sponsor",
      priority: 900,
      isApproved: true,
      isActive: true,
      status: "active",
      startAt: now - 7200e3,
      endAt: now - 3600e3,
    },
    {
      id: "harness-paused",
      brandName: "HARNESS PAUSED",
      headline: "SHOULD NEVER SHOW",
      source: "club_sponsor",
      priority: 900,
      isApproved: true,
      isActive: false,
      status: "paused",
    },
  ]);
}, nowMs);
ev("harness campaign set injected at ~100s (valid + expired + paused)");
await sleep(12000);
const adsAfter = await page.evaluate(() =>
  window.__GTEX_BROADCAST_CONTROL__.getAdvertisingSummary(),
);
fs.writeFileSync(
  path.join(OUT, "ads_summary_t112_harness.json"),
  JSON.stringify(adsAfter, null, 2),
);
await shot(
  "ads_campaign_change",
  "Stadium LED after in-match campaign change (harness test campaign; expired/paused excluded)",
);
await page.evaluate(() => window.__GTEX_BROADCAST_CONTROL__.setStadiumCampaigns([]));
ev("harness campaigns cleared -> expect house fallback");
await sleep(11000);
const adsCleared = await page.evaluate(() =>
  window.__GTEX_BROADCAST_CONTROL__.getAdvertisingSummary(),
);
fs.writeFileSync(path.join(OUT, "ads_summary_cleared.json"), JSON.stringify(adsCleared, null, 2));

await waitMatchTime(150);
await shot("midpoint_gameplay", "Midpoint gameplay");

let crowdShot = false;
const crowdDeadline = Date.now() + 60000;
while (Date.now() < crowdDeadline && !crowdShot) {
  const c = await page.evaluate(() => window.__GTEX_BROADCAST_TELEMETRY__?.crowdReaction);
  if (c && c.type && c.type !== "idle" && c.type !== "none" && c.type !== "neutral") {
    await shot("crowd_reaction_event", `Crowd reaction '${c.type}' (intensity ${c.intensity})`);
    crowdShot = true;
  }
  await sleep(500);
}
if (!crowdShot)
  await shot(
    "crowd_no_reaction_observed",
    "No crowd reaction observed in window (reported as such)",
  );

// Replay with live-timeline verification
await waitMatchTime(190);
const liveBefore = await matchTime();
const wallBefore = Date.now();
const impBefore = await page.evaluate(() => window.__GTEX_BROADCAST_TELEMETRY__.adImpressionCount);
await page.locator('[data-testid="trigger-replay-button"]').click();
ev(`replay opened; live matchTime before=${liveBefore.toFixed(2)}`);
await sleep(3000);
await shot(
  "replay_inspection",
  "Replay inspection (replay cursor), live timeline continues underneath",
);
const replayBadge = await page.locator('[data-testid="broadcast-replay-badge"]').count();
await sleep(5000);
const liveDuring = await matchTime();
await page
  .locator('[data-testid="trigger-replay-button"]')
  .click()
  .catch(() => undefined);
await sleep(1500);
const liveAfter = await matchTime();
const replayResult = {
  liveBefore,
  liveDuring,
  liveAfter,
  wallElapsedSec: (Date.now() - wallBefore) / 1000,
  liveAdvancedDuringReplaySec: liveDuring - liveBefore,
  replayBadgeShown: replayBadge > 0,
  impressionsBeforeReplay: impBefore,
  impressionsAfterReplay: await page.evaluate(
    () => window.__GTEX_BROADCAST_TELEMETRY__.adImpressionCount,
  ),
  fallbackNoticeVisible: (await page.locator('[data-testid="replay-fallback-notice"]').count()) > 0,
};
fs.writeFileSync(path.join(OUT, "replay_result.json"), JSON.stringify(replayResult, null, 2));
note("replay " + JSON.stringify(replayResult));

await waitMatchTime(240);
await shot("later_gameplay", "Later match gameplay");
await page.locator('[data-testid="camera-mode-closeup_action"]').click();
await sleep(2500);
await shot("closeup_players_kits", "Close inspection of players and kits");
await page.locator('[data-testid="camera-mode-director_auto"]').click();

await waitMatchTime(285);
await shot("final_checkpoint", "Final gameplay checkpoint");
await waitMatchTime(DURATION - 1);
await sleep(1500);
await shot("end_of_run", "End of the 300-second run");

const wallTotal = (Date.now() - t0) / 1000;
const result = await page.evaluate(() => {
  const d = window.__ACC__.deltas.slice(2);
  const s = d.slice().sort((a, b) => a - b);
  const q = (p) => s[Math.min(s.length - 1, Math.floor(s.length * p))];
  const avg = d.reduce((a, b) => a + b, 0) / d.length;
  let worstFps = Infinity,
    acc = 0;
  const win = [];
  for (const x of d) {
    win.push(x);
    acc += x;
    while (acc > 5000) acc -= win.shift();
    if (acc >= 4900) worstFps = Math.min(worstFps, win.length / (acc / 1000));
  }
  return {
    frames: d.length,
    avgFps: 1000 / avg,
    p50: q(0.5),
    p95: q(0.95),
    p99: q(0.99),
    max: s[s.length - 1],
    worstSustained5sFps: worstFps,
    stalls100ms: window.__ACC__.stalls.length,
    stallList: window.__ACC__.stalls.slice(0, 30),
    contextLost: window.__ACC__.ctxLost,
    samples: window.__ACC__.samples,
  };
});
const hs = result.samples.map((x) => x.heap).filter((x) => x != null);
const S = result.samples;
const summary = {
  wallTotalSec: wallTotal,
  frameStats: { ...result, samples: undefined },
  heapFirstMb: hs[0],
  heapLastMb: hs[hs.length - 1],
  heapMaxMb: hs.length ? Math.max(...hs) : null,
  qualityTiersSeen: [...new Set(S.map((x) => x.tier))],
  camerasSeen: [...new Set(S.map((x) => x.cam))],
  rigsMin: Math.min(...S.map((x) => x.rigs)),
  rigsMax: Math.max(...S.map((x) => x.rigs)),
  matchTimeFirst: S[0]?.currentTime,
  matchTimeLast: S.at(-1)?.currentTime,
  clockLabels: [...new Set(S.map((x) => x.clock))],
  scoreFinal: S.at(-1)?.score,
  adRotationFinal: S.at(-1)?.rot,
  adImpressionsFinal: S.at(-1)?.imp,
  crowdTypesSeen: [...new Set(S.map((x) => x.crowd))],
  adBrandsSeen: [...new Set(S.flatMap((x) => x.ads))],
  drawCallsRange: [Math.min(...S.map((x) => x.drawCalls)), Math.max(...S.map((x) => x.drawCalls))],
  geometriesFirstLast: [S[0]?.geos, S.at(-1)?.geos],
  texturesFirstLast: [S[0]?.tex, S.at(-1)?.tex],
  consoleErrors: consoleErrors.slice(0, 40),
  pageErrors,
  failedRequests: failedRequests.slice(0, 40),
  apiHits: [...new Set(apiHits)].slice(0, 40),
  shots,
  events,
};
fs.writeFileSync(path.join(OUT, "telemetry_samples.json"), JSON.stringify(S));
fs.writeFileSync(path.join(OUT, "acceptance_summary.json"), JSON.stringify(summary, null, 2));
fs.writeFileSync(path.join(OUT, "run.log"), log.join("\n"));
const videoPath = await page.video()?.path();
await context.close();
await browser.close();
note(`done. video=${videoPath}`);
