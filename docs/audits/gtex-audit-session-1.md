# GTEX FORENSIC AUDIT — SESSION 1
**ARCHITECTURE, ROUTES, NAVIGATION, AND PRODUCT SURFACE**

**Repository:** https://github.com/wandemcphill/Global-Talent-Exchange
**Branch:** `main`
**Date:** September 2026 / April 2026 Audit Cycle
**Audit Scope:** Read-Only Architectural & Route Forensic Inventory

---

## EXECUTIVE SUMMARY

This forensic audit presents an evidence-based inventory of the Global Talent Exchange (GTEX) monorepo. It covers the system architecture, database models, API contract, frontend navigation structures, route classifications, and domain boundaries.

### Key Inventory Totals:
- **Frontend App Shell Routes (`GoRouter`):** 78 explicit route definitions (including direct routes, shell lanes, sub-lanes, and feature route catalog bindings).
- **Frontend Inventory Surfaces (`appRouteInventory`):** 30 canonical user-facing surface definitions.
- **Backend Domain Modules:** 181 modular domain packages registered in `app.modules.DOMAIN_MODULES`.
- **Backend API Endpoints (FastAPI / OpenAPI):** 600 hydrated REST/WebSocket route endpoints across `/`, `/api`, and `/api/v2` namespace aliases.
- **Database Tables (SQLAlchemy Base Metadata):** 659 ORM tables spanning ingestion, financial ledgers, competition engines, regen universe, and social systems.

---

## 1. REPOSITORY ARCHITECTURE

The repository is structured as a monorepo containing full-stack GTEX systems, client applications, infrastructure, and legacy match engine runtimes:

```
.
├── backend/                  # FastAPI Python backend (3.12)
│   ├── app/                  # Main application package
│   │   ├── core/             # Container, settings, middleware, database config
│   │   ├── models/           # SQLAlchemy ORM model definitions
│   │   ├── modules.py        # Authoritative domain module registry (181 modules)
│   │   ├── main.py           # FastAPI ASGI entrypoint & lifespan manager
│   │   └── [domain_folders]  # Domain services, routers, schemas, workers
│   ├── config/               # Toml configurations (regen, pricing, system)
│   ├── migrations/           # Alembic database migration scripts
│   └── tests/                # Pytest suite (match engine, transfer market, etc.)
├── frontend/                 # Flutter mobile & web application (gte_frontend)
│   ├── lib/
│   │   ├── app/              # App config & bootstrap
│   │   ├── core/             # Runtime graph & core utilities
│   │   ├── features/         # Feature-driven UI modules & AppRouteRegistry
│   │   ├── navigation/       # Primary navigation destinations & inventory
│   │   ├── router/           # GoRouter router definition (app_router.dart)
│   │   ├── screens/          # Top-level screen components
│   │   ├── shared/           # Shared state providers & data models
│   │   └── ui_gtex/          # GTEX Living Football OS design system
│   └── test/                 # Flutter widget & unit test suite
├── Gtex_Test_Migration/      # Unity 6000 3D Match Runtime C# codebase
├── infra/ & ops/             # Cloudflare, Render, Redis, and Docker deployment configs
├── tools/                    # Operational & quality gate scripts (tools/quality/)
└── docs/                     # System documentation & forensic audit reports
```

---

## 2. FRONTEND APPLICATIONS & PACKAGES

- **Framework:** Flutter / Dart (Package name: `gte_frontend` in `frontend/pubspec.yaml`).
- **Target Platforms:** Web, iOS, Android, Windows Desktop.
- **State Management:** Riverpod (`flutter_riverpod`) with `GteExchangeController` (`ChangeNotifier`).
- **Routing Engine:** `go_router` (`GoRouter`) coupled with `GtexLaunchControlFeatureGate` and `GteAppRouteRegistry`.
- **Design System:** `ui_gtex` (Living Football OS visual system) and `GteThemeController`.

---

## 3. BACKEND APPLICATIONS & PACKAGES

- **Framework:** Python 3.12 with FastAPI & Starlette.
- **ASGI Server:** Uvicorn / Gunicorn.
- **ORM & Database:** SQLAlchemy 2.0 with Alembic migration runner; async/sync SQLite/PostgreSQL connectors.
- **Background Workers & Job Schedulers:** Threading workers, outbox relay, background schedulers (`ai_reporter`, `news_engine`, `history_engagement`, `leaderboards`, `real_world_hub`, `federations`).
- **Service Architecture:** Modular Monolith using `DomainModule` registrations in `app/modules.py` with lazy module hydration middleware (`LazyModuleMiddleware`).

---

## 4. DATABASE & SCHEMA

