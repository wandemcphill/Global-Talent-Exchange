# Blueprint Cost Audit — render.yaml

Date: 2026-08-25
Branch: main
Scope: production infrastructure and required runtime resources.

## Objective

Keep the production stack explicit and prevent accidental plan escalation while
provisioning the infrastructure the application actually requires.

## Production resources

| Resource | Type | Plan |
|---|---|---|
| gtex-api | web / Python | starter |
| gtex-web | static | static hosting |
| gtex-rq-worker | worker / Python | starter |
| gtex-simulation-worker | worker / Python | starter |
| gtex-outbox-relay | worker / Python | starter |
| gtex-player-ingestion-worker | worker / Node | starter |
| gtex-realplayer-ingest | cron / Python | starter |
| gtex-sofifa-import | cron / Python | starter |
| gtex-appreciation-reprice | cron / Python | starter |
| gtex-regen-rebuild | cron / Python | starter |
| gtex-squad-tier-backfill | cron / Python | starter |
| gtex-cache | Render Key Value | starter |

## Paid resources

The Blueprint intentionally provisions the paid resources required for a
production runtime. The additional paid datastore is `gtex-cache`, because Redis /
Valkey is required for queues, cache coordination, outbox processing, and the
Node ingestion worker.

PostgreSQL is **not** provisioned by Render. The production database remains on
Supabase, referenced through dashboard-managed `DATABASE_URL`.

## Cache configuration

`gtex-cache` is internal-only (`ipAllowList: []`), uses `noeviction` to protect
queued jobs, and uses Journal + Snapshot persistence. All Redis consumers receive
the internal connection string through Blueprint `fromService` wiring.

## Plan discipline

All always-on application services remain pinned to `starter`. No service is
silently promoted to `standard` or higher by the Blueprint.

## Verdict

**Cost-controlled production Blueprint: required services and required cache are
managed as code; Supabase remains the external database provider.**
