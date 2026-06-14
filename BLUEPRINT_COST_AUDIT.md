# Blueprint Cost Audit — render.yaml

Date: 2026-06-14
Branch: deployment/supabase-cloudflare
Scope: infrastructure only — no business logic, no deploy.

## Objective

Prevent the Render Blueprint from silently creating paid resources or upgrading
plans on `render.yaml` sync.

## Before → After

| Service | Type | Plan before | Plan after |
|---|---|---|---|
| gtex-api | web (python) | standard | **starter** |
| gtex-web | static | — (free static) | — (unchanged) |
| gtex-rq-worker | worker | standard | **starter** |
| gtex-simulation-worker | worker | standard | **starter** |
| gtex-outbox-relay | worker | standard | **starter** |
| gtex-player-ingestion-worker | worker (node) | standard | **starter** |
| gtex-cache (Redis) | keyvalue | standard | **block removed** |
| gtex-postgres | database | basic-1gb | already removed (Supabase) |

## Paid-resource auto-creation — eliminated

| Resource | Was Blueprint creating it? | Now |
|---|---|---|
| Render PostgreSQL | No (removed earlier — Supabase) | No `databases:` block |
| Render Redis / Key-Value | **Yes** (`type: keyvalue` block) | **Block removed** — Redis is created manually |
| Web/worker services | Yes (always, by design) | Still declared, but on `starter`, not `standard` |

## Plan rationale

All long-running services dropped from `standard` to `starter`. `starter` is the
lowest always-on paid tier (no cold-start suspension, unlike free). The static
`gtex-web` carries no plan (served free by Render static hosting / superseded by
Cloudflare Pages).

## Net effect

- Blueprint can no longer provision a managed database (none declared).
- Blueprint can no longer provision Redis (no `keyvalue` block).
- Blueprint can no longer push services onto `standard`; they pin to `starter`.
- Operator explicitly creates the one Redis instance once, by hand.

**No paid resource is auto-created beyond the service containers themselves.**
