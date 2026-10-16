# Player-Share Release Gate

The player-share economy is considered releasable only when the economic certification command passes against the target database.

## Command

From `backend/`:

```bash
python scripts/certify_player_share_economy.py --database-url "$DATABASE_URL" --batch-size 1000
```

The command is **read-only**. It must never create markets, top up liquidity, alter holdings, or repair production state.

## Mandatory gates

### Trade boundary

`buy_shares()` and `sell_shares()` must not contain a direct market-creation path. Trading is not allowed to create or initialize a market.

A missing market must fail with `market_not_found`, and the existing market row is locked before economic mutation.

### Trade idempotency

Client retries may provide an idempotency key. The request model captures that key in request-local context for the current router compatibility contract, and the production trade service persists the resulting deterministic reference on the authoritative ledger transaction.

A repeated key replays the original settlement. Reuse of a key for a materially different trade is rejected rather than creating a second economic effect.

When no key is supplied, the service still creates a deterministic trade reference from the locked market, actor, side, pre-trade circulation, and share count.

### Issuer boundary

The bulk player-share issuer must use the explicit issuance path. It must not call the legacy `ensure_market()` bootstrap method. This prevents bulk issuance from being recorded as an auto-initialized market and keeps issuance provenance auditable.

### Lifecycle and market integrity

Every active market must satisfy all of these:

- the player is eligible for a share market
- the market has explicit issuance provenance
- the market has the expected liquidity account
- the liquidity account is denominated in GTEX Coin
- the authoritative liquidity balance is non-negative
- persisted liquidity metadata reconciles with the ledger projection
- share price is positive
- circulation is non-negative and does not exceed total supply
- aggregate positive holdings reconcile exactly to circulation
- active markets are not attached to non-tradable players

### Holdings

The certification rejects:

- negative share holdings
- negative average acquisition cost
- negative dividend balances
- aggregate holdings greater than market circulation
- aggregate holdings greater than total market supply
- holdings for a player with no corresponding market
- positive holdings on an inactive market

## CI coverage

The Phase A economic regression workflow includes the player-share market-integrity, lifecycle, issuer, trade-boundary, trade-idempotency, economic-certification, and request-context regression suites, plus the read-only static economic audits.

## Interpretation

A green certification means the checked economic invariants hold for the target snapshot. It does **not** replace migration verification, application tests outside the Phase A suite, payment-provider verification, or a deployment smoke test.

A failed gate is a release blocker. Do not repair the production database manually merely to make the audit green. Fix the authoritative application path or perform an explicitly reviewed data migration.
