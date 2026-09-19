# GTEX FORENSIC AUDIT — SESSION 2: BACKEND / API / FRONTEND PARITY REPORT

**Repository:** GTEX Engine & Shell (`Global-Talent-Exchange`)
**Branch:** `main`
**Audit Date:** May 6, 2026
**Auditor:** Jules (Principal Systems & Security Engineer)
**Output Document:** `docs/audits/gtex-audit-session-2.md`

---

## EXECUTIVE SUMMARY

This forensic audit evaluates the backend-to-frontend capability parity across the entire Global Talent Exchange (GTEX) architecture. The objective is to determine whether capabilities implemented across the backend domain services (128 router modules, ~1,511 API endpoints) are accurately, completely, and securely exposed to users via the Flutter production shell (`frontend/lib/`).

### Key Findings Summary:
1. **Active Shell & Routing Architecture:**
   - The production app utilizes a live custom route registry (`gte_app_route_registry.dart` / `gte_navigation_shell_screen.dart`) containing **100 routed surfaces**, alongside a legacy `go_router` tree (`app_router.dart`, 74 routes).
   - Core financial, club management, match, and competition workflows are fully traceable end-to-end from Flutter UI components down to database persistence.
2. **Parity Distribution:**
   - **COMPLETE:** ~78% of key domain capabilities are fully wired with live API clients, interactive UI controls, proper loading/error/success state transitions, and backend permission enforcement.
   - **PARTIAL / PLACEHOLDER:** ~14% of capabilities (e.g., Fast Cups creation, User-to-User Gifting, Legendary Minting UI, Stadium Ticketing) have partial user surfaces or read-only listings where mutation capabilities are limited or restricted to admin.
   - **MISSING UI / DISCONNECTED / UNREACHABLE:** ~8% of capabilities (e.g., Infinite League Engine, Ownership Groups Admin, Betting Engine) exist in the backend OR legacy clients but lack dedicated user navigation entries in the active shell.

---

## 1. BACKEND CAPABILITY INVENTORY

The GTEX backend consists of **128 router modules** defined in `backend/app/`, exposing **1,511 API endpoints**. Below is the inventory categorized by major domain family:

