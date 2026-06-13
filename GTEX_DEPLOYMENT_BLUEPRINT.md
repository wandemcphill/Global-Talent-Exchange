# GTEX Deployment Blueprint

## Architecture

```
Cloudflare Pages (Flutter Web)
        |
        | HTTPS / WSS
        v
Render FastAPI Backend (gtex-api)
        |
        +------ Neon PostgreSQL (DATABASE_URL)
        |
        +------ Upstash Redis (REDIS_URL, optional initially)
        |
        +------ Cloudinary (delivery only — CLOUDINARY_CLOUD_NAME)
        |
Render Workers:
  gtex-rq-worker
  gtex-simulation-worker
  gtex-outbox-relay
  gtex-player-ingestion-worker (Node, requires Redis)
```

---

## Step 1: Neon PostgreSQL Setup

1. Create account at https://neon.tech
2. Create project: `gtex`
3. Create database: `gtex`
4. Copy the connection string (starts with `postgres://` or `postgresql://`)
5. Append `?sslmode=require` if not already present
6. Store as `DATABASE_URL`

**Example:**
```
postgresql://gtex_user:password@ep-xxx.us-east-2.aws.neon.tech/gtex?sslmode=require
```

---

## Step 2: Upstash Redis Setup

> Skip for initial deployment. Set `REDIS_ENABLED=false`.

When ready:
1. Create account at https://upstash.com
2. Create Redis database (region: same as Render — Frankfurt or US East)
3. Copy the `rediss://` TLS connection string
4. Store as `REDIS_URL`
5. Set `REDIS_ENABLED=true`

---

## Step 3: Render Setup

### 3a. Update `render.yaml`

Remove the `gtex-web` static service (frontend moves to Cloudflare Pages).

Replace `fromDatabase` and `fromService` references with explicit env var values:
- `DATABASE_URL` → Neon connection string (set as secret in Render dashboard)
- `GTE_REDIS_URL` → Upstash URL (set as secret; leave blank if `REDIS_ENABLED=false`)

Update `GTE_CORS_ALLOW_ORIGINS` to the Cloudflare Pages domain.

### 3b. Create Render services

Option A — Deploy from `render.yaml`:
```
render.yaml → Render Dashboard → New → Blueprint
```

Option B — Manual (recommended for first deploy):
1. Create Web Service: `gtex-api`
   - Runtime: Python
   - Build: `pip install -r backend/requirements.txt`
   - Pre-deploy: `bash ops/render/production-preflight.sh && cd backend && alembic -c migrations/alembic.ini upgrade head`
   - Start: `cd backend && gunicorn app.asgi:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 180 --graceful-timeout 120`
   - Plan: Standard (required for WebSocket)

2. Create Background Worker: `gtex-rq-worker`
   - Start: `cd backend && python -m app.workers.rq_worker_main`

3. Create Background Worker: `gtex-simulation-worker`
   - Start: `cd backend && python -m app.backbone.simulation_worker_main`

4. Create Background Worker: `gtex-outbox-relay` (when `GTE_OUTBOX_RELAY_ENABLED=true`)
   - Start: `cd backend && python -m app.backbone.outbox_relay_main`

5. Create Background Worker: `gtex-player-ingestion-worker`
   - Runtime: Node
   - Build: `cd services/player-ingestion && npm ci`
   - Start: `cd services/player-ingestion && npm run migrate && npm start`

### 3c. Set environment variables in Render

Required for all services:
```
DATABASE_URL          = <Neon connection string>
GTE_APP_ENV           = production
GTE_AUTH_SECRET       = <openssl rand -hex 32>
GTE_MEDIA_SIGNING_SECRET = <openssl rand -hex 32>
```

Required for `gtex-api`:
```
REDIS_ENABLED         = false   (set true when Upstash ready)
REDIS_URL             = <Upstash rediss:// URL>
GTE_CORS_ALLOW_ORIGINS = https://<pages-domain>.pages.dev
GTE_INGESTION_PROVIDER = sportmonks
CLOUDINARY_CLOUD_NAME = <your cloud name>
WEB_CONCURRENCY       = 4
GTE_RUN_MIGRATION_CHECK = true
GTE_TASK_QUEUE_ENABLED = true
GTE_OUTBOX_RELAY_ENABLED = false
```

Required for `gtex-player-ingestion-worker`:
```
DATABASE_URL          = <Neon connection string>
DATABASE_SSL          = true
REDIS_ENABLED         = true
REDIS_URL             = <Upstash rediss:// URL>
SPORTMONKS_API_TOKEN  = <your token>
CLOUDINARY_CLOUD_NAME = <your cloud name>
CLOUDINARY_PLAYER_FOLDER = gtex/players
INGESTION_RUN_ON_START = true
HEALTH_SERVER_ENABLED = true
HEALTH_PORT           = 3000
```

---

## Step 4: Cloudflare Pages Setup

1. Connect GitHub repository to Cloudflare Pages
2. Set build configuration:
   - Build command: `bash ops/cloudflare/build-frontend.sh`
   - Build output directory: `frontend/build/web`
3. Set environment variables:
   ```
   GTE_API_BASE_URL  = https://gtex-api.onrender.com
   GTE_BACKEND_MODE  = live
   ```
4. Deploy

---

## Step 5: Migration Sequence

Run once after Render services are created and `DATABASE_URL` is set:

```sh
# Via Render pre-deploy command (automatic):
bash ops/render/production-preflight.sh
cd backend && alembic -c migrations/alembic.ini upgrade head

# Or manually via Render Shell:
cd backend && alembic -c migrations/alembic.ini upgrade head
```

Verify:
```sh
curl https://gtex-api.onrender.com/health
# Expected: {"status": "ok", ...}

curl https://gtex-api.onrender.com/ready
# Expected: {"status": "ready"}
```

---

## Step 6: Initial Ingestion Sequence

After migrations pass:

1. The `gtex-player-ingestion-worker` starts automatically with `INGESTION_RUN_ON_START=true`
2. It fetches players from Sportmonks and stores them in Neon
3. Player images are **not** uploaded — Cloudinary public_ids are derived from Sportmonks IDs
4. Image URLs are derived as: `https://res.cloudinary.com/{cloud_name}/image/upload/f_auto,q_auto/gtex/players/{id}`

Monitor ingestion progress via Render worker logs.

---

## Step 7: Post-Deploy Verification

```sh
# Health
curl https://gtex-api.onrender.com/health

# Ready
curl https://gtex-api.onrender.com/ready

# API docs
curl https://gtex-api.onrender.com/docs

# Version
curl https://gtex-api.onrender.com/version

# Match center
python ops/render/verify_match_center_routes.py --url https://gtex-api.onrender.com/health
```

---

## Rollback Procedure

### Backend rollback (Render)

1. Go to Render Dashboard → gtex-api → Deploys
2. Click the previous successful deploy
3. Click "Rollback to this deploy"
4. Repeat for workers if needed

### Database rollback (Alembic)

```sh
# Roll back one migration
cd backend && alembic -c migrations/alembic.ini downgrade -1

# Roll back to specific revision
cd backend && alembic -c migrations/alembic.ini downgrade <revision>
```

### Frontend rollback (Cloudflare Pages)

1. Go to Cloudflare Pages Dashboard → gtex → Deployments
2. Click the previous successful deployment
3. Click "Rollback to this deployment"

---

## Environment Variable Summary

See `.env.production.example` for the full list with descriptions.
