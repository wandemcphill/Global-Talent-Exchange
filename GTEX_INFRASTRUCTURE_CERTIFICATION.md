# GTEX Infrastructure Certification

Date: 2026-06-13
Branch: feature/original-visual-runtime
Task: Infrastructure readiness for Cloudflare Pages + Render + Neon + Upstash + Cloudinary

---

## Certification Questions

### 1. Is GTEX ready for Neon?
**YES — READY**

- `normalize_database_url()` rewrites `postgres://` and `postgresql://` to `postgresql+psycopg://` automatically
- `?sslmode=require` passes through unchanged
- Alembic `env.py` uses the same normalisation function
- `pool_pre_ping=True` handles Neon connection hibernation
- No code changes were required

### 2. Is GTEX ready for Redis (Upstash)?
**YES — READY (with Redis optional)**

- `REDIS_ENABLED=false` (default) — application runs entirely without Redis using `NullCacheBackend`
- `REDIS_ENABLED=true` + `REDIS_URL=rediss://...` — connects to Upstash via TLS
- Health endpoint reports `skipped` (not `error`) when Redis is disabled
- Ingestion worker requires Redis for BullMQ job queues (by design)
- Start without Redis; add Upstash when ready for distributed cache, rate limiting, and realtime fan-out

### 3. Is GTEX ready for Render?
**YES — READY**

- Start command: `gunicorn app.asgi:app --worker-class uvicorn.workers.UvicornWorker` ✅
- Pre-deploy: Alembic migration runs before traffic ✅
- Health endpoint: `GET /health` returns `{"status":"ok"}` ✅
- Readiness endpoint: `GET /ready` ✅
- WebSocket: Render Standard plan supports persistent WS connections ✅
- `render.yaml` exists and configures all services ✅
- **Action needed:** Remove `gtex-web` static service from `render.yaml` (frontend moves to Cloudflare Pages)
- **Action needed:** Replace `fromDatabase`/`fromService` references with explicit Neon/Upstash values

### 4. Is GTEX ready for Cloudflare Pages?
**YES — READY**

- Build script created: `ops/cloudflare/build-frontend.sh`
- Build output: `frontend/build/web/`
- `GTE_API_BASE_URL` injected via `--dart-define` at build time
- `GTE_BACKEND_MODE=live` prevents any fixture/localhost path from activating
- 206 `localhost` references are all in `factory .fixture()` constructors — never reached in production
- WebSocket URL derived at runtime from API base URL (no separate env var needed)

### 5. Can ingestion use existing Cloudinary assets?
**YES — CONFIRMED**

All ingestion pipelines now use `resolvePlayerImage()` from `imageResolver.js`:
- No uploads
- No Cloudinary API credentials required for ingestion
- Only `CLOUDINARY_CLOUD_NAME` is needed for delivery URL generation

### 6. Can player images resolve via `gtex/players/{sportmonks_player_id}`?
**YES — VERIFIED BY TESTS**

- `getPlayerPublicId(311129)` → `"gtex/players/311129"` ✅
- `resolvePlayerImage({ playerId: 311129 })` → `{ storageKey: "gtex/players/311129", rightsCleared: true }` ✅
- `get_player_public_id(311129)` (Python) → `"gtex/players/311129"` ✅
- URL: `https://res.cloudinary.com/{cloud}/image/upload/f_auto,q_auto/gtex/players/311129` ✅

### 7. What blockers remain before first deployment?

| # | Blocker | Severity | Owner |
|---|---|---|---|
| 1 | Obtain Neon connection string and set `DATABASE_URL` | **Required** | Ops |
| 2 | Obtain Upstash `rediss://` URL (or start with `REDIS_ENABLED=false`) | Optional | Ops |
| 3 | Set `GTE_AUTH_SECRET` and `GTE_MEDIA_SIGNING_SECRET` (generate with `openssl rand -hex 32`) | **Required** | Ops |
| 4 | Set `SPORTMONKS_API_TOKEN` on `gtex-player-ingestion-worker` | **Required** | Ops |
| 5 | Set `CLOUDINARY_CLOUD_NAME` on all services (for image delivery URLs) | **Required** | Ops |
| 6 | Set `GTE_CORS_ALLOW_ORIGINS` to Cloudflare Pages domain | **Required** | Ops |
| 7 | Remove `gtex-web` from `render.yaml` (or disable it manually) | **Required** | Ops |
| 8 | Set `GTE_API_BASE_URL` in Cloudflare Pages env vars | **Required** | Ops |

No code blockers remain.

### 8. GO / NO-GO Recommendation

**GO — subject to environment variables being set**

All code-level readiness tasks are complete:
- ✅ Central player image resolver implemented (Task A)
- ✅ All ingestion upload paths removed (Task B)
- ✅ Neon PostgreSQL compatibility verified (Task C)
- ✅ Upstash Redis optional gate implemented (Task D)
- ✅ Render deployment configuration verified (Task E)
- ✅ Cloudflare Pages build script created (Task F)
- ✅ Production environment template created (Task G)
- ✅ Deployment blueprint documented (Task H)

The only remaining items are operational (secrets, env vars, account setup) — not engineering blockers.

---

## Files Changed / Created

| File | Type | Change |
|---|---|---|
| `backend/app/core/player_image.py` | **New** | Canonical Python player image resolver |
| `services/player-ingestion/src/imageResolver.js` | **New** | Canonical Node.js player image resolver |
| `ops/cloudflare/build-frontend.sh` | **New** | Cloudflare Pages Flutter web build script |
| `.env.production.example` | **New** | Production environment template |
| `PLAYER_IMAGE_RESOLVER_REPORT.md` | **New** | Task A report |
| `INGESTION_MEDIA_INTEGRATION_REPORT.md` | **New** | Task B report |
| `NEON_POSTGRES_READINESS_REPORT.md` | **New** | Task C report |
| `REDIS_READINESS_REPORT.md` | **New** | Task D report |
| `RENDER_DEPLOYMENT_READINESS_REPORT.md` | **New** | Task E report |
| `CLOUDFLARE_PAGES_READINESS_REPORT.md` | **New** | Task F report |
| `GTEX_DEPLOYMENT_BLUEPRINT.md` | **New** | Task H blueprint |
| `backend/app/core/config.py` | **Modified** | Added `REDIS_ENABLED` / `GTE_REDIS_ENABLED` |
| `backend/app/core/cache.py` | **Modified** | `build_cache_backend` respects `redis_enabled` |
| `backend/app/core/health.py` | **Modified** | Redis `skipped` message updated |
| `backend/tests/app/test_main.py` | **Modified** | Updated health detail string assertions |
| `services/player-ingestion/src/jobs.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/importLaunchLeagueBatch.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/importNamedPlayers.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/importTopEuropeanLeagues.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/importYouthPlayers.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/backfillMarketplaceImages.js` | **Modified** | Replaced upload calls with resolver |
| `services/player-ingestion/src/config.js` | **Modified** | `redisUrl` now optional; added `redisEnabled` |
| `services/player-ingestion/src/queues.js` | **Modified** | Clear error when Redis absent |
