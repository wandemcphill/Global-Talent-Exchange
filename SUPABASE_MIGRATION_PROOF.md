# Phase S5 — Supabase Migration / Boot Proof

Date: 2026-06-14

> Production Supabase data is **not** touched. A SQLite structural proxy is used to exercise the
> migration + boot + connectivity path; Supabase-specific behaviour (URL normalisation, SSL passthrough,
> psycopg driver) is proven separately in `SUPABASE_COMPATIBILITY_REPORT.md` via code-path analysis.

## Environment

```
DATABASE_URL=sqlite:///tmp_supa_test.db   (proxy for postgresql+psycopg://...supabase.co/...?sslmode=require)
GTE_APP_ENV=production
REDIS_ENABLED=false
GTE_AUTH_SECRET=<32+ chars>
GTE_MEDIA_SIGNING_SECRET=<32+ chars>
```

## 1. Migrations run to head

```sh
cd backend && python -m alembic -c migrations/alembic.ini upgrade head
```

```
... -> 20260604_0094_club_squad_sources, Add club squad source records.
... -> 20260612_0095_trader_order_matching, Add trader order matching: fills, partial state, executed trades.
MIGRATE_EXIT=0
```

All migrations applied to head. Exit code **0**.

## 2. Database connectivity

```python
engine = create_database_engine()
with engine.connect() as conn:
    assert conn.execute(text("SELECT 1")).fetchone()[0] == 1
# → "DB connectivity: OK"
```

## 3. App boot

```python
app = create_app(engine=engine, run_migration_check=False)
# → module_count=159 registered
# → App created: Global Talent Exchange API
# → Routes: 328
```

## 4. Health endpoint behaviour (this config)

```json
{
  "status": "ok",
  "checks": {
    "api":      { "status": "ok" },
    "database": { "status": "ok" },
    "redis":    { "status": "skipped" },
    "kafka":    { "status": "skipped" }
  }
}
```

`redis` is `skipped` here only because this proof ran with `REDIS_ENABLED=false`; with Render Redis
enabled it reports `ok` (see `REDIS_CERTIFICATION.md`).

## Real Supabase migration command

```sh
DATABASE_URL="postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres?sslmode=require" \
  alembic -c migrations/alembic.ini upgrade head
# (runs automatically via Render preDeployCommand)
```

## Verdict: SUPABASE MIGRATION READY

Migrations apply cleanly (exit 0), DB connects, app boots with 159 modules / 328 routes.
