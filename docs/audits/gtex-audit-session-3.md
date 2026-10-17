# GTEX Forensic Audit — Session 3: Browser, Playwright, State, Responsive, and Visual UX

**Repository:** `https://github.com/wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Date:** May 2024
**Audit Method:** Read-Only Runtime Audit & Playwright Automated Visual Inspection
**Target Viewports:** Desktop (`1440x900`), Mobile (`390x844`)
**Runtime Engine:** FastAPI Backend (`127.0.0.1:8000`), Flutter Web Release (`127.0.0.1:3000`)

---

## Executive Summary

Session 3 evaluated the live runtime user experience of the GTEX application across **28 distinct routes** on desktop and mobile viewports using headless Chromium via Playwright. The audit inspected real rendered Flutter Web surfaces backed by a live Python/FastAPI backend and SQLite database.

GTEX features a strong dark-mode foundation with custom design system components (`GtexPlayerCard`, `GtexMasterDetailScaffold`, `GtexHeaderOverlay`, neon accenting). However, the audit revealed a significant rift between backend domain richness and frontend presentation:
1. **SaaS/Admin Dashboard Aesthetics:** Many major operational screens (Wallet, Trader Dashboard, KYC, Disputes, Federation, Regens) present dense tabular layouts and text-heavy metric cards typical of generic B2B administrative tools rather than an engaging football management or trading experience.
2. **Surface Gating & Fallback Density:** Gating layers (such as `LIVE GATE ACTIVE`, `ROUTE BLOCKED`, `Verifying shipped capability`) frequently overlay screens or stall without clear action pathways when state prerequisites (e.g., active club contract, live match session) are unfulfilled.
3. **Mobile Layout Constraints:** Complex master-detail views, 11-v-11 tactical pitches, and financial transaction history tables experience severe horizontal clipping and vertical overflow on standard mobile screens (`390px` width).
4. **Target Audience Expectation Gap:** Football gaming enthusiasts (accustomed to *Football Manager*, *EA Sports FC / FIFA*, or *eFootball*) will miss dynamic tactical pitch views, atmospheric club branding, broadcast-style match telemetry, prestige trophies, and instant visual feedback during marketplace/transfer transactions.

---

## 1. Runtime & System Setup Findings

* **Backend API & Data Engine:** Running on `http://127.0.0.1:8000`. Full OpenAPI schema and SQLite persistence active. All major API endpoints (`/api/v2/auth`, `/api/v2/clubs`, `/api/v2/transfer-market`, `/api/v2/wallets`, `/api/v2/regen-universe`) responding correctly.
* **Frontend Web Runtime:** Flutter Web compiled in release mode and served on `http://127.0.0.1:3000`. High canvas stability and smooth route transitions across main shell navigation.
* **Auth & Session Persistence:** Token-based authentication correctly hydrates user state across reloads. Role-based fallback handling routes unauthenticated or unauthorized users to dedicated fallback views (`/fallback/route_blocked`).

---

## 2. Browser & Workflow Audit Findings

