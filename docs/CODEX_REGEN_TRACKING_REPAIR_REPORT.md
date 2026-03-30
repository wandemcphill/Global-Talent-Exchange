# CODEX Regen Tracking Repair Report

Verified on March 30, 2026.

## Problem

- `/regen-universe/tracking` was returning `500` on drifted databases because `national_regen_seeds` did not exist.
- The world aggregate depended on that endpoint, so tracking was the remaining regen-universe blocker after the other world endpoints had already been proven live in `Docs/CODEX_RUNTIME_PROOF_REPORT.md`.

## Root Cause

- `national_regen_seeds` was introduced by `20260329_0068_platform_experience_and_national_regen_seed`.
- Some runtime databases had advanced beyond that point while still missing the table.
- The existing runtime repair migration at `20260330_0074_player_share_market_schema_repair` did not recreate `national_regen_seeds`; it only added the `status` index when the table already existed.
- `/regen-universe/tracking` only needs the table to exist. An empty table is a valid zero-state; production startup does not auto-preseed national regen rows.

## Changes Applied

- Added `backend/migrations/versions/20260330_0076_regen_tracking_schema_repair.py`.
  - Recreates `national_regen_seeds` when missing.
  - Ensures the `country_code`, `seed_type`, `rarity_tier`, and `status` indexes exist.
  - Keeps the repair non-destructive and does not invent seed data.
- Added `backend/tests/regen/test_regen_tracking_api.py`.
  - Confirms `GET /regen-universe/tracking` returns `200` with a valid zero-state payload when the table exists but is empty.
- Extended `backend/tests/persistence/test_migrations.py`.
  - Confirms a database upgraded only through `20260330_0074_player_share_market_schema_repair` can lose `national_regen_seeds`, upgrade to `head`, and recover the table plus indexes.
- Added `backend/tests/hosted_competition_engine/test_public_list.py`.
  - Confirms `/hosted-competitions` returns `200` with an empty list payload on a valid empty database.
- Updated `frontend/lib/features/world/live_world_provider.dart`.
  - The world aggregate now unwraps `/regen-universe/rising-stars` and `/regen-universe/scouting-feed` from their map payloads instead of incorrectly expecting raw lists.

## Verification

Executed successfully:

- `python -m pytest backend\tests\persistence\test_migrations.py -k "persistence_migrations_create_expected_tables or regen_tracking_repair_migration" -vv`
  - Result: `2 passed`
- `python -m pytest backend\tests\regen\test_regen_tracking_api.py -vv`
  - Result: `1 passed`
- `python -m pytest backend\tests\competitions\test_api_discovery.py -k discovery_route_bypasses_lazy_module_hydration -vv`
  - Result: `1 passed`
- `python -m pytest backend\tests\streamer_tournament_engine\test_streamer_tournament_router.py -k public_streamer_list_accepts_lowercase_persisted_statuses -vv`
  - Result: `1 passed`
- `python -m pytest backend\tests\hosted_competition_engine\test_public_list.py -vv`
  - Result: `1 passed`

## Outcome

- `/regen-universe/tracking` now has a durable schema repair path for drifted runtimes and a direct regression test.
- The backend dependency set needed by the world aggregate is now covered as follows:
  - `Docs/CODEX_RUNTIME_PROOF_REPORT.md` already showed `200` responses for `rising-stars`, `scouting-feed`, `seasons`, `awards`, `hall-of-fame`, and `federations`.
  - The new tracking regression test proves `/regen-universe/tracking` returns `200`.
  - The executed competition-family route tests prove `/api/competitions`, `/hosted-competitions`, and `/streamer-tournaments` return `200`.
- With the tracking repair and the world-provider payload fix in place, the world aggregate has no remaining known dependency mismatch in this repo for the repaired backend path.
