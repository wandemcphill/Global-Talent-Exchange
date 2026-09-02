# Render Key Value Production Certification

Date: 2026-08-25
Provider: Render Key Value (`type: keyvalue`, service `gtex-cache`)

## Production mode

`REDIS_ENABLED=true` and `GTE_REDIS_URL` is wired from the Blueprint-managed
`gtex-cache` Key Value instance into the five Redis consumers.

## Why Redis is required

Redis / Valkey is part of the production runtime for:

- shared application caching
- RQ/task queues
- simulation coordination
- outbox relay processing
- Node/BullMQ player ingestion

The application can still boot in a Redis-off development/test mode, but that is
not the production configuration.

## Production datastore configuration

- Service: `gtex-cache`
- Region: Frankfurt
- Plan: starter
- Maxmemory policy: `noeviction`
- Persistence: `journal-snapshot`
- External access: disabled (`ipAllowList: []`)

`noeviction` protects queued jobs from being silently evicted when memory is
exhausted. Journal + Snapshot provides durability appropriate for the queue and
coordination workloads.

## Consumer wiring

| Consumer | Redis enabled | Connection source |
|---|---:|---|
| gtex-api | yes | `fromService: gtex-cache` |
| gtex-rq-worker | yes | `fromService: gtex-cache` |
| gtex-simulation-worker | yes | `fromService: gtex-cache` |
| gtex-outbox-relay | yes | `fromService: gtex-cache` |
| gtex-player-ingestion-worker | yes | `fromService: gtex-cache` |

## Verdict

**PRODUCTION REDIS CERTIFIED — Blueprint-managed Render Key Value, internal-only,
persistent, and wired to all production Redis consumers.**
