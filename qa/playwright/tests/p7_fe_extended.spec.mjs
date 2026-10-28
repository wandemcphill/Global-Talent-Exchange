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
  if (!(await locator.isVisible().catch(() => false))) {
    return false;
  }
  const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
  const box = await locator.boundingBox({ timeout: 1_500 }).catch(() => null);
  if (box && (box.y + box.height > viewport.height - 24 || box.y < 24)) {
    const targetDelta = Math.round(box.y - viewport.height * 0.45);
    if (Math.abs(targetDelta) > 40) {
      await page.mouse.move(Math.round(viewport.width * 0.5), Math.round(viewport.height * 0.5));
      await page.mouse.wheel(0, targetDelta);
      await page.waitForTimeout(350);
      await enableAccessibility(page);
    }
  }
  await locator.click({ force: true, timeout: 2_500 }).catch(async () => {
    await locator.dispatchEvent("click", undefined, { timeout: 1_500 }).catch(() => {});
  });
  return true;
}

test.beforeEach(async ({ page }, testInfo) => {
  test.setTimeout(240_000);
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
  // Club HQ is the explicit Club lane, not the Home tab.
  await visitAuthedRoute(page, "/app/club");

  const liveDataRequired = page.getByText("Live club data required", { exact: true });
  const noClubEntry = page.getByText("Build your club command center", {
    exact: true,
  });
  const clubCommand = page
    .getByText("Club command", { exact: true })
    .or(page.locator('[aria-label*="Club command" i]'))
    .first();
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
    const commandBox = await clubCommand.boundingBox({ timeout: 1_500 }).catch(() => null);
    if (commandBox && commandBox.y > 240) {
      const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
      await page.mouse.move(Math.round(viewport.width * 0.5), Math.round(viewport.height * 0.5));
      await page.mouse.wheel(0, Math.max(320, Math.round(commandBox.y - 160)));
      await page.waitForTimeout(500);
      await enableAccessibility(page);
    }

    const browseButton = page.getByRole("button", { name: "Club sections" });
    // Match the Squad section tile by its unique subtitle rather than /Squad/i so we never
    // match "Switch active club Argentina Academy Squad 01" or "Sync squad".
    const squadSection = page
      .getByRole("button", { name: /Owned players and regens/i })
      .or(page.getByText("Owned players and regens", { exact: true }))
      .first();

    // In compact layouts (mobile/narrow tablet), sections are housed in a "Club sections" sheet;
    // in desktop layouts, the left panel is rendered inline.
    await expect
      .poll(
        async () => {
          await enableAccessibility(page);
          const visibleCount =
            Number(await browseButton.isVisible().catch(() => false)) +
            Number(await squadSection.isVisible().catch(() => false));
          if (visibleCount === 0) {
            const viewport = page.viewportSize() ?? { width: 1280, height: 800 };
            await page.mouse.move(
              Math.round(viewport.width * 0.5),
              Math.round(viewport.height * 0.5),
            );
            await page.mouse.wheel(0, 280);
          }
          return visibleCount;
        },
        { timeout: 25_000 },
      )
      .toBeGreaterThan(0);

    let browseSheetOpened = false;
    if (await browseButton.isVisible().catch(() => false)) {
      for (let attempt = 0; attempt < 3; attempt += 1) {
        if (await squadSection.isVisible().catch(() => false)) {
          break;
        }
        if (await browseButton.isVisible().catch(() => false)) {
          await clickSemanticsControl(page, browseButton);
          browseSheetOpened = true;
        }
        for (let waitTick = 0; waitTick < 6; waitTick += 1) {
          await page.waitForTimeout(300);
          await enableAccessibility(page);
          if (await squadSection.isVisible().catch(() => false)) {
            break;
          }
        }
        if (await squadSection.isVisible().catch(() => false)) {
          break;
        }
      }
    }

    await expect(squadSection).toBeVisible({ timeout: 15_000 });
    await clickSemanticsControl(page, squadSection);

    if (browseSheetOpened) {
      await page.waitForTimeout(500);
      const closeButton = page.getByRole("button", { name: /Close Club sections/i });
      if (await closeButton.isVisible().catch(() => false)) {
        await closeButton.dispatchEvent("click", undefined, { timeout: 1_500 }).catch(() => {});
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
    await expect(page.getByText(/Retry live load/i)).toBeVisible();
  } else if (await noClubEntry.isVisible().catch(() => false)) {
    await expect(page.getByText("Create club", { exact: true })).toBeVisible();
    await expect(page.getByText("Browse clubs", { exact: true })).toBeVisible();
  } else {
    const browseButton = page.getByRole("button", { name: "Club sections" });
    const inlineSection = page.getByText("Identity, badges, and prestige", {
      exact: true,
    });
    await expect
      .poll(
        async () => {
          await enableAccessibility(page);
          return (
            Number(await browseButton.isVisible().catch(() => false)) +
            Number(await inlineSection.isVisible().catch(() => false))
          );
        },
        { timeout: 15_000 },
      )
      .toBeGreaterThan(0);
  }

  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "club-hq");
});

test.skip("A targeted notification opens its supplied target", async ({ page }, testInfo) => {
  await visitAuthedRoute(page, "/app/notifications");
  await expect(page.getByText("Notification 1")).toBeVisible();
  await page.getByText("Notification 1").click();
  await expect(page).toHaveURL(/\/app\/target1/);
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "notification-targeted");
});

test.skip("An untargeted notification leaves navigation unavailable", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/notifications");
  await expect(page.getByText("Notification 2")).toBeVisible();
  await page.getByText("Notification 2").click();
  await expect(page).toHaveURL(/\/app\/notifications/);
  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "notification-untargeted");
});

test("Match Viewer settles to an authoritative or truthful unavailable state", async ({
  page,
}, testInfo) => {
  await visitAuthedRoute(page, "/app/matches");

  const liveMatchButton = page.getByText(/Open match viewer/i).first();
  const unavailableBanner = page.getByText(
    /Match feed is temporarily unavailable|No live matches right now/i,
  );
  const matchCenterHeader = page.getByText(/Match center|Broadcast feed|Live matchday/i).first();
  await expect
    .poll(
      async () => {
        await enableAccessibility(page);
        return (
          Number(await liveMatchButton.isVisible().catch(() => false)) +
          Number(await unavailableBanner.isVisible().catch(() => false)) +
          Number(await matchCenterHeader.isVisible().catch(() => false))
        );
      },
      { timeout: 60_000 },
    )
    .toBeGreaterThan(0);

  if (await liveMatchButton.isVisible().catch(() => false)) {
    await liveMatchButton.click();
    await expect(
      page.getByText(/Match viewer unavailable|Match center|Live 2D|Replay/i).first(),
    ).toBeVisible({ timeout: 30_000 });
  }

  await verifyNoHorizontalOverflow(page);
  await captureScreenshot(page, testInfo, "match-viewer");
});
