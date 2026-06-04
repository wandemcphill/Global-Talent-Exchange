# CODEX Fast Integration Repair Report

## A. Executive Summary

- The shipped runtime remains on `frontend/lib/main.dart` and `frontend/lib/navigation/app_router.dart`.
- The active shell now uses a reactive session source of truth instead of a startup-only auth snapshot.
- The active shell now configures the reliable event queue and flushes queued analytics only when an authenticated session is present.
- The active shell now exposes real login and signup entry paths, a streamer-engine bridge route, honest 2D and 3D match-viewer routes, and a God Mode bridge route without reviving the legacy shell.
- The hosted competition seed client bug was fixed from `GET` to `POST`.
- Backend admin integrity was tightened so delegated admins default to `scoped_admin` instead of inheriting full `god_mode`, and bootstrap-admin creation is now environment-driven instead of hardcoded in `backend/app/main.py`.

## B. Changed Files

### Frontend runtime, session, and routing

- `frontend/lib/main.dart`
- `frontend/lib/navigation/app_destinations.dart`
- `frontend/lib/navigation/app_router.dart`
- `frontend/lib/shared/models/auth_session.dart`
- `frontend/lib/shared/providers/auth_provider.dart`

### Frontend active-shell honesty surfaces

- `frontend/lib/features/home/home_screen.dart`
- `frontend/lib/features/competitions/live_competitions_hub_screen.dart`
- `frontend/lib/features/competitions/streamer_tournament_engine_route_screen.dart`
- `frontend/lib/features/match/live_match_overview_provider.dart`
- `frontend/lib/features/match/live_match_viewer_route_support.dart`
- `frontend/lib/features/match/match_screen.dart`
- `frontend/lib/features/match/match_spectate_screen.dart`
- `frontend/lib/features/match/match_broadcast_screen.dart`
- `frontend/lib/features/match_center/legacy_match_runtime_blocked_screen.dart`
- `frontend/lib/features/match_center/blocked_match_runtime_screen.dart`
- `frontend/lib/features/match/match_simulate_screen.dart`
- `frontend/lib/features/match/match_viewer_capability.dart`
- `frontend/lib/features/match/match_viewer_route_screen.dart`
- `frontend/lib/features/profile/profile_screen.dart`
- `frontend/lib/features/profile/profile_login_screen.dart`
- `frontend/lib/features/profile/profile_signup_screen.dart`
- `frontend/lib/features/profile/profile_admin_screen.dart`
- `frontend/lib/features/profile/profile_god_mode_screen.dart`
- `frontend/lib/features/viral_feed/presentation/viral_feed_screen.dart`
- `frontend/lib/screens/admin/god_mode_admin_screen.dart`
- `frontend/lib/features/match_center/presentation/gtex_match_runtime_blocked_screen.dart`
- `frontend/lib/services/match_3d_bridge.dart`

### Frontend API and tests

- `frontend/lib/data/hosted_competition_api.dart`
- `frontend/test/active_session_provider_test.dart`
- `frontend/test/active_shell_live_migration_smoke_test.dart`
- `frontend/test/active_shell_route_mount_test.dart`
- `frontend/test/hosted_competition_api_test.dart`
- `frontend/test/match/match_screen_broadcast_test.dart`
- `frontend/test/match_3d_bridge_scene_test.dart`
- `frontend/test/match_3d_route_truth_test.dart`
- `frontend/test/profile_admin_visibility_test.dart`

### Backend

- `backend/app/admin_access/router.py`
- `backend/app/admin_godmode/schemas.py`
- `backend/app/admin_godmode/service.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/tests/admin_access/test_admin_access_role_scoping.py`
- `backend/tests/admin_engine/test_admin_engine_router.py`
- `backend/tests/admin_godmode/test_bootstrap_admin.py`
- `backend/tests/conftest.py`

## C. Route-to-Endpoint Wiring Map

