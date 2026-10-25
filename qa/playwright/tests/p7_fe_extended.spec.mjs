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

test("Club squad route loads the roster or explicit no-club state", async ({ page }, testInfo) => {
  // This workflow launches Flutter Web, not the separately hosted React shell
  // at /console. Use the Flutter Club HQ route and its semantic UI.
  await visitAuthedRoute(page, process.env.GTEX_E2E_SQUAD_ROUTE ?? "/app/club");

  const noClubEntry = page.getByText("Build your club command center", {
    exact: true,
  });
  const clubCommand = page.getByText("Club command", { exact: true });
  await expect
    .poll(
      async () =>
        Number(await noClubEntry.isVisible().catch(() => false)) +
        Number(await clubCommand.isVisible().catch(() => false)),
      { timeout: 60_000 },
    )
    .toBeGreaterThan(0);

  if (await noClubEntry.isVisible().catch(() => false)) {
    await expect(page.getByText("Create club", { exact: true })).toBeVisible();
  } else {
    // Select the actual section label. The descriptive subtitle is not a
    // stable accessibility target across the responsive master/detail layout.
    const squadSection = page.getByText("Squad", { exact: true }).filter({ visible: true }).first();
    let browseSheetOpened = false;
    if (!(await squadSection.isVisible().catch(() => false))) {
      await page.getByRole("button", { name: "Club sections" }).click();
      browseSheetOpened = true;
      await expect(squadSection).toBeVisible();
    }
    await squadSection.click();

    if (browseSheetOpened) {
      await page.getByRole("button", { name: "Close Club sections" }).click();
    }

    await expect(page.getByText("Squad room", { exact: true })).toBeVisible();
    await expect(page.getByText("Lineup & squad registration", { exact: true })).toBeVisible();
    await expect(page.getByText("Open Lineup & Tactics", { exact: true })).toBeVisible();
  }

  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "lineup");
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
