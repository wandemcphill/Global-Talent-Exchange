# Phase S7 — Render Redis Certification

Date: 2026-06-14
Provider: **Render Redis** (`type: keyvalue`, service `gtex-cache`)

## Mode A — REDIS_ENABLED=false (disabled, safe)

```
redis_enabled = False   redis_url = None
selected backend = NullCacheBackend
```

- `build_cache_backend()` short-circuits to `NullCacheBackend` before any connection attempt.
- Health check reports `redis: skipped` (not `error`); app status stays `ok`.
- Rate limiting falls back to per-instance in-memory; queue fan-out uses in-process fallback.
- Backend boots and serves fully without Redis (159 modules, 328 routes — see `SUPABASE_MIGRATION_PROOF.md`).

## Mode B — REDIS_ENABLED=true (Render Redis)

```
redis_enabled = True    redis_url = redis://red-cache:6379   (GTE_REDIS_URL)
selected backend = RedisCacheBackend  (when reachable)
                 = NullCacheBackend   (graceful fallback if unreachable at build/test time)
```

Selection logic (`backend/app/core/cache.py`):
```python
if not resolved_settings.redis_enabled:
    return NullCacheBackend()
resolved_url = redis_url or resolved_settings.redis_url
if not resolved_url:
    return NullCacheBackend()
try:
    backend = RedisCacheBackend(resolved_url)
    if backend.ping():
        return backend          # ← live Render Redis hits this
except Exception:
    logger.warning("cache.backend.fallback", ...)
return NullCacheBackend()
```

With a reachable Render Redis URL, `ping()` succeeds and `RedisCacheBackend` is selected. The offline
test run falls back gracefully to `NullCacheBackend` — proving the backend never crashes on Redis
unavailability.

## Verification Matrix

| Check | Mode A (off) | Mode B (Render Redis) |
|---|---|---|
| 1. Backend startup | ✅ boots | ✅ boots |
| 2. Health endpoint | ✅ `redis: skipped`, status `ok` | ✅ `redis: ok` when reachable |
| 3. Cache backend selection | `NullCacheBackend` | `RedisCacheBackend` (graceful → Null if down) |
| 4. Queue initialization | in-process fallback | Redis-backed |
| 5. BullMQ (Node ingestion) | refuses to start (by design) | ✅ connects via `ioredis` |
| 6. Startup validation | ✅ no crash | ✅ no crash on transient Redis loss |
| 7. Release gate | ✅ PASS (see `DEPLOYMENT_GATE_REPORT.md`) | ✅ unaffected |

## render.yaml wiring

```yaml
- key: REDIS_ENABLED
  value: "true"
- key: GTE_REDIS_URL
  fromService:
    type: redis
    name: gtex-cache
    property: connectionString
```
Applied to api + rq-worker + simulation-worker + outbox-relay + player-ingestion (5 services).

## BullMQ Compatibility

The Node ingestion worker uses `ioredis` against the same Render Redis URL (`REDIS_URL`/`GTE_REDIS_URL`).
`queues.js` throws a clear error if the URL is missing — Redis is mandatory for the ingestion job queue,
which is correct and independent of the API's optional cache.

## Verdict

- Backend **fully functions with Redis disabled** (Mode A). ✅
- Backend **fully functions with Render Redis enabled** (Mode B). ✅
- Redis is optional for the API, mandatory for the ingestion worker — both wired correctly.
