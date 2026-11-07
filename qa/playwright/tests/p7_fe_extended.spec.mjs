import { expect, test } from "@playwright/test";
import {
  attachDiagnostics,
  captureScreenshot,
  collectBrowserDiagnostics,
  configured,
  credentialsConfigured,
  enableAccessibility,
  verifyNoHorizontalOverflow,
  visitAuthedRoute,
} from "./helpers.mjs";

async function clickSemanticsControl(page, locator) {
  // Flutter owns a nested scrollable semantics tree. Let Playwright scroll the
  // actual tappable semantics node into view rather than wheel the page body,
  // which is fixed/overflow-hidden in Flutter Web.
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  await locator.click({ force: true, timeout: 8_000 }).catch(async () => {
    await locator.dispatchEvent("click").catch(() => {});
  });
}

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
  test.setTimeout(300_000);
  // Club HQ is the explicit Club lane, not the Home tab.
  await visitAuthedRoute(page, "/app/club");

  const liveDataRequired = page.getByText("Live club data required", { exact: true });
  const noClubEntry = page.getByText("Build your club command center", {
    exact: true,
  });
  const clubCommand = page.getByText("Club command", { exact: true });
  await expect
    .poll(
      async () => {
        await enableAccessibility(page);
        return (
          Number(await liveDataRequired.isVisible().catch(() => false)) +
          Number(await noClubEntry.isVisible().catch(() => false)) +
          Number(await clubCommand.isVisible().catch(() => false))
        );
      },
      { timeout: 60_000 },
    )
    .toBeGreaterThan(0);

  if (await liveDataRequired.isVisible().catch(() => false)) {
    await expect(page.getByText(/generated demo club data/i)).toBeVisible();
  } else if (await noClubEntry.isVisible().catch(() => false)) {
    await expect(page.getByText("Create club", { exact: true })).toBeVisible();
  } else {
    // Scroll Club command toward the top of the Empire workspace scroll view so inline
    // section items and detail headers are inside the active viewport.
    const commandBox = await clubCommand.boundingBox().catch(() => null);
    if (commandBox && commandBox.y > 240) {
      const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
      await page.mouse.move(Math.round(viewport.width * 0.5), Math.round(viewport.height * 0.5));
      await page.mouse.wheel(0, Math.max(320, Math.round(commandBox.y - 160)));
      await page.waitForTimeout(500);
      await enableAccessibility(page);
    }

    // Flutter exposes these controls as flt-semantics nodes. CSS-backed
    // locators avoid repeatedly walking the large accessibility role tree on
    // mobile, where each getByRole visibility query can take several seconds.
    const browseButton = page
      .locator('flt-semantics[role="button"]')
      .filter({ hasText: /^Club sections$/ })
      .first();
    const squadSection = page
      .locator('flt-semantics[role="button"]')
      .filter({ hasText: /Owned players and regens/i })
      .first();

    // Compact layouts put the section list in a bottom sheet; wider layouts
    // render the same list inline. Open the sheet once and wait for the real
    // Squad item rather than polling two slow semantic-role locators together.
    let browseSheetOpened = false;
    if (await browseButton.isVisible().catch(() => false)) {
      browseSheetOpened = true;
      await clickSemanticsControl(page, browseButton);
      await expect(squadSection).toBeVisible({ timeout: 45_000 });
    } else {
      await expect(squadSection).toBeVisible({ timeout: 45_000 });
    }

    await clickSemanticsControl(page, squadSection);

    if (browseSheetOpened) {
      await page.waitForTimeout(500);
      const closeButton = page.getByRole("button", { name: /Close Club sections/i });
      if (await closeButton.isVisible().catch(() => false)) {
        await closeButton.dispatchEvent("click").catch(() => {});
        await page.waitForTimeout(400);
      }
    }

    // Flutter merges header titles and subtitles into a single semantics label
    // or exposes container headers via aria-label on a semantics group node.
    const squadRoom = page
      .getByText(/Squad room/i)
      .or(page.locator('[aria-label*="Squad room" i]'))
      .first();
    await expect
      .poll(
        async () => {
          await enableAccessibility(page);
          return await squadRoom.isVisible().catch(() => false);
        },
        { timeout: 15_000 },
      )
      .toBe(true);

    const lineupRegistration = page
      .getByText(/Lineup & squad registration/i)
      .or(page.locator('[aria-label*="Lineup & squad registration" i]'))
      .first();
    for (let scrollAttempt = 0; scrollAttempt < 3; scrollAttempt += 1) {
      await enableAccessibility(page);
      if (await lineupRegistration.isVisible().catch(() => false)) {
        break;
      }
      const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
      await page.mouse.move(Math.round(viewport.width * 0.5), Math.round(viewport.height * 0.5));
      await page.mouse.wheel(0, 260);
      await page.waitForTimeout(400);
    }
    await expect(lineupRegistration).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page
        .getByRole("button", { name: /Open Lineup & Tactics/i })
        .or(page.getByText(/Open Lineup & Tactics/i))
        .first(),
    ).toBeVisible({
      timeout: 15_000,
    });
  }

  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "lineup");
});

test("Club HQ opens an authoritative club or no-club state", async ({ page }, testInfo) => {
  // Owner operations must show real club context or a truthful unavailable state,
  // never fabricated demo-club data.
  await visitAuthedRoute(page, "/app/club");

  const ownerCockpit = page.getByText("Club owner operations cockpit", { exact: true });
  const clubCommand = page.getByText("Club command", { exact: true });
  const acceptableStates = [
    page.getByText("Live club data required", { exact: true }),
    clubCommand,
    page.getByText("Build your club command center", { exact: true }),
    ownerCockpit,
  ];
  await expect
    .poll(
      async () => {
        await enableAccessibility(page);
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
      if (!(await ownerCockpit.isVisible().catch(() => false))) {
        const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
        await page.mouse.move(Math.round(viewport.width * 0.5), Math.round(viewport.height * 0.5));
        await page.mouse.wheel(0, 480);
        await page.waitForTimeout(500);
        await enableAccessibility(page);
      }
      await expect(ownerCockpit).toBeVisible();
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
