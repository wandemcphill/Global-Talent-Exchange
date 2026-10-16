# CODEX Silent Fallback Kill List

## Scope
This document converts the 2026-03-30 static integrity audit into a strict kill list for silent fallback, fabricated data, mock or stub-backed user-facing routes, and deceptive local persistence.

Source truth for this pass:
- `frontend/lib/data/gte_authed_api.dart`
- `frontend/lib/data/gte_api_repository.dart`
- `frontend/lib/data/gte_exchange_api_client.dart`
- `frontend/lib/data/live_match_fixtures.dart`
- `frontend/lib/services/match_viewer_mapper.dart`
- `frontend/lib/features/match/match_live_subscription.dart`
- `frontend/lib/data/club_api.dart`
- `frontend/lib/data/club_ops_api.dart`
- `frontend/lib/features/club_identity/**`
- `frontend/lib/data/community_api.dart`
- `frontend/lib/data/discovery_api.dart`
- `frontend/lib/data/creator_api.dart`
- `frontend/lib/data/competition_api.dart`
- `frontend/lib/data/admin_engine_api.dart`
- `frontend/lib/data/admin_finance_api.dart`
- `backend/app/core/config.py`

## Non-Negotiables
- No user-visible GTEX route may run in `GteBackendMode.liveThenFixture`.
- No live route may inject `Mock`, `Stub`, `Fixture`, or in-memory fallback repositories.
- No user-visible action may swallow failure and act successful.
- No local-only persistence may be described as live, saved, synced, or updated.
- Local simulation may remain only on routes already disclosed as demo or local.

## Global Fallback Primitives To Kill
| File | Current integrity failure | Required kill action |
| --- | --- | --- |
| `frontend/lib/data/gte_authed_api.dart` | `withFallback` catches any exception in `liveThenFixture` and returns fixtures. Auth, validation, and backend failures can degrade into believable fake data. | Remove from user-visible live routing. Replace with live-only behavior plus explicit blocked or preview states at the screen layer. |
| `frontend/lib/features/app_routes/gte_feature_route_builders.dart` | `_withApi` contains route-level `liveThenFixture` fallback, including hardcoded fallback payloads for routed screens. | Delete routed fallback helper usage. Route builders must return unavailable, blocked, or preview states instead of fixture payloads. |
| `frontend/lib/features/navigation_guards/gte_navigation_guards.dart` | `GteNavigationDependencies` defaults to `liveThenFixture` and factories pass that mode into routed repositories and authed API instances. | Change routed dependency defaults to `live`. Reject `liveThenFixture` for user-visible route construction. |
| `frontend/lib/controllers/club_controller.dart` | `ClubController.standard` defaults to `liveThenFixture` and mounts `ClubApi.standard`. | Remove default fallback mode. Force explicit live-only or explicit preview-only controllers. |
| `frontend/lib/data/gte_api_repository.dart` | Repository-wide fixture fallback exists across exchange, treasury, policy, analytics, and player endpoints. | Keep fixture support only behind non-routed demo harnesses. Live app code must fail closed. |
| `frontend/lib/data/gte_exchange_api_client.dart` | Injects `GteMockApi()` and synthesizes player detail, overview, career totals, seasonal progression, and match spectate sessions. | Delete synthetic fallback methods from routed client paths. Split demo utilities from the live client. |
| `frontend/lib/data/live_match_fixtures.dart` | Builds fabricated live match snapshots and returns them on failure. | Remove from live match routes. Keep only for explicit demo or simulation tooling. |
| `frontend/lib/services/match_viewer_mapper.dart` | Builds `fixture_fallback` match viewer state with canned events. | Replace with blocked state for any missing live viewer session. |
| `frontend/lib/features/match/match_live_subscription.dart` | Default provider returns `MockMatchLiveSubscriptionService`. | Replace with blocked or disconnected state until a real subscription feed exists. |
| `frontend/lib/data/player_service.dart` | Swallows scout, shortlist, and contact action failures and delays instead of surfacing the error. | Remove silent success path. Show blocked or unavailable action state until backend endpoints exist. |
| `backend/app/core/config.py` | Local backend defaults to startup seeding and `default_ingestion_provider="mock"`. | Fail closed for non-demo environments. Demo defaults must not masquerade as live wiring. |

