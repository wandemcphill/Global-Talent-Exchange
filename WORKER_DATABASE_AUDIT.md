# Phase S3 — Worker & Ingestion Database Audit

Date: 2026-06-14

## Services Audited

| Service | Runtime | Start command | DB source | Redis source |
|---|---|---|---|---|
| `gtex-api` | python | `gunicorn app.asgi:app` | `DATABASE_URL` (env) | `GTE_REDIS_URL` (env) + `REDIS_ENABLED=true` |
| `gtex-rq-worker` | python | `app.workers.rq_worker_main` | `DATABASE_URL` (env) | `GTE_REDIS_URL` (env) + `REDIS_ENABLED=true` |
| `gtex-simulation-worker` | python | `app.backbone.simulation_worker_main` | `DATABASE_URL` (env) | `GTE_REDIS_URL` (env) + `REDIS_ENABLED=true` |
| `gtex-outbox-relay` | python | `app.backbone.outbox_relay_main` | `DATABASE_URL` (env) | `GTE_REDIS_URL` (env) + `REDIS_ENABLED=true` |
| `gtex-player-ingestion-worker` | node | `npm run migrate && npm start` | `DATABASE_URL` (env) | `GTE_REDIS_URL`/`REDIS_URL` (env) |

## Python Workers

All Python workers obtain the engine via `app.core.database.create_database_engine()`, which calls
`resolve_database_url()` → reads `DATABASE_URL` from the environment and normalizes it to
`postgresql+psycopg://`. No worker hardcodes a host or a Render database ID.

- `pool_pre_ping=True` is applied (non-sqlite) → survives Supabase pooler connection recycling.
- Same `normalize_database_url()` used by Alembic `env.py` → migrations + workers agree on the URL.

## Node Ingestion Worker (BullMQ)

`services/player-ingestion/src/config.js`:
```js
databaseUrl: required("DATABASE_URL"),
databaseSsl: boolEnv("DATABASE_SSL", databaseSslDefault()),   // auto-true for non-local hosts
redisEnabled: boolEnv("REDIS_ENABLED", false),
redisUrl: env("REDIS_URL") || env("GTE_REDIS_URL") || null,
```

`services/player-ingestion/src/db.js`:
```js
const pool = new Pool({
  connectionString: config.databaseUrl,
  ssl: config.databaseSsl ? { rejectUnauthorized: false } : false,
});
```

- `DATABASE_URL` is **required** — the worker refuses to start without it.
- `DATABASE_SSL` defaults to **true** for Supabase hosts (only disabled for localhost / `postgres://postgres@`).
- BullMQ queue (`queues.js`) **requires** Redis and throws a clear error if `REDIS_URL`/`GTE_REDIS_URL`
  is absent:
  ```
  Player ingestion worker requires Redis. Set REDIS_URL (or GTE_REDIS_URL) and REDIS_ENABLED=true.
  ```
  This is by design — the ingestion job queue is Redis-backed.

## Stale Reference Scan

| Pattern | Worker hits |
|---|---|
| `fromDatabase` / `gtex-postgres` | none |
| Hardcoded `postgres://` host | none |
| Hardcoded Render DB ID | none |

## Verdict: WORKERS CORRECT

Every worker reads `DATABASE_URL` and `REDIS_URL` from the environment. No stale Render Postgres
references remain. SSL is enabled by default for Supabase on the Node ingestion path.
