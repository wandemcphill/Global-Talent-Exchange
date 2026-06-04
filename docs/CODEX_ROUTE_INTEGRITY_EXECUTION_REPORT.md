# CODEX Route Integrity Execution Report

Date: 2026-03-30

Runtime scope for this execution pass was limited to the shipped Flutter runtime:

- `frontend/lib/main.dart`
- `frontend/lib/navigation/app_router.dart`

No legacy shell runtime was revived.

## Executive Summary

- Shipped routed clients now default to `GteBackendMode.live` and fail closed on live-route errors.
- `/matches/viewer/:matchKey`, `/matches/3d/:matchKey`, and `/matches/spectate` now resolve to explicit blocked surfaces instead of probing or degrading into believable fallback behavior.
- `/matches/broadcast/:matchKey` remains visible and live-only.
- `/matches/simulate` remains explicit demo/local.
- `/profile/admin/god-mode` no longer exposes a shipped surface and now redirects back to `/profile/admin`.
- Active-shell routed providers were verified to clamp `liveThenFixture` down to `live`.

## Before / After Route Classification

| Route / Surface | Before | After | Notes |
| --- | --- | --- | --- |
| Home | Live route with routed fallback risk | Keep live | Routed dependencies remain live-only through `criticalBackendModeProvider`. |
| Matches | Live route with deep viewer routes still implying live entry | Keep live | Match hub stays live, but blocked/deep/demo routes are clearly separated. |
| Market | Live route with routed fallback risk | Keep live | Routed dependencies remain live-only through `criticalBackendModeProvider`. |
| Competitions | Live route with routed fallback risk | Keep live | Routed dependencies remain live-only through `criticalBackendModeProvider`. |
| `/matches/broadcast/:matchKey` | Visible live deep route | Keep live | Remains live-backed and fails closed on bootstrap failure. |
| `/matches/viewer/:matchKey` | Deep route that previously tried to open the 2D viewer lane | Convert to blocked | Now mounts `MatchRouteBlockedScreen`. |
| `/matches/3d/:matchKey` | Deep route that previously tried to open Flutter/native-backed 3D | Convert to blocked | Now mounts `MatchRouteBlockedScreen`. |
| `/matches/spectate` | Manual live probe route | Convert to blocked | Now mounts `MatchRouteBlockedScreen`. |
| `/matches/simulate` | Demo/local route | Keep demo | Remains explicitly local and separate from live spectating. |
| `/profile/admin/god-mode` | Hidden deep admin route still addressable from shipped runtime | Hide from active shell | Route now redirects to `/profile/admin`. |

## Preserved Existing Reclassifications

These surfaces were already reclassified in the tree and were preserved as-is during this execution pass:

- Hidden from active shell: `ClubHubScreen`, `CommunityHubScreen`, `AdminCommandCenterScreen`, `GodModeAdminScreen` shell entry.
- Blocked: `ClubProfileScreen`, `ClubOpsScreenHost`, club-admin overlays, `AdminFinancialDashboardScreen`, `GteTreasuryOpsScreen`.
- Preview: `ClubIdentityScreen`, `ReferralHubScreen`, `CreatorDashboardScreen`, `CreatorProfileScreen`.
- Demo/local: `MatchSimulateScreen`.

## Active-Shell Navigation Changes

- `ProfileAdminScreen` no longer exposes an `Open God Mode` action from the shipped shell.
- `AppRoutes.profileGodMode` now redirects to `AppRoutes.profileAdmin`.
- The matches hub still links to 2D, 3D, Broadcast+, spectate probe, native 3D disclosure, and simulate routes, but the blocked routes now disclose their blocked state honestly when opened.
- Route inventory metadata was updated so hidden deep routes no longer describe the blocked viewer lanes as live.

## Fallback Primitive Changes

- `frontend/lib/data/gte_authed_api.dart`
  - Default constructor mode changed from `liveThenFixture` to `live`.
  - `withFallback` was retained only as a compatibility helper for explicit fixture or quarantined legacy callers.
  - In `live` mode it now fails closed and rethrows instead of silently swallowing every error.
- `frontend/lib/data/gte_exchange_api_client.dart`
  - `GteExchangeApiClient.standard()` now defaults to `GteBackendMode.live`.
  - `joinMatchSpectateSession()` now throws `GteApiException.unavailable` when the real backend repository is absent instead of fabricating a spectate session.
- `frontend/lib/features/match/match_live_subscription.dart`
  - Default subscription service is now disconnected instead of mock-ticking live data.
- `frontend/lib/shared/providers/auth_provider.dart` plus `frontend/lib/shared/providers/live_clients_provider.dart`
  - Routed active-shell providers were validated to clamp configured `liveThenFixture` down to `live`.

## Copy Honesty Cleanup

- Match hub spectate-probe copy now labels the route as blocked instead of implying a live probe.
- Viewer route inventory summaries now describe blocked 2D, 3D, and spectate surfaces as blocked.
- Hidden God Mode inventory summary now describes the redirect back to the admin surface.
- Demo/local simulation copy remains explicitly local and non-live.

## Changed Files

Primary shipped-runtime and shared primitive files affected by this pass:

- `frontend/lib/data/gte_authed_api.dart`
- `frontend/lib/data/gte_exchange_api_client.dart`
- `frontend/lib/features/match/live_match_viewer_route_support.dart`
- `frontend/lib/features/match/match_live_subscription.dart`
- `frontend/lib/features/match/match_viewer_route_screen.dart`
- `frontend/lib/features/match_center/legacy_match_runtime_blocked_screen.dart`
- `frontend/lib/features/match/match_spectate_screen.dart`
- `frontend/lib/features/match/match_screen.dart`
- `frontend/lib/features/profile/profile_admin_screen.dart`
- `frontend/lib/features/profile/profile_god_mode_screen.dart`
- `frontend/lib/navigation/app_destinations.dart`
- `frontend/lib/navigation/app_router.dart`

Test coverage updated or added:

- `frontend/test/active_shell_route_mount_test.dart`
- `frontend/test/gte_authed_api_test.dart`
- `frontend/test/gte_exchange_api_client_test.dart`
- `frontend/test/live_clients_provider_test.dart`
- `frontend/test/match_3d_route_truth_test.dart`
- `frontend/test/match_simulate_screen_test.dart`
- `frontend/test/surface_runtime_proof_test.dart`

## Test Commands / Results

Passed:

```bash
flutter test test/active_shell_route_mount_test.dart test/navigation_surface_truth_test.dart test/profile_admin_visibility_test.dart test/match_3d_route_truth_test.dart test/match_broadcast_route_screen_test.dart test/gte_exchange_api_client_test.dart test/gte_api_repository_test.dart test/gte_authed_api_test.dart test/live_clients_provider_test.dart
```

Passed:

```bash
flutter test test/match_simulate_screen_test.dart
```

Passed:

```bash
flutter test test/surface_runtime_proof_test.dart
```

## Remaining Backlog / Intentional Deferrals

- Inactive or legacy-only APIs outside the shipped `main.dart` + `app_router.dart` runtime still contain `liveThenFixture` or fixture helpers. They were not rewritten in this pass because the task scope explicitly excluded reviving or broadening the legacy shell.
- No backend rewires were attempted for the blocked 2D, 3D, or spectate viewer routes. They remain blocked until real viewer/session/commentary/event contracts are available end to end.
- Existing preview and blocked placeholder surfaces outside the shipped runtime were preserved rather than expanded into new feature work.
