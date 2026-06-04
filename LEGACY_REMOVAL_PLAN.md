# GTEX Legacy Removal Plan

Generated: 2026-06-04

Instruction honored: identify only. No legacy files were removed.

## Removal Policy

Do not delete a legacy system until all are true:

1. Replacement path is mounted in production navigation.
2. Route/API contract tests pass.
3. Frontend analyzer passes.
4. Full related feature tests pass.
5. Dirty-tree ownership is resolved.
6. Rollback path is documented.

## Legacy and Duplicate Systems

| System | Observed paths | Replacement path | Complexity | Risk | Delete candidate |
|---|---|---|---|---|---|
| Legacy match UI/data/controllers | old/deleted `frontend/lib/features/match/**`, old match route tests, old simulation wrappers | `frontend/lib/features/match_center/**` plus backend `live_matches`, `realtime`, `match_viewer`, `match_engine` | High | Critical | Not yet |
| Legacy 3D/native runtime | `frontend/lib/features/3d/**`, `Gtex_Test_Migration/**`, `backend/app/api_v1/router.py` legacy websocket format, `backend/app/live_matches/router.py` legacy access helpers | Quarantined 2D backend-authoritative Match Center | High | Critical | Only outside allowed quarantine after tests pass |
| Local match simulation | `frontend/test/match/match_simulation_engine_test.dart`, `frontend/test/match/gtex_match_simulation_screen_test.dart` | Backend-authored realtime match state | Medium | High | Not until stale tests/contracts are updated |
| Competition hub duplicates | `frontend/lib/navigation/app_router.dart`, old competitions hub tests, new `frontend/lib/features/compete/**` | `/app/compete` bracket surface and canonical competition APIs | High | Critical | Not yet |
| Backend competition engine overlap | `backend/app/competitions/**`, `backend/app/competition_engine/**`, `backend/app/hosted_competition_engine/**`, league/cup/national-team engines | Canonical competition/hosted/streamer contracts | High | Critical | No |
| Duplicate admin systems | `backend/app/admin/**`, `admin_engine`, `admin_godmode`, `admin_finance`, `admin_access`, frontend admin screens/islands | `/app/admin` command center with role-guarded domain APIs | Medium | High | No |
| Duplicate capital systems | old wallet/trader/share/club-sale/dispute surfaces, new `frontend/lib/features/capital/**` | Capital wallet/trader/settlement/disputes/liquidity/payout surfaces | Medium | High | No |
| Creator market/stadium/share legacy | old creator share/stadium/league routes and surfaces | Canonical creator island plus capital liquidity where appropriate | Medium | Medium | No |
| API v1 legacy websocket routes | `backend/app/api_v1/router.py` `/api/v2/ws/*` and legacy match runtime bridge | `backend/app/realtime/router.py`, `backend/app/live_matches/router.py` canonical realtime streams | Medium | High | Not until websocket hydration/collision tests pass |
| Legacy material route host | `frontend/lib/features/app_routes/gte_navigation_helpers.dart` fallback comment | Central GoRouter spine | Low | Medium | After all feature routes migrate |

## 3D/Native Reference Boundary

Allowed/quarantine candidates:

- `frontend/lib/features/3d/**`
- `Gtex_Test_Migration/**`
- explicit tests proving quarantine behavior

References outside those areas should be audited before removal:

- `backend/app/api_v1/router.py` legacy match runtime websocket branch.
- `backend/app/live_matches/router.py` legacy runtime access helpers and websocket payload paths.
- `frontend/lib/features/app_routes/gte_navigation_helpers.dart` legacy route-host fallback.
- generated API contract references to legacy board/routes.
- docs/manifests that still point users toward legacy runtime paths.

## Recommended Sequence

1. Freeze dirty tree ownership.
2. Fix analyzer/test contract drift for match monetization, settlement readiness, and legacy blocked route expectations.
3. Make `/app/compete` and Match Center the only production navigation paths.
4. Add websocket route collision checks.
5. Convert legacy route tests into explicit quarantine tests.
6. Remove or archive old deleted systems in one reviewed PR per domain.
7. Regenerate API route maps and prove no production navigation points to removed paths.

## Removal Verdict

Do not remove legacy systems yet. The codebase still has failing tests that reference old contracts and route behavior. Removing now would hide the integration truth rather than improve production readiness.