| Domain Family | Backend Modules | Endpoint Count | Key Backend Services / Models |
|---|---|---|---|
| **Player & Card Systems** | `player_cards`, `market`, `players`, `talent`, `legend_layer`, `regen_universe`, `regen_creation`, `ingestion` | 170 | `PlayerCardMarketplaceService`, `MarketService`, `PlayerService`, `LegendaryPlayerRegistryService`, `RegenCreationService` |
| **Clubs & Club Management** | `clubs`, `lineups`, `squad_tiers`, `academy`, `club_growth`, `club_identity/jerseys`, `club_identity/trophies`, `club_identity/dynasty`, `club_identity/reputation` | 82 | `ClubService`, `LineupService`, `SquadTierService`, `AcademyFacilityEconomyService`, `ClubGrowthService` |
| **Club Ownership & Sales** | `club_ownership`, `club_sale_market`, `ownership_groups` | 63 | `ClubOwnershipService`, `ClubSaleMarketService`, `OwnershipGroupService` |
| **Gifting & Gift Economy** | `gift_engine` | 17 | `GiftEngineService`, `GiftStabilizer` |
| **Leaderboards & Rankings** | `leaderboards`, `ranking_integrity`, `awards` | 15 | `LeaderboardService`, `RankingIntegrityService`, `AwardEngine` |
| **Competitions & Tournaments** | `competitions`, `hosted_competition_engine`, `fast_cups`, `streamer_tournament_engine`, `world_super_cup`, `champions_league`, `infinite_league` | 96 | `CompetitionOrchestrator`, `HostedCompetitionService`, `FastCupService`, `StreamerTournamentService`, `InfiniteLeagueEngine` |
| **Matches & Gameplay** | `live_matches`, `live_match`, `matches`, `match_engine`, `broadcast_rights`, `broadcast_network`, `replay_archive`, `commentary`, `pundits` | 114 | `LiveMatchesService`, `GtexMatchRuntime` (Unity), `MatchSimulationEngine`, `BroadcastRightsService`, `ReplayArchiveService` |
| **Rewards & Daily Tasks** | `daily_challenge_engine`, `reward_engine`, `story_feed_engine` | 10 | `DailyChallengeService`, `RewardEngineService` (`seed_economic_policy`) |
| **Currencies & Wallets** | `wallets`, `treasury`, `coin_traders`, `matchday_economy`, `integrations/payments` | 128 | `WalletService` (`LedgerPosting`), `TreasuryService`, `CoinTradersService` |
| **Fan Systems & Social** | `fan_predictions`, `fan_wars`, `viral`, `community_engine`, `club_social`, `news_engine` | 130 | `FanPredictionService`, `FanWarsService`, `ViralFeedService`, `CommunityEngineService` |
| **Notifications & Messages** | `notifications`, `attachments` | 15 | `NotificationService`, `NotificationMatrix` |
| **Marketplace & Trading** | `transfer_market`, `manager_market`, `creator_marketplace`, `ads_engine` | 64 | `TransferMarketService` (`PlayerLifecycleService`), `ManagerMarketService` |
| **Ownership States & Portfolio** | `portfolio`, `portfolios`, `value_engine` | 10 | `PortfolioService`, `ValueSnapshot` |
| **User Profile & Account** | `users`, `auth`, `access_control`, `risk_ops_engine`, `moderation`, `dispute_engine` | 89 | `UserService`, `AuthService`, `RiskOpsEngineService` |
| **Administration & Ops** | `admin_engine`, `admin_godmode`, `admin_finance`, `launch_control`, `observability`, `surveillance`, `operations_readiness` | 96 | `AdminEngineService`, `GodmodeService`, `LaunchControlService` |
| **Specialist Domains** | `betting`, `ticketing`, `ai_reporter`, `ai_manager`, `global_memory` | 27 | `BettingEngine`, `TicketingService`, `AiReporterService` |

---

## 2. API-TO-UI MAPPING

The table below details how backend API endpoints map to Flutter services, providers, controllers, and presentation screens in the active shell:

