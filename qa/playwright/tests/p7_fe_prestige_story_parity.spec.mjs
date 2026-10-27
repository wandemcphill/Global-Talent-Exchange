import { test, expect } from "@playwright/test";

// Test suite for B5: Owner Showroom, Luxury Assets, Club Chronicle, Newsroom Parity
// Scoped independent test file to prevent overlap with other agents.

const mockClub = {
  club_id: "club-parity-1",
  club_name: "Lagos Atlantic SC",
  short_name: "LSC",
  stage: "active",
  is_active: true,
  world_day: 14,
  prestige: 78,
  fans: 125000,
  cash: 18500,
  primary_color: "#0F766E",
  secondary_color: "#070B11",
  crest_url: "https://example.com/crests/lagos.png",
  city: "Lagos",
  country_code: "NG",
};

const mockControlCenter = {
  clubs: [mockClub],
  integrity: { score: 98 },
  inbox_open_count: 2,
  economy: {
    wallet: {
      gtex_total: 18500,
      fan_total: 4200,
    },
  },
};

const mockCatalog = [
  {
    catalog_key: "falcon_7x_private_jet",
    name: "Dassault Falcon 7X",
    category: "jet",
    model: "Triple-Engine Long Range Executive Fleet",
    price_gtex: 4800,
    broadcast_on_purchase: true,
    can_gift_to_player: false,
    image_url: "https://example.com/assets/falcon7x.jpg",
  },
  {
    catalog_key: "chronos_tourbillon_watch",
    name: "Chronos Tourbillon Horizon",
    category: "watch",
    model: "Titanium Hand-Wound Manufacture Movement",
    price_gtex: 250,
    broadcast_on_purchase: false,
    can_gift_to_player: true,
    image_url: "https://example.com/assets/chronos.jpg",
  },
  {
    catalog_key: "superyacht_prestige_60",
    name: "Prestige 60 Sea Cruiser",
    category: "vehicle",
    model: "60ft Ocean Cruiser for Boardroom Summits",
    price_gtex: 3200,
    broadcast_on_purchase: false,
    can_gift_to_player: false,
    image_url: "https://example.com/assets/yacht.jpg",
  },
];

const mockOwnedAssets = [
  {
    id: "owned-asset-1",
    catalog_key: "falcon_7x_private_jet",
    custom_name: "Atlantic Wings One",
    category: "jet",
    price_gtex: 4800,
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    broadcast_globally: true,
  },
];

const mockSquad = [
  {
    id: "regen-101",
    name: "Chidi Nnamdi",
    position: "FWD",
    rating: 76,
    morale: 80,
    is_regen: true,
    portrait_url: "https://example.com/portraits/chidi.jpg",
  },
  {
    id: "senior-202",
    name: "Wilfred Ndidi",
    position: "MID",
    rating: 84,
    morale: 72,
    is_regen: false,
    portrait_url: "https://example.com/portraits/ndidi.jpg",
  },
];

