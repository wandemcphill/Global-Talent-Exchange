# GTEX Production Gap Report

Generated: 2026-06-04

Question: what prevents GTEX from launch today?

Answer: reproducibility, validation, route health, and integration ownership.

## Critical

| File / Area | Feature | Impact | Recommended fix |
|---|---|---|---|
| Repo root git worktree | Release governance | 862 dirty entries, including 217 deletions and 133 untracked files, make the candidate unreproducible and unsafe to ship. | Classify to owners, split into reviewed PRs, regenerate artifacts, then require clean release branch. |
| `frontend/test/match/broadcast_package_screen_test.dart`, `frontend/test/match_viewer_monetization_test.dart`, `frontend/test/surface_runtime_proof_test.dart` | Frontend build/test gate | `flutter analyze` exits 1 due stale match monetization and settlement readiness contracts. | Update tests/contracts to canonical Match Center and compete finance models; analyzer must pass. |
| Full `frontend/test/**` | Frontend acceptance | Full Flutter test suite exits 1 with 21 failures, including root shell smoke, active shell wallet nav, competitions, match simulation quarantine, trader blocked state. | Fix failing suites by domain; require full green run. |
| Full backend pytest | Backend acceptance | Full backend suite reached only 22% after 08:33:45 and already had 22 failure markers and 39 error markers. | Split slow suites, fix early failures, add CI sharding/time budgets, require full green backend run. |
| `backend/tests/app/test_module_registration_routes.py` / `backend/app/modules.py` | Backend route registration | 20 route contract failures before maxfail; many production routes return `410 Gone` where tests expect live/auth responses. | Decide route lifecycle per endpoint, update module mounts or tests, and add route registry ownership. |
| `backend/tests/competitions/**` | Compete backend | Competition/auth/discovery/financial/invite tests fail or error; create response missing `id` in one flow. | Stabilize competition API contracts before shipping `/app/compete`. |
| `backend/tests/players/test_transfer_bid_wallet_reservations.py` / `backend/app/wallets/service.py` | Transfer/wallet truth | Accepted bid reservation settlement fails shortfall/reserved-balance behavior. | Reconcile wallet reservation truth with transfer lifecycle expectations. |

## High

| File / Area | Feature | Impact | Recommended fix |
|---|---|---|---|
| `frontend/lib/router/app_router.dart` and `frontend/lib/navigation/app_router.dart` | Routing | Parallel routers can drift; tests may target routes production boot does not use. | Remove or quarantine legacy router after migration; route tests must target production router. |
| `backend/app/core/module.py` | Websocket safety | HTTP route collision checks do not clearly cover websocket routes. | Add websocket route fingerprint/collision checks and tests. |
| `backend/app/modules.py` / `backend/app/api_v1/router.py` | Websocket hydration | Lazy `api_v1` websocket routes may depend on prior HTTP/OpenAPI hydration. | Eager-register websocket modules or add websocket hydration path. |
| `frontend/lib/shared/realtime/**`, shell realtime providers | Realtime | Multiple provider families can open duplicate connections or mix contracts. | Consolidate production realtime provider ownership. |
| `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart` | Shell boot | Root shell smoke test expected `Home`, found none; active shell wallet tests missing labels/actions. | Align nav labels/routes/tests with current shell design and prove primary workflows. |
| Visual QA tooling | Visual release gate | Full desktop/tablet/mobile screenshots were not captured; browser automation unavailable. | Add deterministic screenshot CI using Flutter web/Playwright or golden route harness. |

## Medium

| File / Area | Feature | Impact | Recommended fix |
|---|---|---|---|
| `frontend/lib/features/club_hub/**`, `home_dashboard_screen.dart`, `gte_navigation_shell_screen.dart` | UI maintainability | Analyzer unreachable switch warnings indicate enum/state drift. | Remove unreachable cases or rework state enums. |
| `frontend/lib/features/squad/squad.dart` | Shared exports | Duplicate exports can create import ambiguity. | Deduplicate barrel exports. |
| `frontend/test/viral_feed/viral_feed_screen_test.dart` | Visual/interaction | Offscreen tap warning for WhatsApp share target. | Add scroll/viewport-safe interaction and responsive assertion. |
| `frontend/test/trader/trader_dashboard_screen_test.dart` | Capital/trader blocked state | Duplicate `Order book blocked` blocked-state copy. | Render a single canonical blocked state. |
| `backend/tests/regen/**` | Build-a-Son/regen/admin | Regen/admin RBAC and expansion tests fail/error. | Stabilize RBAC fixtures, migrations, and route contracts. |
| `frontend/lib/features/app_routes/gte_navigation_helpers.dart` | Routing migration | Legacy material route-host fallback remains. | Remove after all surfaces use central GoRouter. |

## Low

| File / Area | Feature | Impact | Recommended fix |
|---|---|---|---|
| Docs casing: `docs` and `Docs` | Repository hygiene | Mixed casing can confuse tooling and review. | Normalize docs location after reports are absorbed. |
| Generated artifacts | Build hygiene | Generated files/lockfiles/logs are mixed into dirty tree. | Regenerate deterministically and ignore transient logs. |
| Existing golden coverage | Visual QA | Only two committed golden PNGs found. | Expand route-level screenshot/golden coverage after app tests pass. |

## Production Readiness Assessment

Current production readiness: 38%.

Required work remaining: 62%.

This estimate is driven by failed analyzer, failed frontend tests, failed/unfinished backend tests, route contract failures, dirty-tree unreproducibility, and incomplete visual QA.

## Launch Blockers

- Dirty worktree governance unresolved.
- `flutter analyze` fails.
- Full Flutter test suite fails.
- Full backend pytest does not complete and already shows many failures/errors.
- Backend route/module contract suite fails.
- Competition backend/API contracts fail.
- Wallet transfer reservation truth fails.
- Full desktop/tablet/mobile visual screenshots not captured.

## Launch Risks

- Parallel frontend routers and duplicated realtime providers.
- Legacy 3D/native and match simulation references still visible outside clear quarantine boundaries.
- Websocket route collisions may be undetected.
- App web boot is very slow.
- Current tests encode both old and new product contracts, making pass/fail interpretation noisy.

## Recommended Next 30 Days

1. Freeze and reconcile the dirty tree into owned PRs.
2. Make frontend analyzer green.
3. Fix root shell, active shell wallet, competition hub, trader blocked state, and stale match monetization tests.
4. Fix backend route/module contract failures and competition API failures.
5. Add backend test sharding so full validation completes reliably.

## Recommended Next 60 Days

1. Collapse production routing onto one frontend router.
2. Consolidate realtime provider ownership.
3. Add websocket route collision tests.
4. Stabilize wallet/transfer reservation parity and regen/admin RBAC.
5. Build deterministic desktop/tablet/mobile visual QA automation.

## Recommended Next 90 Days

1. Remove legacy systems only after quarantine tests pass.
2. Harden operational runbooks for migrations, rollback, websocket health, and payment/wallet incidents.
3. Add release gates for clean worktree, analyzer, full frontend suite, full backend suite, route registry, visual QA, and Unity batchmode build if shipping native/3D.
4. Run a production dry run on a clean branch with seeded staging data and observability enabled.

