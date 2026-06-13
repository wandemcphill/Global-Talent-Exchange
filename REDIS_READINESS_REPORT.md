# Task D — Upstash Redis Readiness Report

## Verdict: READY — Redis is optional; disabled by default

---

## Changes Made

### `backend/app/core/config.py`

Added `REDIS_ENABLED` / `GTE_REDIS_ENABLED` env var (default: `false`).

When `REDIS_ENABLED=false`:
- `settings.redis_url` is forced to `None` regardless of `REDIS_URL` value
- `build_cache_backend()` returns `NullCacheBackend` immediately
- Health endpoint reports Redis as `skipped` (not `error`)
- Application behavior is unchanged — all cache misses are handled by in-process fallbacks

When `REDIS_ENABLED=true`:
- `settings.redis_url` is read from `REDIS_URL` or `GTE_REDIS_URL`
- `build_cache_backend()` attempts connection and pings
- Falls back to `NullCacheBackend` silently if connection fails
- Health endpoint reports `ok` or `error` accordingly

### `backend/app/core/cache.py`

`build_cache_backend()` now short-circuits on `redis_enabled=False` before attempting any connection.

### `backend/app/core/health.py`

Redis check now reports `skipped` (not `error`) when `redis_enabled=False`.

### `services/player-ingestion/src/config.js`

`redisUrl` changed from `requiredAny([...])` to optional `env(...) || null`.
Added `redisEnabled: boolEnv("REDIS_ENABLED", false)`.

### `services/player-ingestion/src/queues.js`

Added explicit startup guard: throws with a clear error message if Redis URL is absent.
The ingestion worker **requires** Redis (BullMQ dependency). This is separate from the API's optional Redis.

---

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `REDIS_ENABLED` | `false` | Set `true` when Upstash is provisioned |
| `REDIS_URL` | — | Upstash Redis URL (TLS). Format: `rediss://default:token@host:port` |

## Upstash Compatibility

Upstash Redis uses TLS (`rediss://`). The existing `ioredis` and `redis-py` clients both support TLS URLs natively.

For the Python backend, `redis-py` connects with TLS when the URL starts with `rediss://`.
For the Node ingestion worker, `ioredis` connects with TLS automatically.

## Activation Steps (when Upstash is provisioned)

1. Create Upstash Redis database
2. Copy the `rediss://` connection string
3. Set `REDIS_ENABLED=true` and `REDIS_URL=rediss://...` in Render env vars
4. The API and ingestion worker will connect on next deploy

## What Redis Enables

| Feature | Without Redis | With Redis |
|---|---|---|
| API response cache | In-process NullCache (no-op) | Distributed cache |
| Rate limiting | Per-instance in-memory | Distributed (correct under multiple instances) |
| RQ/BullMQ job queue | Disabled | Enabled |
| Realtime fan-out | Polling fallback | Redis pub/sub |
| Ingestion worker | Cannot start | Starts (BullMQ requires Redis) |
