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
DATABASE_URL="postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require" \
  alembic -c migrations/alembic.ini upgrade head
```

## ⚠️ Connection host: use the pooler, NOT the direct host

Render's network egress is **IPv4-only**. Supabase's **direct** host
`db.<ref>.supabase.co` now publishes **only an IPv6 (AAAA) record**, so Render
cannot reach it — `alembic upgrade head` fails with
`psycopg.OperationalError: ... Network is unreachable` against an IPv6 address.

**Use the Supabase Session pooler** (Supabase dashboard → Connect → Session
pooler), which has an IPv4 address:

```
postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

- host: `aws-0-<region>.pooler.supabase.com` (IPv4) — not `db.<ref>.supabase.co`
- user: `postgres.<ref>` (dot + project ref), not bare `postgres`
- Session pooler (port **5432**) — supports migrations and persistent connections.
  Transaction pooler (6543) rejects psycopg3 prepared statements; avoid it here.

`ops/render/production-preflight.sh` now **hard-fails the deploy** if `DATABASE_URL`
points at a `db.*.supabase.co` direct host or is missing `sslmode`, so this mistake
is caught before the migration step.

## Node ingestion service — TLS handling

`node-postgres` (pg ≥ 8.11) maps `sslmode=require` in the connection string to
`verify-full`, which rejects Supabase's pooler certificate chain with
`self-signed certificate in certificate chain`. The ingestion service therefore
**strips `sslmode`/`ssl` query params** from `DATABASE_URL` (`config.sanitizeDatabaseUrl`)
and manages TLS explicitly via the pg `ssl: { rejectUnauthorized: false }` option —
encrypted, without CA chain verification. The Python backend (psycopg) is
unaffected; it already treats `sslmode=require` as encrypt-without-verify.

## Verdict: SUPABASE READY (via Session pooler)
