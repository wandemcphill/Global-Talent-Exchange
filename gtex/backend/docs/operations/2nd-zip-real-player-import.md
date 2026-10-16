# 2nd.zip Real-Player Import Runbook

Use the repository root as the working directory for every command below.

## Authoritative Database Policy

- Postgres is the authoritative database for the heavy `2nd.zip` import, report, and publish workflow.
- SQLite is acceptable only for local rehearsal and test runs. Do not use SQLite for the authoritative large publish run.
- The matcher ambiguity blocker is already closed. Do not reopen matcher work in this flow.
- The `height_in_cm` hygiene fix is already in place for `2nd.zip` input. Do not widen that behavior here.
- Publish eligibility rules remain unchanged.
- `mapped_partial` and `free_agent_fallback` rows are expected to remain out of `tier_1`.
- Parallel publish is not approved. Use a single publisher only.

Why Postgres is now the authoritative path:

- SQLite hit file-lock contention when long-running publish overlapped report/summary writes.
- The `report` command is now read-only by default, which makes operator monitoring safer during active publish.
- Postgres gives the workflow MVCC-backed read/write isolation instead of SQLite file-level contention.

## Verified Clean Source-of-Truth State

Use these counts as the authoritative clean-state target before `tier_1` publish:

- `mapped_ready=10180`
- `publish_ready=10180`
- `mapped_partial=3514`
- `free_agent_fallback=3514`
- `failed=0`
- `unresolved=0`
- `ambiguous_match_count=0`

Interpretation:

- `mapped_ready` and `publish_ready` are the `tier_1` pool.
- `mapped_partial=3514` is expected and is the same population represented by `free_agent_fallback=3514`.
- Those `3514` rows are not part of `tier_1` and must be handled later in a separate operator pass.
- The current report payload does not emit a separate `ambiguous_match_count` field. Treat `ambiguous_match_count=0` as a verified prerequisite from the matcher-fix validation, not as a new live report counter.

## Prerequisites

- A real Postgres connection string is available as `<POSTGRES_DATABASE_URL>`.
- `2nd.zip` is available locally and is the exact archive you intend to publish.
- You are intentionally running against Postgres, not SQLite.
- No other `tier_1` publisher is already running for the same run.
- The DB readiness check below returns:
  - `status=ready`
  - `authoritative_large_publish_supported=true`

## 1. Verify Postgres Connectivity and Schema Readiness

Run this first:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" check-db
```

Expected result:

- `status` is `ready`
- `database_backend` is `postgresql`
- `authoritative_large_publish_supported` is `true`
- `schema_heads` is non-empty and current

If this command does not pass, stop before import or publish.

## 2. Create or Reuse the Authoritative Postgres Run

Preferred rule:

- Prefer a Postgres database that does not already contain a completed `2nd.zip` batch for this archive and scope.

Actual script behavior:

- The batch key is derived from `archive_sha256` plus scope (`all` or `first-N`).
- Re-running the same import command against the same Postgres database and same archive scope reuses the existing completed batch instead of creating a new run.
- If you need a truly fresh authoritative rerun for the same archive SHA and scope, use a clean Postgres database or clear the old `2nd.zip` batch through your normal DBA cleanup path before rerunning.

Authoritative import/classification command:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" import --file "2nd.zip" --batch-size 1000
```

Capture and retain from the JSON response:

- `run_id`
- `batch_key`
- `archive_path`
- `archive_sha256`

Those fields are the provenance record for the authoritative Postgres run.

## 3. Validate the Postgres Import/Classify State

Read-only report command:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" report --run-id <POSTGRES_RUN_ID>
```

Optional summary writeback if you explicitly want persisted summary/status refresh:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" report --run-id <POSTGRES_RUN_ID> --refresh-summary
```

Expected clean-state target before `tier_1` publish:

