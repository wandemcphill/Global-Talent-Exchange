# CODEX Schema Repair Report

Verified on March 30, 2026 against the shipped local database copy and a repaired copy upgraded through Alembic.

## Baseline

- Shipped local runtime database inspected: `gte_backend.db`
- Shipped Alembic revision found in that database: `20260322_0029_regen_universe_layer`
- Current Alembic head after repair: `20260330_0074_player_share_market_schema_repair`
- Upgrade result on a fresh copy of the shipped database: `0029 -> 0074` completed successfully
- Post-repair schema parity check on the eight target relations: no missing columns or indexes remained

## Root Cause Summary

- The missing runtime relations were not dead code references. They are live SQLAlchemy-backed tables used by current services/routes.
- The shipped database was materially behind the current codebase and migration history, stopping at `20260322_0029_regen_universe_layer`.
- Three migration-history drifts also existed even after a clean head upgrade:
  - `20260327_0049_wallet_transactions_postgres` renamed `ledger_accounts` to `wallets` but left legacy index names behind on upgraded drifted databases.
  - `20260329_0064_gtex_unified_economy` omitted indexes for `gtex_jackpot_rounds.triggered_at` and `gtex_jackpot_rounds.winning_user_id`.
  - `20260329_0068_platform_experience_and_national_regen_seed` omitted the `ix_national_regen_seeds_status` index present in the current model.
- One non-schema runtime bug surfaced after the schema repair:
  - `backend/app/leaderboards/router.py` mixed naive SQLite datetimes with the UTC-aware season clock in `_season_view`, which kept `/season/current` and `/season/history` at `500` until normalized.

## Relation Audit

| Missing relation | Migration that should create it | Root cause | Migration/fix applied | Probes before | Probes after |
| --- | --- | --- | --- | --- | --- |
| `wallets` | `20260327_0049_wallet_transactions_postgres` (rename from `ledger_accounts`) | Shipped DB never advanced past `0029`; pre-rename `ledger_accounts` still existed. Post-upgrade drift also left legacy `ix_ledger_accounts_*` indexes. | Applied outstanding migrations; expanded `20260330_0074_player_share_market_schema_repair` to create `ix_wallets_code` and `ix_wallets_owner_user_id`, then drop legacy wallet index names. | `GET /api/wallets/summary` -> `500`; `GET /api/wallets/overview` -> `500` | `GET /api/wallets/summary` -> `200`; `GET /api/wallets/overview` -> `200` |
| `viral_leaderboard_entries` | `20260329_0060_scale_backbone` | DB drift only; current `app.models.scale_backbone.ViralLeaderboardEntryRecord` is live, not dead code. | Applied outstanding migrations through head; no backfill required. | Not in requested rerun set. On stale boot, the viral ranking worker failed on this missing table. | Not in requested rerun set. Table exists after repair and passed schema parity check. |
| `season_pass_seasons` | `20260327_0042_history_engagement_engine` | DB drift only; history/engagement worker still references the table. | Applied outstanding migrations through head; no backfill required. | Not in requested rerun set. On stale boot, the history worker failed on this missing table. | Not in requested rerun set. Table exists after repair and passed schema parity check. |
| `gtex_jackpot_rounds` | `20260329_0064_gtex_unified_economy` | DB drift only, plus migration/index drift: `triggered_at` and `winning_user_id` indexes were missing from migration history. | Applied outstanding migrations; expanded `20260330_0074_player_share_market_schema_repair` to add `ix_gtex_jackpot_rounds_triggered_at` and `ix_gtex_jackpot_rounds_winning_user_id`. | Not in requested rerun set. | Not in requested rerun set. Table and indexes present after repair. |
| `leaderboard_seasons` | `20260328_0055_leaderboards_seasons` | DB drift only for the missing relation. After schema repair, `/season/*` still failed because `_season_view` subtracted aware and naive datetimes. | Applied outstanding migrations; patched `backend/app/leaderboards/router.py` to normalize `season.end_date` via `SeasonService._normalize_timestamp()` before computing `days_remaining`. No seed migration needed because the route auto-creates the current season. | `GET /leaderboard/global?limit=12` -> `500`; `GET /season/current` -> `500`; `GET /season/history?limit=4` -> `500` | `GET /leaderboard/global?limit=12` -> `200`; `GET /season/current` -> `200`; `GET /season/history?limit=4` -> `200` |
| `national_regen_seeds` | `20260329_0068_platform_experience_and_national_regen_seed` | DB drift only for the missing relation, plus migration/index drift: the model index on `status` was never created by the migration. | Applied outstanding migrations; expanded `20260330_0074_player_share_market_schema_repair` to add `ix_national_regen_seeds_status`. No seed rows required for route stability. | `GET /regen-universe/tracking` -> `500` | `GET /regen-universe/tracking` -> `200` |
| `player_share_markets` | `20260327_0051_economy_governor_player_tokens_and_fx` | DB drift only for the missing table. Once the table exists, the current route contract returns `404` when no market row exists, so existing real players still needed minimal runtime data. | Applied outstanding migrations; expanded existing `20260330_0074_player_share_market_schema_repair` to backfill `150` default active share markets for existing `real_player_profiles`. | `GET /players/{player_id}/shares/market` -> `500` | `GET /players/{player_id}/shares/market` -> `200` |
| `player_share_events` | `20260327_0051_economy_governor_player_tokens_and_fx` | DB drift only for the missing table. Existing real players had no market history rows after table creation alone. | Applied outstanding migrations; expanded existing `20260330_0074_player_share_market_schema_repair` to backfill matching `issue` events for the `150` seeded share markets. | `GET /players/{player_id}/shares/events` -> `500` | `GET /players/{player_id}/shares/events` -> `200` |