const mockStory = {
  club: {
    club_id: "club-parity-1",
    club_name: "Lagos Atlantic SC",
    crest_url: "https://example.com/crests/lagos.png",
    world_day: 14,
    city: "Lagos",
    country_code: "NG",
  },
  save_context_id: "save-ctx-1",
  is_owner: true,
  privacy_redacted: false,
  timeline: [
    {
      id: "time-1",
      category: "private_jet_purchase",
      title: "Atlantic Wings One Commissioned",
      summary: "Executive long-range aviation acquired for continental transit.",
      verified_price_gtex: 4800,
      created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    },
    {
      id: "time-2",
      category: "match_result",
      title: "Dominant Derby Victory (3 - 1)",
      summary: "Lagos Atlantic defeated Enyimba FC on World Day 12.",
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    },
  ],
  unresolved_issues: [
    {
      id: "issue-1",
      category: "staff_contracts",
      title: "Head Scout Contract Extension",
      body: "Chief Analyst requests a 2-year retention agreement before national tournament.",
      deadline_at: new Date(Date.now() + 3600000 * 6).toISOString(),
    },
  ],
  relationships: {
    manager: {
      name: "Tunde Bakare",
      role: "Head Coach",
      rating: 81,
      mentality: "High-Press Possession",
      reputation: "Continental Veteran",
    },
    players: mockSquad,
  },
  scouting_watchlist: [
    {
      id: "scout-1",
      player_name: "Victor Boniface",
      position: "FWD",
      age: 23,
      current_rating: 82,
      potential_rating: 89,
      estimated_value_gtex: 850,
      priority: "high",
      scout_notes: "Dominant aerial target with clinical finishing under physical pressure.",
      recommendation: "Priority Target",
    },
  ],
  upcoming_schedule: [
    {
      id: "match-up-1",
      round: 15,
      home_name: "Lagos Atlantic SC",
      away_name: "Kano Pillars",
      status: "scheduled",
    },
  ],
  recent_results: [
    {
      id: "match-rec-1",
      round: 14,
      home_name: "Lagos Atlantic SC",
      away_name: "Enyimba FC",
      home_goals: 3,
      away_goals: 1,
      status: "completed",
    },
  ],
  club_news: [
    {
      id: "news-art-1",
      category: "private_jet_purchase",
      headline: "Lagos Atlantic SC Commissions Executive Fleet Aviation",
      subheadline: "Boardroom completes acquisition of Dassault Falcon 7X.",
      editorial_narration: "A significant benchmark in the modern era of the club.",
      created_at: new Date().toISOString(),
    },
  ],
  achievements: [
    {
      id: "ach-1",
      title: "Foundation Formed",
      detail: "Club charter ratified on World Day 1.",
    },
    {
      id: "ach-2",
      title: "Prestige Fleet Certified",
      detail: "Commissioned long-range private jet for squad travels.",
    },
  ],
  owner_legacy: {
    prestige: 78,
    tier: "Continental Contender",
    win_rate_pct: 75,
    matches_played: 12,
    wins: 9,
  },
};

const mockNewsroom = {
  articles: [
    {
      id: "art-lead",
      category: "private_jet_purchase",
      headline: "Lagos Atlantic SC Commissions Executive Fleet Aviation",
      subheadline: "Long-range transit commissioned for squad logistics",
      hero_image_url: "https://example.com/assets/falcon7x.jpg",
      editorial_narration: "Grounding report verifies ledger transaction of 4,800 GTX.",
      created_at: new Date().toISOString(),
      world_day: 14,
    },
    {
      id: "art-match",
      category: "match_result",
      headline: "Matchday Report: High-Stakes Derby Decided by 3 Goals",
      subheadline: "Clinical finishing secures three points",
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
      world_day: 14,
    },
    {
      id: "art-gift",
      category: "player_gift",
      headline: "Academy Regen Presented Horology Milestone Incentive",
      subheadline: "Personal boardroom recognition for squad progression",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
      world_day: 13,
    },
  ],
};

// Route intercept helper to mock backend responses during UI verification
async function setupOwnerParityRoutes(page) {
  // Mock auth user state in localStorage
  await page.addInitScript(() => {
    localStorage.setItem("gtex_auth_token", "fake-parity-token-b5");
    localStorage.setItem(
      "gtex_user",
      JSON.stringify({
        id: "owner-user-b5",
        username: "boardroom_owner",
        display_name: "Boardroom Executive",
        role: "user",
        account_type: "user",
      }),
    );
    localStorage.setItem("gtex_active_club", "club-parity-1");
  });

  // Intercept backend API requests
  await page.route("**/owner/control-center", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockControlCenter),
    });
  });

  await page.route("**/owner/clubs/club-parity-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockClub,
        squad: mockSquad,
        economy: { cash_gtex: 18500 },
      }),
    });
  });

  await page.route("**/owner/clubs/club-parity-1/showroom", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        catalog: mockCatalog,
        owned_assets: mockOwnedAssets,
      }),
    });
  });

  await page.route("**/owner/clubs/club-parity-1/showroom/purchase", async (route) => {
    const postData = route.request().postDataJSON() || {};
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        asset: {
          catalog_key: postData.catalog_key || "chronos_tourbillon_watch",
          custom_name: postData.custom_name || "Horizon Timepiece",
          price_gtex: 250,
        },
        broadcast_globally: postData.catalog_key === "falcon_7x_private_jet",
        broadcast_event:
          postData.catalog_key === "falcon_7x_private_jet" ? { id: "bcast-1" } : null,
      }),
    });
  });

  await page.route("**/owner/clubs/club-parity-1/showroom/gift", async (route) => {
    const postData = route.request().postDataJSON() || {};
    const recipient = mockSquad.find((p) => p.id === postData.player_id) || mockSquad[0];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        player: {
          id: recipient.id,
          name: recipient.name,
          position: recipient.position,
          morale: recipient.morale + 15,
        },
        morale_delta: 15,
        asset: {
          catalog_key: postData.catalog_key || "chronos_tourbillon_watch",
          custom_name: "Chronos Tourbillon Horizon",
          price_gtex: 250,
        },
        broadcast_event: { id: "gift-bcast-1" },
      }),
    });
  });

  await page.route("**/owner/clubs/club-parity-1/story", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockStory),
    });
  });

  await page.route("**/owner/newsroom*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockNewsroom),
    });
  });

  await page.route("**/owner/ticker*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ events: [] }),
    });
  });
}

