# GTEX Deployment Guide

## Recommended production stack
- Backend: FastAPI
- Database: PostgreSQL
- Cache / jobs: Redis
- Frontend: Flutter for iOS, Android, macOS, Windows, and tablets

## Environment checklist

### Backend
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY` or equivalent auth secret
- `EMAIL_ENABLED`
- `EMAIL_PROVIDER`
- `EMAIL_FROM_ADDRESS`
- `EMAIL_FROM_NAME`
- `EMAIL_REPLY_TO`
- `BREVO_SMTP_HOST`
- `BREVO_SMTP_PORT`
- `BREVO_SMTP_USERNAME`
- `BREVO_SMTP_PASSWORD` from env only, using a regenerated Brevo SMTP key
- payment gateway secrets
- storage / attachment secrets where applicable
- `GTE_METRICS_ENABLED`
- `GTE_LOG_JSON`
- `GTE_OBSERVABILITY_TRACING_ENABLED`
- `GTE_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- `GTE_OTEL_SERVICE_NAME`
- any moderation or error reporting DSNs

## Local verification before deploy
1. Run migrations to head.
2. Boot the backend.
3. Confirm `/health`, `/ready`, and `/version`.
4. Confirm `/metrics`.
5. Confirm `/docs` loads.
6. Log in with seeded admin credentials and change the password immediately.
7. Confirm wallet, market, competitions, and policy endpoints respond.

## Backend deploy flow
1. Create the database.
2. Set environment variables.
   For current GTEX transactional email, use Brevo SMTP with the temporary Gmail sender `vidzimedialtd@gmail.com` and `GTEX` as the sender name until the domain sender is ready.
3. Run Alembic migrations.
4. Start the FastAPI app with a production ASGI server.
5. Attach Redis for jobs, cache, and event fan-out.

## CI/CD pipeline

The repository now uses a three-environment release model:

- `dev`
  - local Docker / `.env` driven workflow
  - use `backend/.env.example` and `infra/.env.example` as templates
- `staging`
  - deploys automatically after `main` passes CI
  - uses the GitHub Actions `staging` environment and its own Render service IDs and health URL
- `production`
  - deploys only from the manual `Production Deploy` workflow
  - uses the GitHub Actions `production` environment
  - protect this environment with required reviewers so GitHub pauses before the deploy job runs

### GitHub environment contract

Create separate GitHub environments named `staging` and `production` and define these values independently in each one:

- Secrets:
  - `RENDER_API_KEY`
  - `RENDER_SERVICE_API`
  - `RENDER_SERVICE_OUTBOX`
  - `RENDER_SERVICE_SIMULATION`
  - `RENDER_SERVICE_PROJECTIONS`
  - `RENDER_SERVICE_WEB`
- Variables:
  - `RENDER_HEALTH_URL`
  - optional `RENDER_DEPLOY_TIMEOUT_SECONDS`
  - optional `RENDER_HEALTH_TIMEOUT_SECONDS`
  - optional `RENDER_POLL_INTERVAL_SECONDS`

The workflow reads the same variable names in both environments, but GitHub resolves different values per environment so staging and production stay isolated.

### Deployment safety

- Pull requests run tests only. No deploys are triggered from PR workflows.
- Pushes to `main` run CI first, then deploy staging.
- Production deploys are manual and should be dispatched from `main` only.
- Render auto deploys are disabled in `render.yaml` so GitHub Actions remains the single release gate.
- The deploy runner polls Render until each service is live, then calls `/health` and requires:
  - `api`
  - `database`
  - `redis`
- After the API health gate passes, the deploy runner also verifies the hosted Unity live contract:
  - `/api/matches/{match_id}/unity-access`
  - `/api/matches/{match_id}/unity-access/refresh`
- That post-deploy gate fails the rollout if the hosted API is still behind the GTEX workspace backend shape.
- If any deploy or health gate fails, the runner triggers Render rollbacks for the services already promoted in that release.
- The API service runs with two instances and an extended shutdown delay so Render can roll instances without dropping all capacity at once.

### Manual hosted Unity verification

Run this after any manual Render rollout or when validating a hosted incident:

```powershell
python ops/render/verify_unity_routes.py --url "https://gtex-api.onrender.com/health"
```

This accepts either the API base URL or the health URL and fails if the hosted deployment does not expose the Unity access and refresh routes expected by the GTEX Unity runtime.

## Render to Kubernetes

Render remains the simplest production starting point for this repo because the backend is still a modular monolith with separate worker entrypoints. The Kubernetes-ready path is:

1. Keep the API on Render while stabilizing contracts.
2. Move `gtex-outbox-relay`, `gtex-simulation-worker`, and `gtex-projection-workers` onto Kubernetes first.
3. Add HPA for API and worker pods.
4. Add read replicas for query-heavy traffic.
5. Extract payment, notification, wallet, and market boundaries only when scale or ownership justifies separate deployables.

Canonical architecture doc:

- `Docs/architecture/render-to-kubernetes-microservices.md`

Starter Kubernetes manifests and container path:

- `Dockerfile`
- `ops/k8s/README.md`
- `ops/k8s/base/`

## Frontend deploy flow
- build Android APK / AAB
- build iOS archive
- build Windows and macOS desktop releases
- verify policy pages, reporting flows, and store disclosure text before submission


## Production hardening
- use PostgreSQL instead of SQLite
- configure HTTPS and secure cookies if web auth is used
- pin dependency versions for repeatable builds
- enable backups for database and media assets
- run the control-tower stack in `ops/observability/` for logs, metrics, traces, and alert rules
- monitor fraud, suspicious trading, gifting, and view clusters
- review country feature policies before opening deposits and withdrawals in a region
