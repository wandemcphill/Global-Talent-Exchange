# GTEX P7-FE MARKET + OWNERSHIP VERTICAL AUDIT & IMPLEMENTATION BRIEF

**Repository:** `wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Audit Date:** September 2026
**Auditor:** Jules (Principal Systems & Security Engineer)
**Target Document:** `docs/audits/gtex-market-ownership-jules-audit.md`

---

## 1. EXECUTIVE SUMMARY & CORE THESIS

### Executive Summary
This audit provides a forensic inventory and implementation blueprint for the next major GTEX frontend slice: **Market + Ownership Vertical (P7-FE)**.

Across the codebase, GTEX currently features **two parallel market paradigms**:
1. **Player Share / Token Market (`/market`, `/app/market`):** Liquid, continuous trading of player fractional equity backed by match performance, GSI ratings, and value snapshots.
2. **Transfer Market / Club Transfer Center (`/market/transfers`, `/football/transfer-center`):** Formal club-to-club player contracts, bids, loan listings, private negotiations, and squad movement.

In addition, GTEX supports **Club Ownership/Sale Markets (`/clubs/sale-market`)**, **Player Card Marketplace (`/player-cards`)**, **Creator Share Markets (`/creator-share-market`)**, and **Manager Markets (`/coaches`, `/managers`)**.

While the backend architecture (`app.market`, `app.transfer_market`, `app.portfolio`, `app.club_ownership`, `app.club_sale_market`, `app.player_cards`) provides full-featured endpoints, the Flutter frontend currently suffers from **routing fragmentation, dead navigation links, hidden backend capabilities (e.g. watchlist endpoints, WebSocket live streams), state conflation between financial portfolios and squad identity, and responsive clipping on narrow devices**.

### Core Thesis: Football Identity vs. Financial Ticker
GTEX is **not a crypto exchange or equity broker with football skins**. GTEX ownership is a **football identity experience**.
- In GTEX, owning player shares or card tokens is **backing a player's real-world or virtual career journey**—affecting club popularity, matchday form, squad utility, national team eligibility, and fan governance.
- A "Portfolio" in GTEX is not merely a stock balance; it is **The User's Squad & Club Holding Desk**, bridging liquid trading position with pitch performance, contract status, and club prestige.

---

## 2. VERIFIED ROUTE INVENTORY

The following table catalogs all market and ownership routes across `app_router.dart`, `app_destinations.dart`, `gte_route_data.dart`, and `gte_navigation_shell_screen.dart`:

| Surface / Destination | Route Path(s) | Underlying Screen Widget | Shell Mounted? | Route Status | Audit Observations & Issues |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Primary Market Desk** | `/market`<br>`/player-market` | `GteMarketPlayersScreenV2` / `GtexPlayerMarketRedesignScreen` | Yes (`GtePrimaryDestination.market`) | **Canonical** | Main player share market screen. High functional parity for buy/sell & movers rail, but lacks watchlist integration & deep filter overlays. |
| **Transfer Hub / Center** | `/market/transfers`<br>`/football/transfer-center`<br>`/app/transfer-hub` | Redirects to `/market` in `app_router.dart` | No (Redirected) | **Legacy / Alias** | Deep link `/football/transfer-center` redirects to `/market`. The dedicated `FootballTransferCenterRouteData` controller exists in feature packages but lacks an independent top-level route handler. |
| **Transfer Listing Detail** | `/market/transfers/:listingId` | Handled via fallback redirect to `/market` | No | **Dead Nav** | Comment in `app_router.dart` confirms "No screen anywhere renders a single transfer listing... deep link degrades to transfer hub". |
| **Capital Desk / Holdings** | `/wallet`<br>`/capital` | `GtexWalletOverviewScreenV2` / `GtexOwnershipExperience` | Yes (`GtePrimaryDestination.wallet`) | **Canonical** | Combines Wallet, Orders, Holdings (`GtexOwnershipExperience`), Coin Traders, and Trader Dashboard in tabbed desk module. |
| **Portfolio Screen (Standalone)** | `/app/portfolio` (internal) | `GtePortfolioScreen` | No | **Legacy / Duplicate** | Older visitor/authed portfolio screen replaced in shell by `GtexOwnershipExperience`. Retains good state panels but uses outdated provider structures. |
| **Club Sale Market** | `/clubs/sale-market`<br>`/clubs/:clubId/sale-market` | `ClubSaleMarketScreen` | No (Pushed Route) | **Feature Active** | Fully built controller & repository (`ClubSaleMarketController`), allows buying/selling/offering on full football clubs. Hidden from primary shell nav. |
| **Creator Share Market** | `/creator-share-market/clubs/:clubId` | `CreatorShareMarketScreen` | No (Pushed Route) | **Feature Active** | Handles creator club equity trading. Fully built with admin control screens. |
| **Manager Market** | `/coaches`<br>`/managers` | `ManagerMarketScreen` | No (Pushed Route) | **Feature Active** | Coach/Manager hiring desk. Accessible via shell action `_openCoachMarket` which routes to `/market` instead of launching coach screen. |
| **Player Card Marketplace** | `/player-cards` | `PlayerCardMarketplaceScreen` | No (Redirects) | **Alias / Fragmented** | Redirects to `/market` in `app_router.dart`, despite having a full dedicated feature widget in `features/player_card_marketplace`. |

---

## 3. BACKEND / FRONTEND PARITY ANALYSIS

### A. Market & Share Trading Parity

| Feature / Domain | Backend Endpoint | Frontend Controller / Service | Parity Status | Gap / Discrepancy Analysis |
| :--- | :--- | :--- | :---: | :--- |
| **Market Browse Catalog** | `GET /market/browse` | `GtexPlayerMarketRedesignScreen` | **100% Parity** | Fully hydrated leagues, divisions, clubs, nationalities, and availability filters. |
| **Player Detail Market Profile** | `GET /market/players/{id}` | `GteExchangeController.getMarketPlayerProfile` | **100% Parity** | Fetches share price, market cap, circulating supply, dividend yield, and 24h trends. |
| **Movers Rail** | `GET /market/movers` | `GtexMarketMoversRail` | **100% Parity** | Top gainers, top losers, and volume leaders populated live from backend. |
| **Buy Share Position** | `POST /market/buy` | `GteExchangeController.buyPlayerShare` | **90% Parity** | Instant market buys functional. Counter-offers and conditional order types missing in UI modal. |
| **Sell Share Position** | `POST /market/sell` | `GteExchangeController.sellPlayerShare` | **90% Parity** | Instant market sells functional. Limit ask orders not exposed in basic market UI. |
| **Watchlist Management** | `GET/POST/DEL /player-cards/watchlist`<br>`GET/POST /trader/watchlist` | None (No UI state) | **0% Parity (Hidden)** | Watchlist database models and endpoints exist in backend, but frontend market card action buttons for "Watchlist" are unlinked or local-only. |
| **Realtime Market Stream** | `WS /api/transfer-market/listings/{id}/stream` | None | **0% Parity (Hidden)** | Backend supports WebSocket live price/bid updates; Flutter UI relies entirely on manual pull-to-refresh or polling. |

### B. Ownership & Portfolio Parity

| Feature / Domain | Backend Endpoint | Frontend Controller / Service | Parity Status | Gap / Discrepancy Analysis |
| :--- | :--- | :--- | :---: | :--- |
| **User Portfolio Summary** | `GET /api/portfolio`<br>`GET /api/portfolio/summary` | `GtexOwnershipExperience` | **95% Parity** | Renders total asset valuation, cash balance, active holdings, and P&L. |
| **Club Ownership Holdings** | `GET /api/portfolio/clubs` | `GtexClubOwnershipApi` / `GtexOwnershipExperience` | **85% Parity** | Renders owned club shares, board voting power, and dividend entitlement. Governance action execution is read-only in UI. |
| **Realized P&L Tracker** | `GET /api/portfolio/realized-pl` | `GteExchangeController` | **50% Parity** | Backend computes historical trade gains/losses; UI only displays net unrealized holding P&L. |
| **Trade Orders History** | `GET /api/orders` | `GtexWalletOverviewScreenV2` | **80% Parity** | Renders past order history in Wallet/Orders tab. Missing batch cancel and order modification. |

---

## 4. STATE MATRIX

The table below outlines how current Market and Ownership surfaces handle non-ideal UI states:

| Surface / Component | Loading State | Error State | Empty State | Visitor / Locked State |
| :--- | :--- | :--- | :--- | :--- |
| **Market Screen (`GtexPlayerMarketRedesignScreen`)** | Inline circular indicators or card skeleton loaders. | Banner card with retry button (`onRetry`). | Displays "No players matched your filter criteria" card with clear filters button. | Fully accessible in read-only visitor mode. Buy/Sell CTAs open Auth modal (`onOpenLogin`). |
| **Selected Player Panel** | Shimmer/Skeleton card layout for player statistics. | Error banner with reload action. | "Select a player from the market list to view detailed market depth." | Renders price and bio; action buttons display "Sign In to Trade". |
| **Holdings Desk (`GtexOwnershipExperience`)** | `GteStatePanel.loading` with custom pulse animation. | `GteStatePanel.error` with error string and retry CTA. | "No active player holdings in your portfolio" with "Browse Market" CTA button. | Renders visitor Mode banner ("Visitor mode shows layout, not live balances"). Balance masked. |
| **Movers Rail (`GtexMarketMoversRail`)** | Compact shimmer rows. | Hides rail or shows minor inline alert. | Collapses rail view gracefully. | Fully visible to visitors. |
| **Transfer Hub (Redirected)** | N/A (Redirects to `/market`). | N/A | N/A | N/A |

---

## 5. RESPONSIVE & LAYOUT GAPS

1. **Movers Rail Overlap on Tablet Portrait (768px – 1024px):**
   - `_moversRailMinPaneWidth` is set to `640px`. On medium tablets, three vertical mover lists (Gainers, Losers, Volume) take up 100% of vertical height before player cards are visible, forcing extensive scrolling.
2. **Selected Player Side Panel Clipping on Mobile (<600px):**
   - In narrow viewports, `GtexMarketSelectedPlayerPanel` converts to a bottom drawer or secondary tab. However, the order input form buttons ("Buy Shares", "Sell Shares") clip against device bottom safe areas when virtual keyboards appear.
3. **Master-Detail Split Sizing in `GtexPlayerMarketRedesignScreen`:**
   - Grid vs Detail split ratio is fixed at 60/40. On ultra-wide desktop monitors (>1600px), player cards become unnecessarily wide, leaving large empty whitespace inside card containers.
4. **Holdings Table / Squad View Responsive Mismatch:**
   - `GtexOwnershipExperience` displays holdings as compact `GtexPlayerCard` items on mobile, but switches to a dense table on desktop. The table lacks horizontal scroll indicators, causing column truncation on 1024px desktop windows.

---

## 6. UX & DESIGN SYSTEM GAPS

1. **Card Architecture Compliance:**
   - *Requirement:* All GTEX player representations must delegate to or extend `GtexPlayerCard` (`frontend/lib/ui_gtex/football/gtex_player_card.dart`).
   - *Status:* `GtexPlayerMarketRedesignScreen` and `GtexOwnershipExperience` comply with `GtexPlayerCard`. However, legacy surfaces (`GteMarketPlayersScreen`, `GtePortfolioScreen`) still instantiate raw custom `Container` cards with hardcoded `BoxDecoration`.
2. **Ambiguous Terminology (Market vs. Transfer vs. Cards):**
   - Users are presented with "Market" (`/market`), "Transfer Center" (`/market/transfers`), and "Player Cards" (`/player-cards`), but all three redirect to the exact same screen (`GtexPlayerMarketRedesignScreen`). This creates cognitive confusion regarding whether they are trading shares, acquiring contract rights, or opening collectible cards.
3. **Lack of Football Context in Ownership Views:**
   - Ownership items in `GtexOwnershipExperience` display share count and coin value, but lack upcoming match fixture badges, player injury/suspension status, or manager tactical fit indicators.
4. **Missing Watchlist & Saved Search UX:**
   - No bookmark or star icon exists on market cards to add players to a personal watchlist, despite backend schema support (`market_watchlist_entries`, `player_card_watchlists`).

---

## 7. REUSABLE COMPONENT OPPORTUNITIES

To align with the GTEX Design System (`ui_gtex`), the following unified components should be extracted/standardized during the P7-FE implementation:

1. **`GtexMarketHeaderBar`:**
   - Standardized top control bar containing global search, position filter chips, league/country dropdowns, and view toggle (Grid vs. List vs. Heatmap).
2. **`GtexOwnershipPositionCard`:**
   - Standardized holding wrapper wrapping `GtexPlayerCard` with ownership telemetry: shares held, average buy price, current market price, unrealized P&L badge, and matchday form indicator.
3. **`GtexTransferBidModal`:**
   - Reusable bottom sheet / modal dialog for placing contract bids, loan requests, or share purchase orders with live wallet balance checking and fee preview.
4. **`GtexWatchlistButton`:**
   - Universal star/bookmark toggle component bound to backend watchlist endpoints (`/api/player-cards/watchlist`).

---

## 8. PRODUCT HIERARCHY OPTIONS & SYNTHESIS RECOMMENDATION

The prompt requests exploring 3 future product hierarchies for GTEX Market + Ownership:

### Option A: MARKET FLOOR (Discovery & Opportunity First)
- **Concept:** Structure the surface as a high-frequency trading desk. The default view is the live market ticker, top movers, market cap leaders, and instant order books.
- **Pros:** Maximum liquidity visibility; appeals to financial traders and high-frequency coin exchange users.
- **Cons:** De-emphasizes football identity, squad context, and manager storytelling. Reads like a financial crypto broker.

### Option B: PORTFOLIO / OWNERSHIP (User's Football Assets & Identity First)
- **Concept:** Structure the surface around the user's club identity. Default view is "My Squad Holdings & Club Equity", highlighting owned players, performance yield, and governance rights, with market discovery as a secondary tab.
- **Pros:** Deep football identity; reinforces emotional connection to owned players and club prestige.
- **Cons:** Adds friction for users seeking fast market discovery or new trading opportunities.

### Option C: TRANSFER INTELLIGENCE (Movement, Bids, Value & Decision-Making First)
- **Concept:** Structure the surface as a Deadline Day Transfer Center. Default view highlights transfer news, contract expirations, scout recommendations, active bidding wars, and value fluctuation signals.
- **Pros:** Highly engaging football manager aesthetic; unifies player shares, contract transfers, and scout reports under a narrative headline.
- **Cons:** Requires robust real-time feed updates and active narrative generation.

---

### RECOMMENDED SYNTHESIS: "TRANSFER & CAPITAL DESK" COMPOSITE
Based on documented GTEX system behavior and backend capabilities, the recommended composition is a **Unified Transfer & Capital Desk Architecture**:

1. **Primary Navigation Entry (`/market` or `/app/market`):**
   A tabbed dual-mode interface with two canonical operational modes:
   - **Tab 1: Transfer Center (Discovery & Intelligence - Option C + Option A):**
     Integrates live player share catalog, top movers, scout watchlist, and active transfer listings. Allows filtering by liquid shares vs. formal club transfer contracts.
   - **Tab 2: Club Ownership & Holdings (Identity First - Option B):**
     Presents the user's backed players as a **Football Squad Holding Desk**, with performance yield, contract status, and club equity stakes.

2. **Resolution of Duplicate Routes & Product Boundaries:**
   - Propose consolidating `/market`, `/player-market`, `/market/transfers`, and `/football/transfer-center` under the unified market desk shell.
   - **Product Boundary Note (`/player-cards`):** `/player-cards` represents a distinct collectible/card product surface with its own underlying backend contracts (`app/player_cards`). Any future navigation unification involving `/player-cards` is a **hypothesis requiring product/route verification**, not an automatic consolidation rule. The market/ownership slice must preserve distinct business semantics and backend contracts even if navigation eventually unifies shell views.
   - Maintain route parameter deep-linking: `/market?tab=transfers`, `/market?tab=holdings`.

---

## 9. EXACT PROPOSED IMPLEMENTATION SCOPE (P7-FE MARKET & OWNERSHIP SLICE)

The next major GTEX P7-FE Market + Ownership implementation slice shall cover:

1. **Unified Market & Ownership Surface (`GtexMarketOwnershipDeskScreen`):**
   - Replace fragmented redirects in `app_router.dart` with a single canonical shell destination supporting tabbed navigation between **Transfer Hub (Market Floor + Intelligence)** and **Squad Holdings (Ownership Experience)**.
2. **Watchlist Integration:**
   - Wire backend endpoints `GET/POST/DELETE /player-cards/watchlist` to Flutter controllers and add bookmark/star state toggles on all `GtexPlayerCard` instances in market grid.
3. **Refactored Ownership Experience:**
   - Enhance `GtexOwnershipExperience` to render player holdings using full `GtexPlayerCard` widgets with matchday form chips, contract duration, and dividend yield indicators.
4. **Responsive & Drawer Optimization:**
   - Fix selected player order panel bottom clipping on mobile; implement responsive 2-column drawer for viewports under 768px.
5. **Clean Up Legacy Surfaces:**
   - Formally deprecate `GtePortfolioScreen` and standalone legacy transfer room redirects in favor of the new unified desk.

---

## 10. EXACT CODEX IMPLEMENTATION PROMPT

The following prompt can be provided directly to an automated coding agent (Codex) to execute the implementation slice:

```markdown
### CODEX TASK PROMPT: GTEX P7-FE MARKET + OWNERSHIP UNIFIED DESK IMPLEMENTATION

