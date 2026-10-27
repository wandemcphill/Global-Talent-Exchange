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

test.afterEach(async ({ page: _page }, testInfo) => {
  await attachDiagnostics(testInfo);
});

test("P9-SHELL / P7-FEV: Core authenticated shell routes render with GTEX Navy theme and zero horizontal overflow", async ({
  page,
}, testInfo) => {
  test.setTimeout(240_000);

  const routes = [
    ["/app/home", "p9-shell-home"],
    ["/app/club", "p9-shell-club"],
    ["/app/market", "p9-shell-market"],
    ["/app/wallet", "p9-shell-wallet"],
    ["/matches", "p9-shell-matchday"],
    ["/world", "p9-shell-world"],
  ];

  for (const [route, screenshotName] of routes) {
    await visitAuthedRoute(page, route);
    await verifyNoHorizontalOverflow(page);
    await captureScreenshot(page, testInfo, screenshotName);
  }
});
