# Phase 6B: Released Player-Share Supply

Player-share lifetime supply, released primary supply, and circulating ownership are separate concepts.

- `total_shares` is the lifetime authorized quantity for the market.
- `released_shares` is the quantity currently made available to primary buyers.
- `circulating_shares` is the quantity currently owned by users.
- `released_shares - circulating_shares` is the primary supply still available to buy.

Legacy markets keep `released_shares = NULL` until historical release state can be reconciled honestly. Their existing trading behavior remains unchanged rather than inventing historical release counts.

New bulk-issued markets seed `released_shares` from the existing issuance policy's `initial_circulating_cap`, which becomes the launch release cap. This does not create user ownership by itself.

Additional release increases `released_shares` on the existing market only. It never creates a duplicate player or market and never changes `share_price_coin`.

The release operation is admin-attributed, dry-run by default, and does not move Fan Coin or GTEX Coin.
