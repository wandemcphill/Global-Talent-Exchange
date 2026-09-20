import { expect, test } from "@playwright/test";

const configured = Boolean(process.env.GTEX_E2E_BASE_URL || process.env.GTEX_E2E_API_BASE_URL);

test("competition design lab captures three hierarchy specimens", async ({ page }, testInfo) => {
  test.skip(!configured, "Set GTEX_E2E_BASE_URL or GTEX_E2E_API_BASE_URL.");
  test.skip(
    !process.env.GTEX_E2E_DESIGN_LAB,
    "Set GTEX_E2E_DESIGN_LAB=1 to render isolated Design Lab fixtures.",
  );
  test.setTimeout(180_000);

  for (const [direction, captureName] of [
    ["matchday", "competition-matchday-board"],
    ["atlas", "competition-atlas"],
    ["participation", "competition-participation-desk"],
  ]) {
    await page.goto(`/design-lab/competitions?direction=${direction}`, {
      waitUntil: "domcontentloaded",
    });
    const surface = page.locator("flt-glass-pane, flutter-view, canvas").first();
    await expect(surface).toBeVisible({ timeout: 120_000 });
    await page.waitForTimeout(2_000);

    // Flutter Web uses a canvas, so the widget test covers labels and this
    // capture records the rendered composition instead of asserting DOM text.
    await page.screenshot({
      path: testInfo.outputPath(`${captureName}-${testInfo.project.name}.png`),
      fullPage: true,
    });
  }
});