| Route | Active surface | Primary live wiring |
| --- | --- | --- |
| `/home` | Live aggregate hub | `/api/auth/me`, `/users/me`, `/users/me/profile`, `/users/{id}/followers`, `/users/{id}/following`, `/api/competitions`, `/hosted-competitions`, `/streamer-tournaments`, `/players/real-universe`, `/players/{player_id}/shares/market`, `/api/transfer-market/listings`, `/regen-universe/*`, `/federations`, `/daily-challenges`, `/daily-challenges/me` |
| `/matches` | Live matches overview | `/api/broadcast/home` plus viewer-specific bridges |
| `/matches/viewer` and `/matches/spectate` | 2D live viewer bridge | `/api/match-viewer/{matchKey}`, `/api/match-viewer/{matchKey}/session`, best-effort `/api/matches/{matchKey}/spectate` |
| `/matches/broadcast` | PSEUDO_3D viewer bridge | Same live match-viewer endpoints as 2D, opening the existing broadcast renderer |
| `/matches/3d` | FLUTTER_3D or NATIVE_3D viewer bridge | Same live match-viewer endpoints as 2D, opening the existing Flutter 3D viewer and labeling native availability honestly |
| `/matches/native-3d` | Explicit blocked route | No live endpoint call; route exists only to state that native 3D is not mounted in the active shell |
| `/matches/simulate` | DEMO local simulation | Existing local match simulation engine only |
| `/market` | Segmented live market | `/players/real-universe`, `/players/real-universe/search`, `/players/{player_id}/shares/market`, `/players/real-universe/{player_id}`, `/players/{player_id}/shares/events`, `/players/me/shares/holdings`, `/api/transfer-market/listings`, `/api/transfer-market/watchlist`, `/api/transfer-market/listings/{listingId}/bids`, wallet and compliance through the live exchange client |
| `/world` | Live world summary | `/regen-universe/rising-stars`, `/regen-universe/scouting-feed`, `/regen-universe/seasons`, `/regen-universe/awards`, `/regen-universe/hall-of-fame`, `/regen-universe/tracking`, `/federations`, plus competition family summaries |
| `/tasks` | Live challenges and tasks | `/daily-challenges`, `/daily-challenges/me`, `/daily-challenges/{challengeKey}/claim` |
| `/profile` | Live session and profile hub | `/api/auth/me`, `/users/me`, `/users/me/profile`, optional `/clubs/{clubId}` |
| `/profile/login` | Live auth entry | `POST /auth/login` through the live exchange client and secure session store |
| `/profile/signup` | Live auth entry | `POST /auth/register` through the live exchange client and secure session store |
| `/profile/admin` | Admin import hub | `/internal/ingestion/providers/{provider}/health`, `/internal/ingestion/real-players/status`, `/internal/ingestion/real-players/batches`, `/internal/ingestion/real-players/import`, `/internal/ingestion/real-players/batches/{batchId}/resume`, `/players/{playerId}/shares/issue` |
| `/profile/admin/god-mode` | God Mode bridge | Existing `GodModeAdminScreen` using `/api/admin/god-mode/*` and `POST /api/auth/change-password` |
| `/competitions` | Live family hub | `/api/competitions`, `/hosted-competitions`, `/streamer-tournaments` |
| `/competitions/:family` | Live family list | Family-specific list from the same endpoints above |
| `/competitions/:family/:id` | Live competition detail | GTEX: `/api/competitions/{id}`, `/api/competitions/{id}/standings`, `/api/competitions/{id}/fixtures`; Hosted: `/hosted-competitions/{id}`, `/hosted-competitions/{id}/finance`, `/hosted-competitions/{id}/standings`; Streamer: `/streamer-tournaments/{id}`, `/leaderboard/current-season` |
| `/competitions/streamer/engine` | Streamer engine bridge | Existing `StreamerTournamentEngineScreen`, driven by `/streamer-tournaments/*`, `/leaderboard/*`, and streamer admin endpoints |
| `/clips` | Live clips and feed | `/feed/for-you`, `/feed/following`, `/feed/for-you/refresh`, frontend audit hooks, and reliable event queue delivery to `/api/analytics/events` |

## D. LIVE / BLOCKED / DEMO Matrix