## Route Entry And Wiring Bypass Points To Kill
| File | Current bypass | Required action |
| --- | --- | --- |
| `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart` | Builds `ClubHubScreen`, `CommunityHubScreen`, `CompetitionController`, `CreatorController`, and admin screens directly from `widget.backendMode`, not from `criticalBackendModeProvider`. | Route these surfaces through live-only dependencies or reclassify them as preview, demo, blocked, or hidden. |
| `frontend/lib/features/home_dashboard/home_dashboard_screen.dart` | Pushes `ClubProfileScreen` and `CompetitionDiscoveryScreen` directly with `widget.backendMode`. | Route through a live-only gateway or block these deep links until reclassified. |
| `frontend/lib/features/app_routes/gte_app_route_registry.dart` | Builds competition and club identity surfaces from `dependencies.backendMode`, which inherits the fallback-capable navigation dependency default. | Force route registry dependencies to live-only for live surfaces. |

## User-Facing Screen File Kill List

**Club Workspace**
- `frontend/lib/features/club_hub/presentation/club_hub_screen.dart`: default `liveThenFixture`, displays live sync copy while backed by mock or fixture-heavy club data.
- `frontend/lib/features/club_hub/widgets/club_hub_content.dart`: uses live presentation language such as `Live board` for a fixture-backed surface.
- `frontend/lib/screens/clubs/club_profile_screen.dart`: deep club profile route, default `liveThenFixture`, contains live profile save copy while club state is fixture-backed.
- `frontend/lib/screens/gte_club_identity_hub_screen.dart`: launches finance, sponsorship, academy, scouting, and youth routes with the inherited backend mode and contains live sync language for club identity flows.
- `frontend/lib/screens/admin/club_admin_screen.dart`: default `liveThenFixture`, mounts `ClubController.standard`, and loads admin state from the same fallback-capable club stack.

**Club Ops Host And Child Routes**
- `frontend/lib/screens/clubs/club_ops_screen_host.dart`: central host for club ops dashboards, default `liveThenFixture`, creates `ClubOpsApi.standard`.
- `frontend/lib/screens/clubs/academy_overview_screen.dart`
- `frontend/lib/screens/clubs/academy_players_screen.dart`
- `frontend/lib/screens/clubs/academy_player_detail_screen.dart`
- `frontend/lib/screens/clubs/academy_programs_screen.dart`
- `frontend/lib/screens/clubs/academy_training_screen.dart`
- `frontend/lib/screens/clubs/club_finance_screen.dart`
- `frontend/lib/screens/clubs/club_budget_screen.dart`
- `frontend/lib/screens/clubs/club_cashflow_screen.dart`
- `frontend/lib/screens/clubs/club_sponsorships_screen.dart`
- `frontend/lib/screens/clubs/club_sponsorship_catalog_screen.dart`
- `frontend/lib/screens/clubs/club_sponsorship_contract_screen.dart`
- `frontend/lib/screens/clubs/scouting_dashboard_screen.dart`
- `frontend/lib/screens/clubs/scouting_assignments_screen.dart`
- `frontend/lib/screens/clubs/scouting_prospects_screen.dart`
- `frontend/lib/screens/clubs/scouting_prospect_detail_screen.dart`
- `frontend/lib/screens/clubs/youth_pipeline_screen.dart`

All of the screens above inherit the same fallback-capable `ClubOpsScreenHost` and must not remain live while `ClubOpsApi.standard` can fabricate dashboards on backend, auth, validation, or parsing failure.

**Club Admin Analytics Overlays**
- `frontend/lib/screens/admin/club_ops_admin_screen.dart`
- `frontend/lib/screens/admin/academy_analytics_screen.dart`
- `frontend/lib/screens/admin/club_finance_analytics_screen.dart`
- `frontend/lib/screens/admin/club_sponsorship_analytics_screen.dart`
- `frontend/lib/screens/admin/scouting_analytics_screen.dart`

These screens all route through `ClubOpsScreenHost` and therefore inherit the same silent fallback problem.

**Club Identity Routes**
- `frontend/lib/features/club_identity/jerseys/presentation/club_identity_screen.dart`: can instantiate `MockClubIdentityRepository()` directly when `apiBaseUrl` is absent and otherwise uses the fallback-capable API repository.
- `frontend/lib/features/club_identity/reputation/presentation/reputation_screen.dart`
- `frontend/lib/features/club_identity/dynasty/presentation/club_dynasty_overview_screen.dart`
- `frontend/lib/features/club_identity/dynasty/presentation/dynasty_screen.dart`
- `frontend/lib/features/club_identity/dynasty/presentation/dynasty_leaderboard_screen.dart`
- `frontend/lib/features/club_identity/dynasty/presentation/era_history_screen.dart`