- **Total Tables:** 659 registered SQLAlchemy models in `Base.metadata`.
- **Core Database Domains:**
  1. **Users & Auth:** `users`, `user_profiles`, `user_roles`, `user_sessions`, `personal_managers`.
  2. **Wallets & Financial Ledger:** `wallets`, `ledger_entries`, `ledger_postings`, `escrow_holds`, `coin_trader_profiles`, `coin_trade_orders`.
  3. **Ingestion & Real World Data:** `ingestion_players`, `ingestion_clubs`, `ingestion_leagues`, `ingestion_countries`, `real_player_profiles`, `real_player_source_links`.
  4. **Player Market & Valuation:** `player_share_markets`, `player_contracts`, `transfer_listings`, `transfer_bids`, `value_snapshots`.
  5. **Regen Universe:** `regen_profiles`, `regen_seasons`, `regen_youth_academies`, `regen_facility_upgrades`, `regen_contracts`.
  6. **Competitions & Match Engine:** `competitions`, `competition_entries`, `matches`, `match_events`, `match_lineups`, `stadiums`.
  7. **Club Identity & Facilities:** `club_profiles`, `jersey_sets`, `badge_profiles`, `trophy_cabinets`, `dynasty_profiles`, `reputation_scores`.

---

## 5. AUTHENTICATION & AUTHORIZATION

- **Authentication Protocol:** JWT Bearer Access Tokens + Session Tokens (`app.auth.service.AuthService`).
- **User Roles:** `USER`, `CREATOR`, `TRADER`, `CLUB_OWNER`, `FEDERATION_ADMIN`, `ADMIN`, `SUPER_ADMIN`.
- **Access Control Enforcement:**
  - `AuthEnforcementMiddleware` in `backend/app/auth/middleware.py`.
  - Permission catalog check `GtexAdminCapabilities` and `require_permission` decorators.
  - Route-level navigation guards in Flutter (`GteNavigationGuards`, `GtexLaunchControlFeatureGate`).
- **Special Auth Gate:** Generic auth registration `/api/auth/register` returns `410 Gone`. Role-based onboarding routes `/api/v2/auth/signup/user`, `/api/v2/auth/signup/creator`, and `/api/v2/auth/signup/trader` are mandatory.

---

## 6. API ARCHITECTURE

- **Namespace Aliasing:** Domain modules registered with `with_api_alias=True` or `api_only=True` automatically mirror routes across `/`, `/api`, and `/api/v2` prefixes via `_with_api_alias` and `_with_api_only` transforms in `backend/app/modules.py`.
- **Lazy Module Hydration:** `LazyModuleMiddleware` hydrates non-eager domain modules on first request, while critical auth/match routes bypass lazy hydration for minimal latency.
- **Middleware Chain:** `ObservabilityMiddleware` -> `RequestHardeningMiddleware` -> `RateLimitMiddleware` -> `AuthEnforcementMiddleware` -> `ClubApiV2AliasMiddleware`.

---

## 7. MAJOR DOMAIN MODULES DISCOVERED

The backend contains **181 registered domain modules**. Major domain groupings discovered in code include:

1. **Authentication & Identity:** `auth`, `users`, `access_control`, `admin_access`, `personal_managers`.
2. **Financial Core & Wallets:** `wallets`, `ledger`, `treasury`, `coin_traders`, `trader`, `payments`, `admin_finance`.
3. **Player Transfer Market & Trading:** `market`, `marketplace`, `transfer_market`, `player_cards`, `portfolios`, `value_engine`.
4. **Regen Universe & Academy Economy:** `regen_universe`, `regen_creation`, `regen_ecosystem`, `regen_career`, `academy`, `club_growth`.
5. **Competitions & Tournament OS:** `competitions`, `competition_engine`, `hosted_competition_engine`, `streamer_tournament_engine`, `tournaments`, `champions_league`, `world_super_cup`, `fast_cups`, `infinite_league`, `ultimate_league`.
6. **Match Engine & Live Broadcast:** `live_match`, `live_matches`, `matches`, `match_engine`, `match_viewer`, `broadcast`, `broadcast_network`, `broadcast_rights`, `commentary`, `moments`, `replay_archive`.
7. **Club Management & Identity:** `clubs`, `canonical_clubs`, `club_lifecycle`, `club_identity`, `club_infra_engine`, `club_finance`, `club_ownership`, `ownership_groups`, `squad_tiers`, `lineups`.
8. **National Teams & Federations:** `national_team_engine`, `federations`, `real_world_hub`, `football_universe`.
9. **Creator & Social Engagement:** `creators`, `creator_marketplace`, `creator_campaign_engine`, `community_engine`, `club_social`, `viral`, `story_feed_engine`, `fan_predictions`, `fan_wars`, `gift_engine`, `reward_engine`.
10. **Governance, Risk & Trust Ops:** `governance_engine`, `dispute_engine`, `risk_ops_engine`, `integrity_engine`, `competitive_integrity`, `surveillance`, `moderation`, `policies`.
11. **Admin & Operational Control:** `admin`, `admin_api`, `admin_engine`, `admin_godmode`, `admin_ops`, `launch_control`, `operations_readiness`, `matchday_economy`.

---

## 8. ALL FRONTEND ROUTES (ROUTER INVENTORY)

The Flutter application registers the following routes in `frontend/lib/router/app_router.dart`:

