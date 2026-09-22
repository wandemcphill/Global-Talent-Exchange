import { expect, test } from "@playwright/test";
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

test("authenticated shell loads home command center with real data and no overflow", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/home");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "authed-shell-home");
});

test("canonical app route loads successfully", async ({ page }, testInfo) => {
  await visitAuthedRoute(page, "/app");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "authed-shell-app");
});
