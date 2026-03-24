# 2nd.zip Real-Player Import Runbook

Use the backend scripts below from the repository root. All commands need either `--database-url` or `GTE_DATABASE_URL`.

## Read `2nd.zip`

Start with the guarded dry run. This validates the archive, applies the base eligibility fence, records verification state in the import batch tables, and does not publish players.

```bash
python backend/scripts/import_real_players_from_2nd_zip.py --database-url <db-url> --file 2nd.zip --batch-size 1000 --limit 2000
```

The command returns a `run_id`. Keep it for resume, repair, publish, and reporting.

## 2,000-row dry run

Recommended first step:

```bash
python backend/scripts/import_real_players_from_2nd_zip.py --database-url <db-url> --file 2nd.zip --batch-size 1000 --limit 2000
```

Expected report fields include:

- `total_rows_read`
- `eligible_rows`
- `duplicate_skipped`
- `mapped_ready`
- `mapped_partial`
- `unresolved`
- `fallback_valued`
- `free_agent_fallback`
- `publish_ready`
- `published`
- `failed`

The verification fence only marks rows as `publish_ready` when they are eligible, fully mapped, and pass pricing preview without fallback.

## Full import

After the dry run looks clean enough, stage the full archive with the same script and omit `--limit`.

```bash
python backend/scripts/import_real_players_from_2nd_zip.py --database-url <db-url> --file 2nd.zip --batch-size 1000
```

This creates a separate run for the full-scope import path.

## Resume

If a run stops mid-import, resume it with the recorded `run_id`.

```bash
python backend/scripts/resume_real_players_from_2nd_zip.py --database-url <db-url> --run-id <run-id>
```

Resume continues from the next unread `players.csv` row for that run scope.

## Repair

Use repair after fixing canonical mappings or when you want to re-evaluate rows that are still blocked.

Repair a single run:

```bash
python backend/scripts/repair_real_players_from_2nd_zip.py --database-url <db-url> --run-id <run-id>
```

Repair every run that still has unresolved rows:

```bash
python backend/scripts/repair_real_players_from_2nd_zip.py --database-url <db-url> --state unresolved
```

Repair only re-evaluates blocked rows. It does not publish anything.

## Publish

Publish only rows that are still `publish_ready`. Partial, unresolved, invalid, and failed rows are excluded by the fence.

Publish a bounded set:

```bash
python backend/scripts/publish_real_players_from_2nd_zip.py --database-url <db-url> --run-id <run-id> --limit 100
```

Publish a specific tier only:

```bash
python backend/scripts/publish_real_players_from_2nd_zip.py --database-url <db-url> --run-id <run-id> --limit 100 --tier core
```

Publishing writes players through the existing real-player ingestion service one row at a time and updates:

- `inserted`
- `updated`
- `published`

## Reporting

Inspect the current run state at any point:

```bash
python backend/scripts/report_real_players_from_2nd_zip.py --database-url <db-url> --run-id <run-id>
```

Use this after dry run, after repair, and after publish to confirm the counts are still coherent before widening the rollout.
