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

Every economic trade request must be idempotent. A client retry of the same economic intent must resolve to the original settlement rather than create a second ledger transaction, second holding mutation, or second price move. Random UUIDs generated inside `buy_shares()` or `sell_shares()` are not valid idempotency keys because every retry would produce a new economic reference.

`backend/scripts/audit_player_share_trade_idempotency.py` is a read-only static guard for this invariant.

## Read-only operational checks

`backend/scripts/audit_player_share_integrity.py` detects active markets whose players are no longer eligible, zero-priced markets, invalid supply, and over-circulated markets.

`backend/scripts/audit_player_share_lifecycle.py` additionally reconciles active-market issuance provenance and the Coin liquidity-account balance against the market's recorded liquidity metadata.

`backend/scripts/audit_player_share_trade_boundary.py` detects direct implicit market initialization from the trade methods.

`backend/scripts/verify_player_share_inventory.py` certifies the published market inventory against the platform's release threshold.

## Fail-closed behavior

If a market does not exist, trading must return `market_not_found`. It must not implicitly call market issuance or liquidity initialization.

If liquidity is insufficient for a sale, the trade is rejected before ledger settlement.

If a player becomes ineligible, the trade is rejected even if a legacy market row still exists.

If an economic retry cannot be matched to an existing idempotency key, the system must reject rather than guess whether the request is a duplicate.
