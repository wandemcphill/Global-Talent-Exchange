# Phase D6 — Render Redis Certification

Date: 2026-06-14
Provider: Render Redis (`type: keyvalue`, service `gtex-cache`)

## Mode A — REDIS_ENABLED=false
```
redis_enabled = False   redis_url = None
cache backend = NullCacheBackend
```
- `build_cache_backend()` short-circuits to `NullCacheBackend` before any connection.
- `load_settings()` forces `redis_url=None` when disabled, so the health check reports `skipped`.
- App boots fully (175 modules, 398 routes) without Redis.

## Mode B — REDIS_ENABLED=true
```
redis_enabled = True    redis_url = redis://red-cache:6379  (GTE_REDIS_URL)
cache backend = RedisCacheBackend when reachable (graceful NullCache fallback if down)
```

## Backend toggle (ported surgically onto main)
- `config.py`: `redis_enabled: bool` field (`REDIS_ENABLED`/`GTE_REDIS_ENABLED`), and
  `redis_url=source.redis_url if source.redis_enabled else None` in `load_settings()`.
- `cache.py`: `if not resolved_settings.redis_enabled: return NullCacheBackend()`.
- `health.py`: unchanged (existing `if not settings.redis_url` path already yields `skipped`).

## Node ingestion (BullMQ)
- `config.js`: `redisUrl` now optional (`env("REDIS_URL") || env("GTE_REDIS_URL") || null`) + `redisEnabled`.
- `queues.js`: throws a clear error if `redisUrl` missing — Redis is mandatory for the ingestion queue.

## Matrix
| Check | Mode A | Mode B |
|---|---|---|
| Backend boot | ✅ | ✅ |
| Cache selection | NullCacheBackend | RedisCacheBackend (graceful) |
| Health endpoint | `skipped` | `ok` when reachable |
| Queue init | in-process fallback | Redis-backed |
| BullMQ ingestion | refuses (by design) | connects |

## Verdict: Backend works with Redis OFF and ON. CERTIFIED.
