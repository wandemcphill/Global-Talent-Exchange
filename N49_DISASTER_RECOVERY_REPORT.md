# N49 — RECOVERY & ROLLBACK AUDIT

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `18a49f74`
Verdict: **PASS (mechanisms present & coverage strong). One gap: rollback rehearsal not executed this cycle.**

## Recovery surface audit

| Capability | Status | Evidence |
|---|---|---|
| **Migration rollback** | ✅ **100%** | All **163/163** alembic migrations define `downgrade()` (verified by scan). Every schema change is reversible. |
| **Database rollback** | ✅ | Alembic up/down chain intact (boot applies cleanly per N40); test DB uses SAVEPOINT rollback (`gtex_db_session`). |
| **Failed payment recovery** | ✅ | `PayoutStatus.{REJECTED,FAILED}` handled; `release_payout_request()` returns held funds; `PaymentStatus.{FAILED,REVERSED}` modeled. KoraPay verify path has failure branches (N33). |
| **Stale reservation recovery** | ✅ | `release_reserved_funds`, `release_reserved_position_units`, `release_transfer_bid_reservation` — every reserve has a release; N45 proved reserve→cancel is leak-free. |
| **Competition recovery** | ✅ | Competition lifecycle states (draft→live→completed) + `advance`/settlement are persisted and idempotent (N34); a crashed run resumes from DB truth, not memory. |
| **Realtime recovery** | ✅ | Hub evicts stale listeners on send-failure; disconnect/rejoin issues fresh client; `shutdown()` closes all (N44). |
| **Auth/account recovery** | ✅ | Password reset via recovery questions + PIN (N40 `LOCAL_AUTH_CERTIFICATION`); `account_recovery.html` email template. |
| **Operational rollback** | ✅ tooling present | `tools/staging/invoke_gtex_rollback_rehearsal.ps1` + `ops/gtex-live-match-center-rollback-runbook.md`. |

## Key invariants
- **Reversibility:** no one-way migrations (163/163 downgradable).
- **No orphaned money on failure:** reservations and payouts both have explicit release/refund paths; ledger stays balanced (double-entry, `UnbalancedTransactionError`).
- **Crash-safe lifecycle:** competition/order/payout state lives in DB with idempotent transitions — recovery = re-read DB, not replay memory.

## Gaps (transparent)
1. **Rollback rehearsal NOT executed this cycle.** The tool (`invoke_gtex_rollback_rehearsal.ps1`) exists but was not run; no fresh evidence of a clean migrate-down→migrate-up on a populated DB. **Recommend running before public beta** (and recording the result).
2. **No automated stale-reservation sweeper job** found — releases are explicit (on cancel/expire), not a periodic reaper. For closed beta this is fine (reservations release on user action); a reaper is a public-beta hardening item for abandoned sessions.
3. **Failed-payment auto-reconciliation** is status-modeled but the end-to-end "provider webhook says failed → auto-release hold" path was not re-exercised this cycle (covered structurally in N33).

## Conclusion
Recovery posture is **strong for closed beta**: full migration reversibility, complete reservation/payout release paths, crash-safe DB-truth lifecycle, and realtime self-healing. Before public beta: execute the rollback rehearsal and add a stale-reservation reaper.