## Corrective Changes Applied

- Migration repaired and expanded: `backend/migrations/versions/20260330_0074_player_share_market_schema_repair.py`
  - Keeps the existing player-share table repair.
  - Adds wallet index normalization for the `ledger_accounts -> wallets` rename.
  - Adds missing `gtex_jackpot_rounds` indexes.
  - Adds missing `national_regen_seeds.status` index.
  - Backfills default active player-share markets and initial issue events for existing real-player rows.
- Runtime bugfix applied: `backend/app/leaderboards/router.py`
  - `_season_view()` now normalizes `season.end_date` before subtracting the UTC-aware service clock.

## Targeted Probe Evidence

Probe harness details:

- Before-state DB: `gte_backend.db` at `20260322_0029_regen_universe_layer`
- After-state DB: `backend/.tmp_schema_repair_verified.db` upgraded to `20260330_0074_player_share_market_schema_repair`
- App boot mode for probe isolation: migration check disabled at runtime, so the requests exercised the database state directly

Before:

- `GET /regen-universe/tracking` -> `500 Internal Server Error`
- `GET /players/465fa6f3-df6b-4ff0-9e13-2a302ad21d08/shares/market` -> `500 Internal Server Error`
- `GET /players/465fa6f3-df6b-4ff0-9e13-2a302ad21d08/shares/events` -> `500 Internal Server Error`
- `GET /leaderboard/global?limit=12` -> `500 Internal Server Error`
- `GET /season/current` -> `500 Internal Server Error`
- `GET /season/history?limit=4` -> `500 Internal Server Error`
- `GET /api/wallets/summary` -> `500 Internal Server Error`
- `GET /api/wallets/overview` -> `500 Internal Server Error`

After:

- `GET /regen-universe/tracking` -> `200 {"total_seeded_players":0,...}`
- `GET /players/465fa6f3-df6b-4ff0-9e13-2a302ad21d08/shares/market` -> `200` with an active seeded market at `0.0750` coin
- `GET /players/465fa6f3-df6b-4ff0-9e13-2a302ad21d08/shares/events` -> `200` with the seeded `issue` event
- `GET /leaderboard/global?limit=12` -> `200` with an empty board for the auto-created current season
- `GET /season/current` -> `200` with an active season and `days_remaining: 29`
- `GET /season/history?limit=4` -> `200` with the current season in history
- `GET /api/wallets/summary` -> `200 {"available_balance":"0.0000","reserved_balance":"0.0000","total_balance":"0.0000","currency":"credit"}`
- `GET /api/wallets/overview` -> `200 {"available_balance":"0.0000",...,"withdrawable_now":"0.0000","currency":"credit"}`

## Conclusion

- The runtime failures in the requested scope were caused by schema drift, not dead backend references.
- A clean Alembic upgrade path from the shipped `0029` database still works.
- The repo now contains a single corrective head migration that repairs the observed post-upgrade schema drift and seeds the minimum data required for the player-share runtime contract.
