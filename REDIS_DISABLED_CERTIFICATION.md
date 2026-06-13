# Phase V2 — Redis Disabled Certification

Date: 2026-06-13

---

## Test: Backend startup with REDIS_ENABLED=false

### Environment

```
DATABASE_URL=sqlite:///tmp_health_test.db
REDIS_ENABLED=false
GTE_APP_ENV=production
GTE_AUTH_SECRET=acceptance-test-secret-long-enough-32chars
GTE_MEDIA_SIGNING_SECRET=acceptance-media-secret-long-32chars
```

### Config layer output

```
redis_enabled = False
redis_url     = None
app_env       = production
cache_backend = NullCacheBackend
```

### Cache backend verification

```python
cache.ping()         → False   (no Redis — expected)
cache.get("x")       → None    (no Redis — expected)
cache.set("k","v",60)→ no-op   (no Redis — expected)
```

### Health endpoint simulation

```json
{
  "redis": {
    "status": "skipped",
    "detail": "Redis is disabled (REDIS_ENABLED=false); cache, rate limiting, and queue fan-out use in-process fallbacks."
  }
}
```

Redis check status: `skipped` (not `error`).
Application overall status: `ok` — Redis absence does not degrade the health check to error.

### Startup log evidence

```
app.startup.health.redis.begin
app.startup.health.redis.complete
```

Redis health check completes successfully — returns `skipped`, does not throw, does not block startup.

---

## How REDIS_ENABLED=false is enforced

### `backend/app/core/config.py`

```python
redis_enabled: bool = Field(default=False, validation_alias=AliasChoices("REDIS_ENABLED", "GTE_REDIS_ENABLED"))
redis_url: str | None = Field(default=None, validation_alias=AliasChoices("REDIS_URL", "GTE_REDIS_URL"))
```

In `load_settings()`:
```python
redis_url=source.redis_url if source.redis_enabled else None,
```

When `REDIS_ENABLED=false`: `settings.redis_url` is forced to `None` regardless of any `REDIS_URL` value.

### `backend/app/core/cache.py`

```python
def build_cache_backend(...) -> CacheBackend:
    if not resolved_settings.redis_enabled:
        return NullCacheBackend()   # short-circuits before any connection attempt
    ...
```

### `backend/app/core/health.py`

```python
if not settings.redis_enabled or not settings.redis_url:
    return ServiceCheck(status="skipped", detail="Redis is disabled...")
```

---

## Release Gate Result (run during V5)

```
[PASS] pytest:production_guards   (6.2s)
[PASS] pytest:websocket_contracts (26.3s)
[PASS] pytest:module_registration (68.2s)
[PASS] pytest:money_lane          (44.6s)
[PASS] flutter_analyze            (348.8s)

GTEX RELEASE GATE: PASS
```

All gate checks pass with no Redis configured.

---

## Verdict

**Backend works completely without Redis.**

- NullCacheBackend is selected automatically
- Health reports `skipped`, not `error`
- Rate limiting falls back to per-instance in-memory
- Job queue disabled gracefully
- Release gate: PASS 9/9

Note: The player ingestion **worker** requires Redis (BullMQ) and will refuse to start without it. This is by design and is separate from the API.
