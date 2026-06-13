# N42 — EXECUTION ROADMAP (Phase G)

Date: 2026-06-13 · `feature/original-visual-runtime` @ `b5b19730`

Sequenced N43→N50. Ordered by **value/effort and gate dependency**: green the known red lane first, then the public-beta gates, then the GA concurrency/DR trio. Each phase is finite and verification-anchored. No architecture or feature invention.

---

## N43 — Competition test-contract canonicalization + payout E2E
- **Objective:** Green the two red competition sibling files (alias→v2 + envelope unwrap) and add the missing end-to-end payout route test.
- **Files likely affected:** `backend/tests/competitions/test_api_discovery.py`, `backend/tests/competitions/test_backend_contract_routes.py`, `backend/tests/competitions/api_helpers.py` (reuse), optionally `backend/tests/competitions/conftest.py`; new `backend/tests/competitions/test_competition_payout_e2e.py`.
- **Risk:** **Low** (test-only; product code untouched). Recipe verified in N42 Phase B (path rewrite flips 410→201).
- **Verification:** `pytest tests/competitions` fully green; new payout test asserts complete→distribute→wallet-credit + idempotent retry.
- **Readiness gain:** Closed-beta 90→92; Public-beta +2 (honest competition certification).

## N44 — Frontend release artifact + Postgres boot + fail-loud migrations
- **Objective:** Rebuild/boot the web artifact at HEAD against Postgres; replace boot-time schema auto-repair with fail-loud + explicit migration in non-local envs.
- **Files likely affected:** `backend/app/core/database.py` (auto-repair guard), `backend/app/main.py` startup, `ops/render/production-preflight.sh`, `backend/scripts/deployment_preflight.py`, frontend build config (API URL).
- **Risk:** **Medium** (touches boot/migration path — gate behind env flag; keep local SQLite behavior).
- **Verification:** clean Postgres boot; `/health`,`/ready`,`/version` 200; migration runs explicitly; `flutter build web` succeeds and serves.
- **Readiness gain:** Public-beta 70→78.

## N45 — Realtime soak (reconnect / stale-session / multi-device)
- **Objective:** First real soak of the realtime gateway.
- **Files likely affected:** `tools/run_gtex_staging_soak.ps1` (drive), `backend/app/realtime/*`, `backend/app/core/container.py` (outbox), `frontend/lib/shared/realtime/*`.
- **Risk:** **Medium** (may surface reconnect/dup-event defects — that’s the point).
- **Verification:** scripted disconnect/reconnect cycles; assert no duplicate events (outbox dedup), session expiry correct, 2+ devices per user stable.
- **Readiness gain:** Public-beta 78→84.

## N46 — Full backend suite sharded-green + CI matrix
- **Objective:** One green full backend matrix; cut per-test DB DDL cost (rollback-fixture migration).
- **Files likely affected:** `backend/tests/conftest.py` (`gtex_db_session` rollback fixture rollout), CI workflow, slow-suite splits; fix regen expansion + regen-admin RBAC route failures.
- **Risk:** **Medium** (fixture migration can shift test isolation — verify per shard).
- **Verification:** full matrix green across runners; regen RBAC + expansion suites green.
- **Readiness gain:** Public-beta 84→88; GA +3.

## N47 — Wallet/Trader concurrency + settlement safety
- **Objective:** Prove money-path safety under contention.
- **Files likely affected:** `backend/app/trader/matching.py`, `backend/app/wallets/service.py`; new `backend/tests/trader/test_matching_concurrency.py`, `backend/tests/wallets/test_ledger_concurrency.py`.
- **Risk:** **Medium-High** (may expose real race conditions in `with_for_update`/reservation paths — money-critical).
- **Verification:** N parallel buys vs one ask → single settlement, no over-fill; concurrent ledger ops → no lost update; reservation idempotent on retry.
- **Readiness gain:** GA 55→64 (clears the top money risk).

## N48 — Load / throughput baseline + observability
- **Objective:** Capacity numbers + per-lane SLO dashboards.
- **Files likely affected:** `tools/load/gtex_load_probe.py`, observability middleware, metrics endpoints, dashboard config.
- **Risk:** **Low-Medium** (mostly additive/measurement).
- **Verification:** p95/p99 + throughput recorded for wallet/competition/transfer/realtime; SLOs + alerts defined; tracing validated on money paths.
- **Readiness gain:** GA 64→70; Public-beta polish.

## N49 — WebSocket collision authority + admin/support tooling
- **Objective:** Close the WS registration-safety gap; finish admin export + support runbooks.
- **Files likely affected:** `backend/app/core/module.py` (WS fingerprinting), `backend/app/modules.py`, `backend/tests/realtime/test_websocket_route_contracts.py`, admin export paths, support/DB-reset runbooks.
- **Risk:** **Low-Medium**.
- **Verification:** duplicate WS path registration is detected at boot; admin export artifacts produced; runbooks reviewed.
- **Readiness gain:** GA 70→74.

## N50 — DR rehearsal + reconciliation + payment resilience
- **Objective:** Rollback/restore rehearsal, ledger↔rail reconciliation, single-rail fallback runbook; promote trader disputes to first-class entities.
- **Files likely affected:** `tools/staging/invoke_gtex_rollback_rehearsal.ps1`, new reconciliation job, `backend/app/dispute_engine/*`, payment-rail docs.
- **Risk:** **Medium**.
- **Verification:** rollback rehearsed with recorded RPO/RTO; daily ledger-vs-KoraPay match job green; dispute entities queryable.
- **Readiness gain:** GA 74→82 (DR + reconciliation are the last hard GA gates).

---

## Trajectory (evidence-anchored, not guaranteed)

| After | Closed beta | Public beta | GA |
|---|---:|---:|---:|
| now (`b5b19730`) | ~90 | ~70 | ~55 |
| N43–N45 | 92 | 84 | 58 |
| N46–N48 | 92 | 88 | 70 |
| N49–N50 | 92 | 90 | 82 |

GA’s final ~18% beyond N50 is sustained production-soak + a second payment rail (larger effort) — explicitly out of this roadmap’s mechanical scope.
