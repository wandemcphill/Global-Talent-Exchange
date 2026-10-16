# Blueprint Resource Audit — render.yaml

Date: 2026-06-14
Branch: deployment/supabase-cloudflare

## Declared resources after hardening

| Block | Kind | Blueprint-provisioned? | Notes |
|---|---|---|---|
| gtex-api | web service (python) | yes (container) | `starter` |
| gtex-web | static site | yes (free static) | superseded by Cloudflare Pages |
| gtex-rq-worker | worker (python) | yes (container) | `starter` |
| gtex-simulation-worker | worker (python) | yes (container) | `starter` |
| gtex-outbox-relay | worker (python) | yes (container) | `starter` |
| gtex-player-ingestion-worker | worker (node) | yes (container) | `starter` |
| PostgreSQL | — | **no** | Supabase (no `databases:` block) |
| Redis / Key-Value | — | **no** | manual Render Redis (no `keyvalue` block) |

## What Blueprint can NO LONGER do

1. **Recreate Redis** — there is no `type: keyvalue` block. The Redis instance is
   created once, manually, in the Render dashboard. Sync cannot recreate or
   delete it. Redis *usage* is fully retained via `GTE_REDIS_URL` (sync: false).
2. **Change plans** — every long-running service pins `plan: starter`. Blueprint
   cannot drift them to `standard`/`pro` because the file fixes the value.
3. **Overwrite environment variables** — all connection strings and secrets are
   `sync: false`; no `fromService`/`fromDatabase` references remain (verified
   zero). Blueprint reads them from the dashboard and never writes them.
4. **Create paid managed data resources** — no `databases:` block, no `keyvalue`
   block. The only billable units are the service containers themselves.

## Structural verification (yaml.safe_load)

```
services: 6
databases block present: False
keyvalue/redis blocks: []
remaining Blueprint-managed env refs (fromService/fromDatabase): NONE
secret/conn keys NOT sync:false: NONE
plans == starter for all non-static: True
```

## Redis usage retained (not deleted)

Each service still sets `REDIS_ENABLED=true` and reads `GTE_REDIS_URL`. The cache
backend (`build_cache_backend`) and BullMQ ingestion queues consume it exactly as
before. Only the *provisioning* of Redis moved from Blueprint to manual.

## Verdict

render.yaml parses cleanly. No auto-created paid data resources remain. No env
overwrite risk remains. Redis and Postgres are operator-owned; service plans are
pinned to `starter`.
