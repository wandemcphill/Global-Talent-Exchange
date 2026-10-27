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

test("Club HQ opens an authoritative club or no-club state", async ({ page }, testInfo) => {
  // The owner dashboard deliberately refuses to show fabricated club data.
  // Verify an explicit real-data state instead of assuming a roster is present.
  await visitAuthedRoute(page, "/app");

  const ownerCockpit = page.getByText("Club owner operations cockpit", { exact: true });
  const acceptableStates = [
    page.getByText("Live club data required", { exact: true }),
    page.getByText("Club command", { exact: true }),
    page.getByText("Build your club command center", { exact: true }),
    ownerCockpit,
  ];
  await expect
    .poll(
      async () => {
        for (const state of acceptableStates) {
          if (await state.isVisible().catch(() => false)) return true;
        }
        return false;
      },
      { timeout: 60_000 },
    )
    .toBeTruthy();

  const liveDataRequired = page.getByText("Live club data required", { exact: true });
  if (await liveDataRequired.isVisible().catch(() => false)) {
    await expect(page.getByText(/generated demo club data/i)).toBeVisible();
  } else {
    const noClubEntry = page.getByText("Build your club command center", { exact: true });
    if (await noClubEntry.isVisible().catch(() => false)) {
      await expect(page.getByText("Create club", { exact: true })).toBeVisible();
    } else {
      await expect(page.getByText("Club owner operations cockpit", { exact: true })).toBeVisible();
    }
  }

  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "club-command-authoritative-state");
});
test("A targeted notification opens its supplied target", async ({ page }, testInfo) => {
  test.skip(
    !process.env.GTEX_E2E_NOTIFICATION_TEXT || !process.env.GTEX_E2E_NOTIFICATION_TARGET,
    "Provide a seeded notification text and its expected route.",
  );
  await visitAuthedRoute(page, "/notifications");
  const notification = page.getByText(process.env.GTEX_E2E_NOTIFICATION_TEXT).first();
  await notification.click();
  await page.getByRole("button", { name: /open/i }).click();
  await expect(page).toHaveURL(new RegExp(process.env.GTEX_E2E_NOTIFICATION_TARGET));
  await captureScreenshot(page, testInfo, "notifications-targeted");
});

test("An untargeted notification leaves navigation unavailable", async ({ page }) => {
  test.skip(
    !process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT,
    "Provide a real notification without routing metadata.",
  );
  await visitAuthedRoute(page, "/notifications");
  await page.getByText(process.env.GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT).first().click();
  await expect(page.getByRole("button", { name: /open/i })).toBeDisabled();
});

test("Match Viewer settles to an authoritative or truthful unavailable state", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(
    page,
    process.env.GTEX_E2E_MATCH_VIEWER_ROUTE ?? "/matches/viewer/not-available",
  );
  await expect(
    page.getByText(/No match available|Match viewer unavailable|2D Match Viewer/).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Verifying shipped capability")).toHaveCount(0);
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "match-viewer");
});
