# Phase S4 — Supabase Compatibility Report

Date: 2026-06-14

## URL Normalisation (proven)

`backend/app/core/config.py::normalize_database_url()` rewrites all Supabase URL forms to the
psycopg v3 driver while preserving query parameters (including `sslmode`):

```
IN : postgres://postgres.abcdefgh:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require
OUT: postgresql+psycopg://postgres.abcdefgh:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require

IN : postgresql://postgres:pw@db.abcdefgh.supabase.co:5432/postgres?sslmode=require
OUT: postgresql+psycopg://postgres:pw@db.abcdefgh.supabase.co:5432/postgres?sslmode=require

IN : postgresql+psycopg://postgres:pw@db.abcdefgh.supabase.co:5432/postgres?sslmode=require
OUT: (unchanged — already canonical)
```

Both Supabase connection styles work:
- **Direct** `db.<ref>.supabase.co:5432`
- **Pooler (PgBouncer/Supavisor)** `aws-0-<region>.pooler.supabase.com:6543`

## SSL Compatibility

| Layer | Mechanism |
|---|---|
| Backend (psycopg) | `?sslmode=require` carried verbatim in the URL query string by `normalize_database_url()` |
| Node ingestion (pg) | `ssl: { rejectUnauthorized: false }` auto-enabled for non-local hosts (`DATABASE_SSL` default true) |
| Alembic | Same normalized URL → same SSL behaviour |

Supabase requires TLS; both code paths satisfy it.

## psycopg / Driver Compatibility

- App engine uses `postgresql+psycopg://` (psycopg v3) — the modern, Supabase-supported driver.
- `create_database_engine()` adds `connect_timeout` and `pool_pre_ping=True` for non-sqlite engines,
  which handles Supabase pooler idle-connection recycling on the free/small tiers.

## Async Compatibility

The app uses a synchronous SQLAlchemy `Engine` + `sessionmaker` served under Uvicorn workers
(gunicorn `UvicornWorker`). No async driver is required; psycopg v3 sync mode is fully Supabase-compatible.
This matches the existing production model — no architecture change.

## No Hardcoded Hosts

`resolve_database_url()` raises if `DATABASE_URL` is unset — there is no embedded Supabase/Render host
anywhere in the engine creation path.

## Alembic env.py

`backend/migrations/env.py` calls the same `normalize_database_url()` (via `database.py`), so migrations
connect to Supabase identically to the running app.

## Verdict: SUPABASE-COMPATIBLE

PostgreSQL ✅ · SSL ✅ · psycopg v3 ✅ · pooler + direct ✅ · no hardcoded hosts ✅
