# Phase S1 — Database Reference Audit

Date: 2026-06-14
Branch: feature/original-visual-runtime
Target DB: **Supabase PostgreSQL** (was Render-managed Postgres)

Search performed with `git grep` across the canonical tree (excluding `.external_worktrees/`,
`GTEX_FRONTEND_REDESIGN_WORKTREE/`). Patterns: `DATABASE_URL`, `postgres://`, `postgresql://`,
`render.com`, `.render.com`, `supabase`, `psycopg`, `asyncpg`, `db.`, `sslmode`.

## Active Infrastructure References

| File | Line | Value | Action Required |
|---|---|---|---|
| `render.yaml` | 14, 64, ... | `DATABASE_URL` → `sync: false` | ✅ Fixed — was `fromDatabase: gtex-postgres`; now manual Supabase string |
| `render.yaml` | (footer) | Render `databases:` block | ✅ Removed — Supabase hosts the DB, not Render |
| `backend/app/core/config.py` | 322–330 | `normalize_database_url()` rewrites `postgres://`/`postgresql://` → `postgresql+psycopg://` | ✅ Supabase-compatible; preserves `?sslmode=require` |
| `backend/app/core/config.py` | 333–341 | `resolve_database_url()` reads `DATABASE_URL` from env | ✅ Env-driven, no hardcoded host |
| `backend/app/core/database.py` | 116–130 | `create_database_engine()` — `pool_pre_ping=True`, `connect_timeout` | ✅ Handles Supabase pooler/idle drops |
| `backend/migrations/env.py` | — | Uses same `normalize_database_url()` | ✅ Alembic Supabase-ready |
| `services/player-ingestion/src/config.js` | 83–84 | `databaseUrl: required("DATABASE_URL")`, `databaseSsl` auto-on for non-local | ✅ Env-driven, SSL for Supabase |
| `services/player-ingestion/src/db.js` | 9–11 | `new Pool({ ssl: databaseSsl ? {rejectUnauthorized:false} : false })` | ✅ Supabase SSL supported |

## Driver Dependencies

| Driver | Where | Status |
|---|---|---|
| `psycopg` (v3) | backend engine (`postgresql+psycopg://`) | ✅ Supabase-compatible |
| `asyncpg` | (not used by app engine) | n/a |
| `pg` (node) | ingestion `Pool` | ✅ Supabase-compatible |

## Stale / Non-Production References (no action required)

| File | Line | Value | Why safe |
|---|---|---|---|
| `backend/app/core/config.py` | 32 | `DEFAULT_CORS_ALLOWED_ORIGINS = ("https://gtex-web.onrender.com",)` | Default only; overridden by `GTE_CORS_ALLOW_ORIGINS` env (set to Cloudflare Pages domain in prod) |
| `render.yaml` | gtex-web | `GTE_API_BASE_URL=https://gtex-api.onrender.com` | Historical Render static site; superseded by Cloudflare Pages. Backend API URL is correct |
| `ops/render/deploy.py` | 18 | `https://api.render.com/v1` | Render **management API** endpoint (deploy tooling) — correct |
| `Gtex_Test_Migration/**` | — | `gtex-api.onrender.com` | Quarantined Unity/3D migration, not in production build path |
| `tests/**`, `tools/**` | — | render.com strings | Test fixtures / audit-doc generators |

## Conclusion

No stale **Render Postgres** references remain in the active deployment path. `DATABASE_URL` is
fully environment-driven across the API, all four Python workers, and the Node ingestion worker.
The database layer is Supabase-ready.
