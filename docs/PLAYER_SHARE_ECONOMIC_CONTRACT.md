# Player Share Economic Contract

## Lifecycle

A player-share market has three distinct operations:

1. **Discovery**: read existing markets only. Reads must not create markets, seed liquidity, or mutate ledger state.
2. **Issuance**: an explicitly authorized admin operation creates the market, chooses supply/price, and funds liquidity according to the platform policy.
3. **Trading**: buy/sell is allowed only when an issued market already exists. Trading is not an issuance mechanism.

## Eligibility

A market may be displayed as active/tradeable only when its player remains eligible under the current player-share eligibility policy. Eligibility is rechecked at the trade boundary.

## Settlement

Player-share trades settle through the system-owned Coin ledger. The market liquidity account is the source of sale liquidity and the destination of buy proceeds. Trading fees are posted separately to the system trade-fee account.

## Concurrency

Trade mutations must lock the market row before calculating supply, price, or liquidity. Sell mutations must also lock the buyer/seller holding row before decrementing ownership. A stale read must never authorize a trade.

## Retry safety

Every economic trade request must be idempotent. A client retry of the same economic intent must resolve to the original settlement rather than create a second ledger transaction, second holding mutation, or second price move. The trade service now accepts a bounded caller idempotency key, scopes it to actor/player/side, and resolves retries from the durable ledger transaction reference.

The public request schemas expose `idempotency_key` for buy and sell. The trade boundary carries the key into the service. The remaining HTTP-router forwarding is protected by `backend/scripts/audit_player_share_trade_idempotency.py` and must remain green before release.

## Talent projection operations

Talent profile creation and ranking backfill is deliberately separate from market issuance. `backend/app/talent/backfill.py` provides a bounded, cursor-based runner capped at 500 players per batch. It can resume after a player id, process only missing profiles, isolate failures to individual players, and recompute deterministic rankings without writing to the economic value engine.

The operational entry point is `backend/scripts/backfill_talent_exchange.py`. It supports `--after-player-id`, `--all`, `--no-recompute`, a fixed `--as-of` date, and fail-fast mode. The runner never invents football attributes: absent evidence remains absent and the ranking pipeline handles that state explicitly.

## Read-only operational checks

`backend/scripts/audit_player_share_integrity.py` detects active markets whose players are no longer eligible, zero-priced markets, invalid supply, and over-circulated markets.

`backend/scripts/audit_player_share_lifecycle.py` additionally reconciles active-market issuance provenance and the Coin liquidity-account balance against the market's recorded liquidity metadata.

`backend/scripts/audit_player_share_trade_boundary.py` detects direct implicit market initialization from the trade methods.

`backend/scripts/audit_player_share_trade_idempotency.py` statically checks the trade service and HTTP endpoints for idempotency-key propagation.

`backend/scripts/verify_player_share_inventory.py` certifies the published market inventory against the platform's release threshold.

## Fail-closed behavior

If a market does not exist, trading must return `market_not_found`. It must not implicitly call market issuance or liquidity initialization.

If liquidity is insufficient for a sale, the trade is rejected before ledger settlement.

If a player becomes ineligible, the trade is rejected even if a legacy market row still exists.

If an economic retry cannot be matched to an existing idempotency key, the system must reject rather than guess whether the request is a duplicate.
