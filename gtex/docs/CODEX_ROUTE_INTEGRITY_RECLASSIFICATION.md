# CODEX Route Integrity Reclassification

## Purpose
This report translates the silent-fallback audit into route decisions. The target state is simple: no user-visible GTEX route may silently downgrade into fabricated, fixture-backed, or stub-backed data while presenting itself as live.

## Action Legend
- `KEEP LIVE`: keep the route as a live route, but remove all fixture fallback and fail closed on backend errors.
- `CONVERT TO BLOCKED`: route stays addressable, but shows an explicit unavailable or backend-not-connected state.
- `CONVERT TO PREVIEW`: route may remain visible only if every non-live behavior is explicitly labeled preview and no believable fake domain data is rendered.
- `CONVERT TO DEMO`: route is intentionally local and explicitly disclosed as demo.
- `HIDE FROM ACTIVE SHELL`: remove the route from shell navigation and quick entry points until it is safe.
- `REWIRE TO REAL BACKEND`: retain the route objective, but replace fallback or mock plumbing with real backend dependencies before the route is visible again.

## Route Decisions
| Route / screen | Backing repo / client | Current fallback or mock behavior | Recommended action | Remains in active shell |
| --- | --- | --- | --- | --- |
| `HomeDashboardScreen` deep links to club and competition surfaces | `home_dashboard_screen.dart` pushes `ClubProfileScreen` and `CompetitionDiscoveryScreen` with `widget.backendMode` | Home itself is not the problem; the problem is that it bypasses the live-only provider path when opening deep club and competition surfaces. | `KEEP LIVE` | Yes |
| `Navigation shell club destination` -> `ClubHubScreen` | `ClubController.standard` -> `ClubApi.standard` -> mock identity, stub trophies, fixture store, local-only branding and catalog persistence | Active shell surface claims club data is live while club hub data, identity, trophies, prestige, showcase panels, branding, catalog, and admin moderation are fixture-backed or local-only. | `HIDE FROM ACTIVE SHELL` | No |
| `ClubProfileScreen` | `ClubController.standard` -> `ClubApi.standard` | Deep club profile route still inherits fixture-backed club state and contains live profile save copy. | `CONVERT TO BLOCKED` | No |
| `ClubOpsScreenHost` and child screens: `AcademyOverviewScreen`, `AcademyPlayersScreen`, `AcademyPlayerDetailScreen`, `AcademyProgramsScreen`, `AcademyTrainingScreen`, `ClubFinanceScreen`, `ClubBudgetScreen`, `ClubCashflowScreen`, `ClubSponsorshipsScreen`, `ClubSponsorshipCatalogScreen`, `ClubSponsorshipContractScreen`, `ScoutingDashboardScreen`, `ScoutingAssignmentsScreen`, `ScoutingProspectsScreen`, `ScoutingProspectDetailScreen`, `YouthPipelineScreen` | `ClubOpsApi.standard` | Finance, sponsorship, academy, scouting, and youth dashboards silently degrade to fixture data on network, parsing, `notFound`, `validation`, and `unauthorized` failures. | `CONVERT TO BLOCKED` | No |
| `ClubAdminScreen` and club analytics overlays: `ClubOpsAdminScreen`, `AcademyAnalyticsScreen`, `ClubFinanceAnalyticsScreen`, `ClubSponsorshipAnalyticsScreen`, `ScoutingAnalyticsScreen` | `ClubController.standard`, `ClubApi.standard`, `ClubOpsApi.standard` | Admin club surfaces inherit the same fallback-capable club and club-ops stacks, then add fixture-backed analytics. | `CONVERT TO BLOCKED` | No |
| `ClubIdentityScreen` | `ClubIdentityApiRepository.standard` or direct `MockClubIdentityRepository()` | The route can instantiate a mock repository directly and otherwise falls back to fixtures. It is the only club route with a legitimate preview use case. | `CONVERT TO PREVIEW` | No |
| `Club reputation routes` -> `ClubReputationOverviewScreen`, history, leaderboard | `ReputationApiRepository.standard` -> `FixtureReputationRepository` | Prestige history and leaderboard data can be served from seeded reputation fixtures. | `CONVERT TO BLOCKED` | No |
| `Club trophy routes` -> cabinet, timeline, leaderboard | `StubTrophyCabinetRepository` through `ClubApi` or trophy repositories | Trophy history is stubbed with believable club honors. | `CONVERT TO BLOCKED` | No |
| `Club dynasty routes` -> overview, history, leaderboard | `DynastyApiRepository.standard` -> `DynastyFixtureRepository` | Dynasty profiles and leaderboards degrade into seeded fixture history. | `CONVERT TO BLOCKED` | No |
| `Competitions route` -> `CompetitionDiscoveryScreen` | `CompetitionApi.standard` | Direct route construction uses `CompetitionApi.standard`, which can return `_CompetitionFixtureStore` data for list, detail, financials, create, publish, join, and invite flows. | `KEEP LIVE` | Yes |
| `CommunityHubScreen` | `DiscoveryApi.standard`, `CommunityApi.standard`, `NotificationSettingsApi.standard`, `StoryFeedApi.standard`, `ModerationApi.standard`, `DisputeEngineApi.standard`, `GovernanceApi.standard` | Active shell route mixes seeded discovery rails, fake search results, seeded community threads and messages, and fixture-backed governance, moderation, dispute, story, and notification surfaces. | `HIDE FROM ACTIVE SHELL` | No |
| `Creator community path` -> `ReferralHubScreen`, `CreatorDashboardScreen`, `CreatorProfileScreen` | `CreatorController` -> `CreatorApi.standard`; `CreatorApplicationApi.standard`; `ReferralApi.standard` | Creator profile, finance, leaderboard, copilot analysis, and application state can come from fixtures. Referral placeholder sharing is honest, but the backing creator stack is not live-only. | `CONVERT TO PREVIEW` | No |
| `CreatorLeaderboardScreen` | `CreatorApi.fetchCreatorLeaderboard()` | Admin leaderboard currently returns fixture data directly. | `CONVERT TO BLOCKED` | No |
| `AdminCommandCenterScreen` | `AdminEngineApi.standard`, `PolicyAdminApi.standard` | Feature flags, calendar rules, reward rules, and policy surfaces are fallback-capable and can silently become fixtures. | `HIDE FROM ACTIVE SHELL` | No |
| `AdminFinancialDashboardScreen` | `AdminFinanceApi.standard` | Control-tower and simulation results can come from seeded finance fixtures while the copy presents a live economy board. | `CONVERT TO BLOCKED` | No |
| `GodModeAdminScreen` | direct admin HTTP stack plus fallback-capable backend mode and deceptive live treasury copy | Hidden admin route is still launched from the shell and presents live rails and live treasury language without a live-only guarantee. | `HIDE FROM ACTIVE SHELL` | No |
| `GteTreasuryOpsScreen` | `GteExchangeApiClient` and fallback-capable exchange repository | Treasury settings and queues can ride the fallback-capable exchange repository, yet the route uses direct success language for updates. | `CONVERT TO BLOCKED` | No |
| `Matches route` -> `MatchScreen` | live match shell route | This route is comparatively honest and explicitly says it does not use local match fixtures. | `KEEP LIVE` | Yes |
| `Simulation route` -> `MatchSimulateScreen` | local simulation engine | Already explicit that the route is local and demo-only. | `CONVERT TO DEMO` | No |
| `Deep match viewer routes` -> `gtex_match_viewer_screen.dart`, `gtex_match_broadcast_screen.dart`, `gte_live_match_center_screen.dart`, `gte_halftime_analytics_screen.dart`, `gte_match_highlights_screen.dart`, live spectate session services | `MatchViewerMapper`, `live_match_fixtures.dart`, `HybridLiveMatchSnapshotFeedService`, `HybridLiveCommentaryFeedService`, `GteExchangeApiClient.joinMatchSpectateSession`, `MockMatchLiveSubscriptionService` | Viewer sessions, snapshots, commentary, highlights, and event streams can be fabricated by fallback code. | `CONVERT TO BLOCKED` | No |
| `Market route` -> `GteMarketPlayersScreen` | `exchangeApiClientProvider` via `criticalBackendModeProvider`; shared `GteExchangeApiClient` | Active shell route is currently protected by live-only provider wiring, but the shared client still contains synthetic fallback methods that must not leak back into routed use. | `KEEP LIVE` | Yes |
| `Player detail route` -> `GteExchangePlayerDetailScreen` | shared `GteExchangeApiClient`; `PlayerService` action helper | The route uses a shared client that contains synthetic player detail and overview fallback paths, and player actions silently succeed on failure through `PlayerService`. | `KEEP LIVE` | No |

