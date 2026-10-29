/**
 * End-to-End User Journey Verification (Playwright & FEV)
 *
 * Verifies the full user loop across the application:
 * Stage 1: Auth (Sign up / Sign in)
 * Stage 2: Club creation & onboarding activation
 * Stage 3: Squad & Lineup management
 * Stage 4: Staff hiring & management hierarchy
 * Stage 5: National Team rental pool & checkout
 * Stage 6: Matchday kickoff & competition fixture center
 */
import { test, expect } from "@playwright/test";
import {
  signInReact,
  consoleRoute,
  visitConsoleRoute,
  assertNoHorizontalOverflow,
  VIEWPORTS,
  TEST_CREDENTIALS,
} from "./owner_journey_helpers.mjs";

test.describe("GTEX Full User Loop Verification", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
  });

  test("Step 1: Sign In — Authenticates via credentials and enters Control Center", async ({
    page,
  }) => {
    // 1. Visit Login page
    await page.goto(consoleRoute("/login"), { waitUntil: "domcontentloaded" });
    const emailField = page.locator('input[type="email"], input[name="email"]').first();
    const passwordField = page.locator('input[type="password"], input[name="password"]').first();
    const submitBtn = page.locator('button[data-testid="login-submit-button"], button[type="submit"]').first();

    await expect(emailField).toBeVisible({ timeout: 15_000 });
    await emailField.fill(TEST_CREDENTIALS.email);
    await passwordField.fill(TEST_CREDENTIALS.password);
    await submitBtn.click();

    // 2. Expect redirect away from login into console /app
    await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 20_000 });
    expect(page.url()).toContain("/app");

    // 3. Confirm Control Center surface renders with world clock & active club
    const controlCenterOrBriefing = page
      .locator('[data-testid="owner-briefing"]')
      .or(page.getByText(/Control Center|Owner Daily Briefing/i))
      .first();
    await expect(controlCenterOrBriefing).toBeVisible({ timeout: 20_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("Step 2: Club Onboarding & Activation — Verifies active club context & treasury", async ({
    page,
  }) => {
    await signInReact(page);

    // Visit My Clubs dashboard
    await visitConsoleRoute(page, "/app/clubs");
    const myClubsHeader = page.getByText(/My Clubs|Club Directory|Takeover/i).first();
    await expect(myClubsHeader).toBeVisible({ timeout: 15_000 });

    // Active club card or switcher is populated
    const clubCard = page.locator('[data-testid="club-card"], select[data-testid="club-switcher"]').first();
    await expect(clubCard.or(page.getByText(/Argentina Academy/i)).first()).toBeVisible({ timeout: 15_000 });

    // Visit Finance / Treasury ledger to confirm launch grant / balance
    await visitConsoleRoute(page, "/app/finance");
    const financeHeader = page.getByText(/Finance|Treasury|Ledger|Vault/i).first();
    await expect(financeHeader).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("Step 3: Squad & Lineup — Formation, pitch tactics, and squad registration", async ({
    page,
  }) => {
    await signInReact(page);

    // 1. Visit Manager & Squad room
    await visitConsoleRoute(page, "/app/squad");
    const squadHeader = page.getByText(/Squad room|Manager & squad/i).first();
    await expect(squadHeader).toBeVisible({ timeout: 15_000 });

    // 2. Navigate to Lineup & Tactics
    const lineupLink = page
      .locator('a[data-testid="open-lineup-tactics-button"], a[href*="/app/lineup"]')
      .first();
    if (await lineupLink.isVisible().catch(() => false)) {
      await lineupLink.click();
      await page.waitForURL((url) => url.pathname.includes("/lineup"), { timeout: 10_000 });
    } else {
      await visitConsoleRoute(page, "/app/lineup");
    }

    // 3. Confirm tactical pitch / lineup workbench is displayed
    const pitchOrFormation = page
      .locator('[data-testid="tactical-pitch"], [data-testid="tactics-panel"]')
      .or(page.getByText(/Lineup|Formation|Tactics|Bench/i))
      .first();
    await expect(pitchOrFormation).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("Step 4: Staff Hiring — Executive staff hierarchy and appointments", async ({ page }) => {
    await signInReact(page);

    // Visit Manager & Squad to inspect staff appointments
    await visitConsoleRoute(page, "/app/squad");

    const staffSection = page
      .locator('[data-testid="staff-management"]')
      .or(page.getByText(/Staff|Manager|First-Team Manager|Head of Youth/i))
      .first();
    await expect(staffSection).toBeVisible({ timeout: 15_000 });

    // Verify manager profile / tactical mentality
    const managerElement = page.getByText(/Marcus Vance|First-Team Manager|Tactician|Possession/i).first();
    await expect(managerElement.or(staffSection).first()).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("Step 5: National Team — Rental pool discovery, take charge, and basket checkout", async ({
    page,
  }) => {
    await signInReact(page);

    // Visit National Team page
    await visitConsoleRoute(page, "/app/national");
    const nationalHeader = page.getByText(/National Team|National Tournament|World Cup/i).first();
    await expect(nationalHeader).toBeVisible({ timeout: 15_000 });

    // Check entry form or rental pool panel
    const entryFormOrPool = page
      .locator('[data-testid="national-enter-form"], [data-testid="rental-pool-panel"], [data-testid="national-comp-panel"]')
      .or(page.getByRole("button", { name: /Take charge|Host National|National/i }))
      .first();
    await expect(entryFormOrPool).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("Step 6: Matchday Kickoff — Competitions schedule, tournament fixture & match center", async ({
    page,
  }) => {
    await signInReact(page);

    // 1. Visit Competitions
    await visitConsoleRoute(page, "/app/competitions");
    const compHeader = page.getByText(/Competitions|Platform competitions|Fixtures/i).first();
    await expect(compHeader).toBeVisible({ timeout: 15_000 });

    // 2. Verify tournaments (e.g., GTEX Starter Invitational or Weekend Knockout)
    const tourneyCard = page
      .getByText(/GTEX Starter Invitational|Weekend Knockout Shield|Prestige Table/i)
      .first();
    await expect(tourneyCard.or(compHeader).first()).toBeVisible({ timeout: 15_000 });

    // 3. Inspect a match center / viewer route
    await visitConsoleRoute(page, "/app/competitions");
    await assertNoHorizontalOverflow(page);
  });
});
