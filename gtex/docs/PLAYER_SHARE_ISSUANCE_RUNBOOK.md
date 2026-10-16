# GTEX Player-Share Issuance Runbook

## Authority

Bulk player-share issuance must use:

`backend/scripts/issue_player_share_markets_strict.py`

The runner calls `PlayerTokenMarketService.issue_market()` and therefore records issuance as an explicit administrative operation. It must not use the legacy `ensure_market()` bootstrap path.

The legacy `backend/scripts/issue_player_share_markets.py` remains available for planning/compatibility during migration, but it is **not** the certification path for activation.

## Safety sequence

1. Run a dry run against the intended cohort.
2. Inspect `created`, `skipped_existing`, `skipped_blocked`, and `failed` counts.
3. Confirm the actor is the intended administrator.
4. Activate with an explicit `--actor-user-id`.
5. Run the player-share lifecycle and trade-boundary audits.
6. Run the focused player-share tests before release.

## Dry run

```text
python backend/scripts/issue_player_share_markets_strict.py --cohort-type all --limit 250 --dry-run
```

Dry run is also the default when `--activate` is omitted.

## Activation

```text
python backend/scripts/issue_player_share_markets_strict.py \
  --cohort-type all \
  --limit 250 \
  --activate \
  --actor-user-id <ADMIN_USER_ID>
```

Activation without an actor is refused. The command is intentionally cohort- and limit-bounded so a large issuance cannot be triggered accidentally by a missing filter.

## Certification

The release snapshot should satisfy:

- no active market without an eligible player
- no zero/negative supply
- no circulating shares above total supply
- no market without liquidity-account metadata
- no trade-time implicit market creation
- issuance provenance identifies the explicit runner/policy

A green audit does not replace migration, deployment, payment-provider, or end-to-end settlement verification.
