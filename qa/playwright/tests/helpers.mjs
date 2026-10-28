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
    // Do not toggle accessibility if semantics nodes or labelled inputs are already exposed.
    const hasSemantics = await page
      .evaluate(() => {
        const nodes = document.querySelectorAll(
          'flt-semantics[role], input[aria-label], [role="button"]:not([aria-label="Enable accessibility"])',
        );
        return nodes.length > 0;
      })
      .catch(() => false);
    if (hasSemantics) return;

    // Flutter's accessibility toggle is a 1x1 off-screen placeholder and is stateful.
    // Invoke a single native DOM click without dispatching a second synthetic MouseEvent.
    await page.evaluate(() => {
      const element = document.querySelector('[aria-label="Enable accessibility"]');
      if (element) {
        element.focus?.();
        element.click?.();
      }
    });
    await page.waitForTimeout(300);
  } catch {
    // Accessibility may already be enabled or the toggle may not be present.
  }
}

async function fillFlutterTextField(page, locator, value) {
  await locator.click({ force: true });
  // Wait for Flutter Web's SemanticsTextField to round-trip focus to Dart and attach
  // the active TextInputClient before setting the DOM input value.
  await page.waitForTimeout(300);
  await locator.fill(value);
  await page.waitForTimeout(200);
  const currentValue = await locator.inputValue().catch(() => "");
  if (currentValue !== value) {
    await locator.click({ force: true });
    await page.waitForTimeout(250);
    await page.keyboard.press("Control+A").catch(() => {});
    await page.keyboard.type(value, { delay: 15 });
    await page.waitForTimeout(200);
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
  await page.waitForTimeout(1000);

  const emailInput = page
    .locator(
      'input[aria-label="Email"], input[aria-label*="email" i], input[type="email"], input[autocomplete="username"], input[placeholder*="email" i]',
    )
    .first();
  const passwordInput = page
    .locator(
      'input[aria-label="Password"], input[aria-label*="password" i], input[type="password"], input[autocomplete="current-password"], input[placeholder*="password" i]',
    )
    .first();
  const enterBtn = page.getByRole("button", { name: /ENTER GTEX/i });

  const waitDeadline = Date.now() + 45_000;
  while (Date.now() < waitDeadline) {
    await enableAccessibility(page);
    if (await emailInput.isVisible().catch(() => false)) break;
    if (await profileButton.isVisible().catch(() => false)) {
      signedInPages.add(page);
      return;
    }
    await page.waitForTimeout(400);
  }

  if (await emailInput.isVisible().catch(() => false)) {
    await fillFlutterTextField(page, emailInput, process.env.GTEX_E2E_EMAIL);
    await expect(passwordInput).toBeVisible({ timeout: 30_000 });
    await fillFlutterTextField(page, passwordInput, process.env.GTEX_E2E_PASSWORD);
    await expect(enterBtn).toBeVisible({ timeout: 30_000 });
    await enterBtn.click({ force: true });
  } else {
    if (await profileButton.isVisible().catch(() => false)) {
      signedInPages.add(page);
      return;
    }
    const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
    const isNarrow = viewport.width < 820;
    const x = isNarrow ? Math.round(viewport.width * 0.5) : Math.round(viewport.width * 0.72);
    const emailY = 250;
    await page.mouse.click(x, emailY);
    await page.waitForTimeout(250);
    await page.keyboard.press("Control+A").catch(() => {});
    await page.keyboard.type(process.env.GTEX_E2E_EMAIL, { delay: 15 });
    await page.keyboard.press("Tab");
    await page.waitForTimeout(250);
    await page.keyboard.type(process.env.GTEX_E2E_PASSWORD, { delay: 15 });
    await page.keyboard.press("Enter");
    await page.waitForTimeout(800);
    if (!page.url().includes("/app/")) {
      const enterY = 365;
      await page.mouse.click(x, enterY);
    }
  }

  const authenticatedRoute = isHashRouting ? /#\/app(?:\/|$)/ : /\/app\//;
  const authDeadline = Date.now() + 45_000;
  let retryCount = 0;
  let lastSubmitAt = Date.now();
  while (Date.now() < authDeadline) {
    if (authenticatedRoute.test(page.url())) break;
    await enableAccessibility(page);
    const missingEmail = await page
      .getByText("Enter your email address.", { exact: true })
      .isVisible()
      .catch(() => false);
    const missingPassword = await page
      .getByText("Enter your password.", { exact: true })
      .isVisible()
      .catch(() => false);
    const backendError = await page
      .getByText(/Unable to reach the backend|Request failed|timed out/i)
      .first()
      .isVisible()
      .catch(() => false);
    const stalledOnLogin = Date.now() - lastSubmitAt > 8_000;
    if ((missingEmail || missingPassword || backendError || stalledOnLogin) && retryCount < 3) {
      retryCount += 1;
      await page.waitForTimeout(800);
      if (missingEmail || missingPassword || stalledOnLogin) {
        if (await emailInput.isVisible().catch(() => false)) {
          await fillFlutterTextField(page, emailInput, process.env.GTEX_E2E_EMAIL);
        }
        if (await passwordInput.isVisible().catch(() => false)) {
          await fillFlutterTextField(page, passwordInput, process.env.GTEX_E2E_PASSWORD);
        }
      }
      if (await enterBtn.isVisible().catch(() => false)) {
        await enterBtn.click({ force: true });
      }
      lastSubmitAt = Date.now();
    }
    await page.waitForTimeout(400);
  }

  await expect(page).toHaveURL(authenticatedRoute, { timeout: 15_000 });
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
    await enableAccessibility(page);
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
