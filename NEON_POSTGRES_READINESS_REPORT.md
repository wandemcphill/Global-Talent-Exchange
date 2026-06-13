# Task C — Neon PostgreSQL Readiness Report

## Verdict: READY — No code changes required

---

## Audit Results

### DATABASE_URL compatibility

| Check | Result |
|---|---|
| Neon provides `postgres://` or `postgresql://` URLs | Handled by `normalize_database_url()` in `backend/app/core/config.py:321` |
| `postgres://` → `postgresql+psycopg://` rewrite | ✅ Already implemented |
| `postgresql://` → `postgresql+psycopg://` rewrite | ✅ Already implemented |
| `?sslmode=require` passthrough | ✅ Query params are preserved verbatim |
| `GTE_DATABASE_URL` fallback alias | ✅ Supported |
| Alembic reads same env vars | ✅ `env.py` calls `normalize_database_url` |

### SQLAlchemy compatibility

- Driver: `psycopg` (psycopg v3), already specified by the `postgresql+psycopg://` prefix
- `pool_pre_ping=True` is set in `create_database_engine()` — handles Neon connection pool hibernation
- `connect_timeout` is set (default 10s, configurable via `GTE_DATABASE_CONNECT_TIMEOUT_SECONDS`)
- No SQLite-specific code paths affect Neon

### Alembic compatibility

- `backend/migrations/alembic.ini` — `sqlalchemy.url` is blank (correct — reads from env at runtime)
- `backend/migrations/env.py` — calls `normalize_database_url()` with same precedence as app
- Migration command: `cd backend && alembic -c migrations/alembic.ini upgrade head`

### Render pre-deploy command (from `render.yaml`)

```sh
bash ops/render/production-preflight.sh && cd backend && alembic -c migrations/alembic.ini upgrade head
```

This runs before traffic is served. Compatible with Neon.

---

## Required Environment Variables

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Neon connection string. Must include `?sslmode=require`. |

Example Neon URL:
```
postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/gtex?sslmode=require
```

## Risks

| Risk | Mitigation |
|---|---|
| Neon free tier sleeps after 5 minutes of inactivity | `pool_pre_ping=True` reconnects on wake |
| Neon connection limit (free: 100) | Render standard plan + gunicorn 4 workers = ~20 connections; within limit |
| Neon SSL required | `?sslmode=require` in connection string handles this |

## Migration Command

```sh
cd backend
alembic -c migrations/alembic.ini upgrade head
```

Run once after provisioning Neon and setting `DATABASE_URL`. Subsequent deploys run this automatically via `preDeployCommand` in `render.yaml`.