## Direct Wiring Changes Required Before Any Route Stays Live
- `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`: default routed dependencies to `GteBackendMode.live`.
- `frontend/lib/features/app_routes/gte_feature_route_builders.dart`: remove `_withApi` fixture fallback from routed surfaces.
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`: stop constructing club, community, competition, creator, and admin surfaces from raw `widget.backendMode`.
- `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`: stop pushing deep club and competition screens with inherited fallback-capable mode.
- `frontend/lib/features/app_routes/gte_app_route_registry.dart`: routed screen construction must use live-only dependencies for routes classified `KEEP LIVE`.

## Copy Reclassification Rules
- Any route classified `CONVERT TO BLOCKED` must remove `live`, `synced`, `saved`, and `updated` success language.
- Any route classified `CONVERT TO PREVIEW` may use only `preview`, `local`, or `not connected` language.
- Any route classified `KEEP LIVE` must show backend errors directly and may not substitute believable fixture data.
- Any route classified `CONVERT TO DEMO` must retain the existing honest demo disclosure pattern used by `MatchSimulateScreen`.

## Safe Carve-Outs
- `criticalBackendModeProvider` and `shared/providers/live_clients_provider.dart` are the current pattern to preserve for truly live surfaces.
- `MatchScreen` is currently the cleanest example of a route that fails honestly instead of fabricating data.
- `MatchSimulateScreen` is the reference pattern for allowed local simulation.
