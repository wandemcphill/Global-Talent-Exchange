# 2nd.zip Publish Parallelism Plan

## Purpose

This note defines the minimum safe design for a future `2` to `4` worker publish mode for verified `2nd.zip` rows.

It is intentionally additive. It does not change matcher behavior, publish eligibility, tier membership, or the current single-worker publish command.

## Current Assessment

Current multi-worker publish is unsafe.

Why:

- `publish_run(...)` takes a snapshot of all current `publish_ready` rows before any row-level claim exists.
- `_publish_row(...)` performs the expensive downstream write before it flips the import row out of `publish_ready`.
- `_refresh_batch_summary(...)` derives `publish_ready`, `published`, and `failed` directly from row state, so a race can corrupt counters as well as row state.
- `RealPlayerImportRow` has uniqueness per batch row and source key, but no claim token, no lease timestamp, and no worker ownership field.
- Downstream uniqueness on `Player` and `RealPlayerSourceLink` helps prevent duplicate source identities, but it does not prevent two workers from trying the same row, wasting work, or overwriting row status after one worker already succeeded.

## Exact Risks To Solve First

1. Double-selection of the same row.
   Two workers can read the same `publish_ready` row set because selection is not an atomic claim.

2. Success overwritten by a later failure.
   If worker A publishes a row and worker B races the same row and hits a downstream uniqueness error, worker B can still mark the import row `failed` afterward unless the completion update is claim-guarded.

3. Counter corruption.
   Batch `published`, `publish_ready`, and `failed` counts are row-derived. A stale worker can move a genuinely published row back into a failed-looking state.

4. No crash recovery contract.
   There is no lease expiry or reclaim rule if a worker dies after taking work but before finishing it.

5. No bounded worker ownership.
   Batch-level metadata records publish activity, but it does not identify which worker owns which rows.

## Required Prerequisites

Use first-class row claim columns on `real_player_import_rows`. Do not try to build this only on nested JSON metadata.

Recommended columns:

- `publish_claim_token`
- `publish_claim_worker_id`
- `publish_claimed_at`
- `publish_claim_expires_at`
- `publish_attempt_count`

Required behavior:

1. Atomic chunk claim.
   A worker must claim a bounded chunk in one short transaction, only where the row is still `publish_ready`, not yet `published`, and not currently leased by another live worker.

2. Lease-based recovery.
   Claims must expire so abandoned rows can be reclaimed safely after worker death.

3. Claim-bound completion guard.
   Success and failure updates must include the current `publish_claim_token`. A worker that no longer owns the row must not mutate final row state.

4. Published-state guard.
   Failure handling must not downgrade a row that is already marked published.

5. Chunk-based selection.
   Workers should claim small ordered slices, not the entire run, so lease duration stays bounded and reclaim stays practical.

6. Reporting updates.
   Reporting must treat claimed rows as in-flight, not ready or failed, until the owning worker resolves them.

## Recommended Claim Strategy

Start with ordered chunk claims by `row_number`.

Suggested initial operating values:

- worker count: `2`
- max worker count after proof: `4`
- chunk size: `25` to `50`
- lease duration: `15` minutes

Claim rules:

- only tier-filtered rows may be claimed
- only rows with `publish_ready=true` and `published=false` may be claimed
- rows with an unexpired claim owned by another worker are ineligible
- stale claims may be reclaimed only after lease expiry

Completion rules:

- on success: mark `published=true`, `publish_ready=false`, clear claim fields, persist `published_at`
- on handled row failure: clear `publish_ready`, clear claim fields, record `last_publish_error`, increment attempts
- on stale-claim detection: do not overwrite row state; record only worker-local diagnostics

## Rollout Plan

Phase 1:

- keep the active path single-worker
- land batching and commit-efficiency improvements first
- measure the new single-worker drain rate before introducing concurrency

Phase 2:

- add claim columns and claim helpers behind an unused code path
- add tests for double-claim prevention, lease expiry, and stale-worker completion rejection

Phase 3:

- enable `2` workers only for bounded `tier_1` publish slices
- confirm no duplicate downstream writes, no false failures, and coherent counts after restarts

Phase 4:

- consider `4` workers only after a clean `2` worker rollout with stable metrics
- keep `mapped_partial` / `free_agent_fallback` out of this rollout unless row-claim safety is already proven

## Why Single-Worker Batching Is Still Phase One

Single-worker batching should land first because it attacks the current bottleneck without adding ownership, lease, or recovery complexity.

It preserves the existing resumable operator model, avoids row-claim migration risk, and is the lowest-risk way to improve throughput before concurrency is introduced.
