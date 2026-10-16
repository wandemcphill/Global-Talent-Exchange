# GTEX Fallback, Mock, and Demo Audit

## Reachable From The Active Shell

| Category | File(s) | Reachable from active shell? | Status after sweep | Notes |
| --- | --- | --- | --- | --- |
| Explicit demo route | `frontend/lib/features/match/match_simulate_screen.dart` | yes | DEMO | Kept reachable, but explicitly labeled demo. |
| Explicit blocked route | `frontend/lib/features/match/match_native_3d_blocked_screen.dart` | yes | BLOCKED | Native 3D is not claimed as live. |
| Guest clips route gate | `frontend/lib/features/viral_feed/presentation/clips_blocked_screen.dart` | yes | BLOCKED | Added so guests no longer mount the live feed and then fail deep in the repository. |
| Federation join summary action | `frontend/lib/features/world/world_screen.dart` | yes | BLOCKED | Left disabled until a real federation join flow exists. |

## Fallback-Capable Clients Still In Repo But Fenced Off From The Shipped Runtime

| File(s) | Fallback type | Active-shell reachability | Why it is not silently used now |
| --- | --- | --- | --- |
| `frontend/lib/data/gte_api_repository.dart` | `liveThenFixture` fallback wrapper | not reachable on critical active-shell surfaces | `criticalBackendModeProvider` in `frontend/lib/shared/providers/auth_provider.dart` coerces the shipped runtime to `GteBackendMode.live` unless the app is explicitly started in fixture mode. |
| `frontend/lib/data/gte_authed_api.dart` | fallback-aware authed client | not reachable on critical active-shell surfaces | The active shell injects `criticalBackendModeProvider`, which is now live-only in normal shipped runs. |
| `frontend/lib/data/competition_api.dart` | fixture store fallback | fenced | `competitionApiProvider` is used through live providers configured with `criticalBackendModeProvider`; GTEX join in the active shell no longer uses `CompetitionApi.joinCompetition(...)`. |
| `frontend/lib/data/hosted_competition_api.dart` | fixture store fallback | fenced | Active-shell hosted competition providers run in `live` mode. |
| `frontend/lib/data/gte_exchange_api_client.dart` | reliable API repository with fixtures | fenced | The active shell passes live mode, so wallet/compliance surfaces do not silently fall back. |

## Legacy Mock / Demo Providers Not Wired To The Active Shell

These files remain in the repo, but they are not used by `frontend/lib/main.dart` + `frontend/lib/navigation/app_router.dart`:

- `frontend/lib/shared/providers/club_provider.dart`
- `frontend/lib/shared/providers/tasks_provider.dart`
- `frontend/lib/shared/providers/regen_provider.dart`
- `frontend/lib/shared/providers/exchange_hub_provider.dart`
- `frontend/lib/shared/providers/transfer_provider.dart`
- `frontend/lib/shared/providers/match_provider.dart`

## Local-Only Or Fake-Persistence Actions Remaining On Shipped Core Surfaces

- None found on core LIVE surfaces after this sweep.
- The only remaining local-only shipped action is the explicitly labeled demo match simulation route.

## Silent Fallback Paths Removed Or Neutralized

- Session hydration no longer drops backend permissions during `mergeProfile(...)`; admin gating now reads hydrated truth instead of stale token-time claims.
- Guest `/clips` no longer mounts the live feed and masks auth failures behind generic load errors.
- GTEX competition join on the active shell no longer goes through the non-auth `CompetitionApi.joinCompetition(...)` client path.
- Admin import/share issuance no longer present live buttons to scoped admins who cannot complete the backend mutation.

## Remaining Backend Contract Risk Outside The Active Shell

- `backend/app/segments/competitions/segment_competitions.py` now protects authenticated active-shell publish/launch actions with `manage_competitions`, and authenticated joins must match the session user.
- The legacy anonymous publish/launch/join path still exists when no bearer token is supplied. That does not affect the shipped Flutter runtime anymore, but it remains a backend hardening gap for non-active clients and should be retired separately.
