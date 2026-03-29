# GTEX Backend Audit Report

Date: 2026-03-29
Scope: tournament engine, viral feed/event pipeline, creator earnings, scale backbone/outbox/workers, load/chaos readiness.

## Executive Verdict

The audited backend is materially safer than the starting point, but it was not production-safe as originally found.

The main faults fixed in this pass were:

- tournament joins/results/advances were not protected by a distributed lock boundary
- outbox relay and worker consumers lacked durable claim/DLQ protections
- creator earnings could double count likes/shares across caller-generated event ids
- deferred side effects were firing on nested savepoint commits instead of only on the outer commit
- read-replica-backed reads did not fall back to primary on replica failure
- `backend/app/infinite_league/service.py` could fail with `ModuleNotFoundError: services`
- the Alembic graph had unresolved parallel heads again at `20260329_0067_*`

## Thread A: Tournament Engine

Validated / fixed:

- Entry fee charging is idempotent through the wallet transaction `idempotency_key` and tournament-user reference.
- Tournament joins now use a distributed join lock and row-lock-aware tournament reloads.
- Tournament results and round advancement now use a tournament state lock.
- Prize pool is re-synchronized from paid entries instead of relying on incremental mutation.
- `list_tournaments()` no longer mutates active tournaments without lock protection.
- API now surfaces busy lock contention as HTTP `409` instead of silently racing.
- Timeout resolution still advances the lower bracket slot / higher seed.

Remaining risk:

- The concurrency proof in this turn is targeted, not a full 1000-thread live cluster run against Redis/Postgres/Kafka together.

## Thread B: Viral Feed + Event Pipeline

Validated / fixed:

- Feed refresh requests now trigger only when the session tracker threshold is crossed.
- Refresh requests are marked in-flight and completed only after the surrounding transaction commits.
- Missing projection tables now degrade to in-memory stores instead of crashing feed requests.
- Personalized feed, orchestrator global state, viral distribution, and live metrics reads now fall back from read replica to primary on replica failure.
- Redis remains a cache path only; cold-start and persistence paths continue from Postgres-backed stores.

Remaining risk:

- Personalization quality under a real 100K user storm was not executed live in this turn; the provided load harness is the next step.

## Thread C: Creator Earnings

Validated / fixed:

- `clip_earnings_log` is now append-only at the ORM layer.
- Wallet creation and log insertion now use nested-savepoint / integrity-race handling for concurrent writers.
- Likes and shares are canonicalized per `(event_type, clip_id, viewer_user_id)` so a repeated user action cannot double count by swapping reference ids.
- Redis/cache updates remain deferred until the outer transaction commits.
- Earnings throughput metrics are recorded only after commit.

Remaining risk:

- Fraud heuristics beyond one-like/one-share-per-viewer were not expanded in this pass.

## Thread D: Backbone + Workers

Validated / fixed:

- Outbox relay now claims rows before publish, retries stale claims, and dead-letters exhausted rows.
- New durable worker consumer state tables track event claims, retries, and dead letters.
- Scale workers and queue consumers now claim/process/fail events idempotently and commit broker offsets only after a durable outcome.
- Dead-letter and retry boundaries now emit structured logs.
- Scale workers now emit queue/job metrics and dead-letter counters.
- The `services` import bridge was added so the infinite-league runtime resolves absolute imports correctly.
- The `20260329_0067_broadcast_network_watch_sessions` migration now points at the merged `0067` head, restoring a single Alembic head.

Remaining risk:

- A literal 10M pending-event drain was not executed; the new load harness covers backlog draining with configurable counts, but not that full scale in this turn.

## Thread E: Chaos / Production Behavior

Implemented harnesses:

- Load script: `backend/scripts/gtex_reliability_load.py`
- Chaos script: `backend/scripts/gtex_reliability_chaos.py`

Coverage:

- tournament join spike
- tournament burst fill
- feed refresh storm with session-driven reranking
- creator earnings storm
- outbox backlog drain
- deferred callback correctness under nested savepoints
- read replica fallback
- Redis lock fallback
- outbox dead-letter path

## Observability Hooks Added

Metrics added:

- `gtex_feed_refresh_total`
- `gtex_feed_refresh_duration_seconds`
- `gtex_creator_earnings_events_total`
- `gtex_creator_earnings_credit_total`
- `gtex_dead_letters_total`
- `gtex_outbox_relay_total`

Existing metrics also continue to cover:

- match result rate via `gtex_matches_total`
- queue throughput via `gtex_queue_messages_total`
- worker throughput/latency via `gtex_worker_jobs_total` and `gtex_worker_job_duration_seconds`

## Verification Executed

Targeted tests run and passing:

- `python -m pytest tests/backbone/test_queue_runtime.py -q`
- `python -m pytest tests/backbone/test_outbox_relay.py -q`
- `python -m pytest tests/tournaments/test_tournament_router.py -q`
- `python -m pytest tests/creator/test_creator_attention_earnings_service.py -q`
- `python -m pytest tests/viral/test_system_feed_refresh.py tests/viral/test_personalized_feed_service.py -q`

Additional checks run:

- `python -m py_compile ...` across the touched runtime/service/script files
- `python scripts/gtex_reliability_chaos.py --scenario all`
- `python scripts/gtex_reliability_load.py --scenario outbox-backlog --events 20 --concurrency 4`

## Residual Gaps

- No live external-service kill test was run against an actual deployed Redis/Kafka/read-replica topology; the chaos harness uses injected failures in-process.
- No 100K/10M scale execution was run end-to-end in this turn; scripts are ready for that next stage.
- The repository had many unrelated in-flight changes already present; this audit only hardened the targeted reliability surfaces above.
