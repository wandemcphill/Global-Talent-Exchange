# GTEX Backend Migration Runbook

Last reviewed: 2026-06-06

## Guardrail

Migration ownership for this production-readiness lane is verification and runbook truth. Do not create, rename, delete, rebase, or regenerate files under `backend/migrations/versions/*` unless a task explicitly assigns migration script work.

This checkout does not contain `backend/alembic`. Canonical Alembic assets live under `backend/migrations`.

## Current Head

Current observed migration head:

```text
20260604_0094_club_squad_sources
```

Recent durable schema revisions:

```text
20260527_0091_trader_metrics_and_payment_windows
20260531_0092_auth_trust_tables
20260603_0093_club_formations
20260604_0094_club_squad_sources
```

## Inspect Migration State

Run from the repository root:

```powershell
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini current
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini heads
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini history --verbose
```

Expected healthy state:

- `heads` reports a single head, `20260604_0094_club_squad_sources`.
- `current` on an upgraded database matches that head.
- `alembic_version` contains only the current graph head after repair migrations settle.

## Empty-DB Upgrade Verification

Use a disposable database. For local SQLite verification:

```powershell
$env:GTE_DATABASE_URL = "sqlite+pysqlite:///$(Resolve-Path backend)/.tmp_empty_upgrade.db"
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini upgrade head
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini current
Remove-Item backend\.tmp_empty_upgrade.db -ErrorAction SilentlyContinue
```

The test-backed empty-db gate is:

```powershell
C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend/tests/persistence/test_migrations.py backend/tests/regen/test_regen_migrations.py
```

`backend/tests/persistence/test_migrations.py` creates a temporary SQLite database, upgrades it through the current graph, verifies expected contract tables, and checks the resulting Alembic version against the dynamically discovered single head.

## App Boot Schema Check

Normal app boot should keep `GTE_RUN_MIGRATION_CHECK=true` outside local one-off smoke tests. Startup readiness depends on:

- Database connectivity.
- Schema head consistency.
- Redis/Kafka degradation surfaced as dependency issues when those services are intentionally absent.

Only use `SKIP_SCHEMA_CHECK=true` for controlled local diagnostics where schema checks would hide an unrelated failure. Never use it for staging or production readiness.

## Rollback Runbook

Rollback is operational, not a source rewrite:

1. Stop API and workers that can write to the target database.
2. Snapshot or backup the database.
3. Identify the current and target revisions:

```powershell
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini current
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini history --verbose
```

4. For a one-step rollback in a disposable or approved environment:

```powershell
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini downgrade -1
```

5. For a named target, downgrade explicitly:

```powershell
C:\Python314\python.exe -m alembic -c backend/migrations/alembic.ini downgrade <target_revision>
```

6. Re-run `current`, then run the focused migration tests against a restored disposable copy before re-enabling writers.

If a downgrade would drop user economic data, wallet ledger data, payment rail state, auth sessions, or audit evidence, stop and use a forward repair migration instead.

## Test-Credential and Secret Baseline

Production-like environments must replace placeholder secrets before startup. The backend config rejects known local placeholders for:

- `GTE_AUTH_SECRET`
- `GTE_MEDIA_SIGNING_SECRET`

Rotation checklist:

1. Generate unique values in the secret manager.
2. Deploy secrets before the application rollout.
3. Restart API and workers.
4. Confirm `/ready` and protected `/metrics` access through an admin-authenticated path.
5. Remove old secret values from the environment.

Test credentials belong only in `backend/tests/support/secrets.py` and test environment setup. Do not copy those values into `.env`, runbooks for production, staging manifests, or payment rail configuration.

## When to Stop

Stop and hand off to the migration owner when:

- `alembic heads` reports more than one head.
- `current` remains behind `20260604_0094_club_squad_sources` after `upgrade head`.
- A parallel worker has uncommitted edits under `backend/migrations/versions/*`.
- A migration touches wallet ledger, payment rails, auth, audit, or player ownership tables and the rollback would destroy authoritative records.
- A new durable contract needs schema work but the task only assigned runbook or verification ownership.
