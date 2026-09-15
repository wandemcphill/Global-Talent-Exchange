# GTEX Jackpot Economic Hardening — 2026-09-14

This change adds database-level guards to the canonical Jackpot economy while the repository's GitHub Actions runner is unavailable for application-side patch execution.

## Guards added

- Exactly one `open` Jackpot round per pool.
- Unique `(round_id, rank)` payout rows.
- Unique non-null contribution identity `(source_type, source_id, participant_user_id)`.
- Unique ledger transaction references for `gtex-jackpot-payout:*`, preventing a second canonical payout transaction for the same round reference.
- Migration fails closed when any of those duplicate states already exist.

## Remaining application hardening

The canonical service still needs an application-side replay guard on `contribute_from_wallet()` so the wallet debit is idempotent before mutation, plus a row-lock/balance-reconciliation guard inside `trigger_round()`. The frontend Jackpot route also still contains demo fallback data and fake-success responses and must be made live-only.

Those changes are deliberately not approximated through a speculative parallel engine. The repository's GitHub Actions runner currently fails jobs before executing any steps (`steps: []`, no runner assigned), and the connected runtime cannot safely replace the large canonical service/screen files without complete-file verification.