| Domain Capability | Primary Backend Route | Flutter Service / Provider | Active Shell Route | Presentation Screen / Component |
|---|---|---|---|---|
| **Player Card Marketplace** | `POST /api/player-cards/listings/{id}/purchase` | `PlayerCardMarketplaceService` | `/player-cards` | `PlayerCardMarketplaceScreen` |
| **Player Share Trading** | `POST /market/orders` | `MarketApi` / `GteExchangeApiClient` | `/player-market` | `GtexPlayerMarketRedesignScreen` |
| **Real Player Detail** | `GET /players/{id}` | `PlayerApi` / `LiveProfileProvider` | `/players/:playerId/profile` | `GtexFmPlayerProfileScreen` |
| **Build-a-Son Request** | `POST /api/regen-creation/request-son` | `RegenCreationApi` | `/regens/request` | `GtexCreateSonScreenV2` |
| **Youth Academy & Prospects** | `POST /academy/promote/{player_id}` | `AcademyApi` | `/club/academy` | `AcademyOverviewScreen` |
| **Lineup & Tactics** | `PUT /lineups/{club_id}` | `LineupApi` | `/lineup` | `GtexLineupEditorScreen` |
| **Jersey & Badge Customization** | `PUT /api/club-identity/clubs/{id}/jersey` | `ClubIdentityApi` | `/club/jersey-editor` | `JerseyEditorScreen` / `BadgeEditorScreen` |
| **Club Sale Market** | `POST /api/club-sale-market/listings/{id}/buy` | `ClubSaleMarketApi` | `/club-sale-market` | `ClubSaleMarketScreen` |
| **GTEX Competitions Hub** | `POST /api/competitions/{id}/join` | `CompetitionsApi` | `/competitions` | `GteCompetitionsHubScreenV2` |
| **Hosted Competitions** | `POST /hosted-competitions/create` | `HostedCompetitionApi` | `/competitions/hosted` | `CompetitionDiscoveryScreen` |
| **Streamer Tournaments** | `POST /streamer-tournaments/{id}/join` | `StreamerTournamentApi` | `/streamer-tournaments` | `StreamerTournamentEngineScreen` |
| **Live Match Center** | `GET /api/live-matches/{id}/events` | `LiveMatchesApi` | `/match-center` | `GtexMatchCenterScreenV2` |
| **3D Match Viewer (Unity)** | `GET /live-match/{matchId}/render-sync` | `GtexMatchRuntime` | `/matches/3d` | `GtexMatch3dScreen` |
| **Match Simulation Engine** | `POST /api/match-engine/simulate` | `MatchEngineApi` | `/matches/simulate` | `GtexMatchSimulationScreen` |
| **Broadcast Desk** | `GET /api/broadcast-rights/live` | `BroadcastRightsApi` | `/matches/broadcast` | `BroadcastPackageScreen` |
| **Replay Archive** | `GET /api/replay-archive/{match_id}` | `ReplayArchiveApi` | `/matches/replays` | `ReplayArchiveRouteScreen` |
| **Daily Challenges & Tasks** | `POST /api/daily-challenges/{id}/claim` | `DailyChallengeApi` | `/tasks` | `GtexDailyChallengesScreen` |
| **User Wallet & Orders** | `POST /api/wallets/deposit` | `WalletApi` | `/wallet` | `GtexWalletOrdersScreen` |
| **Coin Economy / Traders** | `POST /api/coin-traders/buy-sell` | `CoinTradersApi` | `/coin-traders` | `GtexAdminCoinEconomyScreenV2` |
| **Fan Predictions** | `POST /api/fan-predictions/predict` | `FanPredictionsApi` | `/fan-predictions` | `FanPredictionScreen` |
| **Fan Wars** | `POST /api/fan-wars/vote` | `FanWarsApi` | `/fan-wars` | `FanWarsScreen` |
| **Viral Clips Feed** | `POST /api/viral/clips/{id}/like` | `ViralApi` / `EventService` | `/viral-feed` | `ViralFeedScreen` |
| **Social Fan Hub & Chat** | `POST /api/community/messages` | `CommunityApi` | `/community` | `GtexSocialFanHubScreenV2` |
| **Notifications Center** | `PUT /api/notifications/{id}/read` | `NotificationsApi` | `/notifications` | `GtexNotificationsScreenV2` |
| **Transfer Center Offers** | `POST /api/transfer-market/listings/{id}/contract-offer` | `TransferMarketApi` | `/football/transfer-center` | `TransferCenterScreen` |
| **Manager Marketplace** | `POST /api/manager-market/hire` | `ManagerMarketApi` | `/managers` | `ManagerAdminScreen` |
| **Admin Command Center** | `GET /api/admin-engine/bootstrap` | `AdminEngineApi` | `/admin` | `GtexAdminCommandCenterScreenV2` |
| **God Mode Operating Console** | `GET /api/admin/god-mode/bootstrap` | `AdminGodmodeApi` | `/admin/god-mode` | `ProfileGodModeScreen` |
| **Trust Ops & Risk Cases** | `PUT /api/risk-ops/cases/{id}` | `RiskOpsApi` | `/admin/trust-ops` | `GtexAdminTrustOpsScreenV2` |
| **Launch Control Flags** | `PUT /api/launch-control/flags/{key}` | `LaunchControlApi` | `/admin/launch-control` | `GtexFeatureFlagsLaunchControlScreenV2` |

---

## 3. FRONTEND / BACKEND PARITY MATRIX

Status values used strictly from requirement: `COMPLETE`, `PARTIAL`, `DISCONNECTED`, `MISSING UI`, `MISSING BACKEND`, `UNREACHABLE`, `PLACEHOLDER`, `UNCERTAIN`.