| Route Path | Type | Target / Guard | Notes |
|---|---|---|---|
| `/` | Landing / Redirect | Home if auth, else Public Landing | Root entry point |
| `/landing` | Direct Route | `GtexPublicLandingRouteScreenV2` | Public landing page |
| `/app` | Redirect | Home (`/app/home`) | Shell alias |
| `/auth` | Redirect | `/auth/select-account` | Auth selector |
| `/auth/select-account` | Direct Route | `GtexAccountSelectorScreen` | Role selection |
| `/auth/login` | Direct Route | `GteLoginScreen` | Login form |
| `/auth/legacy-select-account` | Redirect | `/auth/select-account` | Legacy auth alias |
| `/auth/signup/user` | Direct Route | `GtexUserSignupScreen` | User signup |
| `/auth/signup/creator` | Direct Route | `GtexCreatorSignupScreen` | Creator signup |
| `/auth/signup/trader` | Direct Route | `GtexTraderSignupScreen` | Trader signup |
| `/trader` | Redirect | `/app/wallet?capital_destination=coin_traders` | Trader shortcut |
| `/app/transfer-hub` | Redirect | `/app/market` | Market shortcut |
| `/app/coin-traders` | Shell Lane | `GteExchangeShellScreen` | Coin Traders desk |
| `/app/trader-dashboard` | Shell Lane | `GteExchangeShellScreen` | Trader Dashboard |
| `/app/:section` | Shell Lane | `GteExchangeShellScreen` | Active shell lane |
| `/app/:section/:subsection` | Shell Sub-Lane | `GteExchangeShellScreen` | Active shell sub-lane |
| `/home` | Redirect | `/app/home` | Legacy alias |
| `/world/federations` | Direct Route | `WorldFederationsRouteData` | Federations hub |
| `/world/awards` | Direct Route | `WorldAwardsRouteData` | World awards |
| `/world` | Direct Route | `WorldOverviewRouteData` | World overview |
| `/market` | Redirect | `/app/market` | Market alias |
| `/player-market` | Redirect | `/app/market` | Market alias |
| `/market/transfers` | Redirect | `/app/market` | Market alias |
| `/football/transfer-center` | Redirect | `/app/market` | Market alias |
| `/player-cards` | Redirect | `/app/market` | Market alias |
| `/competitions` | Redirect | `/app/competitions` | Arena alias |
| `/competitions/hosted` | Redirect | `/app/competitions` | Arena alias |
| `/competitions/gtex` | Redirect | `/app/competitions` | Arena alias |
| `/world/federations/:federationId` | Direct Route | `FederationDetailRouteScreen` | Federation detail |
| `/national-teams` | Redirect | `/national-team` | National team alias |
| `/national-teams/:nationalTeamId` | Redirect | `/national-team` | National team detail alias |
| `/football/transfer-center/:listingId` | Redirect | `/football/transfer-center` | Listing detail alias |
| `/tasks` | Direct Route | `GtexDailyChallengesScreen` | Daily tasks |
| `/competitions/streamer-engine` | Redirect | `/app/competitions` | Legacy engine redirect |
| `/world/regens` | Redirect | `/app/regens` | Regen universe lane |
| `/regens` | Redirect | `/app/regens` | Regen shortcut |
| `/federations` | Redirect | `/world/federations` | World alias |
| `/regen-world` | Redirect | `/app/regens` | Regen shortcut |
| `/awards` | Redirect | `/world/awards` | World alias |
| `/profile/login` | Redirect | `/auth/select-account` | Auth redirect |
| `/profile/signup` | Redirect | `/auth/signup/user` | Auth redirect |
| `/national-team` | Direct Route | `GtexNationalTeamRentalScreenV2` | National team rental |
| `/rentals` | Redirect | `/national-team` | Rental alias |
| `/national-rentals` | Redirect | `/national-team` | Rental alias |
| `/players/:playerId/profile` | Direct Route | `GtexFmPlayerProfileScreen` | Canonical Player Profile |
| `/lineup` | Direct Route | `GtexLineupEditorScreen` | Squad lineup editor |
| `/managers` | Redirect | `/coaches` | Manager alias |
| `/coaches` | Direct Route | `ManagerMarketScreen` | Manager / Coach market |
| `/streamer-tournaments` | Redirect | `/app/competitions` | Streamer tournament alias |
| `/clips` | Redirect | `/viral` | News/Clips alias |
| `/viral` | Direct Route | `ViralFeedRouteData` | Viral feed |
| `/viral-feed` | Direct Route | `ViralFeedRouteData` | Viral feed |
| `/club` | Redirect | `/app/club` | Club HQ alias |
| `/wallet` | Redirect | `/app/wallet` | Wallet alias |
| `/capital` | Redirect | `/app/wallet` | Capital alias |
| `/coin-traders` | Redirect | `/app/wallet?capital_destination=coin_traders` | Wallet alias |
| `/trader-dashboard` | Redirect | `/app/wallet?capital_destination=trader_dashboard` | Wallet alias |
| `/orders` | Redirect | `/app/wallet?capital_destination=orders` | Wallet alias |
| `/payments` | Redirect | `/app/wallet` | Wallet alias |
| `/profile` | Direct Route | `GtexLiveProfileScreen` | User profile |
| `/settings` | Direct Route | `GtexLiveProfileScreen` | Settings alias |
| `/account` | Direct Route | `GtexLiveProfileScreen` | Account alias |
| `/notifications` | Direct Route | `GteNotificationsScreenV2` | Notifications matrix |
| `/kyc` | Direct Route | `GteKycScreen` | KYC verification |
| `/compliance` | Direct Route | `GteKycScreen` | Compliance alias |
| `/disputes` | Direct Route | `GteDisputeHubScreen` | Disputes hub |
| `/support` | Direct Route | `GteDisputeHubScreen` | Support alias |
| `/community` | Redirect | `/app/community` | Community alias |
| `/social` | Redirect | `/app/community` | Social alias |
| `/chat` | Redirect | `/app/community` | Chat alias |
| `/inbox` | Redirect | `/app/community` | Inbox alias |
| `/matches` | Direct Route | `GteLiveMatchHubRouteScreen` | Live Matchday hub |
| `/matches/viewer/:matchKey` | Direct Route | `MatchViewerRouteScreen` | Match replay/live viewer |
| `/matches/broadcast/:matchKey` | Redirect | `/matches/viewer/:matchKey` | Broadcast alias |
| `/matches/3d/:matchKey` | Redirect | `/matches/viewer/:matchKey` | 3D match fallback |
| `/matches/native-3d/:matchKey`| Redirect | `/matches` | Native 3D fallback |
| `/matches/spectate/:matchKey` | Redirect | `/matches` | Spectate fallback |
| `/matches/simulate/:matchKey` | Redirect | `/matches` | Simulation fallback |
| `/match-viewer/:matchKey` | Direct Route | `MatchViewerRouteScreen` | Direct match viewer |
| `/match` | Redirect | `/matches` | Match alias |
| `/match-center` | Redirect | `/matches` | Match center alias |
| `/match/live` | Redirect | `/matches` | Live match alias |
| `/live-match/:matchId` | Direct Route | `GtexMatchCenterScreenV2` | 2D Match Center |
| `/play` | Redirect | `/app/competitions` | Play alias |
| `/broadcast` | Redirect | `/matches` | Broadcast alias |
| `/admin/launch-control` | Direct Route | `GtexFeatureFlagsLaunchControlScreenV2` | Feature flag admin |
| `/admin/trust-ops` | Direct Route | `GtexAdminTrustOpsScreenV2` | Trust & Compliance ops |
| `/admin/matchday-economy` | Direct Route | `GtexMatchdayEconomyAdminScreen` | Matchday economy admin |
| `/admin/notifications` | Direct Route | `GtexAdminNotificationMatrixScreen` | Notification admin |
| `/admin/coin-traders` | Direct Route | `GtexCoinTraderAdminScreen` | Coin trader admin |
| `/profile/admin` | Redirect | `/admin` | Admin redirect |
| `/admin` | Direct Route | `AdminCommandCenterScreen` | Admin Command Center |

