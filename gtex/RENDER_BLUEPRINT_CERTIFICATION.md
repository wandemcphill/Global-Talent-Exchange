# Render Blueprint Certification

Date: 2026-08-25
Branch: main

## Production resources

| Resource | Type | Region | Role |
|---|---|---|---|
| gtex-api | web / Python | Frankfurt | Production API, wallet and payment webhooks |
| gtex-web | static | — | Production Flutter web shell |
| gtex-rq-worker | worker / Python | Frankfurt | Background task queue |
| gtex-simulation-worker | worker / Python | Frankfurt | Match simulation processing |
| gtex-outbox-relay | worker / Python | Frankfurt | Durable outbox relay |
| gtex-player-ingestion-worker | worker / Node | Frankfurt | Player ingestion / BullMQ |
| gtex-realplayer-ingest | cron / Python | Frankfurt | Real-player refresh |
| gtex-sofifa-import | cron / Python | Frankfurt | SoFIFA frozen import |
| gtex-appreciation-reprice | cron / Python | Frankfurt | Weekly player repricing |
| gtex-regen-rebuild | cron / Python | Frankfurt | Regen rebuild |
| gtex-squad-tier-backfill | cron / Python | Frankfurt | Squad-tier maintenance |
| gtex-cache | keyvalue / Render Valkey | Frankfurt | Shared cache and job queue |

## Redis / Key Value

`gtex-cache` is now Blueprint-managed because Redis/Valkey is required for the
production cache, RQ/task queue, simulation coordination, outbox relay, and the
Node ingestion queue. It uses:

- `plan: starter`
- `maxmemoryPolicy: noeviction` so queued jobs are not evicted under pressure
- `persistenceMode: journal-snapshot` for production durability
- `ipAllowList: []` so the datastore is internal-only
- `GTE_REDIS_URL` is wired from the Key Value service into every Redis consumer

Render documents Key Value as Redis-compatible and recommends `noeviction` for
job queues and Journal + Snapshot for non-cache production workloads.

## Database

PostgreSQL remains Supabase-managed. `DATABASE_URL` stays `sync: false` and no
Render `databases:` block exists.

## Payment rails

Paystack is now production-enabled in the application and Blueprint:

- `GTE_ENABLE_PAYSTACK=true`
- `GTE_PAYSTACK_SECRET_KEY` is dashboard-managed
- `GTE_PAYSTACK_WEBHOOK_SECRET` is dashboard-managed
- `GTE_PAYSTACK_CALLBACK_URL` is dashboard-managed
- Paystack is included in the supported automatic top-up providers
- Paystack webhook routing remains protected by signature verification
- Existing admin payment-rail state already contains Paystack as live

KoraPay remains live as the other automatic gateway. Manual bank transfer
remains available through the treasury flow.

## Environment groups

The repository does **not** currently use Render `envVarGroups` / `fromGroup`.
Shared infrastructure configuration is declared directly in the Blueprint;
secrets and operator-managed values remain dashboard-managed with `sync: false`.
The Render dashboard may contain additional environment variables not represented
in the Blueprint. This certification does not assume those values are absent.

## Production toggles deliberately not enabled

Not every feature flag should be blindly switched on merely because the app is
production-ready. Kafka remains unset because no Kafka service is provisioned;
audio commentary and the season-engine flags remain feature-specific opt-ins.
The outbox relay itself is enabled on its dedicated worker.

## Verdict

**BLUEPRINT CERTIFIED — Supabase PostgreSQL + Blueprint-managed Render Key Value +
production Paystack/KoraPay payment rails.**
