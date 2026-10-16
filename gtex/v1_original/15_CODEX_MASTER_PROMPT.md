# Codex Master Prompt — The Football Talent Exchange

You are building a production-minded MVP for **The Football Talent Exchange**.

Tagline:
**Where football knowledge becomes value**

Read every file in this ZIP first and follow the rules exactly.

## Product identity
This is a skill-based football strategy platform with tradable digital player assets.
It is not gambling and not a securities exchange.

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

## Mandatory rules
1. One user can own only one copy of a player.
2. Every player has a global supply cap.
3. Every user gets exactly 3 teams:
   - Main Team (40)
   - Reserve Team (40)
   - Youth Team (35)
4. Demo wallet starts with 5000 demo coins.
5. 1 coin = 1 euro.
6. Discovery mode must exist.
7. Club valuation ranking must exist.
8. Free transfer auctions use hidden single bids and lowest winning bid clearing.
9. Use realistic-looking avatars.
10. Use Sportmonks primary adapter and API-Football fallback.
11. Build as modular monolith with event-driven workers.
12. Optimize for 100k users.

## Build order
Follow only these stages:
1. foundation
2. market basics
3. data ingestion + value engine
4. squads + competitions
5. discovery + search
6. auctions
7. Flutter app
8. hardening

## First task
Do Stage 1 only:
- monorepo structure
- backend models
- migrations
- signup/login
- wallets
- auto-create 3 teams
- player catalog
- ownership rules
- tests

Then stop and report:
- files changed
- tests passing
- next recommended step
