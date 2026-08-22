# Phase A: Agent Wallet Ledger Migration

## Canonical rule

`AgentWallet` is a compatibility/read-model projection. It is not a monetary authority.

The canonical economic authority is the GTEX ledger.

## Account identity

Until a dedicated account kind is justified by product requirements, agent economic balances must use a deterministic `SYSTEM` ledger account with a stable code:

`agent:<agent_id>:<unit>`

Do not use a user-owned wallet because a creator agent is not a user identity.

## Required behavior

- Missing agent ledger account is created only through an explicit, idempotent ledger-account helper.
- New accounts start at zero.
- `AgentWallet.balance` is hydrated from the ledger, never written as a money source.
- `lifetime_earnings`, `boost_spend`, and ROI remain analytical projections until each has an explicit ledger source mapping.
- `payout_eligible` is a policy/result flag, not a balance authority.
- `apply_spend()` and `settle()` may calculate decisions, but they must not be the final monetary mutation path.
- Monetary mutations require a ledger transaction with a unique business/idempotency key.
- Concurrent spend/settlement must lock the authoritative ledger account before checking balance.

## Migration strategy

1. Add deterministic agent ledger-account helper.
2. Hydrate `AgentWallet.balance` from the ledger.
3. Route boost spend through the ledger.
4. Route approved earnings through the ledger.
5. Keep existing performance metrics as projection fields.
6. Add reconciliation comparing projection and ledger balances.
7. Remove monetary writes to `AgentWalletRecord.balance` after migration and keep the column only for backward-compatible read snapshots.
8. Do not mass-zero existing historical balances. Reconcile them against ledger provenance first.
