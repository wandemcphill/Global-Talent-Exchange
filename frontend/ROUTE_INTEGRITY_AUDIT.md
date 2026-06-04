# Frontend Route Integrity Audit

Date: 2026-04-12

This audit closes A5-001 by listing every current hidden, placeholder, or integrity-wall route surface in the active shell and legacy admin/community shell, then assigning a keep/remove/implement decision.

## Active shell: keep as hidden deep routes

These routes are intentionally hidden in `frontend/lib/navigation/app_destinations.dart` because they are deep links, permission-gated routes, or route targets that already preserve backend truth without pretending they are primary navigation.

| Surface | Current state | Decision | Evidence | Rationale |
|---|---|---|---|---|
| Root | hidden | KEEP | `app_destinations.dart`, `app_router.dart` | Redirect-only route. It is not a user-facing surface. |
| Transfer Listing Detail | hidden | KEEP | `app_destinations.dart` | Deep transfer detail route behind the live transfer center. |
| Federation Detail | hidden | KEEP | `app_destinations.dart` | Deep world/federation route, not primary navigation. |
| National Team Detail | hidden | KEEP | `app_destinations.dart` | Deep national-team route, not primary navigation. |
| Sign In | hidden | KEEP | `app_destinations.dart`, `features/profile/profile_screen.dart` | Deep auth route intentionally launched from Profile actions. |
| Create Account | hidden | KEEP | `app_destinations.dart`, `features/profile/profile_screen.dart` | Deep auth route intentionally launched from Profile actions. |
| Profile Admin | hidden | KEEP | `app_destinations.dart`, `app_router.dart`, `features/profile/profile_screen.dart`, `features/profile/profile_admin_screen.dart` | The current active-shell admin entry point. Hidden from general nav, exposed only to signed-in admins. |
| Competition Family | hidden | KEEP | `app_destinations.dart` | Deep competition-family route behind the live competitions surface. |
| Competition Detail | hidden | KEEP | `app_destinations.dart` | Deep competition-detail route behind the live competitions surface. |
| 2D Match Viewer | hidden | KEEP | `app_destinations.dart` | Deep viewer route that is meant to open a qualified live viewer session or a truthful fallback. |
| Broadcast+ Viewer | hidden | KEEP | `app_destinations.dart` | Deep routed viewer lane, not a shell-level entry point. |
| 3D Match Viewer | hidden | KEEP | `app_destinations.dart` | Deep routed 3D lane, not a shell-level entry point. |

## Active shell: remove from active discovery until implemented

These surfaces still exist, but they should not stay visible in the shipped shell while they resolve to placeholders or blocked disclosures. If they remain in code for QA or future implementation, they should stay hidden and stop presenting themselves as normal user-facing options.

| Surface | Current state | Decision | Evidence | Rationale |
|---|---|---|---|---|
| God Mode | hidden | REMOVE | `app_destinations.dart`, `app_router.dart`, `features/profile/profile_god_mode_screen.dart`, `screens/admin/god_mode_admin_screen.dart` | The route already redirects to `profileAdmin`, and the old God Mode screen still lands on a hidden integrity wall. This is dead active-shell surface area. |
| Blocked Match Runtime | placeholder | REMOVE | `app_destinations.dart`, `app_router.dart`, `features/match/match_screen.dart`, `features/match_center/blocked_match_runtime_screen.dart` | The Matches tab still advertises a coming-soon disclosure, but the dedicated blocked-runtime route does not open a real live match contract yet. Remove it from active discovery until the route is real. |
| 2D Spectate Probe | hidden | REMOVE | `app_destinations.dart`, `app_router.dart`, `features/match/match_screen.dart`, `features/match/match_spectate_screen.dart` | The Matches tab exposes this as a blocked manual probe. Keep it QA-only if needed, but stop surfacing it in the live shell until live viewer sessions are actually served end to end. |
| Simulation | hidden | REMOVE | `app_destinations.dart`, `app_router.dart`, `features/match/match_screen.dart`, `features/match/match_simulate_route_screen.dart` | The route is explicitly fixture-only and mounts a blocked disclosure in live mode. It should not be presented as a normal live-shell lane. |

## Legacy admin shell integrity walls

These screens are still on disk and are the exact surfaces A5-003 needs to either wire end to end or intentionally keep out of the active shell. None of them should be promoted back into visible admin discovery while they still render `GteRouteIntegrityScreen`.

| Surface | Current state | Decision | Evidence | Rationale |
|---|---|---|---|---|
| God Mode admin screen | hidden | REMOVE | `screens/admin/god_mode_admin_screen.dart`, `features/profile/profile_god_mode_screen.dart`, `app_router.dart` | The probe screen still checks `/api/admin/god-mode/bootstrap`, but the concrete admin UI is a hidden integrity wall and the routed path already redirects away. |
| Treasury Ops | blocked | REMOVE | `screens/admin/treasury_ops_screen.dart` | Still blocked until settings, queues, and disputes are real-backend-only. |
| Admin Finance Dashboard | blocked | REMOVE | `screens/admin/admin_financial_dashboard_screen.dart` | Still blocked until economy control tower and simulations run against real backend only. |
| Creator Leaderboard | blocked | REMOVE | `screens/admin/creator_leaderboard_screen.dart` | Still blocked until creator rankings come from the real backend without fixture substitution. |
| Club Admin | blocked | REMOVE | `screens/admin/club_admin_screen.dart` | Still blocked until club admin and analytics are backed by the real club backend only. |

## Community shell integrity wall

| Surface | Current state | Decision | Evidence | Rationale |
|---|---|---|---|---|
| Community Hub | hidden | REMOVE | `screens/community/community_hub_screen.dart` | This screen is still a hidden integrity wall and should stay out of production-visible flows until the real backend replaces the seeded fallback rails. No current active-shell reference was found in `frontend/lib` beyond the screen itself. |

## Notes for the follow-on tasks

- A5-002 should remove the Matches-tab disclosures for Native 3D, 2D Spectate Probe, and Simulation from active user discovery in live mode.
- `features/navigation/presentation/gte_navigation_shell_screen.dart` still pushes `AdminCommandCenterScreen`, so A5-003 should treat that legacy launcher as part of the admin-shell cleanup instead of only editing the newer Profile-admin entry point.
- A5-003 should either implement or explicitly retire the blocked legacy admin screens above instead of leaving them as integrity-wall destinations on disk.
- A5-004 should keep the community hub out of production-visible flows until it can mount against real backend data.