**Objective:**
Implement the P7-FE Market + Ownership Unified Desk slice in Flutter according to `docs/audits/gtex-market-ownership-jules-audit.md`.

**Scope of Changes:**
1. **Create Unified Market & Ownership Screen (`GtexMarketOwnershipDeskScreen`):**
   - Location: `frontend/lib/features/player_market_redesign/presentation/gtex_market_ownership_desk_screen.dart`
   - Implement a tabbed layout:
     - **Tab 0: Transfer Center & Market Floor** (incorporates existing `GtexPlayerMarketRedesignScreen` functionality, mover rail, filters, and player grid).
     - **Tab 1: My Squad Holdings & Club Equity** (incorporates `GtexOwnershipExperience` with `GtexPlayerCard` integration).
   - Support tab selection via route query parameter (`?tab=market` or `?tab=holdings`).

2. **Update Routing (`app_router.dart` & `gte_navigation_shell_screen.dart`):**
   - Bind `/market`, `/player-market`, `/market/transfers`, `/football/transfer-center`, and `/wallet/holdings` to `GtexMarketOwnershipDeskScreen` while preserving `/player-cards` as a distinct route surface backed by `app/player_cards`.
   - Ensure shell navigation rail updates route tab parameters cleanly without page reloads.

3. **Watchlist Capability Integration:**
   - Create `GtexWatchlistController` connecting to `GET/POST/DELETE /player-cards/watchlist`.
   - Add a watchlist star button on `GtexPlayerCard` overlay in market grid view.