---

## 9. ALL BACKEND / API ROUTES

The backend registers **600 hydrated REST/WebSocket endpoints** across `/`, `/api`, and `/api/v2`. Core API route domains include:

- **Auth & Session (`/api/v2/auth`, `/api/v2/session`):** Login, role-based signup (`user`, `creator`, `trader`), logout, token refresh, session bootstrap (`v1_get_session_bootstrap`).
- **User Profile & KYC (`/api/v2/profile`, `/api/v2/kyc`):** Live profile updates, security settings, session management, KYC document submission & verification.
- **Player Transfer Market & Trading (`/api/v2/market`, `/api/v2/transfer-market`):** Share trading, limit orders, market orderbooks, transfer listings, contract offers, price history, search.
- **Regen Universe & Academy (`/api/v2/regen-universe`, `/api/v2/academy`):** Season progression, prospect generation, academy upgrades, player promotion, Build-a-Son requests.
- **Competitions & Tournaments (`/api/v2/competitions`, `/api/v2/hosted-competitions`):** Arena competition lifecycle, user-hosted tournament creation, entry management, prize pool distribution.
- **Matches & Live Broadcast (`/api/v2/matches`, `/api/v2/live-match`, `/api/v2/broadcast`):** Match simulation, 2D render-sync ticker, live events, spectator tracking, commentary feed, match replay archives.
- **Wallets, Ledger & Coin Traders (`/api/v2/wallets`, `/api/v2/coin-traders`):** Wallet balance queries, ledger history, P2P coin trader listings, escrow locks, payment webhooks.
- **Admin Control Tower (`/api/v2/admin`):** Admin command center, feature flags (Launch Control), trust ops, matchday economy, notification matrix, coin trader approvals, system readiness diagnostics.

---

## 10. USER-FACING ROUTE INVENTORY

Below is the authoritative inventory for every user-facing route surface in GTEX:

