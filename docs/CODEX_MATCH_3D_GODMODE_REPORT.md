# CODEX Match 3D God Mode Report

## Executive Summary

- The active shipped runtime remains `frontend/lib/main.dart` plus `frontend/lib/navigation/app_router.dart`.
- The active Matches tab now reads the live `/api/broadcast/home` contract and does not ship mock match business data as live.
- The active shell now exposes:
  - `2D` via `/matches/viewer/:matchKey`
  - `PSEUDO_3D` via `/matches/broadcast/:matchKey`
  - `FLUTTER_3D` via `/matches/3d/:matchKey`
  - `NATIVE_3D` truth via `/matches/native-3d`
- Native 3D is not operational in the shipped app. The Flutter 3D route is live, but the native `match_3d` / `match_3d/events` bridge is unavailable and stays blocked.
- God Mode is now reachable from the active shell at `/profile/admin/god-mode` for authenticated admin sessions that can pass the bootstrap access gate.
- Delegated admin escalation is fixed. Delegated admins now resolve to a scoped baseline instead of inheriting the unrestricted `god_mode` role by default.
- Bootstrap admin creation is now env-driven and disabled by default instead of relying on production-intended hardcoded credentials.

## Active Shipped Routes

- `/matches`
  - Active overview page backed by `/api/broadcast/home`
- `/matches/spectate`
  - Manual match-key probe path using the live viewer repository
- `/matches/viewer/:matchKey`
  - Shipped 2D viewer route
- `/matches/broadcast/:matchKey`
  - Shipped pseudo-3D / broadcast route
- `/matches/3d/:matchKey`
  - Shipped 3D replay route using Flutter 3D fallback unless a native bridge is actually available
- `/matches/native-3d`
  - Honest blocked status page for native 3D
- `/profile/admin`
  - Active-shell admin tools page
- `/profile/admin/god-mode`
  - Active-shell God Mode entrypoint with real access preflight

## Frontend to Backend Wiring

- `frontend/lib/features/match/live_match_overview_provider.dart`
  - `GET /api/broadcast/home`
- `frontend/lib/features/match/live_match_viewer_route_support.dart`
  - `GET /api/match-viewer/{matchKey}`
  - `GET /api/match-viewer/{matchKey}/session`
  - best-effort `POST /api/matches/{matchKey}/spectate`
- `frontend/lib/features/profile/profile_god_mode_screen.dart`
  - preflight `GET /api/admin/god-mode/bootstrap`
- `frontend/lib/screens/admin/god_mode_admin_screen.dart`
  - existing `/api/admin/god-mode/*` endpoints remain the source of truth
- `frontend/lib/shared/providers/auth_provider.dart`
  - session hydration `GET /api/auth/me`

## Capability Matrix

| Surface | Status | Truth |
| --- | --- | --- |
| Matches overview | LIVE | Uses `/api/broadcast/home`; shows BLOCKED when auth or backend is missing instead of falling back to local demo data. |
| 2D viewer | LIVE | `/matches/viewer/:matchKey` uses the live match-viewer bootstrap and session payloads. |
| Pseudo-3D viewer | LIVE | `/matches/broadcast/:matchKey` reuses `GtexMatchBroadcastScreen` with live session loaders and `PSEUDO_3D` labeling. |
| 3D viewer | PARTIAL | `/matches/3d/:matchKey` is live as `FLUTTER_3D`; `NATIVE_3D` remains blocked because the platform bridge is unavailable. |
| Native 3D bridge | BLOCKED | No verified platform implementation for `match_3d` and `match_3d/events`; the shipped app does not label Flutter 3D as native. |
| God Mode dashboard | LIVE | `/profile/admin/god-mode` is exposed in the active shell for authenticated admin sessions that can reach bootstrap. |
| Delegated admin flow | LIVE | Delegated admins now resolve to `scoped_admin` plus additive scoped permissions, not the unrestricted `god_mode` baseline. |

## Native vs Flutter vs Pseudo 3D Truth

- `2D`
  - `frontend/lib/features/match/match_viewer_route_screen.dart`
- `PSEUDO_3D`
  - `frontend/lib/features/match/match_broadcast_screen.dart`
- `FLUTTER_3D`
  - `frontend/lib/features/match/match_3d_route_screen.dart`
  - backed by `frontend/lib/widgets/match_3d/gtex_3d_scene.dart`
- `NATIVE_3D`
  - only reported when `Match3DBridge.isNativeAvailable()` succeeds
  - current shipped truth: unavailable
- `BLOCKED`
  - explicit route and capability badge used when viewer bootstrap fails or native bridge is missing

## God Mode Availability Path

- `ProfileScreen`
  - shows `Open Admin` only for real admin sessions
- `ProfileAdminScreen`
  - shows `Open God Mode` only when `canAccessGodMode` is true
  - otherwise shows a blocked reason from active session state
- `ProfileGodModeScreen`
  - preflights `/api/admin/god-mode/bootstrap`
  - returns explicit blocked reasons such as:
    - `admin required`
    - `missing session claims`
    - `backend route unavailable`

## Delegated Admin Permission Model

- `SUPER_ADMIN`
  - implicit baseline role: `god_mode`
- `ADMIN`
  - implicit baseline role: `scoped_admin`
- explicit delegated assignment role
  - replaces the baseline role for delegated resolution
- explicit delegated permissions
  - additive on top of the delegated role only
- disabled delegated assignment
  - resolves to no delegated permissions

## Bootstrap Admin Model

- Default state
  - bootstrap admin creation disabled
- Env-driven settings
  - `GTE_BOOTSTRAP_ADMIN_ENABLED`
  - `GTE_BOOTSTRAP_ADMIN_EMAIL`
  - `GTE_BOOTSTRAP_ADMIN_PASSWORD`
  - `GTE_BOOTSTRAP_ADMIN_USERNAME`
  - `GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME`

## Remaining Blockers and Next Steps

- Native 3D remains blocked until real platform handlers are implemented for:
  - `match_3d`
  - `match_3d/events`
- The Matches overview is honest, but it still depends on authenticated access and actual broadcast channel publication from `/api/broadcast/home`.
- God Mode sections still depend on the existing backend permission model section-by-section. The active shell now exposes the route truthfully, but unsupported backend actions still need to continue surfacing their exact backend failures.
