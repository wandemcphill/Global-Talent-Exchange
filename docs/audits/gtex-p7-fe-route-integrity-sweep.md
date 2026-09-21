# GTEX P7-FE Route + Dead-Control Integrity Sweep Audit Report

**Repository:** `wandemcphill/Global-Talent-Exchange`
**Branch:** `main`
**Audit Context:** Session P7-FE — Focused Read-Only Engineering Route & Control Integrity Sweep
**Author:** Jules (Software Engineer)
**Date:** September 2026

---

## Executive Summary & Scope

This engineering audit provides a focused, read-only verification sweep of all recently completed **P7-FE routes and actions** across the GTEX Flutter frontend and FastAPI backend (`main` branch, incorporating changes from PRs #216 through #223).

### Strict Operating Principles
- **Read-Only Verification:** No production behavior or application code was modified during this sweep.
- **Zero Hallucinated Features:** No unbacked product capabilities or fake gameplay outcomes are introduced.
- **Architectural Scope Boundaries:** Unity 3D match rendering pipelines (`GtexMatch3D/`), database schemas, and task tracking files (`GTEX_TASKS.md`) remain untouched.

---

## 1. Reviewed Functional Areas & Route Inventory

The sweep evaluated 13 core functional areas across 35 user-facing screens and 54 distinct navigation/action controls:

1. **Home / Command Center:** `/`, `/home`, `/app`
2. **Match Viewer:** `/matches`, `/matches/viewer/:matchKey`
3. **Lineup:** `/lineup`
4. **Notifications:** `/notifications`
5. **Competition / Matchday:** `/competitions`, `/competitions/create`, `/streamer-tournaments`
6. **Market:** `/market`, `/player-market`, `/market/transfers`
7. **Ownership:** `/app/market?mode=ownership`
8. **Club HQ:** `/club`, `/clubs/:clubId`
9. **Player Profile:** `/players/:playerId/profile` (Canonical)
10. **Academy:** Tab in `/club`, `/regens`, `/regens/create-son`
11. **Dynasty:** `/dynasty`, `/dynasty/history`, `/dynasty/leaderboard`
12. **Trophy surfaces:** `/trophies`, `/trophies/timeline`, `/trophies/leaderboard`
13. **Design Lab routes:** `/design-lab`, `/design-lab/club-player-progression`, `/design-lab/competitions`, `/design-lab/market-ownership`

---

## 2. Status Summary Matrix

| Area | Evaluated Routes / Actions | Primary Screen File | Active Controller / Service | Status | Key Finding Summary |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **1. Home / Command Center** | Persona quick actions, world pulse, digest panels | `HomeScreen` | `GtexHomeDigestProvider`, `GteExchangeController` | **FAIL** | `/app/portfolio` CTA in profile/match panels degrades to Home because route parser lacks `'portfolio'` segment mapping. |
| **2. Match Viewer** | 2D match viewer, timeline qualification, spectate join | `MatchViewerRouteScreen` | `liveMatchViewerQualifiedRouteProvider`, `ApiLiveMatchViewerRepository` | **PASS** | 12s timeout boundary; production mode gracefully blocks on error without fabricating mock gameplay frames. |
| **3. Lineup** | Formation picker, slot tap-to-assign, auto-fill, save | `GtexLineupEditorScreen` | `ClubLineupRepository` | **PASS** | Fully wired to `GET /api/market/clubs/{id}/players` and `PUT /api/clubs/{id}/lineup`. Responsive substitute grid. |
| **4. Notifications** | Filter chips, mark read, mark all read, deep link open | `GteNotificationsScreenV2` | `GtexEngagementController`, `GteExchangeController.api` | **PASS** | `GtexNotificationNavigation` checks Launch Control gates before navigating to target routes. |
| **5. Competition / Matchday** | Discovery list, create competition, join competition | `GteCompetitionsHubScreenV2`, `GtexCompetitionCreateScreenV2` | `CompetitionController` | **PASS** | Fully wired to `GET /api/competitions/discovery` and `POST /api/competitions`. Enforces reserved name check. |
| **6. Market** | Player search, category chips, trade modal, detail open | `GteMarketPlayersScreenV2` | `GteExchangeController` | **PASS** | Fully wired to `GET /api/v2/market/snapshot` and share order endpoints. |
| **7. Ownership** | Holdings summary, unrealized P/L, watchlist telemetry | `GtexMarketOwnershipDeskScreen` | `GteExchangeController.portfolio`, `GtexWatchlistController` | **PASS** | Fully wired to `GET /api/portfolio` and `GET /api/watchlist/players`. |
| **8. Club HQ** | Squad tiers, tactics, academy level, trophy shelf | `GtexClubOwnerDashboardV2` | `GtexClubWorkspaceController` | **PASS** | Fully wired to `GET /api/clubs/{id}/v2-snapshot`. Renders reserve & first team squad slots. |
| **9. Player Profile** | Radar chart, career history, market valuation, form | `GtexFmPlayerProfileScreen` | `GtexFmPlayerProfileController` | **FAIL** | "Open Portfolio" CTA calls `context.go('/app/portfolio')`, which degrades to Home due to route parser gap. |
| **10. Academy** | Regen rankings, Create-a-Son flow, reserve assignment | `RegensScreenV2`, `RequestSonScreenV2` | `RegensController`, `RegenCreationService` | **PASS** | Base cost sourced from `regen_generation.toml`. Mints son to reserve squad tier (`tier="reserve"`). |
| **11. Dynasty** | Overview score, era history timeline, leaderboard | `DynastyScreen`, `EraHistoryScreen`, `DynastyLeaderboardScreen` | `DynastyController`, `DynastyApiRepository` | **PASS** | Registered in `GteAppRouteRegistry`. Fully wired to `/dynasty` endpoints. |
| **12. Trophy Surfaces** | Cabinet grid, honors timeline, trophy leaderboard | `TrophyCabinetScreen`, `HonorsTimelineScreen`, `TrophyLeaderboardScreen` | `TrophyCabinetRepository` | **PASS** | Registered in `GteAppRouteRegistry`. Fully wired to `/trophy-cabinet` and `/trophies/leaderboard`. |
| **13. Design Lab Routes** | Isolated visual composition testbeds | `GtexDesignLabScreen`, `GtexMarketOwnershipDesignLabScreen` | Static Fixture Containers | **FAIL** | `/design-lab/market-ownership` route definition is missing from `app_router.dart`. |

---

## 3. Detailed Control-to-Backend End-to-End Traces

### 3.1 Area 1: Home / Command Center
- **UI Control:** `_QuickActionsPanel` -> Role Action Button (e.g. "Watch matchday", "Sign players", "Admin controls").
- **Flutter Navigation:** `context.go(action.location)` or `context.push(action.location)`.
- **Controller/Service:** `GtexHomeDigestProvider` (`gtex_home_digest_provider.dart`), `GteExchangeController`.
- **API Contract:** `GET /api/v2/home/digest`, `GET /api/v2/world/aggregate`, `GET /api/v2/market/snapshot`.
- **Backend Endpoint:** `backend/app/routers/home_digest.py` (`get_home_digest`).
- **Expected Success State:** Returns `GtexHomeDigest` containing `your_players`, `what_moved`, `your_clubs`, `your_prospects`, `attention_items`, and `recent_activity`.
- **Expected Error State:** Falls back safely to empty lists per section without taking down adjacent home panels.

### 3.2 Area 2: Match Viewer
- **UI Control:** Fixture tile in Matchday desk or post-match panel -> "Open 2D Match Viewer".
- **Flutter Navigation:** `context.go('/matches/viewer/$matchKey')`.
- **Controller/Service:** `liveMatchViewerQualifiedRouteProvider` -> `ApiLiveMatchViewerRepository`.
- **API Contract:** `GET /api/match-viewer/$matchKey`, `GET /api/match-viewer/$matchKey/session`.
- **Backend Endpoint:** `backend/app/match_viewer/router.py`.
- **Expected Success State:** Returns `LiveMatchViewerBootstrap` and `MatchViewState` with verified frame timecodes. `GtexMatchViewerScreen` renders animated 2D pitch.
- **Expected Error State:** Production mode (`live`) triggers 12-second timeout boundary or handles missing match error via `MatchRouteBlockedScreen` with retry callback ("Try again") or "Open matchday" redirect. No fabricated gameplay outcomes are generated.

### 3.3 Area 3: Lineup
- **UI Control:** "Set lineup" button in Club HQ or Home quick actions -> Lineup Editor.
- **Flutter Navigation:** `context.push('/lineup')`.
- **Controller/Service:** `GtexLineupEditorScreen` -> `ClubLineupRepository`.
- **API Contract:** `GET /api/market/clubs/{clubId}/players`, `GET /api/clubs/{clubId}/lineup`, `PUT /api/clubs/{clubId}/lineup`.
- **Backend Endpoint:** `backend/app/lineups/router.py` (`get_club_lineup`, `update_club_lineup`).
- **Expected Success State:** Loads squad list, renders 11 starter slot tiles with role tags (`GK`, `DEF`, `MID`, `FWD`), substitute grid. Saving invokes `PUT` and displays `SnackBar("Lineup saved")`.
- **Expected Error State:** Displays `_ErrorState` with "Could not load your squad and lineup." and a "Retry" button.

### 3.4 Area 4: Notifications
- **UI Control:** Shell header notification bell -> Notification list item -> "Open linked item".
- **Flutter Navigation:** `context.go(target.route)`.
- **Controller/Service:** `GteNotificationsScreenV2` -> `GteExchangeController.api.listNotifications()` -> `GtexNotificationNavigation.resolve()`.
- **API Contract:** `GET /api/notifications`, `POST /api/notifications/read-all`, `POST /api/notifications/{id}/read`.
- **Backend Endpoint:** `backend/app/routers/notifications.py`.
- **Expected Success State:** Notification list displays categorized alerts (`transfers`, `matches`, `market`, `traders`, `club`, `wallet`, `kyc`, `dispute`). Clicking "Open linked item" evaluates `GtexLaunchControlFeatureGate` and navigates to the target route.
- **Expected Error State:** Renders `GtexEmptyState` with error message and "Retry" callback.

### 3.5 Area 5: Competition / Matchday
- **UI Control:** Arena tab -> "Create Competition" button -> Competition Form -> Submit.
- **Flutter Navigation:** `context.push('/competitions/create')`.
- **Controller/Service:** `CompetitionController` (`competition_controller.dart`) -> `CompetitionApi`.
- **API Contract:** `GET /api/competitions/discovery`, `POST /api/competitions`.
- **Backend Endpoint:** `backend/app/competitions/router.py`.
- **Expected Success State:** Validates fields, posts new competition payload. HTTP 201 Created returns `CompetitionSummary` and redirects user to the created competition workspace.
- **Expected Error State:** Validation failures (e.g. attempting to create a user-hosted competition with "gtex" in the name) return HTTP 400 Bad Request with error reason `reserved_gtex_name`, rendered as an in-form error banner.

### 3.6 Area 6: Market & Area 7: Ownership
- **UI Control:** Mode Toggle Chip ("Transfer Hub" vs "My Ownership") -> Search / Filter -> Player card -> "Buy Shares" / "Watchlist".
- **Flutter Navigation:** `context.go('/app/market?mode=ownership')` or `context.push('/players/:id/profile')`.
- **Controller/Service:** `GteMarketPlayersScreenV2` / `GtexMarketOwnershipDeskScreen` -> `GteExchangeController`.
- **API Contract:** `GET /api/v2/market/snapshot`, `GET /api/portfolio`, `GET /api/watchlist/players`.
- **Backend Endpoint:** `backend/app/routers/market_v2.py`, `backend/app/wallets/router.py`.
- **Expected Success State:** Renders market player grid with live share prices, 24h change, and volume. Ownership mode renders `GtexOwnershipTelemetryCard` with holdings quantity, market value, unrealized P/L, and watchlist items.
- **Expected Error State:** Network errors display `GteStatePanel` with "Retry" action.

### 3.7 Area 8: Club HQ
- **UI Control:** Primary Navigation "Club" -> Club HQ Workspace -> Tab switching (Squad, Lineup, Academy, Identity, Silverware).
- **Flutter Navigation:** `context.go('/app/club')`.
- **Controller/Service:** `GtexClubOwnerDashboardV2` -> `GtexClubWorkspaceController`.
- **API Contract:** `GET /api/clubs/{club_id}/v2-snapshot`.
- **Backend Endpoint:** `backend/app/routers/clubs_v2.py`.
- **Expected Success State:** Returns `ClubV2SnapshotResponse` containing club profile, squad tiers (`first_team`, `reserve`), active formation, academy investment level, prestige score, and trophy cabinet summary.
- **Expected Error State:** Displays `GtexEmptyState` for unowned club or `GteStatePanel` for server error.

### 3.8 Area 9: Player Profile
- **UI Control:** Any player tile across lineup, market, or squad -> Tap.
- **Flutter Navigation:** `GtexPlayerNavigator.tapToOpen(context, playerId)` -> `context.push('/players/:playerId/profile')`.
- **Controller/Service:** `GtexFmPlayerProfileScreen` -> `GtexFmPlayerProfileController`.
- **API Contract:** `GET /api/players/{playerId}/summary`, `GET /api/players/{playerId}/career`, `GET /api/players/{playerId}/overview`.
- **Backend Endpoint:** `backend/app/routers/players.py`.
- **Expected Success State:** Renders canonical FM player profile with radar chart (Pace, Shooting, Passing, Dribbling, Defense, Physical), market valuation ticker, career log, contract status, and ownership consequence card.
- **Expected Error State:** Returns HTTP 404 if player ID does not exist; screen displays `GtexEmptyState` with "Browse market" CTA.

### 3.9 Area 10: Academy
- **UI Control:** Regen Universe Hub / Club HQ Academy Tab -> "Build-a-Son" CTA -> Submit Son Draft.
- **Flutter Navigation:** `context.push('/regens/create-son')`.
- **Controller/Service:** `RequestSonScreenV2` -> `RegenCreationService`.
- **API Contract:** `GET /regen-universe/rankings`, `POST /api/regen-universe/sons/request`.
- **Backend Endpoint:** `backend/app/routers/regen_universe.py`.
- **Expected Success State:** Deducts Fan Coin per `regen_generation.toml` pricing config, generates custom son attributes, persists regen profile, and automatically assigns son to requesting club's reserve squad tier (`tier="reserve"`, `source="son"`).
- **Expected Error State:** Insufficient wallet balance returns HTTP 402 Payment Required; rendered as "Insufficient Fan Coins" dialog with "Top up wallet" CTA.

### 3.10 Area 11: Dynasty & Area 12: Trophy Surfaces
- **UI Control:** Club HQ Dynasty / Silverware Card -> "View Era History" / "Trophy Cabinet" / "Global Leaderboard".
- **Flutter Navigation:** `GteNavigationHelpers.pushRoute` -> `ClubDynastyHistoryRouteData`, `ClubTrophyCabinetRouteData`, `ClubTrophyLeaderboardRouteData`.
- **Controller/Service:** `DynastyController`, `TrophyCabinetRepository`.
- **API Contract:** `GET /api/dynasty/{clubId}`, `GET /api/dynasty/{clubId}/history`, `GET /api/clubs/{clubId}/trophy-cabinet`, `GET /api/trophies/leaderboard`.
- **Backend Endpoint:** `backend/app/dynasty/router.py`, `backend/app/trophies/router.py`.
- **Expected Success State:** Returns `DynastyProfileDto` (dynasty score, streak list, era triggers) and `TrophyCabinetDto` (cup silverware shelf, honors timeline).
- **Expected Error State:** Empty trophy cabinet displays `GtexEmptyState` ("No Trophies Won Yet").

### 3.11 Area 13: Design Lab Routes
- **UI Control:** Direct URL entry or developer menu -> `/design-lab`, `/design-lab/club-player-progression`, `/design-lab/competitions`, `/design-lab/market-ownership`.
- **Flutter Navigation:** `context.go('/design-lab/market-ownership')`.
- **Controller/Service:** Isolated fixture-only screens (`GtexMarketOwnershipDesignLabScreen`).
- **Expected Success State:** Renders isolated design lab testbed using mock fixtures without calling live production APIs.

---

## 4. Findings Register & Concrete Issues

The sweep identified **2 concrete issues** that affect routing integrity or deep-linking. Both are classified with severity, P7-FE exit gate blocker flag, and minimal recommended fixes.

---

### Finding 1: `/app/portfolio` Route Alias Degrades Incorrectly to Home
- **Location / File:** `frontend/lib/features/navigation/routing/gte_navigation_route.dart` (Symbol: `GteNavigationRoute.parse`)
- **Referenced In:**
  - `frontend/lib/features/player_detail/gtex_fm_player_profile_screen.dart` (line 224)
  - `frontend/lib/features/player_detail/widgets/ownership_consequence_card.dart` (line 116)
  - `frontend/lib/features/match_redesign/presentation/gtex_match_center_screen_v2.dart` (line 146)
- **Issue Description:**
  Multiple core UI surfaces render a "Portfolio" CTA that navigates via `context.go('/app/portfolio')`. However, in `GteNavigationRoute.parse()`, path segment `'portfolio'` is not handled explicitly in the `switch` statement. Consequently, it falls into `default: return const GteNavigationRoute.home()`.
  When a user taps "Open Portfolio" on a player profile card or post-match summary, instead of opening their wallet holdings or ownership desk, they are unexpectedly dumped on the Home screen.
- **Severity:** Medium
- **Blocks P7-FE Exit Gate:** **YES** (Degrades core user navigation flow from Player Profile and Matchday into Portfolio).
- **Recommended Minimal Fix (Without Implementation):**
  In `frontend/lib/features/navigation/routing/gte_navigation_route.dart`, add `'portfolio'` to the route parser switch block:
  ```dart
  case 'portfolio':
  case 'holdings':
    return const GteNavigationRoute.wallet(
      capitalDestination: GteCapitalDestination.holdings,
    );
  ```

---

### Finding 2: `GtexMarketOwnershipDesignLabScreen` Unregistered in App Router (RESOLVED)
- **Location / File:** `frontend/lib/router/app_router.dart` (Symbol: `buildGtexAppRouter`)
- **Referenced In:**
  - `frontend/lib/design_lab/gtex_market_ownership_design_lab_screen.dart`
- **Issue Description:**
  The isolated GTEX Design Lab screen for Market and Ownership visual compositions (`GtexMarketOwnershipDesignLabScreen`) was created in `frontend/lib/design_lab/gtex_market_ownership_design_lab_screen.dart`, and is now registered under `/design-lab/market-ownership` in `app_router.dart`.
- **Severity:** Low (Resolved)
- **Blocks P7-FE Exit Gate:** **NO**

---

## 5. Audit of Merged PRs #216 Through #223

A dedicated check was conducted on changes merged across PRs #216 through #223:

1. **PR #216 – PR #219 (Market & Ownership Redesign):**
   - **Verification:** Verified `GtexMarketOwnershipDeskScreen`, `GtexOwnershipTelemetryCard`, and `GtexWatchlistController`.
   - **Result:** Market search, 24h volume tickers, and share order placements perform as expected. Watchlist API calls map correctly to `GET/POST /api/watchlist/players`.

2. **PR #220 – PR #222 (Audio Foundation & Matchday Viewer Enhancements):**
   - **Verification:** Verified context-aware audio switching in `GteNavigationShellScreen._syncAudioContextForDestination` and 2D match viewer timeout boundaries in `live_match_viewer_route_support.dart`.
   - **Result:** Audio contexts (`home`, `club`, `market`, `competition`, `world`) transition seamlessly upon route changes. Match viewer 12s timeout boundary prevents infinite loading.

3. **PR #223 (Club, Player Identity & Progression Universe):**
   - **Verification:** Verified `GtexClubOwnerDashboardV2`, `GtexFmPlayerProfileScreen`, `DynastyScreen`, `TrophyCabinetScreen`, and new UI primitives (`GtexIdentityHeader`, `GtexProgressionBar`, `GtexSilverwareShelf`).
   - **Result:** All surfaces load from canonical backend endpoints (`GET /api/clubs/{id}/v2-snapshot`, `GET /api/players/{id}/summary`, `GET /dynasty/{id}`, `GET /clubs/{id}/trophy-cabinet`). Identified the `/app/portfolio` degradation gap in Player Profile.

---

## 6. Exit Gate Certification Status

- **Total Functional Areas Swept:** 13
- **Total Surfaces / Screens Evaluated:** 35
- **PASS Count:** 10 areas
- **FAIL Count:** 3 areas (Home, Player Profile due to `/app/portfolio` route gap; Design Lab due to missing route)
- **Blocking Exit Gate Issues:** **1** (Finding 1: `/app/portfolio` route degradation)
- **Non-Blocking Exit Gate Issues:** **1** (Finding 2: Unregistered Design Lab route)

### Certification Decision:
**P7-FE Exit Gate is BLOCKED until Finding 1 (`/app/portfolio` route alias in `gte_navigation_route.dart`) is resolved.**
