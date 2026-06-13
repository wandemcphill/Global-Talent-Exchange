# GTEX Deployment Certification — Supabase + Cloudflare + Render Redis

Date: 2026-06-14
Branch: feature/original-visual-runtime

## Target Stack

| Layer | Provider |
|---|---|
| Frontend | Cloudflare Pages |
| Backend | Render |
| Database | **Supabase PostgreSQL** |
| Cache / Queue | **Render Redis** |
| Media | Cloudinary (existing `gtex/players/{id}` assets) |
| DNS | Cloudflare |

## Changes Applied (infrastructure only)

- `render.yaml`: `DATABASE_URL` moved from Render-managed `fromDatabase: gtex-postgres` to
  `sync: false` (Supabase string, set in dashboard) across all 5 services.
- `render.yaml`: removed the Render `databases:` block (DB now lives on Supabase).
- `render.yaml`: added `REDIS_ENABLED=true` to all 5 Redis-consuming services.

No business logic, UI, or features were modified.

## Certification Answers

| # | Question | Answer |
|---|---|---|
| 1 | Any remaining Render Postgres references? | **No** — `fromDatabase`/`gtex-postgres`/`databases:` all removed |
| 2 | Blueprint correctly uses DATABASE_URL? | **Yes** — `sync: false`, env-driven |
| 3 | Blueprint correctly uses REDIS_URL? | **Yes** — `GTE_REDIS_URL` from Render Redis `gtex-cache` |
| 4 | Workers use correct DB? | **Yes** — all read `DATABASE_URL` from env |
| 5 | Workers use correct Redis? | **Yes** — `GTE_REDIS_URL`/`REDIS_URL` from env |
| 6 | Supabase ready? | **Yes** — URL normalisation + migrations + boot proven |
| 7 | SSL configured? | **Yes** — `?sslmode=require` (py) + `ssl` auto-on (node) |
| 8 | Cloudinary resolver-only? | **Yes** — `images.js` dead, zero active uploads |
| 9 | Render Redis optional and safe? | **Yes** — Mode A (off) and Mode B (on) both boot |
| 10 | Cloudflare Pages ready? | **Yes** — build script + `frontend/build/web`, no Vercel/Netlify |
| 11 | API routing production-safe? | **Yes** — env-injected, `StateError` on empty in live |
| 12 | WebSocket routing production-safe? | **Yes** — derived `https→wss`, no separate var |
| 13 | Any localhost leakage? | **No** — all localhost refs are fixture/classifier/hint |
| 14 | Remaining blockers? | **None** infrastructure-side; 3 pre-existing test-fixture failures unrelated |
| 15 | GO / NO-GO? | **GO** |

## Evidence Index

- `DATABASE_REFERENCE_AUDIT.md` · `BLUEPRINT_DATABASE_AUDIT.md` · `WORKER_DATABASE_AUDIT.md`
- `SUPABASE_COMPATIBILITY_REPORT.md` · `SUPABASE_MIGRATION_PROOF.md`
- `CLOUDINARY_CERTIFICATION.md` · `REDIS_CERTIFICATION.md`
- `WEB_DEPLOYMENT_AUDIT.md` · `CLOUDFLARE_BUILD_CERTIFICATION.md`
- `API_URL_CERTIFICATION.md` · `DART_DEFINE_CERTIFICATION.md`
- `DEPLOYMENT_GATE_REPORT.md`

## Pre-Deploy Operator Checklist (manual, in dashboards — not performed here)

1. Render → each service → set `DATABASE_URL` to the Supabase connection string (`?sslmode=require`).
2. Render → provision the `gtex-cache` Redis (`keyvalue`) service.
3. Cloudflare Pages → set `GTE_API_BASE_URL=https://api.gtex.com`, `GTE_BACKEND_MODE=live`;
   build cmd `bash ops/cloudflare/build-frontend.sh`, output `frontend/build/web`.
4. Set `GTE_CORS_ALLOW_ORIGINS=https://app.gtex.com` on the API.
5. Set Cloudinary + Sportmonks secrets (`sync: false`) on the ingestion worker.

## Final Verdict: **GO**

Release gate PASS 9/9. Supabase, Render Redis, Cloudflare Pages, and Cloudinary paths all certified.