| Workflow Area | Inspected Routes | Primary Observation | Key UX Deficit |
| :--- | :--- | :--- | :--- |
| **Authentication** | `/login`, `/signup`, `/kyc` | Dark themed, clean input fields, clear validation states. | Signup requires role selection without explaining differences (e.g. User vs Club Manager). |
| **Dashboard / Home** | `/dashboard`, `/home` | Summarizes club metrics, quick links, active matches. | Text-heavy metric cards dominate; lacks visual match summaries or player highlights. |
| **Marketplace & Cards** | `/market`, `/player/1` | Unified `GtexPlayerCard` rendered with live stats and prices. | Market search filters are buried in collapsed drawers; filter chips lack active counts. |
| **Club & Lineups** | `/club`, `/lineup` | Interactive tactical pitch view with formation switcher. | Pitch scaling clips squad reserves on mobile; substitute bench overflows off-screen. |
| **Competitions & Matches**| `/competitions`, `/matches`, `/match_viewer` | Scheduled fixtures and tournament brackets. | 2D Match Viewer hangs on `Verifying shipped capability` loading gate without fallback simulation. |
| **Finance & Trading** | `/wallet`, `/trader_dashboard`, `/coin_traders` | Balance breakdowns, ledger postings, P2P order books. | Reads like an accounting spreadsheet; lacks visual currency badges and interactive chart controls. |
| **Social & Identity** | `/community`, `/viral`, `/federations`, `/awards` | User rankings, referral trees, federation listings. | Award trophies are displayed as plain list items without 3D badge rendering or prestige highlights. |
| **Governance & Admin** | `/profile`, `/notifications`, `/disputes`, `/admin` | Account settings, audit logs, dispute tickets. | Notification feed lacks direct deep-links to affected entities (e.g., bid accepted notification doesn't link to player profile). |

---

## 3. Screenshot Inventory & Visual Artifact Register

A total of **56 visual artifacts** (28 desktop + 28 mobile) were generated during the audit session and archived to `/tmp/gtex_audit_screenshots/`:

1. `landing_desktop.png` / `landing_mobile.png` — Hero landing page, value proposition, registration CTA.
2. `login_desktop.png` / `login_mobile.png` — Credentials auth form with dark theme cards.
3. `signup_desktop.png` / `signup_mobile.png` — Multi-step registration workflow.
4. `dashboard_desktop.png` / `dashboard_mobile.png` — Overview dashboard with club status and metrics.
5. `market_desktop.png` / `market_mobile.png` — Player market with filter drawers and player cards.
6. `player_profile_desktop.png` / `player_profile_mobile.png` — Comprehensive player statistics and valuation history.
7. `club_desktop.png` / `club_mobile.png` — Club profile, squad roster, and facility indicators.
8. `lineup_desktop.png` / `lineup_mobile.png` — 11-v-11 tactical pitch editor and bench management.
9. `competitions_desktop.png` / `competitions_mobile.png` — Active leagues, tournament trees, and entry gates.
10. `national_team_desktop.png` / `national_team_mobile.png` — Single-nationality national squad management.
11. `matches_desktop.png` / `matches_mobile.png` — Fixture calendar, live scores, and matchday center.
12. `match_viewer_desktop.png` / `match_viewer_mobile.png` — 2D Match engine viewer and tactical replay screen.
13. `wallet_desktop.png` / `wallet_mobile.png` — Fan Coin balances, ledger entries, and deposit/withdraw actions.
14. `coin_traders_desktop.png` / `coin_traders_mobile.png` — P2P coin exchange listings and seller trust scores.
15. `trader_dashboard_desktop.png` / `trader_dashboard_mobile.png` — Active trade orders, spread analytics, and liquidity.
16. `community_desktop.png` / `community_mobile.png` — Social leaderboard, squad sharing, and fan feeds.
17. `viral_desktop.png` / `viral_mobile.png` — Referral bonus trees, share links, and viral reward track.
18. `regens_desktop.png` / `regens_mobile.png` — Youth academy regen pipeline and generation settings.
19. `federations_desktop.png` / `federations_mobile.png` — Global football federations and regional hubs.
20. `awards_desktop.png` / `awards_mobile.png` — Seasonal honors, trophy cabinet, and manager accolades.
21. `profile_desktop.png` / `profile_mobile.png` — User account settings, personal manager profile, security.
22. `kyc_desktop.png` / `kyc_mobile.png` — Verification status, document upload forms.
23. `notifications_desktop.png` / `notifications_mobile.png` — System alerts, trade notices, match reminders.
24. `disputes_desktop.png` / `disputes_mobile.png` — Dispute ticket submission and tribunal status.
25. `admin_desktop.png` / `admin_mobile.png` — Platform administration and economic override controls.
26. `fallback_route_blocked_desktop.png` / `fallback_route_blocked_mobile.png` — Permission/gating block screen.
27. `fallback_not_found_desktop.png` / `fallback_not_found_mobile.png` — 404 Route handling.
28. `fallback_server_error_desktop.png` / `fallback_server_error_mobile.png` — 500 Server error handling screen.

---

## 4. Evaluation Across 20 UX Dimensions

1. **Visual Hierarchy:** Secondary and tertiary metadata (e.g. DB IDs, internal status flags) carry identical typographic weight to primary stats (OVR rating, market price).
2. **Discoverability:** High-value actions like "Promote Prospect", "Appoint Personal Manager", and "Settle Reward" are nested inside multi-tab detail views without home-screen shortcuts.
3. **Primary Actions:** Primary buttons generally use bright neon green (`#A3FF12`), providing clear focus, though some cards contain up to 3 identical neon CTAs.
4. **Secondary Actions:** Secondary buttons lack contrast against the dark background, often appearing disabled when they are active.
5. **Buttons:** Touch targets on desktop are well-sized, but on mobile, icon-only buttons fall below the 44x44px accessibility threshold.
6. **Links:** Inline text links rely on subtle underline effects that blend into body copy.
7. **Tabs:** Horizontal scroll tabs on mobile lack visual fade cues, hiding off-screen tabs.
8. **Filters:** Market filters collapse completely into a modal; active filter pill counts are not shown on the trigger button.
9. **Search:** Global search is absent; user must navigate to specific domain screens to filter data.
10. **Modals:** Modal dialogs on mobile take up 95% screen height but lack clear sticky footers for submission.
11. **Drawers:** Navigation drawer overlays content without dimming the background sufficiently on tablet viewports.
12. **Forms:** Form validation is responsive, but input fields lack contextual inline hints (e.g., explaining Fan Coin decimal limits).
13. **Feedback:** Action feedback uses transient snackbars that dismiss too quickly (2 seconds) before users can read transaction IDs.
14. **Loading States:** Heavy use of generic circular progress spinners rather than pulse/shimmer skeletons styled like football trading cards.
15. **Empty States:** Empty states present plain text ("No items found") without illustrative graphics or quick call-to-actions to seed data.
16. **Error States:** Server error fallback cards display unformatted backend trace strings or generic error codes without recovery buttons.
17. **Success States:** Successful transfer bid or contract signing lacks celebratory animation or trophy splash effect.
18. **Disabled States:** Disabled buttons use low-opacity gray text that fails WCAG AA contrast standards.
19. **Permission States:** Blocked/gated routes display prominent technical badges (`LIVE GATE ACTIVE`) that confuse standard users expecting clean paywall or lock icons.
20. **Responsive Behaviour:** Layout switching occurs smoothly at `768px` breakpoint, but tactical pitch and financial data tables collapse on mobile.

---

## 5. Visual & UX Findings Register (P0 – P4)

### P0 — Severe Usability / Correctness Problems
* **P0-01: 2D Match Viewer Loading Stalls on Verification Gate**
  * **Location:** `/match_viewer` (`match_viewer_desktop.png`)
  * **Description:** Accessing the match viewer screen causes the application to hang perpetually on `Verifying shipped capability` / `Loading route` without timeout handling or fallback replay controls.
  * **Evidence:** Playwright crawler captured loading ring staying active indefinitely.

* **P0-02: Tactical Pitch Reserve Bench Overflow on Mobile**
  * **Location:** `/lineup` (`lineup_mobile.png`)
  * **Description:** On a 390px mobile viewport, rendering 11 starter cards and substitute players on the tactical pitch causes horizontal clipping and renders bench players inaccessible without horizontal scroll gestures that conflict with drag-and-drop.
  * **Evidence:** Mobile screenshot shows sub bench cut off on right screen boundary.

---

### P1 — Major Workflow Problems
* **P1-01: Technical Gate Overlay Blocks Non-Club Users Without Direct Onboarding Pathway**
  * **Location:** `/lineup`, `/club` (`lineup_mobile.png`)
  * **Description:** When a user without an active club profile navigates to squad lineup, a full-screen `ROUTE BLOCKED / LIVE GATE ACTIVE` modal appears. The CTA "Back to GTEX" returns to home rather than offering a direct "Create / Claim Club" onboarding button.
  * **Evidence:** Overlay text explicitly reads "No club yet... ROUTE BLOCKED".

* **P1-02: Notifications Feed Lacks Deep-Linking to Related Domain Entities**
  * **Location:** `/notifications` (`notifications_desktop.png`)
  * **Description:** System notifications (e.g., bid acceptances, dividend payouts) display as static text cards. Tapping a notification does not navigate the user to the relevant Player Profile, Wallet Ledger, or Match Summary.
  * **Evidence:** Notification item cards contain no interactive ink wells or navigation handlers.

---

### P2 — Important UX Problems
* **P2-01: Market Filter State Invisible When Filter Drawer is Closed**
  * **Location:** `/market` (`market_desktop.png`)
  * **Description:** Applying country, position, or valuation filters alters the card grid, but the filter button on the main toolbar shows no badge or active filter count when closed.
  * **Evidence:** Toolbar filter button reads "Filter" without active badge indicators.

* **P2-02: Wallet Transaction Ledger Resembles Generic Financial Spreadsheet**
  * **Location:** `/wallet` (`wallet_desktop.png`)
  * **Description:** Ledger entries are displayed in dense monospace tables with internal source tags (`PLAYER_CARD_PURCHASE`, `FACILITY_UPGRADE_SPEND`). The interface lacks icon-coded transaction categories or color-coded credit/debit indicators.
  * **Evidence:** Plain tabular layout showing raw enum strings.

---

### P3 — Visual & Design-System Problems
* **P3-01: Generic SaaS Metric Card Aesthetics**
  * **Location:** `/dashboard`, `/trader_dashboard`, `/federations` (`dashboard_desktop.png`)
  * **Description:** Key metrics (e.g., Club Value, Win Rate, Coin Balance) are displayed in grey rectangular boxes with subtle borders, visually identical to B2B SaaS analytics dashboards (e.g. Stripe/Datadog) rather than an immersive sports gaming experience.
  * **Evidence:** Screen composed of uniform grey boxes with minimal color accenting.

* **P3-02: Awards Screen Uses Plain Text Lists for Trophies and Honors**
  * **Location:** `/awards` (`awards_desktop.png`)
  * **Description:** Major achievements and seasonal trophies are presented as text list items without trophy badges, metallic accents, or showcase cards.
  * **Evidence:** `awards_desktop.png` shows simple bulleted rows for competition honors.

---

### P4 — Polish Opportunities
* **P4-01: Action Feedback Lacks Celebratory Visual Polish**
  * **Location:** Market & Club Purchase Workflows
  * **Description:** Purchasing a player card or signing a contract triggers a standard bottom snackbar instead of an animated card reveal or confetti particle overlay.
  * **Evidence:** Standard Flutter `SnackBar` popup observed on state changes.

* **P4-02: Absence of Live Audio/Visual Soundscapes or Crowd Ambience Elements**
  * **Location:** Match Center & Tactical Pitch
  * **Description:** Match simulation and tactical screens lack stadium background visual textures or toggleable match audio indicators.

---

## 6. Expected Features GTEX Users May Struggle to Find

Football gaming users (familiar with *Football Manager*, *EA Sports FC*, *PES*) will typically expect the following features, which are currently obscured, buried, or missing from the frontend:

1. **Instant Tactical Formation Pitch Toggle:** Users expect to drag-and-drop players directly on a visual pitch view on the main Club screen without entering a separate sub-route.
2. **Player Scouting & Comparison View:** Users expect a side-by-side player stat comparison tool on the Transfer Market.
3. **Live Match Visual Radar / 2D Pitch Representation:** Users expect a live 2D pitch dot-radar showing ball movement during live match simulation.
4. **Trophy Cabinet & Prestige Room:** Users expect a visual 3D trophy room showcasing historical titles, manager awards, and legendary badges.
5. **Interactive Price Trend Charts:** On the Player Detail and Market pages, users expect interactive candlestick or line charts showing historical card price movements over 7d/30d/1y intervals.
6. **Quick Squad Lineup Quick-Actions:** Ability to auto-select "Best XI" or "Rotate Squad" with a single tap.

---

## 7. Highest-Priority Visual & UX Opportunities

To transition GTEX from a functional backend platform into an irresistible football exchange & management product, the following visual opportunities should be prioritized:

1. **Transform `GtexPlayerCard` into an Iconic Collectible Surface:**
   Incorporate dynamic foil textures, metallic borders for legendary players, animated shine effects on hover, and clear rarity tiering (Standard, Gold, Legend, Regen).
2. **Revamp Tactical Lineup Screen into an Interactive Pitch Hub:**
   Replace flat card lists on the lineup builder with a high-fidelity grass pitch canvas supporting fluid drag-and-drop, position chemistry indicators, and instant bench swapping.
3. **Replace Generic SaaS Cards with Gamified Football Widgets:**
   Redesign dashboard metric cards into "Matchday Hub" widgets featuring club crests, stadium backdrops, live ticker feeds, and visual coin stacks.
4. **Elevate Reward & Competition Presentation:**
   Introduce glowing trophy badges, podium animations for tournament winners, and animated reward unboxing screens when opening player packs or settling rewards.
5. **Streamline Mobile Navigation & Responsive Table Layouts:**
   Convert wide data tables on mobile into mobile-optimized stacked cards with collapsible detail sections.

---

## Conclusion & Next Steps

GTEX possesses a highly sophisticated backend infrastructure spanning complex transfer mechanics, regen universe lifecycles, ledger-backed wallets, and national team eligibility rules. However, the current frontend experience conceals much of this domain richness behind SaaS-like administrative screens and rigid gating overlays. By implementing the visual and UX recommendations outlined in this audit, GTEX can deliver a distinctive, gamified, and prestigious user experience tailored to sports fans and crypto-native football traders alike.