| Capability | Backend | API | Route | UI | Action | States | Permissions | E2E | Status |
|---|---|---|---|---|---|---|---|---|---|
| **Player Card Marketplace** | `player_cards/router.py` | `POST /api/player-cards/listings/{id}/purchase` | `/player-cards` | `PlayerCardMarketplaceScreen` | Purchase Card Button | Loading, Success, Insufficient Funds Error | Authenticated Session | Yes (`PlayerCardMarketplaceService`) | **COMPLETE** |
| **Player Share Trading** | `market/router.py` | `POST /market/orders` | `/player-market` | `GtexPlayerMarketRedesignScreen` | Place Buy/Sell Order | Order Book Sync, Insufficient Balance Error | Authenticated Session + Club Context | Yes (`MarketService` / `WalletService`) | **COMPLETE** |
| **Real Player Profile** | `players/router.py` | `GET /players/{id}` | `/players/:playerId/profile` | `GtexFmPlayerProfileScreen` | View Attributes, Holdings, Valuation | Tab Switching, Portfolio CTA | Public / Authenticated | Yes (`PlayerService`) | **COMPLETE** |
| **Build-a-Son (Regens)** | `regen_creation/router.py` | `POST /api/regen-creation/request-son` | `/regens/request` | `GtexCreateSonScreenV2` | Custom Son Form Submit | TOML Cost Calc, Success Modal, Error | Authenticated Session | Yes (`RegenCreationService`) | **COMPLETE** |
| **Legendary Player Layer** | `legend_layer/router.py` | `GET /api/legend-layer/players` | `/world/regens` | `GtexRegenWorldScreenV2` | View Legend Catalog | Filter by Era / Country, Catalog view | Public / Authenticated | Yes (`LegendaryPlayerRegistryService`) | **PARTIAL** |
| **Real Player Ingestion Import** | `ingestion/router.py` | `POST /internal/ingestion/real-players/import` | `/admin` | `GtexAdminCommandCenterScreenV2` | Trigger Import Batch Button | Progress Meter, Error Banner | Admin + `manage_manager_catalog` | Yes (`IngestionService`) | **COMPLETE** |
| **Club Owner Dashboard** | `clubs/router.py` | `GET /clubs/me` | `/club` | `GtexClubOwnerDashboardV2` | View Squad, Fin, Stadium, Ops | Loading Skeleton, Retry State | Club Owner | Yes (`ClubService`) | **COMPLETE** |
| **Lineup & Tactics Editor** | `lineups/router.py` | `PUT /lineups/{club_id}` | `/lineup` | `GtexLineupEditorScreen` | Drag Player / Swap Position | Interactive Pitch Grid, Auto-Save Banner | Club Owner | Yes (`LineupService`) | **COMPLETE** |
| **Squad Tier Management** | `squad_tiers/router.py` | `PUT /squad-tiers/{club_id}` | `/club/squad-tiers` | `ClubScreen` | Move to Reserve / Academy | Tier Capacity Check, Re-assign Confirmation | Club Owner | Yes (`SquadTierService`) | **COMPLETE** |
| **Youth Academy & Scouting** | `academy/api/router.py` | `POST /academy/promote/{player_id}` | `/club/academy` | `AcademyOverviewScreen` | Promote Prospect to Squad | Capacity Limit Alert, Success Toast | Club Owner | Yes (`AcademyFacilityEconomyService`) | **COMPLETE** |
| **Jersey & Badge Editor** | `club_identity/jerseys/router.py` | `PUT /api/club-identity/clubs/{id}/jersey` | `/club/jersey-editor` | `JerseyEditorScreen` | Save Custom Colors & Pattern | 3D Preview Card, Save Spinner | Club Owner | Yes (`ClubIdentityService`) | **COMPLETE** |
| **Club Sale Marketplace** | `club_sale_market/router.py` | `POST /api/club-sale-market/listings/{id}/buy` | `/club-sale-market` | `ClubSaleMarketScreen` | Buy Club / Submit Bid | Purchase Modal, Cash Ledger Settlement | Authenticated Session | Yes (`ClubSaleMarketService`) | **COMPLETE** |
| **Club Ownership Groups** | `ownership_groups/router.py` | `POST /api/ownership-groups` | None | None | None | None | Admin Only | No | **MISSING UI** |
| **Gift Economy Admin Pools** | `gift_engine/router.py` | `POST /api/gift-engine/pools` | `/admin/gift-economy` | `GiftEconomyAdminScreen` | Create Pool, Adjust Allocations | Admin Metrics Grid, Settlement Logs | Admin | Yes (`GiftEngineService`) | **COMPLETE** |
| **User-to-User Gift Sending** | `gift_engine/router.py` | `POST /api/gift-engine/gifts/send` | None | None | None | None | Authenticated Session | No | **MISSING UI** |
| **Global Leaderboards** | `leaderboards/router.py` | `GET /api/leaderboards/users` | `/world/dynasty-leaderboard` | `DynastyLeaderboardScreen` | Filter by Season / Division | Ranked Table, Empty State | Public | Yes (`LeaderboardService`) | **COMPLETE** |
| **Trophy Cabinet & Leaderboard** | `club_identity/trophies/router.py` | `GET /api/club-identity/trophies/leaderboard` | `/world/trophy-leaderboard` | `TrophyLeaderboardScreen` | View Trophy History | Timeline Carousel, Ranked List | Public | Yes (`TrophyIdentityService`) | **COMPLETE** |
| **Prestige Leaderboard** | `club_identity/reputation/router.py` | `GET /api/club-identity/reputation/leaderboard` | `/world/prestige-leaderboard` | `PrestigeLeaderboardScreen` | Filter Prestige Metrics | Trend Chart, Tier Badges | Public | Yes (`ReputationIdentityService`) | **COMPLETE** |
| **GTEX Competitions Hub** | `competitions/router.py` | `POST /api/competitions/{id}/join` | `/competitions` | `GteCompetitionsHubScreenV2` | Join / Publish / Launch | Reserved Name Error, Joined Badge | Authenticated Session / `manage_competitions` | Yes (`CompetitionOrchestrator`) | **COMPLETE** |
| **Hosted Competitions** | `hosted_competition_engine/router.py` | `POST /hosted-competitions/create` | `/competitions/hosted` | `CompetitionDiscoveryScreen` | Custom Rule Builder & Launch | Entry Fee Calc, Bracket Generator | Authenticated Session | Yes (`HostedCompetitionService`) | **COMPLETE** |
| **Fast Cups Engine** | `fast_cups/api/router.py` | `POST /api/fast-cups/join` | `/competitions` | `GteCompetitionsHubScreenV2` | Fast Cup Lane View | Active Tournament Summary Card | Authenticated Session | Yes (`FastCupService`) | **PARTIAL** |
| **Streamer Tournament Engine** | `streamer_tournament_engine/router.py` | `POST /streamer-tournaments/{id}/join` | `/streamer-tournaments` | `StreamerTournamentEngineScreen` | Join Streamer Room / Bracket | Room Stream Feed, Bracket Tree | Authenticated Session | Yes (`StreamerTournamentService`) | **COMPLETE** |
| **World Super Cup** | `world_super_cup/api/router.py` | `GET /api/world-super-cup/fixtures` | `/competitions/world-super-cup` | `GteWorldSuperCupScreen` | View Qualification Standings | Qualification Matrix, Knockout Tree | Public | Yes (`WorldSuperCupService`) | **COMPLETE** |
| **Infinite League Engine** | `infinite_league/router.py` | `POST /api/infinite-league/simulate` | None | None | None | Background Service Status | System | No | **MISSING UI** |
| **Live Match Center** | `live_matches/router.py` | `GET /api/live-matches/{id}/events` | `/match-center` | `GtexMatchCenterScreenV2` | Live Ticker, Tactics Change | Event Timeline, Halftime Analytics | Authenticated / Public | Yes (`LiveMatchesService`) | **COMPLETE** |
| **3D Match Viewer (Unity)** | `live_match/router.py` | `GET /live-match/{matchId}/render-sync` | `/matches/3d` | `GtexMatch3dScreen` | Camera Toggle, Speed Control | Render Sync Stream, Fallback Screen | Authenticated Session | Yes (`GtexMatchRuntime`) | **COMPLETE** |
| **Match Simulation Sandbox** | `match_engine/api/router.py` | `POST /api/match-engine/simulate` | `/matches/simulate` | `GtexMatchSimulationScreen` | Run Match Simulation | Simulation Report Grid | Public / Demo | Yes (`MatchSimulationEngine`) | **COMPLETE** |
| **Broadcast Desk** | `broadcast_rights/router.py` | `GET /api/broadcast-rights/live` | `/matches/broadcast` | `BroadcastPackageScreen` | Overlay Switch, Stream Select | Stream Video Canvas, Sponsor Overlay | Public / Broadcaster | Yes (`BroadcastRightsService`) | **COMPLETE** |
| **Replay Archive** | `replay_archive/router.py` | `GET /api/replay-archive/{match_id}` | `/matches/replays` | `ReplayArchiveRouteScreen` | Replay Scrubber, Event Marker | Event Playback Timeline | Public | Yes (`ReplayArchiveService`) | **COMPLETE** |
| **Daily Challenges & Tasks** | `daily_challenge_engine/router.py` | `POST /api/daily-challenges/{id}/claim` | `/tasks` | `GtexDailyChallengesScreen` | Claim Task Reward Button | Streak Banner, Claimed State | Authenticated Session | Yes (`DailyChallengeService`) | **COMPLETE** |
| **User Wallet & Orders** | `wallets/router.py` | `POST /api/wallets/deposit` | `/wallet` | `GtexWalletOrdersScreen` | Deposit Cash / Withdraw Coin | KYC Verification Gate, Ledger Table | Authenticated Session | Yes (`WalletService`) | **COMPLETE** |
| **Coin Economy / Traders** | `coin_traders/router.py` | `POST /api/coin-traders/buy-sell` | `/coin-traders` | `GtexAdminCoinEconomyScreenV2` | Buy / Sell Coin Packages | Price Band Indicator, Transaction Log | Authenticated Session / Admin | Yes (`CoinTradersService`) | **COMPLETE** |
| **Fan Predictions** | `fan_predictions/router.py` | `POST /api/fan-predictions/predict` | `/fan-predictions` | `FanPredictionScreen` | Submit Score Prediction | Confidence Slider, Leaderboard | Authenticated Session | Yes (`FanPredictionService`) | **COMPLETE** |
| **Fan Wars** | `fan_wars/router.py` | `POST /api/fan-wars/vote` | `/fan-wars` | `FanWarsScreen` | Vote for Club Banner | Dynamic Dominance Bar, Rivalry Card | Authenticated Session | Yes (`FanWarsService`) | **COMPLETE** |
| **Viral Clips Feed** | `viral/router.py` | `POST /api/viral/clips/{id}/like` | `/viral-feed` | `ViralFeedScreen` | Like / Share Clip Button | Reliable Queue Action, Guest Gate Screen | Authenticated Session (Guest Gated) | Yes (`ViralFeedService`) | **COMPLETE** |
| **Community Social Hub** | `community_engine/router.py` | `POST /api/community/messages` | `/community` | `GtexSocialFanHubScreenV2` | Send Post / Chat Message | Realtime Feed, Flag Thread Dialog | Authenticated Session | Yes (`CommunityEngineService`) | **COMPLETE** |
| **User Notifications** | `notifications/router.py` | `PUT /api/notifications/{id}/read` | `/notifications` | `GtexNotificationsScreenV2` | Mark Read, Archive Notification | Unread Count Badge, Filter Tabs | Authenticated Session | Yes (`NotificationService`) | **COMPLETE** |
| **Admin Notification Matrix** | `notifications/router.py` | `POST /api/notifications/broadcast` | `/admin/notifications` | `GtexAdminNotificationMatrixScreen` | Broadcast System Alert | Target User Selector, Delivery Audit | Admin | Yes (`NotificationMatrix`) | **COMPLETE** |
| **Transfer Center Offers** | `transfer_market/router.py` | `POST /api/transfer-market/listings/{id}/contract-offer` | `/football/transfer-center` | `TransferCenterScreen` | Submit Private Contract Offer | Negotiation History, Salary Slider | Club Owner Context | Yes (`TransferMarketService`) | **COMPLETE** |
| **Manager Marketplace** | `manager_market/router.py` | `POST /api/manager-market/hire` | `/managers` | `ManagerAdminScreen` | Hire Manager / Appoint Personal Mgr | Staff Role Validation, Contract Cost | Club Owner | Yes (`ManagerMarketService`) | **COMPLETE** |
| **Admin Command Center** | `admin_engine/router.py` | `GET /api/admin-engine/bootstrap` | `/admin` | `GtexAdminCommandCenterScreenV2` | Trigger Queue Batch, System Health | Health Indicators, Metric Grid | Admin Role | Yes (`AdminEngineService`) | **COMPLETE** |
| **God Mode Console** | `admin_godmode/router.py` | `GET /api/admin/god-mode/bootstrap` | `/admin/god-mode` | `ProfileGodModeScreen` | Force State Advance, User Audit | Audit Permission Check, System Tree | Admin + `view_audit_log` | Yes (`GodmodeService`) | **COMPLETE** |
| **Trust Ops & Risk Cases** | `risk_ops_engine/router.py` | `PUT /api/risk-ops/cases/{id}` | `/admin/trust-ops` | `GtexAdminTrustOpsScreenV2` | Freeze Account, Resolve Case | Case Severity Badge, Action Log | Admin / Compliance | Yes (`RiskOpsEngineService`) | **COMPLETE** |
| **Launch Control Flags** | `launch_control/router.py` | `PUT /api/launch-control/flags/{key}` | `/admin/launch-control` | `GtexFeatureFlagsLaunchControlScreenV2` | Toggle Feature Flag | Real-Time Switch, Environment Pill | Admin | Yes (`LaunchControlService`) | **COMPLETE** |
| **Betting Engine** | `betting/router.py` | `POST /api/betting/place` | None | None | None | Fenced / Disabled | Disabled | No | **DISCONNECTED** |
| **Stadium Ticketing** | `ticketing/router.py` | `POST /api/ticketing/purchase` | `/creator-stadium` | `CreatorStadiumMonetizationScreen` | Adjust Ticket Prices | Price Tier Card, Revenue Projection | Stadium Owner | Yes (`TicketingService`) | **PARTIAL** |