- `publish_ready=10180`
- `mapped_ready=10180`
- `mapped_partial=3514`
- `free_agent_fallback=3514`
- `failed=0`
- `unresolved=0`

Stop conditions before publish:

- `scope_complete` is `false`
- `failed` is non-zero
- `unresolved` is non-zero
- `publish_ready` does not line up with the expected clean-state target
- provenance fields (`archive_path`, `archive_sha256`, `batch_key`) do not match the intended archive

If counts differ, stop and explain the difference before publishing.

## 4. Run Tier-1 Publish on Postgres

Use the existing single-worker path. Do not enable parallel publishing.

Recommended command:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" publish --run-id <POSTGRES_RUN_ID> --tier tier_1 > backend/.tmp_2ndzip_tier1_postgres.out 2> backend/.tmp_2ndzip_tier1_postgres.err
```

Notes:

- This uses the safe default publish batch size of `100`.
- The service checkpoints publish bookkeeping every `500` processed rows by default.
- Publish selects only the rows that are currently `publish_ready` for the requested tier.
- `mapped_partial` and `free_agent_fallback` rows remain excluded from `tier_1`.

If you need the explicit batch-size form, keep it single-worker:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" publish --run-id <POSTGRES_RUN_ID> --tier tier_1 --batch-size 100 > backend/.tmp_2ndzip_tier1_postgres.out 2> backend/.tmp_2ndzip_tier1_postgres.err
```

## 5. Monitor Progress Safely

Use read-only report polling while publish is active:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" report --run-id <POSTGRES_RUN_ID>
```

Watch these fields:

- `status`
- `published`
- `inserted`
- `updated`
- `publish_ready`
- `failed`
- `unresolved`

Expected status meanings:

- `running`: the import or publish invocation is still active
- `completed`: the run has no remaining `failed` or `unresolved` rows
- `completed_with_errors`: the run has one or more real `failed` or `unresolved` rows

Important status rule:

- Expected `mapped_partial` / `free_agent_fallback` rows by themselves do not mean `completed_with_errors`.

## 6. Safe Resume / Rerun Rule

If the `tier_1` publisher exits before `publish_ready=0`, rerun the exact same command:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" publish --run-id <POSTGRES_RUN_ID> --tier tier_1 > backend/.tmp_2ndzip_tier1_postgres.out 2> backend/.tmp_2ndzip_tier1_postgres.err
```

Why this is safe:

- The publisher only targets rows that are still `publish_ready` at invocation time.
- Successfully published rows are marked out of the candidate pool.
- No separate publish-resume subcommand is required.

Drain rule:

- Keep rerunning only until `publish_ready=0` for `tier_1`.
- Do not mix the `3514` `mapped_partial` / `free_agent_fallback` rows into this pass.

## 7. Operator Sequence

1. Run `check-db` against `<POSTGRES_DATABASE_URL>`.
2. Run the authoritative Postgres `import`.
3. Save `run_id`, `batch_key`, `archive_path`, and `archive_sha256`.
4. Run `report` and confirm the clean-state counts.
5. Start `tier_1` publish.
6. Poll `report` until `publish_ready=0` for `tier_1`.
7. If publish exits early, rerun the same `publish` command.
8. Leave `mapped_partial` / `free_agent_fallback` for a later dedicated pass.

## 8. Troubleshooting

### Postgres connection issues

- Run `check-db` again.
- Confirm the URL is a real Postgres URL, not SQLite.
- Confirm `authoritative_large_publish_supported=true`.
- Confirm the target host is reachable from the operator environment.

### Migration or schema drift

- Run `check-db`. It verifies connectivity and schema readiness before the run.
- Do not start import or publish until `check-db` returns `status=ready`.

### Postgres foreign key violation during import

Symptom:

- The import fails immediately with `insert or update on table "real_player_import_rows" violates foreign key constraint`.
- The missing key is a `player_import_item_id` value that looks like `2ndzip:<player_id>`.

Cause:

