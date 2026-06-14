# Phase D4 — render.yaml Certification

Date: 2026-06-14

## Services

| Service | Type | DATABASE_URL | Redis |
|---|---|---|---|
| gtex-api | web (python) | `sync: false` (Supabase) | `REDIS_ENABLED=true` + `GTE_REDIS_URL` from `gtex-cache` |
| gtex-rq-worker | worker (python) | `sync: false` (Supabase) | `REDIS_ENABLED=true` + `GTE_REDIS_URL` |
| gtex-simulation-worker | worker (python) | `sync: false` (Supabase) | `REDIS_ENABLED=true` + `GTE_REDIS_URL` |
| gtex-outbox-relay | worker (python) | `sync: false` (Supabase) | `REDIS_ENABLED=true` + `GTE_REDIS_URL` |
| gtex-player-ingestion-worker | worker (node) | `sync: false` (Supabase) | `REDIS_ENABLED=true` + `GTE_REDIS_URL` |
| gtex-web | static | — | — |
| gtex-cache | keyvalue (Render Redis) | — | retained |

## Verification

| Check | Result |
|---|---|
| `DATABASE_URL` from env (`sync: false`) | ✅ 5 services |
| `REDIS_ENABLED=true` on Redis consumers | ✅ count = 5 |
| `GTE_REDIS_URL` from Render Redis `gtex-cache` | ✅ |
| Render Postgres `fromDatabase` references | ✅ none |
| Render `databases:` block | ✅ removed |
| Korapay / Treasury / strict-live env vars | ✅ preserved (untouched) |
| YAML parses | ✅ 7 services, no `databases` key |

## Verdict: BLUEPRINT CERTIFIED — Supabase DB + Render Redis, env-driven.