---

## 4. MISSING USER SURFACES

The following capabilities exist in backend controllers and database schemas but lack dedicated routed screens in the active Flutter shell:

1. **Infinite League Engine (`backend/app/infinite_league/router.py`):**
   - **Backend Capabilities:** 8 endpoints for generating infinite fixture streams, bracket states, and autonomous match runs.
   - **Gap:** No dedicated user screen or tournament tab is exposed in the active shell. It operates exclusively as a supporting match generation service behind other competition managers.
2. **Club Ownership Groups (`backend/app/ownership_groups/router.py`):**
   - **Backend Capabilities:** 8 endpoints for multi-club holding structures, syndicate equity management, and group cashflow consolidation.
   - **Gap:** No multi-club management dashboard exists for non-admin users in the UI.
3. **User-to-User Direct Gifting (`backend/app/gift_engine/router.py`):**
   - **Backend Capabilities:** Endpoints for sending player cards, share quantities, or Fan Coins directly between GTEX user profiles.
   - **Gap:** The frontend features an administrative gift pool control panel (`GiftEconomyAdminScreen`), but lacks a direct user-to-user gifting modal on player profile or social surfaces.
4. **Broadcast Rights Bidding Portal (`backend/app/broadcast_rights/router.py`):**
   - **Backend Capabilities:** Endpoints for bidding on league media packages, territorial rights allocation, and distributor licensing.
   - **Gap:** The UI includes the `BroadcastPackageScreen` for viewing streams, but bidding on commercial rights packages has no user-facing portal.

