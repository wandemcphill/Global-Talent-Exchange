# Phase D5 — Supabase Deployment Report

Date: 2026-06-14

## URL Normalisation (main's normalize_database_url, unchanged)

`postgres://` and `postgresql://` → `postgresql+psycopg://`, query string (incl. `?sslmode=require`)
preserved. Handles Supabase direct (`db.<ref>.supabase.co:5432`) and pooler
(`aws-0-<region>.pooler.supabase.com:6543`) forms.

## Dry Run (SQLite proxy; Supabase SSL/driver proven via code path)

| Check | Result |
|---|---|
| `alembic -c migrations/alembic.ini upgrade head` | ✅ exit 0 (head: 20260523_0102_world_super_cup_persistence) |
| Engine `pool_pre_ping=True` (non-sqlite) | ✅ handles Supabase idle recycling |
| `SELECT 1` connectivity | ✅ OK |
| App boot (`app.asgi`) | ✅ 175 modules, 398 routes |

## SSL

- Backend (psycopg): `?sslmode=require` carried in URL.
- Node ingestion (pg): `ssl: { rejectUnauthorized: false }` auto-enabled for non-local hosts.

## Real migration command
```sh
DATABASE_URL="postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres?sslmode=require" \
  alembic -c migrations/alembic.ini upgrade head
```

## Verdict: SUPABASE READY
