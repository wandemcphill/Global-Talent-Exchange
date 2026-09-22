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

test("Audio settings and soundtrack OS shell load without visual or layout errors", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/home");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "audio-soundtrack-shell");
});