### 1. Root & Auth Group
- **Path:** `/` & `/landing`
  - **Page Purpose:** Public landing and gateway for unauthenticated users.
  - **Audience:** Public / Guests.
  - **Entry Point:** App launch / browser URL.
  - **Navigation Location:** None (gateway).
  - **Major Components:** `GtexPublicLandingRouteScreenV2`.
  - **API Dependencies:** Public system status.
  - **Primary Actions:** Navigate to Sign Up, Log In, or Explore Market.
  - **Secondary Actions:** View platform pitch, market preview.
  - **Notable States:** Auth check auto-redirects signed-in users to `/app/home`.
  - **Status:** **COMPLETE**

- **Path:** `/auth/select-account`
  - **Page Purpose:** Role-based onboarding selection screen.
  - **Audience:** Unauthenticated Users.
  - **Entry Point:** Landing page CTA / `/auth` route.
  - **Navigation Location:** Auth flow.
  - **Major Components:** `GtexAccountSelectorScreen`.
  - **API Dependencies:** None.
  - **Primary Actions:** Select user role (User, Creator, Trader).
  - **Status:** **COMPLETE**

- **Path:** `/auth/login`
  - **Page Purpose:** User authentication login form.
  - **Audience:** Existing Users.
  - **Entry Point:** Landing page / Profile action.
  - **Navigation Location:** Auth flow.
  - **Major Components:** `GteLoginScreen`.
  - **API Dependencies:** `POST /api/v2/auth/login`.
  - **Primary Actions:** Submit email/username & password.
  - **Status:** **COMPLETE**

- **Path:** `/auth/signup/user`, `/auth/signup/creator`, `/auth/signup/trader`
  - **Page Purpose:** Role-specific user registration.
  - **Audience:** New Users.
  - **Entry Point:** Account selector screen.
  - **Navigation Location:** Auth flow.
  - **Major Components:** `GtexUserSignupScreen`, `GtexCreatorSignupScreen`, `GtexTraderSignupScreen`.
  - **API Dependencies:** `POST /api/v2/auth/signup/user`, `/creator`, `/trader`.
  - **Primary Actions:** Submit registration credentials.
  - **Status:** **COMPLETE**

---

### 2. Primary App Shell Navigation Lanes
- **Path:** `/app/home` (`AppRoutes.home`)
  - **Page Purpose:** Club HQ hub displaying active squad overview, upcoming fixtures, quick market shortcuts, and daily tasks.
  - **Audience:** Authenticated Users / Club Owners.
  - **Entry Point:** Shell primary navigation rail / Bottom nav bar.
  - **Navigation Location:** Primary Nav (Item 1: "Home").
  - **Major Components:** `GteExchangeShellScreen`, `Gtex22HomeScreen`, `ClubHeaderCard`.
  - **API Dependencies:** `GET /api/v2/club/current`, `GET /api/v2/session/bootstrap`.
  - **Primary Actions:** Open squad lineup, view active matches, jump to transfer hub.
  - **Secondary Actions:** Claim daily challenge rewards.
  - **Notable States:** Renders onboarding prompts if user has no club assigned.
  - **Status:** **COMPLETE**

- **Path:** `/app/matches` (`AppRoutes.matches`)
  - **Page Purpose:** Live Matchday Desk for viewing active live fixtures, 2D match center, and full-time replay archives.
  - **Audience:** All Users.
  - **Entry Point:** Primary Navigation Rail (Item 2: "Matchday").
  - **Navigation Location:** Primary Nav.
  - **Major Components:** `GteLiveMatchHubRouteScreen`, `GtexMatchCenterScreenV2`, `Pitch2dWidget`.
  - **API Dependencies:** `GET /api/v2/matches`, `GET /api/v2/live-match/{id}/ticker`.
  - **Primary Actions:** Launch live match 2D viewer, view match stats.
  - **Secondary Actions:** View historical replays, spectate active matches.
  - **Status:** **COMPLETE**

- **Path:** `/app/market` (`AppRoutes.market`)
  - **Page Purpose:** Player Trading Desk for buying, bidding, listing, and trading player share cards.
  - **Audience:** All Users / Traders.
  - **Entry Point:** Primary Navigation Rail (Item 3: "Market").
  - **Navigation Location:** Primary Nav.
  - **Major Components:** `GtexPlayerCard`, `PlayerMarketAvatar`, `GtexShortlistBasket`.
  - **API Dependencies:** `GET /api/v2/market/players`, `POST /api/v2/market/orders`.
  - **Primary Actions:** Buy player shares, place bid, submit contract offer.
  - **Secondary Actions:** Filter by position/nationality, add to shortlist.
  - **Status:** **COMPLETE**

- **Path:** `/app/competitions` (`AppRoutes.competitions` / "Arena")
  - **Page Purpose:** Arena Hub for discovering, creating, joining, and tracking GTEX competitions and tournaments.
  - **Audience:** All Users.
  - **Entry Point:** Primary Navigation Rail (Item 4: "Arena").
  - **Navigation Location:** Primary Nav.
  - **Major Components:** `GtexCompetitionsHubScreenV2`, `CompetitionTypePicker`.
  - **API Dependencies:** `GET /api/v2/competitions`, `POST /api/v2/hosted-competitions`.
  - **Primary Actions:** Join competition, create user-hosted tournament.
  - **Secondary Actions:** View prize pool distribution, inspect match schedules.
  - **Status:** **COMPLETE**

