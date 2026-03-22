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
3. Run Alembic migrations.
4. Start the FastAPI app with a production ASGI server.
5. Attach Redis for jobs, cache, and event fan-out.

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
