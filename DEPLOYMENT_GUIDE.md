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
- any moderation, telemetry, or error reporting DSNs

## Local verification before deploy
1. Run migrations to head.
2. Boot the backend.
3. Confirm `/health`, `/ready`, and `/version`.
4. Confirm `/docs` loads.
5. Log in with seeded admin credentials and change the password immediately.
6. Confirm wallet, market, competitions, and policy endpoints respond.

## Backend deploy flow
1. Create the database.
2. Set environment variables.
   For current GTEX transactional email, use Brevo SMTP with the temporary Gmail sender `vidzimedialtd@gmail.com` and `GTEX` as the sender name until the domain sender is ready.
3. Run Alembic migrations.
4. Start the FastAPI app with a production ASGI server.
5. Attach Redis for jobs, cache, and event fan-out.

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
- monitor fraud, suspicious trading, gifting, and view clusters
- review country feature policies before opening deposits and withdrawals in a region
