# GTEX / Global Talent Exchange
## P7-FEV Browser Verification Readiness Report

**Repository:** `https://github.com/wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Date:** May 2026
**Status:** **BLOCKED BY P7-FE EXIT GATE** (P7-FEV Execution On Hold)

---

## 1. Executive Summary & Readiness Declaration

> **CRITICAL DIRECTIVE COMPLIANCE:**
> - **P7-FEV Status:** P7-FEV is currently **BLOCKED** by the P7-FE exit gate.
> - **GTEX_TASKS.md:** Has NOT been modified.
> - **P7-FEV Certification:** P7-FEV is **NOT** claimed to be ready for sign-off or completion.
> - **Product Scope:** No broad product implementation or code modifications were performed.
> - **Data Integrity:** No credentials, users, API responses, screenshots, or gameplay outcomes were manufactured or fabricated.

This audit evaluates the current browser-testing readiness and Playwright infrastructure for GTEX Phase 7 Frontend Verification (P7-FEV). The Playwright test harness located at `qa/playwright/` is fully operational for isolated visual regression tests (Design Lab) and structural route assertions, but live end-to-end browser verification of authenticated workflows remains **BLOCKED** until P7-FE certification is achieved and live backend seed accounts are provisioned in the verification environment.

---

## 2. Playwright Harness Infrastructure Audit

An inspection of `qa/playwright/` (`playwright.config.mjs`, `package.json`, `tests/p7_fe_slice_2.spec.mjs`, `tests/p7_fe_slice_4.spec.mjs`, `README.md`) yields the following technical assessment across six structural criteria:

### 2.1 Deterministic Setup
- **Status:** **PARTIALLY READY**
- **Capabilities:** The harness in `playwright.config.mjs` conditionally launches Flutter's local web server (`flutter run -d web-server --web-hostname 127.0.0.1 --web-port 7357`) when `GTEX_E2E_API_BASE_URL` is set, or points to a pre-hosted instance via `GTEX_E2E_BASE_URL`.
- **Gaps:** Account login relies on external environment variables (`GTEX_E2E_EMAIL`, `GTEX_E2E_PASSWORD`). Without an active seed database script running prior to execution, authed tests gracefully skip rather than failing non-deterministically.

### 2.2 Stable Selectors
- **Status:** **SPECIALIZED (FLUTTER WEB CANVAS)**
- **Capabilities:** Flutter Web builds render via a WebGL/Canvas glass pane (`flt-glass-pane`, `flutter-view`, `canvas`). Standard CSS text selectors work for accessible text and DOM input fields (e.g., login inputs, standard HTML forms), but Flutter-rendered canvas surfaces are verified using canvas visibility checks, semantic text matchers, and pixel/screenshot snapshot assertions.

### 2.3 Route Assertions
- **Status:** **READY**
- **Capabilities:** Route assertions test URL patterns (`expect(page).toHaveURL(...)`) and hash/path deep links (`/design-lab`, `/notifications`, `/lineup`, `/matches/viewer/:matchKey`). The router handles unauthenticated fallbacks to `/landing` or `/auth` gracefully.

### 2.4 Screenshot Capture
- **Status:** **READY**
- **Capabilities:** Automated full-page screenshot capturing is implemented in `capture(page, testInfo, name)`. Artifacts are saved per project viewport with test output pathing (`${name}-${project.name}.png`).

### 2.5 Failure Diagnostics
- **Status:** **READY**
- **Capabilities:** `collectBrowserDiagnostics` attaches console error streams and failed HTTP network request logs (`requestfailed`) as a `browser-diagnostics.json` attachment in Playwright test reports. Traces and videos are retained on test failures (`trace: 'retain-on-failure'`, `video: 'retain-on-failure'`).

### 2.6 Responsive Viewport Control
- **Status:** **READY**
- **Capabilities:** Configured across three distinct Playwright projects matching the required GTEX device matrix:
  - **Mobile:** Pixel 5 profile (`390x844`, `deviceScaleFactor: 2.75`)
  - **Tablet:** Custom profile (`768x1024`, `deviceScaleFactor: 1`)
  - **Desktop:** Custom profile (`1440x900`, `deviceScaleFactor: 1`)

### 2.7 Harness Alignment Observations
In accordance with P7-FEV constraints, zero product or test code modifications have been made in this PR. All findings regarding harness alignment, viewport layout nuances, or test assertions are documented herein strictly as observations to be addressed during P7-FE remediation or post-gate test suite execution.

---

## 3. Required Viewport Matrix

| Viewport Category | Resolution | Device Reference | Purpose / Layout Focus |
| :--- | :--- | :--- | :--- |
| **Mobile** | `390x844` | Pixel 5 / iOS standard | Single-column stack, bottom navigation rail/bar, responsive drawer overlays, scroll overflow safety. |
| **Tablet** | `768x1024` | iPad / Medium Tablet | Two-column responsive grid, expanded header metrics, adaptive pitch layout. |
| **Desktop** | `1440x900` | Standard Laptop / Monitor | Multi-column command desk, side navigation rail, persistent audio dock, wide data tables. |

---

## 4. Comprehensive 13-Surface Browser Verification Matrix

The status of each route is classified strictly using one of four canonical states:
1. **`ALREADY COVERED`**: Currently covered in the Playwright suite (`qa/playwright/tests/`).
2. **`READY TO VERIFY`**: Unauthenticated / public / design lab surface ready for immediate Playwright automation without credentials.
3. **`BLOCKED BY AUTH/DATA`**: Functionally ready in Flutter code, but requires live backend running and authenticated seed credentials (`GTEX_E2E_EMAIL`/`GTEX_E2E_PASSWORD`).
4. **`BLOCKED BY PRODUCT`**: Route or feature dependent on P7-FE completion or gated backend capabilities.

---

### Surface 1: Home / Command Center

- **Route:** `/app/home` (alias `/home`, `/`)
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes (Redirects to `/landing` or `/auth` if unauthenticated).
- **Test Data Required:** Seed user profile, active club profile, financial balances, active competition summary.
- **Backend Dependency:** Live backend `/api/v2/auth/me`, `/api/v2/clubs/me`, `/api/v2/wallet/balances`.
- **Expected State:** Hydrated command center displaying portfolio valuation, active match alerts, daily challenges, and navigation rail.
- **Primary Actions:** Tap quick action buttons, toggle balance visibility, navigate to Club, Market, or Wallet.
- **Expected Screenshot:** `home-command-center-{viewport}.png`
- **Mobile Verification (`390x844`):** Bottom navigation active, vertical stacking of quick action cards, summary metrics scrollable.
- **Desktop Verification (`1440x900`):** Left navigation rail pinned, 3-column desk layout with right-hand activity feed.
- **Known Blocker:** Unauthenticated requests redirect to Landing page; needs live backend auth token.

---

### Surface 2: Match Viewer

- **Route:** `/matches/viewer/:matchKey` (aliases `/match-viewer/:matchKey`, `/matches`)
- **Classification:** **`ALREADY COVERED`** (Structural check in `p7_fe_slice_2.spec.mjs`) / **`BLOCKED BY AUTH/DATA`** (Live match stream)
- **Authentication Required:** Yes (for authed match shell), No (for static offline/fallback state test).
- **Test Data Required:** Authoritative replay match key or active match fixture ID (e.g., `sim-match-101`).
- **Backend Dependency:** `/api/v2/matches/{match_id}/replay` or `/api/v2/matches/{match_id}/live`.
- **Expected State:** 2D canvas/pitch representation with scoreline banner, minute timer, match events ticker, and play/pause controls. (Never invents fake outcome if unavailable; surfaces truthful "No match available" state).
- **Primary Actions:** Toggle camera angle, play/pause replay playback, inspect match statistics.
- **Expected Screenshot:** `match-viewer-{viewport}.png`
- **Mobile Verification (`390x844`):** Pitch renders full-width, timeline controls stay touch-accessible at bottom, statistics fold into modal sheet.
- **Desktop Verification (`1440x900`):** Wide 16:9 pitch canvas with right-side live box score and commentary log.
- **Known Blocker:** Real match replay payload needed from engine; fake match playback is strictly prohibited.

---

### Surface 3: Lineup

- **Route:** `/lineup` (or `/app/club/lineup`)
- **Classification:** **`ALREADY COVERED`** (`p7_fe_slice_2.spec.mjs` verifies substitute overflow) / **`BLOCKED BY AUTH/DATA`** (Live editing)
- **Authentication Required:** Yes.
- **Test Data Required:** Active club with minimum 11 starting players and 7 substitutes in squad database.
- **Backend Dependency:** `/api/v2/clubs/{club_id}/squad` and squad tier management services.
- **Expected State:** Interactive tactical pitch with 11 player position cards, formation dropdown selector, and horizontal/vertical substitute bench.
- **Primary Actions:** Change formation dropdown, select substitute, tap starter to swap position.
- **Expected Screenshot:** `lineup-editor-{viewport}.png`
- **Mobile Verification (`390x844`):** Bench scroll overflow verified (`document.documentElement.scrollWidth <= window.innerWidth`).
- **Desktop Verification (`1440x900`):** Pitch on left, bench and detailed player attribute panel on right.
- **Known Blocker:** User must own a club with populated player squad.

---

### Surface 4: Notifications / Deep Links

- **Route:** `/notifications`
- **Classification:** **`ALREADY COVERED`** (`p7_fe_slice_2.spec.mjs` covers targeted & untargeted notifications)
- **Authentication Required:** Yes.
- **Test Data Required:** Seeded notification record with target metadata (`GTEX_E2E_NOTIFICATION_TEXT`, `GTEX_E2E_NOTIFICATION_TARGET`).
- **Backend Dependency:** `/api/v2/notifications`.
- **Expected State:** Notification list itemized by timestamp, read/unread indicators, filter tabs (All, Transfers, System, Matches).
- **Primary Actions:** Tap notification card, tap "OPEN" action button to trigger deep link navigation.
- **Expected Screenshot:** `notifications-{viewport}.png`
- **Mobile Verification (`390x844`):** Full-screen list, swipe-to-dismiss actions, deep link CTA button prominent.
- **Desktop Verification (`1440x900`):** Split view with notification feed on left and target preview details on right.
- **Known Blocker:** Requires pre-seeded notification in database to test deep link routing.

---

### Surface 5: Competition

- **Route:** `/app/competitions` (and `/design-lab/competitions`)
- **Classification:** **`ALREADY COVERED`** (`p7_fe_slice_4.spec.mjs` for Design Lab) / **`BLOCKED BY AUTH/DATA`** (Live Hub)
- **Authentication Required:** No for `/design-lab/competitions`, Yes for `/app/competitions`.
- **Test Data Required:** Active tournament, league table, fixture schedule.
- **Backend Dependency:** `/api/v2/competitions`, `/api/v2/competitions/{id}/standings`.
- **Expected State:** Tournament selection carousel, group tables, knockout brackets, prize pool ticker.
- **Primary Actions:** Filter competition categories (GTEX Official, User Hosted), view group standings, tap "Join Tournament".
- **Expected Screenshot:** `competition-hub-{viewport}.png`
- **Mobile Verification (`390x844`):** Tabbed navigation between Overview, Standings, and Fixtures.
- **Desktop Verification (`1440x900`):** Full bracket/table visualization with sidebar details.
- **Known Blocker:** Live tournament fixtures and backend competition orchestrator state required.

---

### Surface 6: Market

- **Route:** `/app/market` (aliases `/market`, `/player-market`, `/market/transfers`)
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes.
- **Test Data Required:** Active player share market listings, tradable regens, price history candles.
- **Backend Dependency:** `/api/v2/market/listings`, `/api/v2/market/orderbook`, `/api/v2/market/watchlist`.
- **Expected State:** Unified GTEX Market & Ownership Command Surface (Transfer Intelligence mode), order book depth chart, watchlist toggle, filter drawer.
- **Primary Actions:** Search player name, apply price filter, switch between Player Shares and Club Transfers, tap player card to open profile.
- **Expected Screenshot:** `market-command-desk-{viewport}.png`
- **Mobile Verification (`390x844`):** Compact search header, vertical player market cards, slide-over filter sheet.
- **Desktop Verification (`1440x900`):** Grid view of player market assets, live ticker bar, inline order book panel.
- **Known Blocker:** Requires populated player market order book in backend database.

---

### Surface 7: Ownership

- **Route:** `/app/ownership`
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes.
- **Test Data Required:** User portfolio holding records (`PlayerShareHolding`), share yield history, player valuation snapshots.
- **Backend Dependency:** `/api/v2/market/holdings`, `/api/v2/wallet/portfolio`.
- **Expected State:** Unified GTEX Market & Ownership Command Surface (My Ownership mode), showing portfolio equity value, dividend income, and `OwnershipConsequenceCard` widgets.
- **Primary Actions:** Toggle holding view mode, tap "Sell Shares", view holding return percentage.
- **Expected Screenshot:** `ownership-desk-{viewport}.png`
- **Mobile Verification (`390x844`):** Card-based portfolio list, summary equity card pinned to top.
- **Desktop Verification (`1440x900`):** High-density table view with performance charts and quick liquidation actions.
- **Known Blocker:** Requires user account with active share portfolio holdings.

---

### Surface 8: Club HQ

- **Route:** `/app/club` (alias `/club`)
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes.
- **Test Data Required:** User club entity, staff contracts, stadium facility levels, squad size metrics.
- **Backend Dependency:** `/api/v2/clubs/me`, `/api/v2/clubs/{id}/facilities`.
- **Expected State:** Club HQ Dashboard V2 featuring club badge, reputation tier, silverware shelf, staff contracts overview, and squad overview.
- **Primary Actions:** Navigate to Lineup, Academy, Facilities, or Financial Reports.
- **Expected Screenshot:** `club-hq-dashboard-{viewport}.png`
- **Mobile Verification (`390x844`):** Stacked dashboard sections, quick navigation grid.
- **Desktop Verification (`1440x900`):** Hero club header banner, 3-column facility & performance matrix.
- **Known Blocker:** Requires authenticated user linked to an active club profile.

---

### Surface 9: Player Profile

- **Route:** `/players/:playerId/profile`
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes (or public read access depending on environment setup).
- **Test Data Required:** Canonical `Player` record (e.g., standard or legendary regen ID) with full attributes, contract data, and market valuation history.
- **Backend Dependency:** `/api/v2/players/{player_id}`, `/api/v2/market/players/{player_id}/profile`.
- **Expected State:** GTEX FM Player Profile screen displaying radar attribute chart, career trajectory, contract status, market valuation, and `GtexProgressionBar`.
- **Primary Actions:** Switch attribute tabs (Technical, Tactical, Physical, Mental), tap "Buy Shares", add to Watchlist.
- **Expected Screenshot:** `player-profile-{viewport}.png`
- **Mobile Verification (`390x844`):** Scrollable single column, radar chart responsive resize, sticky bottom CTA bar ("Buy / Bid").
- **Desktop Verification (`1440x900`):** Split layout with left-hand bio card & radar chart, right-hand market trading panel and career history log.
- **Known Blocker:** Valid player ID must exist in database. Missing/unresolvable status defaults safely to `unknown_unavailable`.

---

### Surface 10: Academy

- **Route:** `/app/academy`
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes.
- **Test Data Required:** Club facility levels (`youth_recruitment`, `academy`), active youth prospects, promotion quota.
- **Backend Dependency:** `/api/v2/clubs/{id}/academy`, `/api/v2/clubs/{id}/prospects`.
- **Expected State:** Youth Academy facility view, prospect list with potential ratings, upgrade facility controls, and prospect promotion CTA.
- **Primary Actions:** Inspect prospect scout report, tap "Promote to Reserve Squad", trigger facility upgrade (Fan Coin settlement).
- **Expected Screenshot:** `academy-facility-{viewport}.png`
- **Mobile Verification (`390x844`):** Facility level indicator tile, prospect list with expandable detail cards.
- **Desktop Verification (`1440x900`):** Grid of academy prospects alongside facility economy upgrade progress bars.
- **Known Blocker:** Requires active club with AcademyFacilityEconomyService data in backend.

---

### Surface 11: Dynasty

- **Route:** `/app/dynasty` (and sub-routes `/world/dynasty`, `/club/dynasty`)
- **Classification:** **`BLOCKED BY AUTH/DATA`**
- **Authentication Required:** Yes.
- **Test Data Required:** Multi-season club historical records, trophy honors, manager tenure logs, prestige score.
- **Backend Dependency:** `/api/v2/clubs/{id}/dynasty`, `/api/v2/clubs/{id}/honors`.
- **Expected State:** Era history timeline, `GtexSilverwareShelf` displaying won trophies, dynasty prestige leaderboard.
- **Primary Actions:** Scroll timeline eras, toggle trophy filter, tap era milestone for detail modal.
- **Expected Screenshot:** `dynasty-overview-{viewport}.png`
- **Mobile Verification (`390x844`):** Vertical timeline view, horizontally scrollable trophy cabinet shelf.
- **Desktop Verification (`1440x900`):** Multi-column timeline layout with interactive trophy showcase gallery.
- **Known Blocker:** Requires club history and trophy records in backend.

---

### Surface 12: Design Lab

- **Route:** `/design-lab` (and `/design-lab/club-player-progression`, `/design-lab/competitions`)
- **Classification:** **`ALREADY COVERED`** (`p7_fe_slice_2.spec.mjs` & `p7_fe_slice_4.spec.mjs`) / **`READY TO VERIFY`**
- **Authentication Required:** **No** (Deliberately unlinked, isolated fixture screen).
- **Test Data Required:** None (Uses isolated in-memory test fixtures).
- **Backend Dependency:** **None** (100% client-side UI visual verification surface).
- **Expected State:** GTEX Design Lab screen rendering visual compositions across Matchday Pulse, Club Atlas, Ownership Ledger, Competition Boards, and Club/Player Identity primitives.
- **Primary Actions:** Switch direction dropdown (`?direction=matchday`, `?direction=club`, `?direction=ownership`, `?direction=atlas`), view UI component layouts.
- **Expected Screenshot:** `design-lab-matchday-pulse-desktop.png`, `design-lab-club-atlas-mobile.png`, `design-lab-ownership-ledger-tablet.png`
- **Mobile Verification (`390x844`):** Verifies responsive rendering of `GtexIdentityHeader`, `GtexProgressionBar`, `GtexOwnershipIndicatorTile`, and `GtexSilverwareShelf`.
- **Desktop Verification (`1440x900`):** Full multi-panel layout rendering at 1440x900 resolution without canvas pixel distortion.
- **Known Blocker:** None. Runnable today via `GTEX_E2E_DESIGN_LAB=1 npm test`.

---

### Surface 13: Audio Controls

- **Route:** Shell-wide / Persistent Audio Dock (accessible via header/settings on any shell route, e.g., `/app/home`)
- **Classification:** **`READY TO VERIFY`** (DOM / UI control state) / **`BLOCKED BY PRODUCT`** (Browser Autoplay Audio Context)
- **Authentication Required:** No (for static settings sheet), Yes (within authenticated shell).
- **Test Data Required:** `GtexSoundtrackCatalogue` asset manifest.
- **Backend Dependency:** Stem stream URL availability (CDN or static audio assets).
- **Expected State:** Persistent GTEX Audio dock or `GtexAudioSettingsSheet` overlay displaying 5-channel sliders (Master, Music, Commentary, Crowd, Effects), track metadata banner, and play/mute toggle.
- **Primary Actions:** Toggle mute button, adjust volume sliders, open soundtrack settings sheet.
- **Expected Screenshot:** `audio-controls-overlay-{viewport}.png`
- **Mobile Verification (`390x844`):** Audio settings modal sheet opens smoothly over current route, slider thumb controls touch-friendly.
- **Desktop Verification (`1440x900`):** Audio dock embedded in bottom navigation rail or header bar.
- **Known Blocker:** Automated browser audio context policies require user interaction before web audio playback initiates; Playwright can test UI control state and DOM events, but audio playback sound output verification requires manual browser context interaction.

---

## 5. Summary Surface Classification Matrix

| Surface ID | Surface / Feature | Primary Route | Verification Classification | Auth Required? | Backend Required? |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **1** | **Home / Command Center** | `/app/home` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **2** | **Match Viewer** | `/matches/viewer/:matchKey` | **`ALREADY COVERED`** / **`BLOCKED BY AUTH/DATA`** | Optional | Yes |
| **3** | **Lineup** | `/lineup` | **`ALREADY COVERED`** / **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **4** | **Notifications / Deep Links**| `/notifications` | **`ALREADY COVERED`** | Yes | Yes |
| **5** | **Competition** | `/app/competitions` | **`ALREADY COVERED`** (Design Lab) / **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **6** | **Market** | `/app/market` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **7** | **Ownership** | `/app/ownership` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **8** | **Club HQ** | `/app/club` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **9** | **Player Profile** | `/players/:playerId/profile` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **10** | **Academy** | `/app/academy` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **11** | **Dynasty** | `/app/dynasty` | **`BLOCKED BY AUTH/DATA`** | Yes | Yes |
| **12** | **Design Lab** | `/design-lab` | **`ALREADY COVERED`** / **`READY TO VERIFY`** | **No** | **No** |
| **13** | **Audio Controls** | Shell-wide / Settings Sheet | **`READY TO VERIFY`** (UI) / **`BLOCKED BY PRODUCT`** (Autoplay) | No | No |

---

## 6. Concrete Post-P7-FE Browser Verification Backlog

Once P7-FE exits its gate and active QA credentials/seed data are provisioned, execute the following minimal concrete browser-verification backlog:

1. **Test Seed Account Provisioning Script (`Task P7-FEV-1`)**
   - Execute database seeder script to create `seed.fan@gte.local` with an active club, squad lineup, player share holdings, notifications, and active competition entry.

2. **Authenticated Shell Baseline Spec (`Task P7-FEV-2`)**
   - Implement `qa/playwright/tests/p7_fe_authed_shell.spec.mjs`.
   - Automate login flow via `signIn(page)`.
   - Verify `/app/home`, `/app/club`, `/app/market`, `/app/ownership` across all 3 viewports (`390x844`, `768x1024`, `1440x900`).
   - Capture full-page visual regression baseline screenshots.

3. **Club & Squad Management Spec (`Task P7-FEV-3`)**
   - Implement `qa/playwright/tests/p7_fe_club_squad.spec.mjs`.
   - Verify `/lineup`, `/app/academy`, `/players/:playerId/profile`, `/app/dynasty`.
   - Assert zero horizontal scroll overflow on mobile (`390x844`) for substitute benches and facility progress indicators.

4. **Market Trading & Portfolio Spec (`Task P7-FEV-4`)**
   - Implement `qa/playwright/tests/p7_fe_market_portfolio.spec.mjs`.
   - Verify Market order book interaction, player watchlist toggle, and Portfolio equity card rendering.

5. **Competition & Live Matchday Spec (`Task P7-FEV-5`)**
   - Implement `qa/playwright/tests/p7_fe_competition_match.spec.mjs`.
   - Verify Competition Hub standings, tournament bracket rendering, and Match Viewer 2D pitch state.

6. **Audio Controls & Persistent Shell Spec (`Task P7-FEV-6`)**
   - Implement `qa/playwright/tests/p7_fe_audio_shell.spec.mjs`.
   - Verify `GtexAudioSettingsSheet` overlay opening, channel slider interaction, and persistent audio dock rendering across viewports.

---

*End of Report.*
