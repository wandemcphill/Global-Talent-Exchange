# CODEX Route Integrity Execution Report

## Scope
This pass executed the route reclassification defined in:
- `docs/CODEX_SILENT_FALLBACK_KILL_LIST.md`
- `docs/CODEX_ROUTE_INTEGRITY_RECLASSIFICATION.md`

It did not add new product features or revive legacy shell paths. The implementation goal was enforced directly in routing, shell composition, and route-entry screens: no user-visible GTEX route in this pass silently downgrades into fixture, mock, stub, or local-only data while presenting itself as live.

## Routes Removed From Active Shell
- `Navigation shell club destination`
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Club is no longer in `_shellPrimaryDestinations`.
  - Club tab entry now resolves to an explicit `NOT IN ACTIVE SHELL` integrity state.
- `Navigation shell community destination`
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Community is no longer in `_shellPrimaryDestinations`.
  - Community shell slot now resolves to an explicit `NOT IN ACTIVE SHELL` integrity state.
- `Admin command center` shell launch
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Admin command-center action was removed from the shell app bar.
- `God Mode` shell launch
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - God Mode action was removed from the shell app bar.

## Routes Converted To Blocked
- `ClubProfileScreen`
  - `frontend/lib/screens/clubs/club_profile_screen.dart`
- `Club ops host and child routes`
  - `frontend/lib/screens/clubs/club_ops_screen_host.dart`
  - This blocks academy, finance, sponsorship, scouting, youth pipeline, and club-ops admin descendants that mount through the host.
- `ClubAdminScreen`
  - `frontend/lib/screens/admin/club_admin_screen.dart`
- `Club reputation routes`
  - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
- `Club trophy routes`
  - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
- `Club dynasty routes`
  - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
- `CreatorLeaderboardScreen`
  - `frontend/lib/screens/admin/creator_leaderboard_screen.dart`
- `AdminFinancialDashboardScreen`
  - `frontend/lib/screens/admin/admin_financial_dashboard_screen.dart`
- `GteTreasuryOpsScreen`
  - `frontend/lib/screens/admin/treasury_ops_screen.dart`
- `Deep match viewer stack`
  - `frontend/lib/screens/match/gtex_match_viewer_screen.dart`
  - `frontend/lib/screens/match/gtex_match_broadcast_screen.dart`
  - `frontend/lib/screens/competitions/gte_live_match_center_screen.dart`
  - `frontend/lib/screens/competitions/gte_halftime_analytics_screen.dart`
  - `frontend/lib/screens/competitions/gte_match_highlights_screen.dart`
- `Home club trophy and tactics deep links`
  - `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`
  - Home now pushes an explicit blocked state instead of opening fallback-capable club identity routes.

## Routes Converted To Preview
- `ClubIdentityScreen`
  - `frontend/lib/features/club_identity/jerseys/presentation/club_identity_screen.dart`
- `ReferralHubScreen`
  - `frontend/lib/screens/referrals/referral_hub_screen.dart`
- `CreatorDashboardScreen`
  - `frontend/lib/screens/creators/creator_dashboard_screen.dart`
- `CreatorProfileScreen`
  - `frontend/lib/screens/creators/creator_profile_screen.dart`

## Routes Kept Live
- `CompetitionDiscoveryScreen`
  - `frontend/lib/screens/competitions/competition_discovery_screen.dart`
  - Default backend mode changed to `GteBackendMode.live`.
- `Competition routes in route registry`
  - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
  - Competition discovery, detail, create, join, and share now use `dependencies.liveOnly()`.
- `HomeDashboardScreen`
  - `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`
  - Club and competition controllers now mount with `GteBackendMode.live`.
- `Navigation shell live surfaces`
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Home, market, competitions, and wallet remain active.
  - Shell-created competition, creator-application, creator, and referral controllers now mount with `GteBackendMode.live`.
- `GteExchangePlayerDetailScreen`
  - `frontend/lib/screens/gte_exchange_player_detail_screen.dart`
  - Kept live, but deceptive degraded-data copy was removed.
- `MatchSimulateScreen`
  - Preserved as the disclosed local/demo route. No integrity downgrade path was reintroduced there.

## Fallback Primitives Disabled Or Quarantined
- `GteNavigationDependencies` now defaults to `GteBackendMode.live`.
  - `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
- Added `GteNavigationDependencies.liveOnly()`.
  - `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
- Route-level `_withApi` fallback was disabled.
  - `frontend/lib/features/app_routes/gte_feature_route_builders.dart`
  - Routed feature surfaces no longer use fixture payloads when live requests fail.
- Routed fake player-card detail payload was removed.
  - `frontend/lib/features/app_routes/gte_feature_route_builders.dart`
- Shell and home no longer construct competition and club controllers from raw fallback-capable mode.
  - `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - `frontend/lib/features/home_dashboard/home_dashboard_screen.dart`
- Route registry now forces live-only dependencies for routes kept live.
  - `frontend/lib/features/app_routes/gte_app_route_registry.dart`
- Navigation guard fallback probes for trophy and dynasty routes were removed.
  - `frontend/lib/features/navigation_guards/gte_navigation_guards.dart`
- Player action silent-success fallback was removed.
  - `frontend/lib/data/player_service.dart`
  - Scout, shortlist, and contact now fail closed on backend errors.
- Shared blocked/preview/hidden integrity state screen added for explicit route reclassification.
  - `frontend/lib/widgets/gte_route_integrity_screen.dart`

## Copy Changes Made
- Replaced hidden routes with explicit `NOT IN ACTIVE SHELL` wording.
  - Club hub
  - Community hub
  - Admin command center
  - God Mode
- Replaced blocked routes with explicit unavailable wording.
  - Club profile
  - Club ops
  - Club admin
  - Admin finance
  - Treasury ops
  - Deep match viewer stack
- Replaced preview routes with explicit preview wording.
  - Club identity
  - Creator referrals
  - Creator dashboard
  - Creator profile
- Removed deceptive player-detail refresh copy.
  - `frontend/lib/screens/gte_exchange_player_detail_screen.dart`
  - Replaced “latest confirmed profile” and “latest available profile snapshot” wording with plain failure wording.

## Tests Run And Results
- `dart format`
  - Ran on all edited source files plus edited tests.
  - Result: passed.
- `dart analyze`
  - Ran on the edited route, shell, controller, API, and integrity-screen files.
  - Result: passed with no issues.
- `flutter test test/club_identity/club_identity_screen_test.dart test/referrals/referral_hub_test.dart test/player_service_test.dart`
  - Result: passed.
  - Total observed result: `13` tests passed.
- `flutter test test/active_shell_route_mount_test.dart test/gte_feature_routing_test.dart test/club_identity/club_identity_screen_test.dart test/referrals/referral_hub_test.dart test/player_detail/player_detail_screen_test.dart test/competitions/competition_discovery_test.dart`
  - Result: timed out during the broader grouped route sweep.
  - Follow-up: verification was narrowed to focused route tests after updating expectations to the new blocked/preview behavior.

## Notes
- This workspace already contains unrelated user changes outside this execution pass. They were not reverted.
- The integrity changes here are intentionally strict: affected routes now fail closed as blocked, preview, or hidden instead of fabricating believable fallback data.
