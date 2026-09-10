# Phase 5I — Historical Player-Share Repair Boundary

## Purpose

Phase 5G introduced auditable realized P/L for new System A trades. Historical player-share rows must not be reconstructed from insufficient evidence.

## Authoritative sources

- `PlayerShareEvent` is the historical trade-event source.
- `PlayerShareHolding` is the current ownership projection.
- Wallet ledger transactions are the money-settlement source.
- `PlayerShareMarket.share_price_coin` is the current tradable price and is never a historical cost-basis source.

## Repair classification

Every historical user/player position should be classified into exactly one bucket:

1. **RECONCILABLE** — complete buy/sell event history, settlement metadata, and current holding reconcile. May be included in accounting views.
2. **HISTORY_INCOMPLETE** — ownership exists but event history or settlement metadata is missing. Realized P/L remains unavailable.
3. **POSITION_MISMATCH** — event-derived quantity does not equal the canonical holding. Realized P/L remains unavailable until the discrepancy is explained.
4. **SETTLEMENT_INCOMPLETE** — trade event exists but its ledger transaction/settlement evidence is incomplete. Do not infer proceeds or fees.
5. **LEGACY_NON_SYSTEM_A** — historical order-book/System B material. Do not bridge it into System A without an explicit migration contract.

## No-write rule

The first implementation of Phase 5I is a read-only audit/report. It must not mutate holdings, ledger entries, player-share events, share prices, or balances.

A later repair migration may only be considered when a row is provably reconstructible from immutable settlement evidence. Otherwise the UI/API should expose an unavailable status rather than a guessed value.

## Accounting continuity

The Phase 5G weighted-average method remains the only supported realized P/L calculation for System A. Historical repair must not change the accounting policy or silently create synthetic cost lots.

## Required outputs from the audit

- Counts by classification.
- Sample identifiers for each non-green class, without secrets.
- Reconciliation deltas for `PlayerShareHolding` versus event-derived quantity.
- Missing transaction/fee metadata counts.
- Any System B artifacts detected separately from System A.

## Explicit prohibition

Do not backfill a historical average cost from today's `PlayerShareHolding.average_cost_coin`, current share price, published player valuation, or any other present-day value. Those values cannot prove the cost basis at the time of a historical sale.
