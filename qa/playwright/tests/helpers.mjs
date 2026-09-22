import { expect } from "@playwright/test";

export const configured = Boolean(
  process.env.GTEX_E2E_BASE_URL || process.env.GTEX_E2E_API_BASE_URL,
);

export const credentialsConfigured = Boolean(
  process.env.GTEX_E2E_EMAIL && process.env.GTEX_E2E_PASSWORD,
);

const diagnosticsByTest = new Map();

export async function collectBrowserDiagnostics(page, testInfo) {
  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("requestfailed", (request) => {
    failedRequests.push(
      `${request.method()} ${request.url()} (${request.failure()?.errorText ?? "failed"})`,
    );
  });
  diagnosticsByTest.set(testInfo.testId, { consoleErrors, failedRequests });
}

export async function attachDiagnostics(testInfo) {
  const diagnostics = diagnosticsByTest.get(testInfo.testId);
  if (diagnostics) {
    await testInfo.attach("browser-diagnostics.json", {
      body: JSON.stringify(diagnostics, null, 2),
      contentType: "application/json",
    });
  }
}

export async function signIn(page) {
  if (!credentialsConfigured) return;

  const loginUrl = process.env.GTEX_E2E_HASH_ROUTING ? "/#/" : "/";
  await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

  const emailInput = page.locator("input").nth(0);
  await expect(emailInput).toBeVisible({ timeout: 120_000 });
  await emailInput.fill(process.env.GTEX_E2E_EMAIL);

  const passwordInput = page.locator("input").nth(1);
  await expect(passwordInput).toBeVisible({ timeout: 30_000 });
  await passwordInput.fill(process.env.GTEX_E2E_PASSWORD);

  const enterBtn = page.getByRole("button", { name: "ENTER GTEX" });
  await expect(enterBtn).toBeVisible({ timeout: 30_000 });
  await enterBtn.click({ force: true });

  await expect(page).toHaveURL(/\\/(?:#\\/)?app\\/home/, { timeout: 60_000 });
}

export async function visitAuthedRoute(page, route) {
  await signIn(page);
  const targetRoute = process.env.GTEX_E2E_HASH_ROUTING ? `/#${route}` : route;
  await page.goto(targetRoute, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForTimeout(5000);
}

export async function captureScreenshot(page, testInfo, name) {
  const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
  await expect(surface).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({
    path: testInfo.outputPath(`${name}-${testInfo.project.name}.png`),
  });
}

export async function verifyNoHorizontalOverflow(page) {
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), {
      timeout: 30_000,
    })
    .toBeTruthy();
}