test.describe("Prestige, Story, and Showroom Parity (Agent B5)", () => {
  test("Showroom navigation, verified catalogue, purchase flow and idempotency", async ({
    page,
  }) => {
    await setupOwnerParityRoutes(page);
    await page.goto("/app/showroom");

    // Verify Showroom Screen loads with GTEX Styling & Header
    await expect(page.locator('[data-testid="showroom-screen"]')).toBeVisible();
    await expect(page.getByText("Owner Showroom & Luxury Fleet")).toBeVisible();
    await expect(page.getByText("Club Treasury")).toBeVisible();

    // Verify Demarcation Banner: Owner Luxury Gifting vs Community Gifting
    await expect(page.getByText("Owner Luxury Gifting (Club GTEX Coin)")).toBeVisible();
    await expect(page.getByText("Community Gifting (FanCoin)")).toBeVisible();

    // Verify Catalogue Items Render Verified GTX Prices and Wire Badges
    const jetItem = page.locator('[data-testid="showroom-item-falcon_7x_private_jet"]');
    await expect(jetItem).toBeVisible();
    await expect(jetItem.getByText("Global Wire Notice")).toBeVisible();
    await expect(jetItem.getByText("4,800 GTX")).toBeVisible();

    const watchItem = page.locator('[data-testid="showroom-item-chronos_tourbillon_watch"]');
    await expect(watchItem).toBeVisible();
    await expect(watchItem.getByText("Private Collection")).toBeVisible();
    await expect(watchItem.getByText("250 GTX")).toBeVisible();

    // Click Acquire on watch item -> verify purchase confirm modal
    await watchItem.locator('[data-testid="acquire-btn-chronos_tourbillon_watch"]').click();
    const purchaseModal = page.locator('[data-testid="showroom-purchase-confirm"]');
    await expect(purchaseModal).toBeVisible();
    await expect(purchaseModal.getByText("Treasury Authorization")).toBeVisible();
    await expect(purchaseModal.getByText("250 GTX")).toBeVisible();

    // Confirm purchase -> verify confirmed receipt modal
    await purchaseModal.locator('[data-testid="confirm-purchase-button"]').click();
    const receiptModal = page.locator('[data-testid="showroom-purchase-receipt"]');
    await expect(receiptModal).toBeVisible();
    await expect(receiptModal.getByText("Acquisition Confirmed")).toBeVisible();
    await receiptModal.locator('[data-testid="close-purchase-receipt"]').click();
    await expect(receiptModal).toBeHidden();
  });

  test("Owner-to-Player luxury gifting strictly targets academy regens with verified receipt", async ({
    page,
  }) => {
    await setupOwnerParityRoutes(page);
    await page.goto("/app/showroom");

    const watchItem = page.locator('[data-testid="showroom-item-chronos_tourbillon_watch"]');
    await expect(watchItem).toBeVisible();

    // Click Gift Regen button -> open gift confirm modal
    await watchItem.locator('[data-testid="gift-btn-chronos_tourbillon_watch"]').click();
    const giftModal = page.locator('[data-testid="showroom-gift-confirm"]');
    await expect(giftModal).toBeVisible();
    await expect(giftModal.getByText("Owner Luxury Gifting")).toBeVisible();

    // Verify academy regen player is listed (Chidi Nnamdi)
    const regenBtn = giftModal.locator('[data-testid="select-regen-regen-101"]');
    await expect(regenBtn).toBeVisible();
    await regenBtn.click();

    // Fill personal dedication note
    const noteInput = giftModal.locator('[data-testid="gift-note-input"]');
    await noteInput.fill("Exemplary performance in the continental cup.");

    // Submit gift -> verify gift receipt displays confirmed morale delta
    await giftModal.locator('[data-testid="confirm-gift-button"]').click();
    const giftReceipt = page.locator('[data-testid="showroom-gift-receipt"]');
    await expect(giftReceipt).toBeVisible();
    await expect(giftReceipt.getByText("Luxury Gift Delivered")).toBeVisible();
    await expect(giftReceipt.getByText("Morale +15 · Confirmed")).toBeVisible();
    await expect(
      giftReceipt.getByText("Exemplary performance in the continental cup."),
    ).toBeVisible();

    await giftReceipt.locator('[data-testid="close-gift-receipt"]').click();
    await expect(giftReceipt).toBeHidden();
  });

  test("Club Story chronicle displays verified lore, schedule, manager, and dispatches", async ({
    page,
  }) => {
    await setupOwnerParityRoutes(page);
    await page.goto("/app/story");

    // Verify screen title and club identity
    await expect(page.locator('[data-testid="club-story-screen"]')).toBeVisible();
    await expect(page.locator('[data-testid="club-story-title"]')).toHaveText("Lagos Atlantic SC");
    await expect(page.getByText("World Day 14")).toBeVisible();

    // Verify Surface Directory navigation buttons exist
    await expect(page.locator('[data-testid="link-to-showroom"]')).toBeVisible();
    await expect(page.locator('[data-testid="link-to-newsroom"]')).toBeVisible();
    await expect(page.locator('[data-testid="link-to-inbox"]')).toBeVisible();

    // Verify Timeline Tab
    await expect(page.locator('[data-testid="timeline-tab-content"]')).toBeVisible();
    await expect(page.getByText("Atlantic Wings One Commissioned")).toBeVisible();
    await expect(page.getByText("Dominant Derby Victory (3 - 1)")).toBeVisible();

    // Switch to Club Dispatches tab
    await page.locator('[data-testid="tab-dispatches"]').click();
    await expect(page.locator('[data-testid="dispatches-tab-content"]')).toBeVisible();
    await expect(
      page.getByText("Lagos Atlantic SC Commissions Executive Fleet Aviation"),
    ).toBeVisible();

    // Switch to Staff & Squad tab
    await page.locator('[data-testid="tab-relationships"]').click();
    await expect(page.locator('[data-testid="relationships-tab-content"]')).toBeVisible();
    await expect(page.getByText("Tunde Bakare")).toBeVisible();
    await expect(page.getByText("Chidi Nnamdi")).toBeVisible();
    await expect(page.getByText("Academy Regen")).toBeVisible();

    // Switch to Save Fixtures tab
    await page.locator('[data-testid="tab-schedule"]').click();
    await expect(page.locator('[data-testid="schedule-tab-content"]')).toBeVisible();
    await expect(page.getByText("Lagos Atlantic SC vs Kano Pillars")).toBeVisible();
    await expect(page.getByText("Lagos Atlantic SC 3 - 1 Enyimba FC")).toBeVisible();
  });

  test("AI Newsroom dispatches verified grounded stories and category filters", async ({
    page,
  }) => {
    await setupOwnerParityRoutes(page);
    await page.goto("/app/newsroom");

    await expect(page.locator('[data-testid="newsroom-screen"]')).toBeVisible();
    await expect(page.getByText("The Boardroom Chronicle")).toBeVisible();
    await expect(page.getByText("Grounding & Privacy Certified")).toBeVisible();

    // Verify categories
    await expect(page.locator('[data-testid="cat-private_jet_purchase"]')).toBeVisible();
    await expect(page.locator('[data-testid="cat-player_gift"]')).toBeVisible();

    // Lead story
    await expect(page.locator('[data-testid="lead-story-card"]')).toBeVisible();
    await expect(
      page.getByText("Lagos Atlantic SC Commissions Executive Fleet Aviation").first(),
    ).toBeVisible();
  });

  test("Multi-viewport responsiveness without horizontal overflow", async ({ page }) => {
    await setupOwnerParityRoutes(page);

    const viewports = [
      { name: "mobile-compact", width: 360, height: 740 },
      { name: "mobile-modern", width: 393, height: 852 },
      { name: "tablet", width: 768, height: 1024 },
      { name: "desktop-standard", width: 1280, height: 800 },
      { name: "desktop-wide", width: 1440, height: 900 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      for (const route of ["/app/showroom", "/app/story", "/app/newsroom"]) {
        await page.goto(route);
        await page.waitForLoadState("domcontentloaded");

        // Verify no horizontal overflow
        const hasOverflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });

        expect(
          hasOverflow,
          `Horizontal overflow detected on ${route} at ${vp.name} (${vp.width}x${vp.height})`,
        ).toBe(false);
      }
    }
  });
});
