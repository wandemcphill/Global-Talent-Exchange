# Real-Player Bulk Import Runbook

This runbook covers the staged 10k-15k real-player bulk-import operator flow.

## File Format

Use a JSON array, `players` object key, or JSONL file of row objects.

Each row should include at minimum:

- `provider_player_id`
- `canonical_name`
- `nationality` or `nationality_code`
- `date_of_birth` or `birth_year`
- `primary_position`
- `current_real_world_club` and `current_real_world_league`

Optional row fields:

- `current_real_world_club_key`
- `current_real_world_league_key`
- `current_market_reference_value`
- `market_reference_currency`
- `priority_bucket`

Test-only sample fixture:

- `backend/tests/fixtures/real_player_bulk_import_sample.json`

## Dry-Run Flow

1. Stage the file without publishing:

```bash
python backend/scripts/import_real_players_bulk.py --file backend/tests/fixtures/real_player_bulk_import_sample.json --provider bulk-fixture --batch-size 1000 --database-url $env:GTE_DATABASE_URL
```

2. Inspect the tracked counts:

```bash
python backend/scripts/report_real_player_import.py --run-id <run-id> --database-url $env:GTE_DATABASE_URL
```

3. Validate the first publish slice without writing players:

```bash
python backend/scripts/publish_real_players.py --run-id <run-id> --limit 500 --priority default --dry-run --database-url $env:GTE_DATABASE_URL
```

## Sample Import Flow

1. Import the staged file:

```bash
python backend/scripts/import_real_players_bulk.py --file <path> --provider <provider-name> --batch-size 1000 --database-url $env:GTE_DATABASE_URL
```

2. Capture the returned `run.id`.

3. Report the run:

```bash
python backend/scripts/report_real_player_import.py --run-id <run-id> --database-url $env:GTE_DATABASE_URL
```

Expected report fields:

- `inserted_rows`
- `updated_rows`
- `duplicate_skipped_rows`
- `mapped_rows`
- `unresolved_rows`
- `publish_ready_rows`
- `published_rows`
- `failed_rows`
- `processing_state_distribution`

## Resume Flow

Use this when an import fails on malformed input after some batches already committed.

1. Fix the source file.

2. Resume the saved run:

```bash
python backend/scripts/resume_real_players_bulk.py --run-id <run-id> --database-url $env:GTE_DATABASE_URL
```

3. Re-run the report and confirm `resume_cursor` is now `null`.

## Repair Flow

Repair canonical mappings after missing club or competition references are added.

Repair one run:

```bash
python backend/scripts/repair_real_player_mappings.py --run-id <run-id> --database-url $env:GTE_DATABASE_URL
```

Repair every unresolved staged row:

```bash
python backend/scripts/repair_real_player_mappings.py --state unresolved --database-url $env:GTE_DATABASE_URL
```

Then re-run the report and confirm `unresolved_rows` moved down while `publish_ready_rows` moved up.

## Publish Flow

Publish only rows already classified as `mapped_ready`.

```bash
python backend/scripts/publish_real_players.py --run-id <run-id> --limit 500 --priority default --database-url $env:GTE_DATABASE_URL
```

Then audit the run again:

```bash
python backend/scripts/report_real_player_import.py --run-id <run-id> --database-url $env:GTE_DATABASE_URL
```

The publish command excludes rows still in partial or invalid states and only marks successfully written rows as `published`.