- Older `2nd.zip` dry-run code wrote a synthetic `player_import_item_id` into `real_player_import_rows` without creating a matching `player_import_items` parent row first.
- SQLite rehearsals could miss this because SQLite foreign-key enforcement is not enabled by default in the local test path.

Fix now in place:

- Eligible `2nd.zip` candidates now create or reuse a real `player_import_items` row before evaluation/staging continues.
- That parent row is committed before any dependent `real_player_import_rows` insert uses the foreign key.
- The child row now stores the real `player_import_items.id`, not the synthetic `2ndzip:<player_id>` placeholder.

Safe rerun after deploying the fix:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" resume --run-id <FAILED_POSTGRES_RUN_ID>
```

For the failed authoritative run captured during this issue, replace `<FAILED_POSTGRES_RUN_ID>` with `b73c52f5-5bab-4a4c-941b-dfc4a80b94ca`.

### Postgres rollback / reconnect failure during import or resume

Symptom:

- The run fails after processing rows successfully with `Can't reconnect until invalid transaction is rolled back. Please rollback() fully before proceeding`.
- `scope_complete` stays `false` and `next_resume_row_number` points to the first row of the unfinished chunk.

Cause:

- `RealPlayerIngestionService._prepare_batch()` caught row-level exceptions from match, stage, or preview work and kept using the same SQLAlchemy session afterward.
- On Postgres, a fatal SQLAlchemy database error invalidates the active transaction/connection. Reusing that session for `_upsert_import_row()` or later queries triggered the reconnect failure instead of the original database error.

Fix now in place:

- Fatal SQLAlchemy database exceptions in `_prepare_batch()` now bubble out immediately instead of being downgraded into row-level issues.
- The caller rolls back the transaction before any further ORM work happens on that session.
- The `2nd.zip` operator path records batch failure metadata in a fresh session, so resume can continue cleanly from the last committed row on the next invocation.

Safe resume after deploying the fix:

```bash
python backend/scripts/real_player_import_from_2nd_zip.py --database-url "<POSTGRES_DATABASE_URL>" resume --run-id b73c52f5-5bab-4a4c-941b-dfc4a80b94ca
```

Do not start `tier_1` publish for this run until `report` shows `scope_complete=true`.

### Import count mismatch

- Re-run `report` for the same `run_id`.
- Confirm `archive_sha256`, `archive_path`, and `batch_key` match the intended archive.
- Confirm you are not accidentally looking at a reused batch for the same archive scope on an older Postgres database.
- Stop before publish if `failed` or `unresolved` is non-zero.

### Interrupted publish

- Re-run the exact same `publish --tier tier_1` command.
- Confirm progress with `report`.
- Continue only until `publish_ready=0` for `tier_1`.

### Empty or noisy logs

- The redirected `stdout` file will normally contain the final JSON payload after the publish command exits.
- The redirected `stderr` file may be quiet even while publish is healthy.
- Treat `report` as the authoritative live-monitoring command if log files are empty.
- If `stderr` is noisy, keep the command as-is and rely on the JSON `report` output for the actual counters.

### Count verification checklist

Before `tier_1` publish:

- `publish_ready=10180`
- `mapped_ready=10180`
- `mapped_partial=3514`
- `free_agent_fallback=3514`
- `failed=0`
- `unresolved=0`

After `tier_1` drain:

- `publish_ready=0` for `tier_1`
- `failed=0`
- `unresolved=0`
- `mapped_partial=3514`
- `free_agent_fallback=3514`

## 9. Hard Rules for Future Reruns

- Use Postgres for the authoritative large import/publish workflow.
- Keep SQLite only for local rehearsal.
- Do not change matcher logic in this operator flow.
- Do not change publish eligibility rules in this operator flow.
- Do not pull `mapped_partial` / `free_agent_fallback` into `tier_1`.
- Do not introduce parallel publish until safe row claiming exists.
