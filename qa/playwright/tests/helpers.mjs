import { expect } from "@playwright/test";

export const configured = Boolean(process.env.GTEX_E2E_BASE_URL);

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

  const loginUrl = process.env.GTEX_E2E_HASH_ROUTING ? "/#/auth/login" : "/auth/login";
  await page.goto(loginUrl);
  await page.locator("flt-glass-pane, flutter-view, canvas").first().waitFor({ timeout: 15_000 });
  await page.waitForTimeout(1000);

  const viewport = page.viewportSize();
  if (viewport && viewport.width < 780) {
    await page.locator("flutter-view, flt-glass-pane").first().click({ force: true });
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press("PageDown");
      await page.waitForTimeout(50);
    }
  }

  await page.evaluate(() => {
    document.querySelector("flt-semantics-placeholder")?.click();
  });
  await page.waitForTimeout(500);

  const emailInput = page.locator("input").first();
  await expect(emailInput).toBeVisible({ timeout: 15_000 });
  await emailInput.focus();
  await emailInput.fill(process.env.GTEX_E2E_EMAIL);
  await emailInput.dispatchEvent("input");

  const passwordInput = page.locator("input").nth(1);
  await passwordInput.focus();
  await passwordInput.fill(process.env.GTEX_E2E_PASSWORD);
  await passwordInput.dispatchEvent("input");

  const enterBtn = page.getByRole("button", { name: "ENTER GTEX" });
  await enterBtn.click({ force: true });
  await expect
    .poll(() => page.url(), { timeout: 15_000 })
    .not.toContain("/auth/login");
}

export async function visitAuthedRoute(page, route) {
  await signIn(page);
  const targetRoute = process.env.GTEX_E2E_HASH_ROUTING ? `/#${route}` : route;
  await page.goto(targetRoute);
  await page.waitForTimeout(2000);
}

export async function captureScreenshot(page, testInfo, name) {
  const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
  await expect(surface).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({
    path: testInfo.outputPath(`${name}-${testInfo.project.name}.png`),
  });
}

export async function verifyNoHorizontalOverflow(page) {
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
    .toBeTruthy();
}