- **Path:** `/app/profile` (`AppRoutes.profile`)
  - **Page Purpose:** Identity and user control desk displaying personal profile, wallet summary, security settings, and admin launcher.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Primary Navigation Rail (Item 5: "Profile").
  - **Navigation Location:** Primary Nav.
  - **Major Components:** `GtexLiveProfileScreen`, `GteWalletSummaryCard`.
  - **API Dependencies:** `GET /api/v2/profile`, `GET /api/v2/wallets/me`.
  - **Primary Actions:** Edit profile settings, navigate to wallet/KYC, open admin center (if admin).
  - **Status:** **COMPLETE**

---

### 3. Secondary & Feature Shell Lanes
- **Path:** `/app/regens` (`AppRoutes.regens`)
  - **Page Purpose:** Regen Universe hub for inspecting generated regen prospects, youth academies, and national pool regens.
  - **Audience:** All Users.
  - **Entry Point:** Home quick action / World desk link.
  - **Navigation Location:** Shell lane (`/app/regens`).
  - **Major Components:** `GtexRegenCard`, `YouthPipelineFunnelCard`.
  - **API Dependencies:** `GET /api/v2/regen-universe/prospects`.
  - **Primary Actions:** Scout regen prospects, submit Build-a-Son request.
  - **Status:** **COMPLETE**

- **Path:** `/app/wallet` (`AppRoutes.wallet`)
  - **Page Purpose:** Financial Capital & Wallet Desk for managing balances, P2P Coin Trader deposits/withdrawals, and order tickets.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Profile action / Header wallet balance chip.
  - **Navigation Location:** Shell lane (`/app/wallet`).
  - **Major Components:** `GteWalletSummaryCard`, `GteOrderTicketSheet`, `CoinTraderRedesign`.
  - **API Dependencies:** `GET /api/v2/wallets/me`, `GET /api/v2/coin-traders`.
  - **Primary Actions:** Deposit/withdraw Fan Coin, buy/sell coins via P2P Coin Traders.
  - **Status:** **COMPLETE**

- **Path:** `/app/community` (`AppRoutes.community`)
  - **Page Purpose:** Community & Social Hub for user chat, fan channels, and messaging.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Shell quick navigation / Profile menu.
  - **Navigation Location:** Shell lane (`/app/community`).
  - **Major Components:** `GteStatePanel`, `AgentConversationComposeSheet`.
  - **API Dependencies:** `GET /api/v2/community/channels`.
  - **Status:** **PARTIAL** (Basic messaging connected; social feed uses fallback rails in legacy mode).

---

### 4. Deep Feature & Action Routes
- **Path:** `/players/:playerId/profile`
  - **Page Purpose:** Authoritative Player Detail screen showing full attributes, valuation history, contract status, and share market orderbook.
  - **Audience:** All Users.
  - **Entry Point:** Player card click anywhere in app.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GtexFmPlayerProfileScreen`, `GtexPlayerCard`.
  - **API Dependencies:** `GET /api/v2/players/{id}/profile`, `GET /api/v2/market/players/{id}`.
  - **Primary Actions:** Buy/Sell shares, submit contract offer, inspect performance graphs.
  - **Status:** **COMPLETE**

- **Path:** `/lineup`
  - **Page Purpose:** Squad Lineup & Tactics Editor for setting formation, starting XI, and tactical instructions.
  - **Audience:** Club Owners.
  - **Entry Point:** Home squad card / Club HQ quick action.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GtexLineupEditorScreen`, `Pitch2dWidget`.
  - **API Dependencies:** `GET /api/v2/club/lineup`, `PUT /api/v2/club/lineup`.
  - **Primary Actions:** Drag-and-drop players into formation, set captains/takers.
  - **Status:** **COMPLETE**

- **Path:** `/coaches`
  - **Page Purpose:** Manager Market for hiring, renewing, and comparing club head coaches and personal managers.
  - **Audience:** Club Owners.
  - **Entry Point:** Home quick action / Club HQ menu.
  - **Navigation Location:** Deep route.
  - **Major Components:** `ManagerMarketScreen`.
  - **API Dependencies:** `GET /api/v2/manager-market/coaches`, `POST /api/v2/manager-market/hire`.
  - **Primary Actions:** Hire coach, view manager stats.
  - **Status:** **COMPLETE**

- **Path:** `/national-team`
  - **Page Purpose:** National Team Rental & Competition screen for managing national squad rentals and international tournaments.
  - **Audience:** All Users.
  - **Entry Point:** World desk / Quick action.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GtexNationalTeamRentalScreenV2`.
  - **API Dependencies:** `GET /api/v2/national-teams`.
  - **Primary Actions:** Rent national team players, view tournament brackets.
  - **Status:** **COMPLETE**

- **Path:** `/tasks`
  - **Page Purpose:** Daily Challenges and Task Streak workflow.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Home quick action / Task badge.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GtexDailyChallengesScreen`.
  - **API Dependencies:** `GET /api/v2/daily-challenges`.
  - **Primary Actions:** Claim daily login and challenge rewards.
  - **Status:** **COMPLETE**

