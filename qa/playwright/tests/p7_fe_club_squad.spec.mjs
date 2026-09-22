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

test("Club HQ surface renders identity, squad, and actions without horizontal overflow", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/club");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "club-hq");
});

test("Player Profile surface renders attributes, radar, and market telemetry", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/players");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "player-profile");
});
