# Phase S2 — Blueprint (render.yaml) Database Audit

Date: 2026-06-14

## Files Inspected

- `render.yaml` (canonical deployment blueprint)
- `GTEX_DEPLOYMENT_BLUEPRINT.md` (documentation)
- `ops/render/build-frontend.sh`, `ops/render/production-preflight.sh`

## Changes Applied (stale-reference fixes)

### 1. DATABASE_URL — moved off Render-managed Postgres

**Before:**
```yaml
- key: DATABASE_URL
  fromDatabase:
    name: gtex-postgres
    property: connectionString
```

**After (×5 services — api, rq-worker, simulation-worker, outbox-relay, player-ingestion):**
```yaml
# Supabase PostgreSQL connection string (postgresql://...?sslmode=require).
# Set manually in the Render dashboard. GTEX no longer provisions a
# Render-managed Postgres instance; the database lives on Supabase.
- key: DATABASE_URL
  sync: false
```

### 2. Removed the Render `databases:` block

**Before:**
```yaml
databases:
  - name: gtex-postgres
    region: frankfurt
    plan: basic-1gb
    ipAllowList: []
```

**After:** block removed; replaced with a comment documenting that PostgreSQL is hosted on Supabase.

### 3. Enabled Render Redis explicitly

Added `REDIS_ENABLED=true` to every service that consumes `GTE_REDIS_URL` (api + 4 workers = 5).
This is required because the backend defaults `REDIS_ENABLED=false`; production with Render Redis
must opt in.

```yaml
- key: REDIS_ENABLED
  value: "true"
- key: GTE_REDIS_URL
  fromService:
    type: redis
    name: gtex-cache
    property: connectionString
```

## Verification

| Check | Result |
|---|---|
| `DATABASE_URL` sourced from env (no `fromDatabase`) | ✅ `grep fromDatabase render.yaml` → none |
| No `gtex-postgres` references | ✅ none |
| No Render `databases:` block | ✅ removed |
| `REDIS_URL`/`GTE_REDIS_URL` from `fromService` (Render Redis `keyvalue`) | ✅ `gtex-cache` |
| `REDIS_ENABLED=true` on all Redis consumers | ✅ count = 5 |
| No hardcoded Postgres credentials / DB IDs | ✅ none |
| Auth & media secrets `sync: false` | ✅ unchanged |

## Render Redis Service (target — retained)

```yaml
- type: keyvalue
  name: gtex-cache
  region: frankfurt
  plan: standard
  ipAllowList: []
```

This is the **intended** cache/queue provider (Render Redis) and is correct for the target stack.

## Verdict: BLUEPRINT CORRECT

`DATABASE_URL` and `REDIS_URL` are environment-driven. No stale Render Postgres references or
database IDs remain. Render Redis is wired and explicitly enabled.
