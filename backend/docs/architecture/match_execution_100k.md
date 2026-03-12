# Match Execution At 100k Concurrent Users

## Scope

This document covers the canonical path from fixture scheduling to final replay exposure for league, cup, and tournament matches. It separates what is implemented in the current codebase from the infrastructure that is still required for production scale.

## Canonical Lifecycle

1. Fixture scheduling writes the competition fixture and emits `competition.match.scheduled`.
2. The dispatcher creates one idempotent `match_simulation` queue job per fixture.
3. A worker consumes the queued job outside the request path.
4. Deterministic simulation produces commentary, scoreline, and key-moment replay payloads.
5. Replay archive persistence stores the append-only replay version and countdown metadata.
6. Competition services apply standings updates, knockout advancement, and settlement triggers.
7. Notification jobs emit user-facing match and tournament transition events.

## Implemented Now

- API tier: FastAPI app nodes expose notifications and replay APIs and initialize the local execution seam during module startup.
- Queue seam: `InMemoryQueuePublisher` publishes broker-ready queue events with a serialized `job_payload`.
- Worker tier: `LocalMatchExecutionWorker` consumes queue events from the in-process event bus and applies deterministic simulation, replay archival, league state updates, and settlement notifications.
- Replay archive: records are persisted through the replay archive repository with visibility-policy enforcement and public countdown metadata.
- Notifications: competition notification jobs are idempotent by `competition_id`, template, resource, and audience.
- Idempotency: match execution, settlement execution, and notification execution each maintain claim keys before applying side effects.

## Production Architecture

### API Tier

- Run stateless FastAPI pods behind an L7 load balancer.
- Keep request handlers write-light: validate input, persist fixture intent, enqueue work, return immediately.
- Terminate auth, rate limits, and request tracing at the edge and forward correlation IDs to internal services.

### Queue And Broker Tier

- Replace the in-memory publisher with Kafka, Redpanda, or RabbitMQ for durable queueing.
- Use separate topics or queues for `match_simulation`, `notification`, `bracket_advancement`, and `payout_settlement`.
- Partition `match_simulation` by `fixture_id` and transition jobs by `competition_id` to keep ordering deterministic where it matters.
- Persist the dispatcher outbox in the primary database so fixture commits and job publication are atomic.

### Worker Tier

- Run dedicated simulation workers that consume only match jobs and scale on queue lag and CPU.
- Run separate lightweight workers for notifications and settlement work to avoid head-of-line blocking behind simulation jobs.
- Store worker claim keys in Redis or the primary database so retries are safe across process restarts.
- Keep simulation deterministic from the job payload alone so retries do not need request context.

### Cache Tier

- Use Redis Cluster for countdown state, hot replay summaries, idempotency keys, and websocket fanout metadata.
- Cache replay list responses and public featured lists with short TTLs and explicit invalidation on replay archive writes.
- Keep per-user notification inbox cursors in Redis to reduce repeated database scans.

### Primary Database Strategy

- Use PostgreSQL for fixtures, replay metadata, outbox tables, and competition ledgers.
- Partition high-write append-only tables by day or competition season when volume grows.
- Keep replay metadata relational, but move bulky replay blobs out of the primary database.

### Read Replicas

- Serve replay list, public featured, standings reads, and notification history reads from replicas.
- Keep worker writes on the primary only.
- Use replica lag thresholds; fall back to primary for immediately-after-write user flows when lag exceeds the threshold.

### Websocket And Fanout Path

- Publish live state changes into Redis Streams or Kafka, then fan out through dedicated websocket gateway nodes.
- Keep websocket nodes stateless and shard subscriptions by fixture or competition.
- Push only compact state deltas over sockets; replay payload retrieval stays on HTTP.

### Object Storage

- Store replay payload JSON, commentary streams, and future rich media in object storage such as S3 or GCS.
- Keep only replay metadata, object keys, versions, and visibility flags in PostgreSQL.
- Use immutable object keys per replay version to preserve append-only auditability.

### Rate Limiting

- Apply per-user and per-IP rate limits at the API gateway.
- Use stricter limits on replay detail and public featured endpoints during finals and tournament spikes.
- Protect dispatcher endpoints with tighter write limits than read endpoints.

### Observability

- Emit structured logs with `fixture_id`, `competition_id`, `season_id`, and `idempotency_key`.
- Track queue lag, simulation latency, replay persistence latency, notification send latency, and websocket fanout failures.
- Add distributed traces from API enqueue to worker completion and replay exposure.
- Alert on duplicate execution attempts, replay persistence failures, and settlement job retries.

### Autoscaling

- Scale API pods on request rate and tail latency.
- Scale simulation workers on queue depth, CPU, and average execution duration.
- Scale websocket gateways on active connection count and outbound throughput.
- Pre-warm worker capacity before scheduled tournament windows and finals.

### Failure Recovery

- Use at-least-once queue delivery with idempotent workers.
- Persist an execution ledger entry per fixture state transition so workers can resume from the last completed step.
- Retry transient replay archive and notification failures independently from match simulation results.
- Dead-letter poisoned jobs and expose replay or settlement recovery runbooks for operators.

### Idempotency

- Fixture dispatch must be keyed by `fixture_id`, `match_date`, and window.
- Notification dispatch must be keyed by competition, template, resource, and audience.
- Settlement dispatch must be keyed by competition, settlement date, and source scope.
- Replay versions remain append-only; retries either no-op or write a higher version with the same immutable source match result.

## Why Simulation Stays Off The Request Path

- Simulation is CPU-heavy and can spike unpredictably during tournament bursts.
- Inline execution would couple user latency to simulation time and reduce API capacity under load.
- Queue-backed workers give retry control, backpressure, deterministic recovery, and better autoscaling signals.

## Capacity Model For 100k Simultaneous Users

- 100k concurrent users should be assumed to generate read-heavy traffic: replay lists, countdown polling, websocket subscriptions, and notification fetches.
- API nodes should target horizontal scale for reads while workers scale for scheduled kickoff density, not for total connected users.
- Finals and synchronized windows are the main burst driver, so worker pools, websocket gateways, and cache throughput must be sized for the number of simultaneous live fixtures rather than only logged-in users.

## Implemented Now Vs Infra Needed Later

### Implemented Now

- Canonical fixture-to-dispatch-to-simulation-to-replay-to-notification flow exists in code.
- Local execution seam is broker-ready because workers already consume serialized queue events.
- Replay visibility policy and public featured replay selection are enforced.
- League season completion emits settlement completion events and qualification notifications.

### Infra Needed Later

- Durable broker and transactional outbox.
- Shared idempotency store across workers.
- PostgreSQL plus read replicas for persistent competition and replay metadata.
- Redis cluster for countdown hot paths, fanout coordination, and replay caching.
- Object storage for replay payload bodies.
- Dedicated websocket gateway and broadcast infrastructure.
- Autoscaling policies, SLO dashboards, and operator recovery runbooks.