---

## 5. DISCONNECTED WORKFLOWS

The following workflows exist in code but have severed connections or fenced runtime execution paths:

1. **Betting / Wagering Engine (`backend/app/betting/router.py`):**
   - **Backend Capabilities:** 4 endpoints for match betting pools, odds calculation, and payout settlement.
   - **Status:** **DISCONNECTED**. Intentionally fenced off from the active production shell for legal and regulatory compliance.
2. **Legacy `go_router` Routing System (`frontend/lib/router/app_router.dart`):**
   - **Architecture Conflict:** GTEX maintains two parallel routing frameworks: the active `gte_app_route_registry.dart` custom shell registry vs. the legacy 74-route `go_router` tree.
   - **Effect:** Deep links targeting legacy routes (e.g. `/market/transfers`) rely on `app_router.dart` fallbacks rather than the active shell spine.
3. **Summary Federation Join Action (`frontend/lib/features/world/widgets/world_screen_widgets.dart`):**
   - **Status:** **BLOCKED**. The join federation button on the world summary widget is explicitly kept in a disabled state until federation context providers complete full session wiring.

---

## 6. INCOMPLETE INTERACTIONS

The following UI surfaces expose partial backend capability or suffer from degraded user state feedback:

1. **Fast Cups Tournament Lane (`GteCompetitionsHubScreenV2`):**
   - **Issue:** Users can discover active Fast Cups in the competitions hub, but creating or configuring a new Fast Cup relies on administrative script calls rather than a user modal.