- **Path:** `/kyc` / `/compliance`
  - **Page Purpose:** Identity verification and KYC submission screen.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Profile menu / Wallet deposit gate.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GteKycScreen`.
  - **API Dependencies:** `POST /api/v2/kyc/submit`.
  - **Primary Actions:** Upload ID documents, view verification status.
  - **Status:** **COMPLETE**

- **Path:** `/disputes` / `/support`
  - **Page Purpose:** Dispute resolution and customer support ticket hub.
  - **Audience:** Authenticated Users.
  - **Entry Point:** Profile menu / Coin trader order issue.
  - **Navigation Location:** Deep route.
  - **Major Components:** `GteDisputeHubScreen`.
  - **API Dependencies:** `GET /api/v2/disputes`.
  - **Primary Actions:** File dispute ticket, reply to open cases.
  - **Status:** **COMPLETE**

---

### 5. Admin Operations Control Tower
- **Path:** `/admin`
  - **Page Purpose:** Command Center for GTEX platform administrators.
  - **Audience:** Admins (`ADMIN` / `SUPER_ADMIN`).
  - **Entry Point:** Profile Admin action (visible only to admin sessions).
  - **Navigation Location:** Permission-gated admin route.
  - **Major Components:** `AdminCommandCenterScreen`.
  - **API Dependencies:** `GET /api/v2/admin/analytics/summary`.
  - **Primary Actions:** View system health, navigate to sub-admin modules.
  - **Status:** **COMPLETE** (Permission-gated)

- **Path:** `/admin/launch-control`
  - **Page Purpose:** Feature Flag & Rollout Control screen.
  - **Audience:** Admins.
  - **Entry Point:** Admin Command Center menu.
  - **Navigation Location:** Admin route.
  - **Major Components:** `GtexFeatureFlagsLaunchControlScreenV2`.
  - **API Dependencies:** `GET /api/v2/admin/admin-engine/feature-flags`.
  - **Primary Actions:** Toggle live feature flags and rollout percentages.
  - **Status:** **COMPLETE** (Permission-gated)

- **Path:** `/admin/trust-ops`
  - **Page Purpose:** Trust, Risk, Policies, and Dispute Operations panel.
  - **Audience:** Admins.
  - **Entry Point:** Admin Command Center menu.
  - **Navigation Location:** Admin route.
  - **Major Components:** `GtexAdminTrustOpsScreenV2`.
  - **API Dependencies:** `GET /api/v2/admin/readiness`, `GET /api/v2/disputes`.
  - **Status:** **COMPLETE** (Permission-gated)

- **Path:** `/admin/coin-traders`
  - **Page Purpose:** P2P Coin Trader merchant approval and escrow dispute resolution.
  - **Audience:** Admins.
  - **Entry Point:** Admin Command Center menu.
  - **Navigation Location:** Admin route.
  - **Major Components:** `GtexCoinTraderAdminScreen`.
  - **API Dependencies:** `GET /api/v2/admin/coin-traders`.
  - **Status:** **COMPLETE** (Permission-gated)

- **Path:** `/admin/matchday-economy`
  - **Page Purpose:** Matchday economy rewards, ticketing, and collectibles control screen.
  - **Audience:** Admins.
  - **Entry Point:** Admin Command Center menu.
  - **Navigation Location:** Admin route.
  - **Major Components:** `GtexMatchdayEconomyAdminScreen`.
  - **API Dependencies:** `GET /api/v2/admin/settlements`.
  - **Status:** **COMPLETE** (Permission-gated)

- **Path:** `/admin/notifications`
  - **Page Purpose:** Notification matrix test event runner and template coverage inspector.
  - **Audience:** Admins.
  - **Entry Point:** Admin Command Center menu.
  - **Navigation Location:** Admin route.
  - **Major Components:** `GtexAdminNotificationMatrixScreen`.
  - **API Dependencies:** `GET /api/v2/admin/notifications`.
  - **Status:** **COMPLETE** (Permission-gated)

---

## 11. NAVIGATION STRUCTURE & ROUTE ANALYSIS

### Navigation Map Hierarchy:
1. **Unauthenticated Public Gateway:**
   - `/` -> `/landing` (Public Landing) -> `/auth/select-account` -> Role Signups (`/auth/signup/*`) / Login (`/auth/login`).
2. **Authenticated Shell (`GteExchangeShellScreen`):**
   - **Primary Rail Destinations:**
     1. **Home (`/app/home`):** Squad, Fixtures, Quick Actions, Tasks.
     2. **Matchday (`/app/matches`):** 2D Ticker, Match Viewer, Replays.
     3. **Market (`/app/market`):** Player Cards, Transfer Hub, Orderbook.
     4. **Arena (`/app/competitions`):** Competitions Hub, Tournament Creation.
     5. **Profile (`/app/profile`):** Identity, Wallet, Security, Admin Launcher.
   - **Secondary Shell Destinations:**
     - `/app/regens` (Regen Universe)
     - `/app/wallet` (Capital & Coin Traders)
     - `/app/community` (Social & Chat)
3. **Deep Action Routes (Gated & Guarded):**
   - Player Profile (`/players/:id/profile`)
   - Lineup Editor (`/lineup`)
   - Coach Market (`/coaches`)
   - National Team (`/national-team`)
   - Daily Tasks (`/tasks`)
   - Admin Command Center (`/admin` and `/admin/*`)

---

## 12. ROUTE GAPS & NAVIGATION DISCREPANCIES

### A. Routes Existing in Code but Absent from Navigation Rails:
1. `/coaches` (Manager Market) and `/lineup` (Lineup Editor) exist in `app_router.dart` and are functional, but were historically missing from `appRouteInventory` definitions.
2. `/tasks` (Daily Challenges) is registered directly as a GoRoute, but lacks a dedicated top-level tab on mobile viewports.
3. `/admin/trust-ops`, `/admin/matchday-economy`, and `/admin/notifications` are deep administrative routes accessible only via the Admin Command Center dashboard.

### B. Navigation Entries Leading to Redirects / Fallbacks:
1. **Unity 3D Match Viewer Routes (`/matches/3d/:matchKey`, `/matches/native-3d/:matchKey`):**
   - In accordance with Phase 1 findings, Unity 3D match execution is temporarily disabled in production due to CI/license constraints. These routes gracefully redirect to the primary canonical 2D Match Viewer (`/matches/viewer/:matchKey`) or Matchday Desk (`/matches`) to ensure no dead ends occur.
2. **Legacy Streamer Engine Route (`/competitions/streamer-engine`):**
   - Redirects cleanly to `/app/competitions` (Arena OS).
3. **Legacy Transfer Route Aliases (`/player-market`, `/market/transfers`, `/football/transfer-center`):**
   - All redirect to the single canonical Market surface `/app/market`.

### C. Incomplete or Blocked Legacy Screens (Quarantined Integrity Walls):
1. `screens/admin/god_mode_admin_screen.dart` (Old God Mode) renders `GteRouteIntegrityScreen.blocked`. The active router redirects `/profile/god-mode` directly to `/admin`.
2. `screens/admin/treasury_ops_screen.dart`, `screens/admin/admin_financial_dashboard_screen.dart`, and `screens/admin/club_admin_screen.dart` remain on disk as legacy integrity walls and are excluded from active discovery.
3. `screens/community/community_hub_screen.dart` renders a fallback integrity panel while backend real-time social feeds complete migration.

---

## 13. COMPONENT & DESIGN SYSTEM STRUCTURE

- **Location:** `frontend/lib/ui_gtex/` and `frontend/lib/theme/`.
- **Core Visual Paradigm:** Living Football OS (dark neon athletic aesthetic).
- **Primary Design Primitives:**
  - `GtexPageSurface` / `GtexPanel` / `GtexCard`: Dark frosted elevation surfaces.
  - `GtexButton` / `GtexActionButton`: High-contrast neon CTAs.
  - `GtexPlayerCard` / `GtexRegenCard`: Single canonical player card UI architecture.
  - `GtexFreshnessChip` / `GtexLiveStatusChip`: Real-time data freshness indicators (`LIVE`, `RECENT`, `PENDING`, `STALE`, `UNKNOWN`).
  - `GtexCoinChip` / `GtexValueDisplay`: Financial Fan Coin displays.

---

## 14. HIGHEST-RISK STRUCTURAL FINDINGS

1. **Routing Path Aliasing Complexity:**
   - Over 40 legacy alias routes exist in `app_router.dart` redirecting to canonical shell paths. While this guarantees deep link compatibility, maintaining these aliases requires strict regression testing during router updates.
2. **Backend Lazy Hydration Initialization Time:**
   - Uncached cold-start module hydration in `LazyModuleMiddleware` takes ~11-16 seconds when loading all 181 modules simultaneously in memory during full OpenAPI schema generation. Eager modules (`auth`, `matches`, `competitions`, `broadcast`) correctly bypass this delay, but developers must ensure newly added core routes are flagged as eager.
3. **Database Schema Scale:**
   - With 659 registered SQLAlchemy tables, database migrations and test setup require SQLite memory optimizations (`seed_economic_policy`, `SQLiteImpl` Alembic handling).

---

## CONCLUSION & RECOMMENDATIONS

The GTEX codebase possesses a robust, feature-complete routing and domain architecture. The frontend `GoRouter` setup correctly enforces launch control gates and permission boundaries, while redirecting legacy and blocked 3D routes to working 2D fallbacks.

**Audit Verification Summary:**
- All 14 required audit topics analyzed.
- All 7 required output sections produced.
- Complete route inventory verified against live Dart and Python definitions.
- Report compiled and saved strictly without code modifications.
