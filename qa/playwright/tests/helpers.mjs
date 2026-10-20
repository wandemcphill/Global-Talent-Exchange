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

export async function enableAccessibility(page) {
  const accessibilityButton = page.locator('[aria-label="Enable accessibility"]').first();
  try {
    if (await accessibilityButton.isVisible({ timeout: 5000 })) {
      for (let attempt = 0; attempt < 10; attempt++) {
        await accessibilityButton.evaluate((element) => element.click()).catch(() => {});
        await page.waitForTimeout(500);
        const buttonVisible = await accessibilityButton.isVisible().catch(() => false);
        if (!buttonVisible) {
          break;
        }
      }
    }
  } catch {
    // Accessibility button may already have been consumed or not present
  }
}

export async function signIn(page) {
  if (!credentialsConfigured) return;

  const currentUrl = page.url();
  if (currentUrl.includes("/app/")) {
    return;
  }

  const loginUrl = process.env.GTEX_E2E_HASH_ROUTING ? "/#/auth/login" : "/auth/login";
  await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

  const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
  await expect(surface).toBeVisible({ timeout: 120_000 });

  const accessibilityButton = page.locator('[aria-label="Enable accessibility"]').first();
  await expect(accessibilityButton).toBeVisible({ timeout: 120_000 });

  const emailInput = page.locator('input[aria-label="Email"]').first();
  for (let attempt = 0; attempt < 12; attempt++) {
    if (await emailInput.isVisible().catch(() => false)) break;
    await accessibilityButton.evaluate((element) => element.click()).catch(() => {});
    await page.waitForTimeout(750);
  }
  await expect(emailInput).toBeVisible({ timeout: 60_000 });
  await emailInput.fill(process.env.GTEX_E2E_EMAIL);

  const passwordInput = page.locator('input[aria-label="Password"]').first();
  await expect(passwordInput).toBeVisible({ timeout: 30_000 });
  await passwordInput.fill(process.env.GTEX_E2E_PASSWORD);

  const enterBtn = page.getByRole("button", { name: "ENTER GTEX" });
  await expect(enterBtn).toBeVisible({ timeout: 30_000 });
  await enterBtn.click({ force: true });

  await expect(page).toHaveURL(/\/(?:#\/)?app\/home/, { timeout: 60_000 });
}

export async function visitAuthedRoute(page, route) {
  await signIn(page);

  const isHashRouting = Boolean(process.env.GTEX_E2E_HASH_ROUTING);
  const targetRoute = isHashRouting ? `/#${route}` : route;

  let isAlreadyAtRoute = false;
  try {
    const currentUrl = page.url();
    const urlObj = new URL(currentUrl);
    if (isHashRouting) {
      isAlreadyAtRoute = urlObj.hash === `#${route}`;
    } else {
      isAlreadyAtRoute =
        urlObj.pathname === route ||
        (route === "/app/home" && urlObj.pathname.includes("/app/home"));
    }
  } catch {}

  if (!isAlreadyAtRoute) {
    await page.goto(targetRoute, { waitUntil: "domcontentloaded", timeout: 120_000 });
    const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
    await expect(surface).toBeVisible({ timeout: 120_000 });
    await enableAccessibility(page);
    await page.waitForTimeout(2000);
  } else {
    await enableAccessibility(page);
    await page.waitForTimeout(500);
  }
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
