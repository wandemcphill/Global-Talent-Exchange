# N42 — GA READINESS (Phase F)

Date: 2026-06-13 · `feature/original-visual-runtime` @ `b5b19730`
Current GA readiness: **~55% (NO-GO)**. GA = real money at scale; the bar is concurrency safety, settlement correctness under contention, and operability.

## 10,000 users
**Performance**
- Load baseline established and **re-run as a regression gate** on the hot lanes (wallet ledger writes, competition join/settlement, transfer bid escrow, realtime fan-out). No baseline exists today (*N39 #8*).
- Frontend web cold-load budget defined (boot was historically slow — *BOOT_HEALTH*); CDN/caching for web assets.

**Concurrency**
- **Trader matching under contention proven**: N concurrent buys vs one ask → exactly one settlement, no over-fill; `with_for_update` row-locking validated, not just present (*N39 #5*).
- Wallet ledger: concurrent debit/credit on one account → no lost update; reservation/settlement idempotency under retries.

**Settlement safety**
- Competition payout distribution E2E + idempotent on retry; partial-failure rollback proven.
- P2P trader offers moved to **automated escrow** (parity with order book) or explicitly disabled for GA (*N39 #14*).
- Outbox-relay exactly-once verified under worker restart.

**Fraud controls**
- KYC gating enforced on money-out paths (already modeled: `KycStatus.FULLY_VERIFIED`); velocity/withdrawal limits via `admin_godmode` withdrawal-controls exercised under abuse scenarios.

## 50,000 users
**Observability**
- Per-lane SLOs (availability, p95/p99, error budget); distributed tracing on money paths (tracing is wired in `create_app` — validate it end-to-end).
- Realtime connection-count + reconnect-rate dashboards; alert on gateway saturation.

**Operational runbooks**
- Wallet/payment incident runbook; competition settlement-stuck runbook; realtime gateway-degraded runbook; DB migration runbook (with the auto-repair → explicit-migration change from Phase E).
- Admin export/audit artifacts working (currently blocked) for finance reconciliation.

**Concurrency/DB**
- Connection-pool + read-replica strategy for the 567-table schema; slow-query budget; index review on discovery/leaderboards/ledger.
- WebSocket horizontal fan-out across workers with **no duplicate events**; add WS route-collision fingerprinting at registration (HTTP-only today).

## 100,000 users
**Disaster recovery**
- Documented + rehearsed **rollback** (`invoke_gtex_rollback_rehearsal.ps1`, currently unrun — *N39 #15*) and **restore-from-backup** with RPO/RTO targets.
- Multi-AZ / failover posture for DB and realtime; backup integrity drill.

**Settlement safety at scale**
- Reconciliation job: ledger vs external rail (KoraPay) daily settlement match; alert on drift.
- Payment-provider concentration mitigated — at minimum a manual-rail fallback runbook; ideally a second rail (larger effort) (*N39 #13*).

**Admin operations**
- God-mode controls (withdrawal/competition) load-safe and fully audit-logged; dispute resolution promoted to first-class entities for incident response (*N39 #19*).

## GA gate summary

| Pillar | State | GA requirement | Status |
|---|---|---|---|
| Performance baseline | none | load gate on hot lanes | ❌ |
| Trader concurrency | untested | proven no over-fill at load | ❌ (money-critical) |
| Wallet concurrency | green serial | proven under contention | ⚠️ |
| Payout E2E + idempotency | missing | green + retry-safe | ❌ |
| Full-suite single-pass | never completed | green matrix | ❌ |
| Rollback / DR | unrun | rehearsed + documented | ❌ |
| Observability/SLO | partial | per-lane SLOs + tracing | ⚠️ |
| Fraud / KYC at scale | modeled | abuse-tested | ⚠️ |
| Payment resilience | single rail | fallback documented | ❌ |
| WS authority at scale | gap | collision-safe + fan-out proven | ❌ |

**Verdict:** GA **NO-GO**. The remaining work is a finite, enumerated list of concurrency proofs, settlement-safety tests, and ops/DR rehearsals — not architecture or feature work. Estimated **2–4 focused weeks** beyond public-beta gate, gated by the load + concurrency + rollback trio.
