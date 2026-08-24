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

`buy_shares()` and `sell_shares()` must not contain a direct `ensure_market()` call. Trading is not allowed to create or initialize a market.

A missing market must fail with `market_not_found`.

### Lifecycle

Every active market must satisfy all of these:

- the player is eligible for a share market
- the market has explicit issuance provenance
- the market has the expected liquidity account
- the liquidity account is denominated in GTEX Coin
- the persisted liquidity balance is non-negative
- persisted liquidity metadata reconciles with the ledger projection

### Holdings

The certification also rejects:

- negative share holdings
- negative average acquisition cost
- negative dividend balances
- aggregate holdings greater than market circulation
- aggregate holdings greater than total market supply
- holdings for a player with no corresponding market

### Issuance

Bulk issuance must be an explicit issuance operation. A bootstrap/issuer command must not disguise a newly created market as a trade-time auto-initialized market.

## Interpretation

A green certification means the checked economic invariants hold for the target snapshot. It does **not** replace migration verification, application tests, payment-provider verification, or a deployment smoke test.

A failed gate is a release blocker. Do not repair the production database manually merely to make the audit green. Fix the authoritative application path or perform an explicitly reviewed data migration.