**Competition And Creator Discovery**
- `frontend/lib/screens/competitions/competition_discovery_screen.dart`: default `liveThenFixture`, constructs `CompetitionApi.standard` directly.
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`: builds `CompetitionController` directly with `CompetitionApi.standard`.
- `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`: deep-links directly into `CompetitionDiscoveryScreen` with inherited backend mode.

**Community, Discovery, And Creator Community**
- `frontend/lib/screens/community/community_hub_screen.dart`: mounts `DiscoveryApi.standard`, `CommunityApi.standard`, `NotificationSettingsApi.standard`, `StoryFeedApi.standard`, `ModerationApi.standard`, `DisputeEngineApi.standard`, and `GovernanceApi.standard`. This route is currently exposed from the shell.
- `frontend/lib/screens/referrals/referral_hub_screen.dart`: the share-channel placeholder copy is honest, but the route still relies on a `CreatorController` built from fallback-capable creator APIs.
- `frontend/lib/screens/creators/creator_dashboard_screen.dart`
- `frontend/lib/screens/creators/creator_profile_screen.dart`
- `frontend/lib/screens/admin/creator_leaderboard_screen.dart`

**Admin Surfaces**
- `frontend/lib/screens/admin/admin_command_center_screen.dart`: mounts `AdminEngineApi.standard` and `PolicyAdminApi.standard`.
- `frontend/lib/screens/admin/admin_financial_dashboard_screen.dart`: mounts `AdminFinanceApi.standard` and uses live-economy copy against fixture-backed control-tower data.
- `frontend/lib/screens/admin/god_mode_admin_screen.dart`: default `liveThenFixture`, presents live rails and live treasury copy on a fallback-capable admin surface.
- `frontend/lib/screens/admin/treasury_ops_screen.dart`: default `liveThenFixture`, uses the fallback-capable exchange repository and success copy such as `Treasury settings updated.`.

**Matches**
- `frontend/lib/screens/match/gtex_match_viewer_screen.dart`: loads `MatchViewerMapper`, which can return `fixture_fallback` state.
- `frontend/lib/screens/match/gtex_match_broadcast_screen.dart`: same viewer fallback path as the 2D viewer.
- `frontend/lib/screens/competitions/gte_live_match_center_screen.dart`: uses `loadLiveMatchSnapshot`.
- `frontend/lib/screens/competitions/gte_halftime_analytics_screen.dart`: uses `loadLiveMatchSnapshot`.
- `frontend/lib/screens/competitions/gte_match_highlights_screen.dart`: uses `loadLiveMatchSnapshot`.
- `frontend/lib/features/match/live_match_session_service.dart`: relies on fallback-capable spectate session creation.

These screens must not keep live labeling while the match stack can fabricate sessions, commentary, highlights, and event streams.

**Market And Player Actions**
- `frontend/lib/screens/gte_market_players_screen.dart`: shell route is protected by live-only provider wiring today, but it still depends on a shared client with synthetic fallback methods.
- `frontend/lib/screens/gte_exchange_player_detail_screen.dart`: contains status copy that implies confirmed live refresh while the shared client can synthesize player detail and overview in fallback mode.

## Repository And API Client Kill List

**Club Stack**
- `frontend/lib/data/club_api.dart`: fixture store, mock identity repo, stub trophy repo, local-only save and purchase persistence, and dual fallback helpers.
- `frontend/lib/data/club_ops_api.dart`: fixture dashboards for finance, sponsorships, academy, scouting, youth pipeline, and analytics; falls back on `notFound`, `validation`, and `unauthorized`.
- `frontend/lib/features/club_identity/jerseys/data/club_identity_repository.dart`: `MockClubIdentityRepository` plus fallback on fixture-supporting, `notFound`, `unknown`, and parsing errors.
- `frontend/lib/features/club_identity/reputation/data/reputation_repository.dart`: `FixtureReputationRepository`.
- `frontend/lib/features/club_identity/trophies/data/trophy_cabinet_repository.dart`: `StubTrophyCabinetRepository`.
- `frontend/lib/features/club_identity/dynasty/data/dynasty_api_repository.dart`: `DynastyFixtureRepository` plus fallback behavior.

**Community And Discovery Stack**
- `frontend/lib/data/discovery_api.dart`: seeded discovery home, featured rails, fake search results, and live-now fixture story.
- `frontend/lib/data/community_api.dart`: seeded digest, watchlist, live threads, private messages, and local mutation of those fixtures.
- `frontend/lib/data/story_feed_api.dart`
- `frontend/lib/data/notification_settings_api.dart`
- `frontend/lib/data/dispute_engine_api.dart`
- `frontend/lib/data/governance_api.dart`
- `frontend/lib/data/moderation_api.dart`

The files above all use `GteAuthedApi.withFallback`, so backend failures can become believable user-facing fixtures.

**Competition And Creator Stack**
- `frontend/lib/data/competition_api.dart`: `_CompetitionFixtureStore.seed()` plus route-visible fallback for list, detail, financials, create, publish, join, and invite flows.
- `frontend/lib/data/creator_api.dart`: fixture profile, fixture leaderboard, and fixture copilot analysis.
- `frontend/lib/data/creator_application_api.dart`: fixture-backed verification and application state.
- `frontend/lib/data/referral_api.dart`: fallback-capable referral runtime.

**Admin Stack**
- `frontend/lib/data/admin_engine_api.dart`: fixture feature flags, calendar rules, and reward rules.
- `frontend/lib/data/admin_finance_api.dart`: fixture finance control tower and simulation results.
- `frontend/lib/data/policy_admin_api.dart`: fallback-capable admin policy surface.
- `frontend/lib/data/sponsorship_admin_api.dart`
- `frontend/lib/data/risk_ops_api.dart`

**Exchange And Match Stack**
- `frontend/lib/data/gte_mock_api.dart`: fixture exchange repository used by the routed client.
- `frontend/lib/data/gte_exchange_api_client.dart`: synthetic player, market, and match session fallback methods.
- `frontend/lib/data/live_match_fixtures.dart`: fabricated match snapshots.
- `frontend/lib/services/match_viewer_mapper.dart`: fabricated viewer session state.
- `frontend/lib/features/match/match_live_subscription.dart`: mock subscription provider.

## Deceptive Copy To Remove
| File | Current wording | Why it must go | Replacement direction |
| --- | --- | --- | --- |
| `frontend/lib/features/club_hub/presentation/club_hub_screen.dart` | `Squad, prestige, and club style are live.` | Club hub is fixture or stub-backed. | Use blocked or preview language only. |
| `frontend/lib/features/club_hub/widgets/club_hub_content.dart` | `Live board` | Labels a mocked club workspace as live. | Replace with `Preview board` or remove the pill entirely. |
| `frontend/lib/screens/clubs/club_profile_screen.dart` | `save club identity updates to the live profile` | Save path is local-only or preview-backed in current code. | Replace with preview-only wording until persistence is real. |
| `frontend/lib/screens/gte_club_identity_hub_screen.dart` | `sync club identity updates with live services` | Club identity stack is mock-backed. | Replace with preview wording or blocked state. |
| `frontend/lib/screens/clubs/scouting_dashboard_screen.dart` | `live assignments`, `more live signals`, `live recommendation` | Scouting dashboards are generated through fixture fallback. | Replace with blocked state or preview-only explanatory copy. |
| `frontend/lib/screens/admin/admin_financial_dashboard_screen.dart` | `LIVE ECONOMY`, `Last sync ... this board should show it first.` | Control-tower data can come from fixture simulation. | Replace with blocked state copy unless backend is real. |
| `frontend/lib/screens/admin/god_mode_admin_screen.dart` | `Treasury LIVE`, `Live rails` | Admin surface can run in fallback mode and is not safe to present as live. | Remove live language until route is truly backend-only. |
| `frontend/lib/screens/admin/treasury_ops_screen.dart` | `Treasury settings updated.` | Current stack is fallback-capable and can imply successful persistence after a degraded path. | Confirm real backend persistence before success messaging. |
| `frontend/lib/screens/gte_exchange_player_detail_screen.dart` | `Showing the latest confirmed profile while live data refresh completes.` | Shared client contains synthetic player fallback paths. | Use plain error or unavailable wording unless data is definitely cached live data. |

## Explicitly Honest Surfaces To Preserve
- `frontend/lib/features/match/match_screen.dart`: honest live-only match page copy.
- `frontend/lib/features/match/match_simulate_screen.dart`: explicit demo and local simulation disclosure.
- `frontend/lib/navigation/app_destinations.dart`: honest `Preview`, `Coming soon`, and placeholder route state labels.
- `frontend/lib/screens/referrals/referral_hub_screen.dart`: placeholder channel disclosure is honest and should be preserved if the route stays preview-only.

## Immediate Enforcement Order
1. Kill route-level `liveThenFixture` from club, community, competition, and admin entry points.
2. Delete or quarantine the shared fallback primitives in `GteAuthedApi`, `GteReliableApiRepository`, `GteExchangeApiClient`, `live_match_fixtures.dart`, and `match_viewer_mapper.dart`.
3. Reclassify every affected route to live, blocked, preview, demo, hidden, or rewired as captured in `docs/CODEX_ROUTE_INTEGRITY_RECLASSIFICATION.md`.
