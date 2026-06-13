# N43 — FULL ROUTER CONSOLIDATION AUDIT

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `f61d0edc`
Verdict: **PASS — one canonical router, integrity-enforced by tests; legacy surfaces quarantined, not duplicated**

## Single canonical router (confirmed)
- **Exactly one `GoRouter` instantiation** in the entire frontend: `frontend/lib/router/app_router.dart::buildGtexAppRouter()`. No competing routers.
- Route tree composed from four ordered sources:
  1. Static auth/public routes (`/`, `/public`, `/auth`, `/auth/login`, `/auth/region`, `/auth/signup`).
  2. `_buildLegacyCompetitionAliasRoutes()` — **explicit, intentional** legacy competition deep-links (`/competitions/gtex|hosted|streamer[/:id]`).
  3. `_buildRegisteredFeatureRoutes()` — from `GteAppRouteCatalog.registrations`, **sorted by specificity** (`_compareRouteRegistrationSpecificity`) so param routes never shadow static ones.
  4. `_buildCanonicalAppRoutes()` — shell roots + `:screen`, `:screen/:id`, `:screen/:id/:detail` nesting.

## No dead/orphan routes
- Router `errorBuilder` → `GteRouteIntegrityScreen.blocked` ("Route unavailable"). Unknown routes fail closed, visibly — no silent dead destinations.
- Unparseable registered routes also fall through to `_buildUnavailablePage` (same blocked screen).

## No duplicate destinations
- Legacy paths are **redirected, not re-implemented**: `_canonicalPathForLegacyReference()` maps `/home`,`/world*`→home; `/market*`,`/player-cards*`,`/football/transfer-center`→market; `/competitions*`,`/national-team*`→competitions; `/trader*`→wallet; `/clips`→community. One destination per surface; aliases collapse into it via redirect at `_normalizeInitialLocation`.

## Integrity enforced by tests (passed in N31: 871 green)
`frontend/test/router/route_coverage_test.dart` + `navigation_surface_truth_test.dart` assert:
- Canonical route constants match the shell tree (`/app`, `shellRoots`).
- Unknown/quarantined paths render "Route unavailable" (`findsNothing` shell, `findsOneWidget` blocked) — proves no orphan mounts.
- **Legacy 3D/match surfaces are NOT promoted** to visible nav and are **rejected by `GteAppRouteParser.parse` (`isNull`)** — quarantine enforced at the router, consistent with canonical 2D direction.
- Primary nav excludes placeholder routes (records only live routes).
- Supporting: `router/gtex_role_guard_test.dart` (role guards), `active_shell_route_mount_test.dart`, `gte_feature_routing_test.dart`, `competition_route_scope_lock_test.dart`, `match_3d_route_hardening_test.dart`, `match_3d_route_truth_test.dart`.

## Findings
| # | Severity | Finding |
|---|---|---|
| 1 | Info | Legacy competition alias routes (`_buildLegacyCompetitionAliasRoutes`) are intentional back-compat deep-links, integrity-tested. Keep. |
| 2 | Low | `route_constants.dart` + `GtexCanonicalAppRoutes` + `GteNavigationRoute` are three constant sources; all consistent and test-locked, but consolidating to one would reduce future drift risk. Not a blocker. |
| 3 | Info | 775-line `gte_app_route_registry.dart` is the single screen-builder dispatch; no duplicate registrations found. |

## Conclusion
Router is **consolidated and certified**: one production router, specificity-ordered, legacy surfaces redirected or quarantined, integrity asserted by passing tests. No duplicate destinations, no dead registrations, no orphan names promoted to nav. **No action required for closed beta.**
