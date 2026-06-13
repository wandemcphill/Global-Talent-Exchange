# N42 — PUBLIC BETA READINESS (Phase E)

Date: 2026-06-13 · `feature/original-visual-runtime` @ `b5b19730`

Current posture: **Local alpha GO for 5 (N40)**, **Closed beta GO with conditions (N39, ~90%)**, **Public beta ~70% — NO-GO** until the gates below clear. Tiers are cumulative (each builds on the prior).

## 50 users (controlled public beta)
**Required before turning it on:**
- Backend: rebuild & boot the **frontend release artifact** at current HEAD (`flutter build web`) against a stable backend URL; today’s artifact was built at an earlier SHA (N40). *(N39 #1)*
- Database: move off local SQLite boot to the target Postgres; capture migration time; **replace boot-time schema auto-repair with fail-loud + explicit migration** in non-local envs. *(N39 #4/#17)*
- Realtime: run a **first reconnect/disconnect soak** (`tools/run_gtex_staging_soak.ps1`) — even a short one; reconnect storms are currently unproven. *(N39 #7)*
- Wallet: validate withdrawal **fee-policy env config** at deploy (a preflight assertion), since fee bps/minimum are now config-driven. *(N39 #3-risk)*
- Competitions: land the **N43 competition test-contract fix** (Phase B) so discovery/contract lanes are green and the surface is honestly certified.
- Monitoring/Logging: confirm `/health`, `/ready`, `/version`, `/metrics` are scraped; ship structured request logs (the app already emits `app.startup.*`, `http.request.completed`).
- Admin/Support: a documented **DB reset/backup** runbook (testers can create irreversible-looking data — N40 risk #9).

## 100 users
**Add:**
- Backend: **shard the full backend suite across CI runners** and get one green full matrix (today only sharded-serial green; 8h+ single pass). *(N39 #4)*
- Realtime: **multi-device** session soak (same user, 2+ devices) + stale-session expiry behavior verified end-to-end.
- Wallet/Competitions: **E2E payout route test** (complete competition → distribute → wallet credit) green. *(N39 #10)*
- Monitoring: error-rate + p95 latency dashboards per lane (auth, wallet, competitions, realtime); alert thresholds.
- Admin tooling: working **export/artifact** paths (currently flagged blocked) for finance/audit.
- WebSocket: add **WS route-collision fingerprinting** at module registration (HTTP-only today).

## 500 users
**Add:**
- Backend/DB: a **throughput baseline** via `tools/load/gtex_load_probe.py` on the hottest lanes (wallet ledger, competition join, transfer bid, realtime fan-out); know capacity numbers, not guesses. *(N39 #8)*
- Trader: **concurrency proof** — N parallel buys against one ask; assert no over-fill / single settlement (the `with_for_update` path is untested under contention). *(N39 #5)* — money-critical even at 500.
- Realtime: gateway thundering-herd test (mass reconnect) with outbox-dedup verified at the edge.
- Support: a triage runbook for the top-10 expected user issues (session restore, tunnel/CORS, wallet compliance blocks, competition eligibility) from N40.

## 1000 users
**Add:**
- DB: connection-pool sizing + slow-query review against 567-table single-metadata schema; migration-ordering rehearsal.
- Realtime: horizontal fan-out validation (multiple workers) without duplicate events.
- Ops: **rollback rehearsal** recorded (`tools/staging/invoke_gtex_rollback_rehearsal.ps1`) and an on-call runbook for wallet/payment incidents. *(N39 #15)*
- Payments: document single-provider (KoraPay/manual) concentration risk and a manual-rail fallback procedure. *(N39 #13/risk)*

## Public-beta gate summary

| Domain | Closed-beta state | Public-beta requirement | Status |
|---|---|---|---|
| Backend correctness | green (sharded) | full-suite matrix green | ❌ |
| Frontend artifact | built earlier SHA | rebuilt+booted at HEAD | ❌ |
| Database | local SQLite | Postgres + fail-loud migrations | ❌ |
| Realtime | contract-green | reconnect+multi-device soak | ❌ |
| Wallet | certified | fee-config preflight | ⚠️ partial |
| Competitions | lifecycle green | sibling lanes green + payout E2E | ❌ |
| Monitoring/Logging | health endpoints | dashboards+alerts | ⚠️ partial |
| Admin/Support | strong backbone | export + reset/backup runbook | ⚠️ partial |

**Verdict:** Public beta stays **NO-GO**. The blockers are verification, ops, and the competition test-contract fix — not architecture. Estimated **1–2 focused weeks** to the 50–100-user gate if N43–N44 land.
