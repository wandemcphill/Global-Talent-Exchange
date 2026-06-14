# Blueprint Environment Variable Protection — render.yaml

Date: 2026-06-14
Branch: deployment/supabase-cloudflare

## Goal

Ensure the Blueprint cannot overwrite operator-managed secrets and connection
strings on each sync. Anything with `sync: false` is owned by the dashboard;
Blueprint reads it but never writes it.

## Protected keys (now `sync: false` on every service that uses them)

| Key | Category | Before | After |
|---|---|---|---|
| DATABASE_URL | DB connection (Supabase) | sync: false | sync: false ✓ |
| GTE_REDIS_URL | Redis connection | `fromService` (Blueprint-managed) | **sync: false** |
| CLOUDINARY_URL | Media credential | sync: false | sync: false ✓ |
| GTE_AUTH_SECRET | JWT secret | api: sync:false / workers: `fromService` | **sync: false everywhere** |
| GTE_MEDIA_SIGNING_SECRET | Signing secret | api: sync:false / workers: `fromService` | **sync: false everywhere** |
| GTE_KORAPAY_* (4) | Payment API keys | sync: false | sync: false ✓ |
| TREASURY_* (3) | Payout config | sync: false | sync: false ✓ |
| SPORTMONKS_API_TOKEN | Ingestion API key | sync: false | sync: false ✓ |
| ELEVENLABS_API_KEY | Media API key | sync: false | sync: false ✓ |
| SENTRY_DSN | Observability | sync: false | sync: false ✓ |

## Blueprint-managed references removed

Previously the three Python workers pulled `GTE_AUTH_SECRET` and
`GTE_MEDIA_SIGNING_SECRET` from `gtex-api` via `fromService`, and all five
services pulled `GTE_REDIS_URL` from the `gtex-cache` service via `fromService`.
Those cross-references made Blueprint the owner of those values. **All
`fromService` / `fromDatabase` references are now removed** — verified: zero remain.

## ⚠️ Required operator action (consequence of removing the secret cross-refs)

Because the worker secrets are no longer auto-derived from `gtex-api`, you MUST
set the **same** value on every service:

- `GTE_AUTH_SECRET` — identical on gtex-api + all 3 Python workers
- `GTE_MEDIA_SIGNING_SECRET` — identical on gtex-api + all 3 Python workers
- `GTE_REDIS_URL` — the manual Render Redis `rediss://` string on all 5 services
- `DATABASE_URL` — the Supabase `postgresql://...?sslmode=require` string on all 5

Mismatched `GTE_AUTH_SECRET` between api and a worker will cause cross-service
auth tokens to fail validation. A missing required secret fails the service boot
(fail-safe, not silent).

## Non-secret `value:` keys (intentionally left as `value:`)

Config flags such as `REDIS_ENABLED`, `GTE_APP_ENV`, `WEB_CONCURRENCY`,
`GTE_INGESTION_PROVIDER`, cron schedules, and feature toggles remain inline
`value:` entries. These are non-sensitive defaults; Blueprint managing them is
the intended behavior and carries no secret-overwrite risk.

## Verification

```
remaining Blueprint-managed env refs (fromService/fromDatabase): NONE
secret/conn keys NOT sync:false: NONE
```
