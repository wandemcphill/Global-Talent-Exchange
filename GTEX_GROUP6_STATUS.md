# GTEX Group 6 Status Ledger

## Repository lane

| Gate | Status | Evidence |
|---|---|---|
| Live frontend build requires API base URL | GREEN | `ops/render/build-frontend.sh` fails fast when `GTE_API_BASE_URL` is absent |
| KoraPay environment contract | GREEN | Production and Kubernetes templates contain secret, webhook secret, redirect and notification variables |
| Correct KoraPay webhook route | GREEN | `/integrations/payments/korapay/webhook` is the documented callback contract |
| Player-share buy compliance | GREEN | Buy route uses `get_current_trading_user` |
| Player-share sell compliance | GREEN | Sell route uses `get_current_trading_user` |
| Hosted competition invites | GREEN | Invite router/tests exist |
| Admin runtime state | GREEN | `AdminRuntimeState` is the database-backed state source; legacy file state is reconciled/imported |
| Unity Windows CI gate | GREEN | Workflow is present and explicitly classifies Unity licensing failures |
| Group 6 release audit | GREEN | Added to Quality Gates |
| Backup/restore rehearsal tooling | GREEN | Safe isolated-target helper added |
| Rollback preflight | GREEN | Migration-aware, non-destructive rollback helper added |
| Bounded soak tooling | GREEN | HTTP concurrency/latency harness added |

## Runtime lane

The following are deliberately **OPEN/BLOCKED**, because repository code cannot manufacture real production evidence:

1. Confirm the canonical deployed backend URL.
2. Confirm the bootstrap admin secret is in the real vault and injected into staging/production.
3. Execute real KoraPay staging checkout -> redirect -> webhook -> settlement with real credentials.
4. Import/publish/issue the approved 5000+ real-player cohort and verify it live.
5. Execute authenticated GTEX and hosted competition E2E flows in staging.
6. Run the 15-minute realtime/live-match soak.
7. Run PostgreSQL wallet/treasury concurrency soak against staging.
8. Execute backup -> isolated restore rehearsal against the real staging database.
9. Execute controlled deployment rollback rehearsal.
10. Run Unity Windows batch build on a licensed runner.
11. Capture production monitoring/alert evidence.

## Launch rule

Do not convert an OPEN/BLOCKED runtime item to GREEN merely because the repository contains the corresponding code or test. Group 6 is fully launch-certified only after the runtime lane has real evidence for every mandatory item.
