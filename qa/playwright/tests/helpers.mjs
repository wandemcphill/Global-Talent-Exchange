import { expect } from "@playwright/test";

export const configured = Boolean(
  process.env.GTEX_E2E_BASE_URL || process.env.GTEX_E2E_API_BASE_URL,
);

export const credentialsConfigured = Boolean(
  process.env.GTEX_E2E_EMAIL && process.env.GTEX_E2E_PASSWORD,
);

const diagnosticsByTest = new Map();
const signedInPages = new WeakSet();

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
  try {
    await page.evaluate(() => {
      const element = document.querySelector('[aria-label="Enable accessibility"]');
      if (element) {
        element.focus?.();
        element.click?.();
        element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      }
    });
    await page.waitForTimeout(300);
  } catch {
    // Accessibility button may already have been consumed or not present
  }
}

export async function signIn(page) {
  if (!credentialsConfigured) return;

  const currentUrl = page.url();
  if (signedInPages.has(page)) return;

  const profileButton = page.getByRole("button", {
    name: /Profile and settings/i,
  });
  const isHashRouting = Boolean(process.env.GTEX_E2E_HASH_ROUTING);
  const looksLikeAppRoute = isHashRouting
    ? currentUrl.includes("#/app/")
    : new URL(currentUrl || "http://localhost").pathname.startsWith("/app/");
  if (looksLikeAppRoute && (await profileButton.isVisible().catch(() => false))) {
    signedInPages.add(page);
    return;
  }

  const loginUrl = isHashRouting ? "/#/auth/login" : "/auth/login";
  await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

  const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
  await expect(surface).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(1500);

  await enableAccessibility(page);

  const emailInput = page
    .locator('input[aria-label="Email"]')
    .or(page.locator('input[type="email"]'))
    .or(page.locator('input[autocomplete="username"]'))
    .first();
  const passwordInput = page
    .locator('input[aria-label="Password"]')
    .or(page.locator('input[type="password"]'))
    .or(page.locator('input[autocomplete="current-password"]'))
    .first();
  const semanticEmail = page.getByRole("textbox", { name: /^Email$/i }).first();
  const semanticPassword = page
    .getByRole("textbox", { name: /^Password$/i })
    .first();
  const enterBtn = page.getByRole("button", { name: /^ENTER GTEX$/i });

  const isVisible = async (locator) => locator.isVisible().catch(() => false);
  const enterFieldValue = async (locator, value) => {
    try {
      await locator.fill(value, { timeout: 1_500 });
      return true;
    } catch {
      if (!(await isVisible(locator))) return false;
      await locator.click({ timeout: 1_500 });
      await page.keyboard.press("Control+A").catch(() => {});
      await page.keyboard.type(value);
      return true;
    }
  };

  if (await isVisible(emailInput) && await isVisible(passwordInput)) {
    await emailInput.fill(process.env.GTEX_E2E_EMAIL);
    await passwordInput.fill(process.env.GTEX_E2E_PASSWORD);
    await expect(enterBtn).toBeVisible({ timeout: 30_000 });
    await enterBtn.click({ force: true });
  } else if (
    await isVisible(semanticEmail) &&
    await isVisible(semanticPassword)
  ) {
    await enterFieldValue(semanticEmail, process.env.GTEX_E2E_EMAIL);
    await enterFieldValue(semanticPassword, process.env.GTEX_E2E_PASSWORD);
    if (await isVisible(enterBtn)) {
      await enterBtn.click({ force: true });
    } else {
      await page.keyboard.press("Enter");
    }
  } else {
    // A valid persisted session may redirect away from the login form. Detect
    // the authenticated shell before attempting coordinate-based form entry.
    if (await profileButton.isVisible().catch(() => false)) {
      signedInPages.add(page);
      return;
    }

    // Flutter web can expose text fields only through its semantics layer.
    // Keep this as a last resort, using the current login card's field/button
    // positions rather than the obsolete coordinates from the previous shell.
    const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
    const isNarrow = viewport.width < 820;
    const x = isNarrow
      ? Math.round(viewport.width * 0.5)
      : Math.round(viewport.width * 0.72);
    const emailY = isNarrow ? 230 : 410;
    await page.mouse.click(x, emailY);
    await page.waitForTimeout(200);
    await page.keyboard.press("Control+A").catch(() => {});
    await page.keyboard.type(process.env.GTEX_E2E_EMAIL);
    await page.keyboard.press("Tab");
    await page.waitForTimeout(150);
    await page.keyboard.type(process.env.GTEX_E2E_PASSWORD);
    await page.keyboard.press("Enter");
    await page.waitForTimeout(800);
    const atAuthenticatedRoute = isHashRouting
      ? /#\/app(?:\/|$)/.test(page.url())
      : /\/app\//.test(new URL(page.url()).pathname);
    if (!atAuthenticatedRoute) {
      const enterY = isNarrow ? 370 : 555;
      await page.mouse.click(x, enterY);
    }
  }

  const authenticatedRoute = isHashRouting ? /#\/app(?:\/|$)/ : /\/app\//;
  await expect(page).toHaveURL(authenticatedRoute, { timeout: 30_000 });
  await expect(profileButton).toBeVisible({ timeout: 30_000 });
  signedInPages.add(page);
  await page.waitForTimeout(1500);
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
  } catch {
    // Current URL may not be valid or parseable; fall through to navigate.
  }

  if (!isAlreadyAtRoute) {
    await page.goto(targetRoute, { waitUntil: "domcontentloaded", timeout: 120_000 });
    const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
    await expect(surface).toBeVisible({ timeout: 120_000 });
    await enableAccessibility(page);
    await page.waitForTimeout(1200);
  } else {
    await enableAccessibility(page);
    await page.waitForTimeout(400);
  }
}

export async function captureScreenshot(page, testInfo, name) {
  const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
  await expect(surface).toBeVisible({ timeout: 120_000 });
  await page.waitForTimeout(800);
  await page.screenshot({
    path: testInfo.outputPath(`${name}-${testInfo.project.name}.png`),
    animations: "disabled",
  });
}

export async function verifyNoHorizontalOverflow(page) {
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), {
      timeout: 30_000,
    })
    .toBeTruthy();
}
