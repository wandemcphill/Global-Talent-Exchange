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

test.afterEach(async (_fixtures, testInfo) => {
  await attachDiagnostics(testInfo);
});

test("Lineup keeps substitutes reachable without horizontal page overflow", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, process.env.GTEX_E2E_LINEUP_ROUTE ?? "/lineup");
  await expect(page.getByText("SUBSTITUTES")).toBeVisible();
  await expect(
    page.getByText(
      "Select a substitute, then tap a starter position to assign them.",
    ),
  ).toBeVisible();
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "lineup");
});

test("A targeted notification opens its supplied target", async ({
  page,
}, testInfo) => {
  test.skip(
    !process.env.GTEX_E2E_NOTIFICATION_TEXT ||
      !process.env.GTEX_E2E_NOTIFICATION_TARGET,
    "Provide a seeded notification text and its expected route.",
  );
  await visitAuthedRoute(page, "/notifications");
  const notification = page
    .getByText(process.env.GTEX_E2E_NOTIFICATION_TEXT)
    .first();
  await notification.click();
  await page.getByRole("button", { name: /open/i }).click();
  await expect(page).toHaveURL(
    new RegExp(process.env.GTEX_E2E_NOTIFICATION_TARGET),
  );
  await captureScreenshot(page, testInfo, "notifications-targeted");
});

test("An untargeted notification leaves navigation unavailable", async ({
  page,
}) => {
  test.skip(
    !process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT,
    "Provide a real notification without routing metadata.",
  );
  await visitAuthedRoute(page, "/notifications");
  await page
    .getByText(process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT)
    .first()
    .click();
  await expect(page.getByRole("button", { name: /open/i })).toBeDisabled();
});

test("Match Viewer settles to an authoritative or truthful unavailable state", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(
    page,
    process.env.GTEX_E2E_MATCH_VIEWER_ROUTE ??
      "/matches/viewer/not-available",
  );
  await expect(
    page.getByText(
      /No match available|Match viewer unavailable|2D Match Viewer/,
    ).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Verifying shipped capability")).toHaveCount(0);
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "match-viewer");
});
