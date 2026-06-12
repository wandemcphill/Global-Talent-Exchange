# STAGING READINESS REPORT (N38)

Date: 2026-06-12
Branch: `feature/original-visual-runtime` @ `ca771311`
Verdict: **STAGING-READY for closed beta — with 3 environment/ops conditions to clear**

## Readiness matrix (evidence-based)

| Subsystem | Status | Evidence |
|---|---|---|
| Backend startup | ✅ READY | `create_app(run_migration_check=False)` composes **159 modules / 332 routes**; `test_lifespan.py` green; standalone compose green in release gate |
| Database readiness | ✅ READY | Startup schema smoke check passes (with auto-repair fallback); 567-table metadata builds; no DDL errors across ~221 executed tests |
| Wallet readiness | ✅ READY | 100 money-lane tests green; double-entry ledger, reservation lifecycle, KoraPay/manual rails, withdrawal holds all proven (N33) |
| Websocket readiness | ✅ READY (contract) | 6 realtime suites green; match/wallet gateways register; authority flags honored (N35) |
| Competition readiness | ✅ READY | Full create→settlement lifecycle green against canonical v2 API (N34) |
| Frontend startup | ⚠️ CONDITIONAL | `flutter analyze` 0 issues + `flutter test` 871 passed (N31), but a **release/web build was NOT produced** this cycle; CLI bootstrap is disk-pressure-flaky |
| Realtime under churn | ⚠️ CONDITIONAL | reconnect / stale-session / multi-device not load-tested (N35) |

## Conditions to clear before staging soak

1. **Disk pressure (P1, ops).** C: ~97% full. Frees needed for reliable flutter builds and visual QA. Delete legacy `*.unitypackage` (111MB, git-excluded), `.codex_tmp_*`, `.pytest_tmp/*`.
2. **Frontend release build (P1).** Produce a real `flutter build web` (or target build) on a clean-disk host and confirm it boots against staging backend. Analyze+tests pass; the artifact build is the missing proof.
3. **Stale competition route-test files (P2).** Sibling `test_api_*.py` files still use the deprecated `/api/competitions` alias; canonicalize via the conftest wrapper so the full competition lane gates green.

## Staging entry checklist
- [x] Backend composes and serves `/health`
- [x] DB schema builds / smoke-checks
- [x] Money lane certified
- [x] Realtime contracts certified
- [x] Competition lifecycle certified
- [x] Release gate PASS (fast mode)
- [ ] Frontend release artifact built + boots
- [ ] Disk freed
- [ ] Staging soak (`tools/run_gtex_staging_soak.ps1`) executed with reconnect scripting
- [ ] Visual QA screenshots captured (N36)

## Recommendation
Deploy to **staging for closed beta** now; the backend/data/money/realtime/competition lanes are certified. Gate the **public** beta on items 1–3 + the staging soak + visual QA.
