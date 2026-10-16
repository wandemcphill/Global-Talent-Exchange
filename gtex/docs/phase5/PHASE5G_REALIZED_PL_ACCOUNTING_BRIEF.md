# Phase 5G — Realized P/L and Player-Share Accounting

## Baseline

Current `main` after Phase 5D, 5E, and 5F integration.

Canonical player-share architecture is **System A**:

- Ownership: `PlayerShareHolding`
- Tradable price: `PlayerShareMarket.share_price_coin`
- Settlement: `PlayerTokenMarketService`
- Portfolio: `PortfolioService`
- Ledger: existing wallet/ledger transaction system

System B player-share order creation is retired. Do not resurrect or bridge the old order-book ownership model.

## Problem to solve

Realized P/L is currently intentionally unavailable for System A because historical sale events do not preserve enough information to reconstruct cost basis. The product must move from `realized_pl_available=false` to an explicit, auditable accounting model for **new** System A sells, without pretending historical trades are reconstructible.

The product must also surface player-share trading history from the canonical System A event stream where useful, while preserving the separation:

`VALUE != SHARE PRICE != COST BASIS != REALIZED P/L`

## Required audit first

Trace the actual buy/sell settlement path before changing schema or formulas. Identify exactly where a sale transaction is created, where `PlayerShareEvent` is written, how `PlayerShareHolding.average_cost_coin` is updated, and how the ledger transaction is linked to the domain event.

Do not infer event semantics from names. Use actual callers and persistence behavior.

## Economic model

Use a single explicit cost-basis convention for **new System A trades**. Preferred model: weighted-average cost basis per holding, because the canonical holding already stores `average_cost_coin` and System A is instant-settlement rather than lot-based.

On BUY:

`new_average_cost = ((old_quantity * old_average_cost) + gross_buy_cost) / new_quantity`

where `gross_buy_cost` is the actual coin consideration attributed to the acquired shares according to the existing service's fee semantics. Do not invent a fee rule. Trace the current implementation and document whether fees belong in acquisition cost or are expensed separately.

On SELL:

`realized_pl = sale_consideration_ex_fee_or_as_defined_by_existing_ledger_contract - (sold_quantity * pre_sell_average_cost)`

The exact treatment of fees must follow an existing canonical ledger convention if one exists. If none exists, stop and document the ambiguity rather than inventing a hidden formula.

The sell must snapshot the pre-sell average cost basis into an immutable trade/event record before mutating the holding. The record must contain enough information to independently recompute realized P/L later.

## Historical honesty

Historical System A sales that occurred before the new accounting fields existed must remain explicitly unavailable unless their cost basis can be proven from persisted data. Do not backfill fake cost basis from current `average_cost_coin` or current price.

The API should distinguish:

- `realized_pl_available=true`: complete accounting exists for the reported period.
- `realized_pl_available=false`: accounting is not reconstructible.
- `realized_pl_total=0`: only when the accounting source is complete and the true realized result is actually zero.

## Data model requirements

Prefer additive schema changes with immutable trade accounting records. A candidate record should preserve at minimum:

- trade/event id
- user id
- player id
- side
- share quantity
- execution/share price in coin
- gross consideration in coin
- fee in coin if applicable
- cost basis per share at the moment of sale for sells
- total cost basis for sold quantity
- realized P/L in coin for sells
- event timestamp
- ledger transaction id when available
- idempotency key when available
- accounting version

Do not duplicate the ledger as a second balance system. The accounting record is explanatory/audit data; the wallet ledger remains the source for money movement.

Add uniqueness/idempotency constraints so a retried trade cannot create a second accounting record.

## Portfolio behavior

`PortfolioService` should aggregate realized P/L only from canonical System A accounting records whose accounting version is supported and complete.

Do not mix realized P/L units with player valuation credits or EUR reference values.

Unrealized P/L remains:

`quantity * share_price_coin - quantity * average_cost_coin`

Matchday valuation changes must never alter realized P/L or tradable share price.

## UI requirements

Do not create a new dashboard for this phase.

On Portfolio, clearly label:

- Unrealized P/L: coin
- Realized P/L: coin
- Realized P/L availability state

For unavailable historical accounting, use honest copy such as `Not calculated for this historical period` rather than zero.

Where the canonical player-share event history already exists, add a compact transaction/history view on the relevant player or portfolio surface using real events only. Do not fabricate timestamps, prices, fills, or counterparties.

For each sell event, the user should be able to understand the realized result and the cost basis used, without exposing internal ledger implementation details.

## Trading history

Trace and expose `PlayerShareEvent` only where its current schema is sufficient. If existing event rows do not include enough information to provide an honest history entry, render the missing field as unavailable rather than reconstructing it from mutable current state.

Do not create an order-book history UI for the retired System B player-share path.

## Admin buyback

Do **not** re-home the old admin buyback automatically. First determine whether its current semantics still have a legitimate meaning under System A. If it is only historical System B behavior, leave it isolated and document it. A re-home requires a separate explicit economic decision.

## Portfolio wording gap

Phase 5E/5F established that matchday form can change published player valuation while the owner's position market value remains driven by `share_price_coin`. Portfolio wording must reflect that clearly. This is a copy/labeling fix, not a coupling between valuation and share price.

## Acceptance tests

Required tests must prove, using the real canonical service path:

1. Buy establishes a weighted-average coin cost basis.
2. Multiple buys produce the correct weighted-average basis.
3. Partial sell snapshots the pre-sell basis for the sold quantity.
4. Realized P/L is correct for profitable sell.
5. Realized P/L is correct for loss-making sell.
6. Full sell closes the holding without losing the accounting record.
7. Repeat of the same idempotency key does not duplicate the accounting event.
8. Historical rows without accounting metadata remain unavailable, not guessed.
9. Portfolio realized and unrealized P/L remain coin-denominated and independent from value-engine credits/EUR.
10. Matchday valuation overlay cannot change realized P/L or share price.
11. Accounting rows and wallet ledger transaction ids remain consistent.
12. Trading history uses immutable stored trade data, not current mutable holding state.

Run targeted backend accounting/portfolio/market suites plus the existing Phase 5 economic regression suite and relevant Flutter portfolio/player-detail tests.

## Guardrails

- No production writes.
- No historical backfill unless the source data proves the result.
- No resurrection of System B as a user-facing player-share venue.
- No router/shell redesign.
- No invented liquidity or market-maker behavior.
- Preserve `PRICE != VALUE`.
- Preserve idempotency.
- Preserve holdings on player retirement.
- Do not claim tests passed without actual execution evidence.

## Delivery

PR-only against current `origin/main`.

Audit first, implement only what the repository can prove, add regression tests, run quality gates, and open a focused PR. Do not merge automatically.