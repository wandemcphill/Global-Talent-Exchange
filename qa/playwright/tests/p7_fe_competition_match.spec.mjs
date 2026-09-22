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

test("Competitions surface renders family selectors, discovery, and fixtures", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/competitions");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "competitions-discovery");
});

test("Matches surface renders live/upcoming fixtures or truthful unavailable state", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/matches");
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "matches-fixtures");
});

test("Match Viewer settles to an authoritative view or truthful unavailable state", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/matches/viewer/not-available");
  await expect(
    page.getByText(/No match available|Match viewer unavailable|2D Match Viewer/).first(),
  ).toBeVisible({ timeout: 20_000 });
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "match-viewer-authoritative");
});