2. **Legendary Player Layer Minting (`GtexRegenWorldScreenV2`):**
   - **Issue:** Users can view legendary player catalog cards and historical stats, but minting or issuing legendary shares is gated behind admin tools (`LegendaryPlayerRegistryService`).
3. **Guest Viral Clips Route Gate (`ClipsBlockedScreen`):**
   - **Issue:** Non-authenticated guest users who navigate to `/viral-feed` are stopped by an explicit `ClipsBlockedScreen` requiring login, rather than viewing a read-only preview mode.

---

## 7. HIGHEST-PRIORITY PARITY PROBLEMS

| Rank | Domain | Problem Description | Impact | Recommended Remediation |
|---|---|---|---|---|
| **1** | **Routing Architecture** | Dual parallel routing systems (`go_router` vs. custom route registry). | Risk of deep link failures and state desynchronization across navigation tabs. | Deprecate legacy `go_router` tree in favor of single unified custom route registry. |
| **2** | **Gifting Engine** | Missing user-to-user gift modal in social & player detail screens. | Backend supports user gifting, but users cannot initiate gifts from UI. | Add "Send Gift" action sheet on `GtexFmPlayerProfileScreen` wired to `POST /api/gift-engine/gifts/send`. |
| **3** | **Fast Cups** | Read-only tournament lane with missing user creation flow. | Users cannot host quick fast cup tournaments directly. | Add "Host Fast Cup" action dialog in `GteCompetitionsHubScreenV2`. |
| **4** | **Broadcast Rights** | Missing commercial rights bidding surface for media creators. | Monetization capabilities are restricted to backend scripts. | Expose media rights bidding card inside `CreatorStudioHubScreenV2`. |
| **5** | **Ownership Groups** | Missing multi-club syndicate management UI. | Advanced multi-club owners cannot manage group allocations in UI. | Mount multi-club syndicate widget inside `GtexClubOwnerDashboardV2`. |

---
*Report certified complete by Jules (GTEX Principal Systems & Security Engineer).*
