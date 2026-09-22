import { test } from "@playwright/test";
import {
  attachDiagnostics,
  captureScreenshot,
  collectBrowserDiagnostics,
  configured,
  credentialsConfigured,
  verifyNoHorizontalOverflow,
  visitAuthedRoute,
} from "./helpers.mjs";

test.beforeEach(async ({ page }, testInfo) => {
  test.skip(
    !configured || !credentialsConfigured,
    "Requires GTEX E2E base URL and auth credentials.",
  );
  await collectBrowserDiagnostics(page, testInfo);
});

test.afterEach(async (_fixtures, testInfo) => {
  await attachDiagnostics(testInfo);
});

test("Market surface renders player market grid and filters", async ({ page }, testInfo) => {
  await visitAuthedRoute(page, "/app/market");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "market-hub");
});

test("Ownership surface renders real holdings, valuation, and consequence cards", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/market?mode=ownership");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "ownership-hub");
});

test("Wallet Holdings surface resolves directly from portfolio aliases", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/portfolio");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "portfolio-holdings");
});
