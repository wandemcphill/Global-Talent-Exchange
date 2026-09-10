# Phase 5H — Admin Buyback Decision Boundary

## Current state

The existing admin buyback implementation is attached to the retired System B order-book domain (`Order`, `TradeExecution`, order reservations, and `MatchingService`). System A is now the canonical player-share economy (`PlayerShareMarket`, `PlayerShareHolding`, `PlayerTokenMarketService`).

## Safe conclusions

- Existing `/orders/{order_id}/admin-buyback-preview` and `/orders/{order_id}/admin-buyback` cannot be the canonical System A exit path because both require an `Order`.
- Creating a synthetic System B order solely to reuse these methods would reintroduce the retired trading venue.
- A System A admin buyback must operate from `PlayerShareHolding` and settle against a defined platform/admin liquidity source.
- User ownership must be reduced atomically with the payout, with a balanced ledger transaction and a canonical player-share event.
- Fallback/admin pricing must remain distinct from the tradable `share_price_coin`.
- An admin exit must not mutate `share_price_coin` merely because the exit occurred.

## Blocking accounting decision

The repository does not currently expose a clearly authoritative System A funding account for admin buybacks. The generic `credit_trade_proceeds()` helper cannot safely be assumed to represent an approved admin-liquidity debit without proving its balancing account and accounting policy.

Therefore Phase 5H must not mint payout liquidity by calling a credit helper without a corresponding source posting.

## Required executable contract

1. Canonical input: authenticated user + player + quantity against `PlayerShareHolding`.
2. Eligibility: KYC, integrity, minimum-hold, country and policy checks remain explicit and fail closed.
3. Pricing: an explicit fallback/admin buyback price, separate from `share_price_coin`.
4. Funding: a named and balanced Coin-denominated system liquidity account with explicit debit/credit postings.
5. Settlement: one atomic transaction that reduces the holding, moves platform liquidity, credits user Coin, and records a `PlayerShareEvent` with settlement metadata.
6. Idempotency: required on execution.
7. History: buyback must appear as a canonical player-share exit event without creating a System B order.
8. Realized P/L: the Phase 5G calculator must include the buyback event under the same accounting rules or explicitly return unavailable. No silent special case.

## Out of scope

- Rehoming old System B orders into System A.
- Creating synthetic orders for compatibility.
- Historical P/L backfill.
- Changing tradable share price because of an admin exit.

## Decision

**Do not ship an executable System A admin buyback until the authoritative liquidity/funding account and its ledger semantics are identified and tested.** The existing System B buyback remains legacy tooling only.
