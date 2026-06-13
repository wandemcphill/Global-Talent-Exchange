# Task E — Render Deployment Readiness Report

## Verdict: READY

---

## Startup Command

```sh
cd backend && gunicorn app.asgi:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:$PORT \
  --workers ${WEB_CONCURRENCY:-2} \
  --timeout 180 \
  --graceful-timeout 120
```

Status: ✅ Correct. Uses `$PORT` (Render injects this). ASGI app at `app.asgi:app`.

## Pre-Deploy Command

```sh
bash ops/render/production-preflight.sh && cd backend && alembic -c migrations/alembic.ini upgrade head
```

Status: ✅ Runs migrations before traffic. Neon-compatible.

## Health Endpoints

| Endpoint | Purpose | Expected response |
|---|---|---|
| `GET /health` | Load balancer / Render health check | `{"status": "ok"}` |
| `GET /ready` | Readiness (schema check) | `{"status": "ready"}` |
| `GET /version` | Version info | JSON |
| `GET /metrics` | Prometheus metrics | Text |

Render should be configured to hit `/health`. Returns HTTP 503 when degraded.

## WebSocket Compatibility

Render's `web` service type supports WebSocket connections.
The ASGI app uses `uvicorn.workers.UvicornWorker` which handles WebSocket upgrades.
The match broadcast system uses `/api/v2/match-center/ws/{match_id}`.

**Note:** Render Standard plan required (not Free) for persistent WebSocket connections.

## Services in `render.yaml`

| Service | Type | Notes |
|---|---|---|
| `gtex-api` | web (Python) | Main FastAPI backend |
| `gtex-web` | web (static) | **Replace with Cloudflare Pages** |
| `gtex-rq-worker` | worker (Python) | RQ job worker |
| `gtex-simulation-worker` | worker (Python) | Match simulation |
| `gtex-outbox-relay` | worker (Python) | Event outbox |
| `gtex-player-ingestion-worker` | worker (Node) | Sportmonks ingestion |

**Action required:** Remove `gtex-web` from Render — frontend is now Cloudflare Pages.

## Required Render Environment Variables

| Variable | Source |
|---|---|
| `DATABASE_URL` | Neon connection string |
| `REDIS_ENABLED` | `true` (when Upstash connected) |
| `REDIS_URL` | Upstash `rediss://` URL |
| `GTE_AUTH_SECRET` | Generate: `openssl rand -hex 32` |
| `GTE_MEDIA_SIGNING_SECRET` | Generate: `openssl rand -hex 32` |
| `GTE_APP_ENV` | `production` |
| `GTE_CORS_ALLOW_ORIGINS` | Cloudflare Pages domain |
| `GTE_INGESTION_PROVIDER` | `sportmonks` |
| `SPORTMONKS_API_TOKEN` | From Sportmonks dashboard |
| `CLOUDINARY_CLOUD_NAME` | From Cloudinary dashboard |
| `WEB_CONCURRENCY` | `4` |

## Render `render.yaml` Update Required

The `gtex-web` static service must be removed (frontend moves to Cloudflare Pages).
The `GTE_CORS_ALLOW_ORIGINS` must be updated to the Cloudflare Pages domain.
The `DATABASE_URL` must reference the Neon connection string (not `fromDatabase`).
The `GTE_REDIS_URL` must reference the Upstash URL (not `fromService`).

See `GTEX_DEPLOYMENT_BLUEPRINT.md` for the updated `render.yaml` diff.