4. **Responsive Fixes:**
   - Ensure selected player order panel on mobile converts into a bottom sheet that avoids virtual keyboard clipping.
   - Adjust Movers Rail width threshold to display as horizontal swipable cards on viewports < 768px.

5. **Quality Gate Verification:**
   - Run `flutter test` on modified package paths.
   - Ensure zero regressions in golden tests and design lab screens.

**Strict Constraints:**
- Do NOT edit backend code or database schemas.
- Do NOT edit Unity 3D match engine code (`Gtex_Test_Migration/`).
- All player cards MUST delegate to `GtexPlayerCard` (`frontend/lib/ui_gtex/football/gtex_player_card.dart`).
```

---

## 11. DEPENDENCIES ON EXISTING P7-FE WORK

1. **GTEX Design System (`ui_gtex` package):**
   - Relies on `GtexPlayerCard` (`frontend/lib/ui_gtex/football/gtex_player_card.dart`), `GtexMasterDetailScaffold`, and `GtexStatePanel`.
2. **Navigation Shell Engine (`gte_navigation_shell_screen.dart`):**
   - Relies on `GteNavigationRoute` routing parser and `GteExchangeController` state manager.
3. **Backend API Contracts (`app.market`, `app.portfolio`, `app.player_cards`):**
   - Relies on active endpoints verified on backend `main` (`/market/browse`, `/market/movers`, `/api/portfolio`, `/player-cards/watchlist`).

---
