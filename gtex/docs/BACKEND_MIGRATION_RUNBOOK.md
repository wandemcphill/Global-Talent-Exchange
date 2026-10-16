# GTEX Backend Migration Runbook

## Guardrail

Migration freeze is active for parallel threads. Do not create, rename, delete, rebase, or regenerate files under `backend/migrations/versions/*` unless the task explicitly requires migration work.

This documentation lane observed the migration state but did not edit any migration files.

## Merge order

Validate the staged merge in this order:

1. Thread A + Thread B
2. Club-Social isolated slice
3. Thread C
4. Thread D

## Current coordination target

Observed merge-pack revisions in this workspace:

- `20260316_0012_thread_a_creator_league_core.py`
- `20260316_0012b_creator_account_system.py`
- `20260316_0013_merge_creator_heads.py`
- `20260316_0014_thread_c_creator_broadcast_revenue.py`
- `20260317_0015_thread_d_creator_fan_engagement.py`

Observed on `2026-03-17`:

- `python -m alembic -c backend/migrations/alembic.ini heads` -> `20260317_0015 (head)`
- `python -m alembic -c backend/migrations/alembic.ini current` -> `20260316_0013 (mergepoint)`

The migration chain is present in the repo, but the local SQLite database inspected here is not yet at head.

## Inspect migration state

```powershell
python -m alembic -c backend/migrations/alembic.ini current
python -m alembic -c backend/migrations/alembic.ini heads
python -m alembic -c backend/migrations/alembic.ini history --verbose
```

## Apply existing migrations

```powershell
python -m alembic -c backend/migrations/alembic.ini upgrade head
```

Or use the local wrapper:

```powershell
python backend/scripts/dev.py migrate
```

If `current` still reports `20260316_0013 (mergepoint)`, do not validate Thread C or Thread D routes against the local app database until `upgrade head` succeeds.

## Reset local SQLite demo state

```powershell
python backend/scripts/dev.py reset-db
python backend/scripts/dev.py migrate
python backend/scripts/dev.py rebuild-demo-market --seed 20260311
```

Use this only for disposable local SQLite work. Do not delete or rewrite migration files to recover a bad state.

## Evidence-backed verification

Validated from this workspace on `2026-03-17`:

```powershell
python -m pytest backend/tests/persistence/test_migrations.py -q
```

Result:

- `1 passed, 4 warnings in 24.50s`

The migration verification test creates a temporary `sqlite+pysqlite` database and confirms the expected merged tables are materialized through Thread D.

## SQLite caveat

- The migration evidence recorded here is SQLite-backed.
- This docs lane did not re-run Postgres or other non-SQLite migration validation.
- `backend/.env.example` still keeps `GTE_RUN_MIGRATION_CHECK=true`, so normal app boot continues to perform a schema check.

## When to stop instead of fixing

- `alembic heads` does not resolve to a single `20260317_0015 (head)` in the merged branch you are validating.
- `alembic current` stays behind the expected head after an `upgrade head`.
- A parallel thread has uncommitted changes under `backend/migrations/versions/*`.
- You think a new migration is needed. Stop and hand that work to the merge owner instead of generating one from a parallel thread.