| Route | Status | Notes |
| --- | --- | --- |
| `/home` | LIVE | Live aggregate; no local club, match, or task cards as shipped truth |
| `/matches` | LIVE | Live overview from `/api/broadcast/home`, with explicit viewer-mode routing |
| `/matches/viewer` | LIVE | 2D viewer bridge |
| `/matches/spectate` | LIVE | Alias to the 2D viewer bridge |
| `/matches/broadcast` | LIVE | PSEUDO_3D |
| `/matches/3d` | LIVE | FLUTTER_3D by default, NATIVE_3D only when the bridge actually answers |
| `/matches/native-3d` | BLOCKED | Native renderer not mounted in the active shell |
| `/matches/simulate` | DEMO | Local-only simulation |
| `/market` | LIVE | Live player-share and transfer-listing segmentation; wallet and compliance may show blocked subsections when auth or policy prevents access |
| `/world` | LIVE | Live discovery surface; federation join remains explicitly blocked from this summary route |
| `/tasks` | LIVE | Live daily challenges and streaks; claims require real auth and session state |
| `/profile` | LIVE | Honest guest, auth, and admin summary route |
| `/profile/login` | LIVE | Real login path |
| `/profile/signup` | LIVE | Real signup path |
| `/profile/admin` | LIVE for admins, BLOCKED otherwise | Honest import and admin route |
| `/profile/admin/god-mode` | LIVE for eligible admins, BLOCKED otherwise | Strict gate before opening the shipped God Mode console |
| `/competitions` | LIVE | Family split preserved |
| `/competitions/:family` | LIVE | GTEX, hosted, and streamer families kept distinct |
| `/competitions/:family/:id` | LIVE or BLOCKED per backend availability | No fixture masking |
| `/competitions/streamer/engine` | LIVE | Honest bridge into the existing streamer engine |
| `/clips` | LIVE | Feed route visible and classified; auth-dependent actions remain auth-dependent |

## E. Test Commands and Results

### Frontend

Command:

```bash
flutter test test/active_shell_live_migration_smoke_test.dart test/active_shell_route_mount_test.dart test/active_session_provider_test.dart test/hosted_competition_api_test.dart
```

Result:

- Passed: `10` tests
- Coverage: active-shell route mounts, session controller update and clear behavior, auth visibility, viewer route smoke coverage, hosted competition seed verb regression

Command:

```bash
flutter test test/match_3d_bridge_scene_test.dart test/match_3d_route_truth_test.dart test/profile_admin_visibility_test.dart test/match/match_screen_broadcast_test.dart
```

Result:

- Passed: `9` tests
- Coverage: native-vs-Flutter 3D truth labeling, blocked match route behavior, admin-entry visibility on profile, blocked live-match overview behavior, and 3D bridge scene sync

### Backend

Command:

```bash
python -m pytest tests/admin_access/test_admin_access_role_scoping.py tests/admin_godmode/test_bootstrap_admin.py -q
```

Result:

- Passed: `6` tests
- Coverage: scoped admins do not inherit God Mode baseline permissions, super-admin baseline remains intact, disabled delegated assignments resolve to no delegated permissions, bootstrap admin defaults remain environment-driven and disabled by default

### Testing Note

- A broader `tests/app/test_main.py` run was not used for signoff because it was too slow and noisy for this repair pass.

## F. Remaining Blockers

- Federation join is still intentionally blocked from the World summary route because a verified live membership-create flow was not bridged into the active shell during this pass.
- Native 3D remains blocked unless the platform bridge actually responds. The active shell now says that explicitly instead of conflating it with Flutter 3D.
- Competition detail routes are live-backed, but their exact status still depends on backend endpoint availability per family and per item. They do not silently fall back.
- The richer legacy club, community, and profile surfaces were not mounted in this pass because they were not proven to be more honest or more live than the repaired active profile route.
- The repository already had unrelated in-progress backend and frontend changes outside this pass. They were not reverted or folded into this commit unless directly required.

## G. Surface Coverage Summary

### Home

- Local club, match, and task truth was removed from the active path.
- Home now routes to real competitions, the streamer engine, tasks, clips, and auth entry.

### Matches

- Match tab now reads `/api/broadcast/home` for live discovery and routes into the mounted viewers.
- 2D, pseudo-3D, Flutter 3D, native-3D-blocked, and simulation are explicitly separated.

### Market

- Active market remains segmented between player shares and transfer listings.
- `Tradable` depends on live share-market presence, not local provider state.

### World

- Active world is a live summary and discovery surface.
- Federation join remains blocked with the actual reason shown.

### Profile

- Guest, auth, and admin states are explicit.
- Real login and signup entry routes exist.

### Tasks

- Live daily challenges and streak flows are mounted.
- Claims use backend endpoints.

### Clips

- Clips is reachable from the active app.
- Route classification is visible in debug mode.

### Competitions Routes

- `/competitions`
- `/competitions/:family`
- `/competitions/:family/:id`
- `/competitions/streamer/engine`

### Match Viewer Routes

- `/matches/viewer`
- `/matches/spectate`
- `/matches/broadcast`
- `/matches/3d`
- `/matches/native-3d`
- `/matches/simulate`

### Admin Routes

- `/profile/admin`
- `/profile/admin/god-mode`
