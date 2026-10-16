# Technical Architecture for 100k Users

## Build style
Use a modular monolith first.

## Stack
- FastAPI
- PostgreSQL
- Redis
- Celery
- WebSockets
- Flutter
- Docker
- SQLAlchemy
- Alembic

## Core modules
1. Auth & Users
2. Wallet & Ledger
3. Player Catalog
4. Asset Ownership
5. Market Engine
6. Squad & Competition Engine
7. Value Engine
8. Discovery & Search
9. Notifications
10. Data Ingestion

## Infra
### API
- 4 to 8 FastAPI instances

### Database
- 1 PostgreSQL primary
- 2 read replicas

### Cache
- 1 Redis with persistence

### Workers
- 4 Celery workers
- 1 scheduler

### Realtime
- 2 websocket service instances

### Object storage
- S3-compatible storage

## Critical rule
Do not do heavy jobs inside request handlers.
Use workers for:
- value recalculation
- leaderboard refresh
- auction settlement
- discovery feed refresh
- notification fanout

## Data flow
Sportmonks / API-Football
-> normalization
-> event tables
-> value engine jobs
-> leaderboard jobs
-> notifications
-> websocket fanout
