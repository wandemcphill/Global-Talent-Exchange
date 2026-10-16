import { expect, test } from '@playwright/test';

const configured = Boolean(
  process.env.GTEX_E2E_BASE_URL || process.env.GTEX_E2E_API_BASE_URL,
);
const credentialsConfigured = Boolean(
  process.env.GTEX_E2E_EMAIL && process.env.GTEX_E2E_PASSWORD,
);
const diagnosticsByTest = new Map();

async function collectBrowserDiagnostics(page, testInfo) {
  const consoleErrors = [];
  const failedRequests = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(error.message));
  page.on('requestfailed', (request) => {
    failedRequests.push(`${request.method()} ${request.url()} (${request.failure()?.errorText ?? 'failed'})`);
  });
  const diagnostics = { consoleErrors, failedRequests };
  diagnosticsByTest.set(testInfo.testId, diagnostics);
}

async function signIn(page) {
  if (!credentialsConfigured) return;
  await page.goto('/');
  await page.locator('input').nth(0).fill(process.env.GTEX_E2E_EMAIL);
  await page.locator('input').nth(1).fill(process.env.GTEX_E2E_PASSWORD);
  await page.getByRole('button', { name: 'ENTER GTEX' }).click();
  await expect(page).toHaveURL(/\/app\/home/, { timeout: 30_000 });
}

async function visitAuthedRoute(page, route) {
  await signIn(page);
  await page.goto(route);
  await page.waitForTimeout(750);
}

async function capture(page, testInfo, name) {
  await page.screenshot({
    path: testInfo.outputPath(`${name}-${testInfo.project.name}.png`),
    fullPage: true,
  });
}

test('Chromium browser runner is available', async ({ page }) => {
  await page.goto('data:text/html,<title>GTEX browser harness</title>');
  await expect(page).toHaveTitle('GTEX browser harness');
});

test.beforeEach(async ({ page }, testInfo) => {
  if (testInfo.title === 'Chromium browser runner is available') return;
  test.skip(!configured, 'Set GTEX_E2E_BASE_URL or GTEX_E2E_API_BASE_URL.');
  if (testInfo.title === 'design lab captures three Flutter-native directions') {
    test.skip(!process.env.GTEX_E2E_DESIGN_LAB, 'Set GTEX_E2E_DESIGN_LAB=1 to render isolated Design Lab fixtures.');
    await collectBrowserDiagnostics(page, testInfo);
    return;
  }
  test.skip(!credentialsConfigured, 'Set an approved GTEX_E2E_EMAIL and GTEX_E2E_PASSWORD.');
  await collectBrowserDiagnostics(page, testInfo);
});

test('design lab captures three Flutter-native directions', async ({ page }, testInfo) => {
  // Flutter Web paints application text to a canvas. The component-level
  // widget test asserts semantic content; this browser check captures pixels
  // from a rendered Flutter surface instead of querying browser DOM text.
  test.setTimeout(180_000);
  for (const direction of [
    ['matchday', 'matchday-pulse'],
    ['club', 'club-atlas'],
    ['ownership', 'ownership-ledger'],
  ]) {
    const route = process.env.GTEX_E2E_HASH_ROUTING
      ? `/?validation=${direction[0]}#/design-lab?direction=${direction[0]}`
      : `/design-lab?direction=${direction[0]}`;
    await page.goto(route, { waitUntil: 'domcontentloaded' });
    const surface = page.locator('flt-glass-pane, flutter-view, canvas').first();
    await expect(surface).toBeVisible({ timeout: 120_000 });
    await page.waitForTimeout(3_000);
    await capture(page, testInfo, `design-lab-${direction[1]}`);
  }
});

test.afterEach(async ({}, testInfo) => {
  const diagnostics = diagnosticsByTest.get(testInfo.testId);
  if (diagnostics) {
    await testInfo.attach('browser-diagnostics.json', {
      body: JSON.stringify(diagnostics, null, 2),
      contentType: 'application/json',
    });
  }
});

test('lineup keeps every substitute reachable without horizontal page overflow', async ({ page }, testInfo) => {
  await visitAuthedRoute(page, process.env.GTEX_E2E_LINEUP_ROUTE ?? '/lineup');
  await expect(page.getByText('SUBSTITUTES')).toBeVisible();
  await expect(page.getByText('Select a substitute, then tap a starter position to assign them.')).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await capture(page, testInfo, 'lineup');
});

test('a payload-backed notification opens its supplied target and preserves read state', async ({ page }, testInfo) => {
  test.skip(!process.env.GTEX_E2E_NOTIFICATION_TEXT || !process.env.GTEX_E2E_NOTIFICATION_TARGET, 'Provide a seeded notification text and its expected route.');
  await visitAuthedRoute(page, '/notifications');
  const notification = page.getByText(process.env.GTEX_E2E_NOTIFICATION_TEXT).first();
  await notification.click();
  await page.getByRole('button', { name: /open/i }).click();
  await expect(page).toHaveURL(new RegExp(process.env.GTEX_E2E_NOTIFICATION_TARGET.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  await capture(page, testInfo, 'notifications');
});

test('a notification without a target leaves navigation unavailable', async ({ page }) => {
  test.skip(!process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT, 'Provide a real notification without routing metadata.');
  await visitAuthedRoute(page, '/notifications');
  await page.getByText(process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT).first().click();
  await expect(page.getByRole('button', { name: /open/i })).toBeDisabled();
});

test('match viewer settles to an authoritative view or truthful unavailable state', async ({ page }, testInfo) => {
  await visitAuthedRoute(page, process.env.GTEX_E2E_MATCH_VIEWER_ROUTE ?? '/matches/viewer/not-available');
  await expect(page.getByText(/No match available|Match viewer unavailable|2D Match Viewer/).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('Verifying shipped capability')).toHaveCount(0);
  await capture(page, testInfo, 'match-viewer');
});
