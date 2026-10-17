# GTEX API Documentation

This repository exposes a FastAPI backend. Interactive API docs are available when the server is running:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Core surface map

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `POST /api/auth/change-password`

### Wallets and treasury
- `GET /api/wallets/summary`
- `GET /api/wallets/overview`
- `POST /api/treasury/deposits/initiate`
- `POST /api/treasury/withdrawals/request`
- `GET /api/treasury/withdrawals/eligibility`

### Policies and compliance
- `GET /policies/documents`
- `GET /policies/documents/{document_key}`
- `POST /policies/acceptances`
- `GET /policies/me/acceptances`
- `GET /policies/me/requirements`
- `GET /policies/me/compliance`
- `GET /policies/country/{country_code}`
- `POST /admin/policies/documents`
- `GET /admin/policies/country-policies`
- `POST /admin/policies/country-policies`

### Market and portfolio
- `GET /api/market/players`
- `GET /api/market/ticker/{player_id}`
- `GET /api/orders/book/{player_id}`
- `GET /api/portfolio`
- `GET /api/portfolio/snapshot`

### Competitions and match engine
- `GET /api/competitions/...`
- `GET /api/leagues/...`
- `GET /api/champions-league/...`
- `GET /api/world-super-cup/...`
- `GET /api/match-engine/...`

### Admin
- `GET /api/admin/...`
- `GET /api/admin/godmode/bootstrap`
- `POST /api/admin/access`

## Compliance behavior

Deposits and withdrawals are policy-aware:
- mandatory latest policy versions must be accepted before regulated flows unlock
- country feature policies decide whether deposits and platform-reward withdrawals are enabled
- wallet overview and treasury eligibility endpoints surface the exact blocker reason

## Frontend contract notes

The Flutter app is expected to consume JSON responses using both snake_case and camelCase tolerant parsing in several client-side model readers. This keeps mock fixtures and backend responses compatible while the API continues to harden.
