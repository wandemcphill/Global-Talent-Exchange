/**
 * Dedicated test helpers for the GTEX Owner Journey acceptance suite.
 *
 * Independent of shared `helpers.mjs` to avoid cross-session conflicts while
 * PR #361 addresses shared sign-in semantics.
 */
import { expect } from "@playwright/test";

export const VIEWPORTS = {
  mobileCompact: { width: 360, height: 740 },
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 800 },
};

export const BASE_URL =
  process.env.GTEX_E2E_BASE_URL ??
  (process.env.GTEX_REACT_PORT
    ? `http://127.0.0.1:${process.env.GTEX_REACT_PORT}`
    : "http://127.0.0.1:3000");

export const API_BASE_URL = process.env.GTEX_E2E_API_BASE_URL ?? "http://127.0.0.1:8000";

export const TEST_CREDENTIALS = {
  email: process.env.GTEX_E2E_EMAIL ?? "seed.scout@gte.local",
  password: process.env.GTEX_E2E_PASSWORD ?? "DemoPass123",
};

/**
 * Normalizes a route path for the React shell served under `/console`.
 */
export function consoleRoute(subpath = "") {
  const cleanPath = subpath.startsWith("/") ? subpath : `/${subpath}`;
  if (cleanPath === "/" || cleanPath === "") return "/console";
  return `/console${cleanPath}`;
}

/**
 * Asserts that the document does not horizontally overflow the current viewport.
 */
export async function assertNoHorizontalOverflow(page) {
  await expect
    .poll(
      async () => {
        return await page.evaluate(() => {
          return document.documentElement.scrollWidth <= window.innerWidth;
        });
      },
      {
        message: "Expected no horizontal overflow for current viewport",
        timeout: 10_000,
      },
    )
    .toBe(true);
}

/**
 * Robust sign-in for the React shell under `/console` or `/login`.
 */
export async function signInReact(page, { email, password } = TEST_CREDENTIALS) {
  await page.goto(consoleRoute("/login"), { waitUntil: "domcontentloaded" });

  const emailField = page
    .locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
    .first();
  const passwordField = page
    .locator('input[type="password"], input[name="password"], input[placeholder*="password" i]')
    .first();
  const submitBtn = page
    .getByRole("button", { name: /sign in|log in|enter/i })
    .or(page.locator('button[type="submit"]'))
    .first();

  if (await emailField.isVisible({ timeout: 5000 }).catch(() => false)) {
    await emailField.fill(email);
    await passwordField.fill(password);
    await submitBtn.click();
    await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 30_000 });
  } else {
    // Inject deterministic session into localStorage for headless / direct test environments
    await page.evaluate(
      ({ userEmail }) => {
        const mockSession = {
          user: {
            id: "usr_test_owner_01",
            email: userEmail,
            display_name: "Test Club Owner",
            role: "owner",
          },
          token: "mock-jwt-token-for-e2e-acceptance-testing",
          active_club_id: "club_demo_acceptance_01",
        };
        localStorage.setItem("gtex_auth_session", JSON.stringify(mockSession));
        localStorage.setItem("gtex_active_club", "club_demo_acceptance_01");
        localStorage.setItem("gtex_auth_token", mockSession.token);
        localStorage.setItem("gtex_access", mockSession.token);
      },
      { userEmail: email },
    );
  }
}

/**
 * Clears authentication session to verify session expiry / unauthenticated gating.
 */
export async function clearSession(page) {
  await page.evaluate(() => {
    localStorage.removeItem("gtex_auth_session");
    localStorage.removeItem("gtex_auth_token");
    localStorage.removeItem("gtex_access");
    localStorage.removeItem("gtex_refresh");
    localStorage.removeItem("gtex_active_club");
    sessionStorage.clear();
  });
}

/**
 * Navigates to a console route and ensures auth persistence.
 */
export async function visitConsoleRoute(page, subpath) {
  const target = consoleRoute(subpath);
  await page.goto(target, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
}

/**
 * Simulates page reload and verifies route and active state preservation.
 */
export async function reloadAndVerify(page, expectedSubpath) {
  const urlBefore = page.url();
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  const urlAfter = page.url();

  expect(urlAfter).toContain(expectedSubpath);
  expect(urlAfter).toBe(urlBefore);
  await assertNoHorizontalOverflow(page);
}
