# CODEX Streamer Engine Repair Report

Date: 2026-03-30

## Scope

This repair targeted the streamer/e-game tournament lane only:

- `GET /streamer-tournaments`
- `GET /leaderboard/global`
- `GET /season/current`
- `GET /season/history`

No streamer tournament behavior was merged into football competition flows.

## Root Cause Audit

### 1. Streamer tournament enum drift

Database definitions:

- `backend/migrations/versions/20260317_0016_streamer_tournament_engine.py`
- The streamer enum types are defined with lowercase wire values such as `published`, `live`, and `completed`.

ORM definitions before repair:

- `backend/app/models/streamer_tournament.py`
- The SQLAlchemy `Enum` columns did not set `values_callable`, so SQLAlchemy bound enum member names like `PUBLISHED` instead of the lowercase DB values from the migration.
- On Postgres, that caused the runtime failure reported in `CODEX_RUNTIME_PROOF_REPORT.md`:
  - `invalid input value for enum streamertournamentstatus: "PUBLISHED"`

API serialization:

- `backend/app/streamer_tournament_engine/schemas.py`
- The API schemas were already aligned with lowercase wire values because the models use `str` enums and FastAPI/Pydantic serialize them as their string values.
- No serializer contract change was required.

### 2. Leaderboard season schema/runtime drift

Schema source:

- `backend/migrations/versions/20260328_0055_leaderboards_seasons.py`
- The leaderboard season tables already existed in migration history, but runtime databases could still be missing them due to drift.

Failure mode:

- `leaderboard_seasons` and its related tables were missing in the shipped runtime DB used for proof.
- That broke:
  - `GET /leaderboard/global`
  - `GET /season/current`
  - `GET /season/history`

Additional enum consistency note:

- `backend/app/leaderboards/models.py` had the same SQLAlchemy enum-value drift pattern for leaderboard season enums.
- It did not trigger the original proof failure, but it was normalized in the repair so future rows stay aligned with the migration-defined lowercase values.

## Code Changes

### ORM fixes

- Updated `backend/app/models/streamer_tournament.py`
  - All streamer tournament SQLAlchemy enums now use `values_callable` and `validate_strings=True`.
  - The ORM now binds lowercase wire values that match the DB enum labels.

- Updated `backend/app/leaderboards/models.py`
  - Leaderboard enums now also use `values_callable` and `validate_strings=True`.
  - This removes lowercase/uppercase drift between model writes and schema defaults.

### Migration repair

- Added `backend/migrations/versions/20260330_0075_streamer_engine_schema_repair.py`
  - Recreates missing leaderboard season tables and indexes if a runtime database drifted behind the expected schema.
  - Normalizes lowercase enum/text values for streamer and leaderboard rows on non-Postgres drifted databases.

## Regression Coverage

Added or updated:

- `backend/tests/streamer_tournament_engine/test_streamer_tournament_router.py`
  - Verifies `/streamer-tournaments` can discover a tournament persisted with lowercase enum values.

- `backend/tests/leaderboards/test_leaderboard_router.py`
  - Verifies `/leaderboard/global`, `/season/current`, and `/season/history` return `200` with valid payloads.

- `backend/tests/persistence/test_migrations.py`
  - Verifies a drifted database can recover missing leaderboard tables at migration head.

## Verification

### Targeted tests

Passed:

- `python -m pytest backend/tests/streamer_tournament_engine/test_streamer_tournament_router.py -q`
- `python -m pytest backend/tests/leaderboards/test_leaderboard_router.py -q`
- `python -m pytest backend/tests/persistence/test_migrations.py -k "persistence_migrations_create_expected_tables or player_share_market_repair_migration_restores_missing_tables" -q`

### Runtime endpoint re-run

Verification environment:

- Source DB copy: `gte_backend.db`
- Migrated verification copy: `backend/.tmp_streamer_engine_repair_verify.db`
- App booted through the FastAPI app with migrations enabled and startup seeding disabled

Observed results after repair:

- `GET /streamer-tournaments` -> `200`
  - Body summary: `{"tournaments": []}`

- `GET /leaderboard/global?limit=12` -> `200`
  - Body summary: empty global board for the active season

- `GET /season/current` -> `200`
  - Active season auto-created successfully
  - Returned season id: `2ef983ff-4297-47ec-b9a9-5ea12b24e650`

- `GET /season/history?limit=4` -> `200`
  - Returned the active season instead of `500`

## Outcome

The streamer tournament enum mismatch is repaired at the ORM boundary, drifted leaderboard season schemas are recoverable through migration head, and the four affected public endpoints now respond successfully in the repaired runtime path.
