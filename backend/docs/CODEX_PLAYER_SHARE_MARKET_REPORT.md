# CODEX Player Share Market Report

Verified on March 30, 2026.

## Outcome

Real-player share trading is operational on the backend for issued markets.

- `GET /players/{player_id}/shares/market` returns `200` for an issued imported real player.
- `GET /players/{player_id}/shares/events` returns `200` and includes `issue` and `buy` events.
- `POST /players/{player_id}/shares/buy` returns `201` and persists the holding plus event log.
- A new repair migration recreates missing `player_share_markets`, `player_share_holdings`, and `player_share_events` tables on drifted databases during upgrade to head.
- The repair migration also backfills an active market plus an `issue` event for imported real players that were already present but had no share market.

## Backend Changes

- Wired `Player` ORM relations to `PlayerShareMarket`, `PlayerShareHolding`, and `PlayerShareEvent`.
- Exported player-share models from [`app/models/__init__.py`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/models/__init__.py).
- Hardened issuance in [`app/players/token_service.py`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/app/players/token_service.py):
  - validates market status against `active|paused|closed`
  - flushes the market before logging the `issue` event so event metadata includes `market_id`
  - records imported-player metadata on issuance
  - records richer `buy` event metadata
  - stabilizes event ordering with `created_at DESC, id DESC`
- Added repair migration [`20260330_0074_player_share_market_schema_repair.py`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/migrations/versions/20260330_0074_player_share_market_schema_repair.py).
  - recreates missing player-share tables and indexes
  - backfills active share markets for imported real players missing one
- Updated the canonical schema doc to include `player_share_events` in [`docs/architecture/postgres_live_economy_schema.sql`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/docs/architecture/postgres_live_economy_schema.sql).

## Endpoint Proof

Proof run used an imported real-player fixture:

- `player_id`: `proof-real-player`
- `source_name`: `transfermarkt_2nd_zip`
- `ingestion_batch_id`: `2nd-zip-proof-batch`

Observed responses:

```text
POST /players/proof-real-player/shares/issue -> 200
GET  /players/proof-real-player/shares/market -> 200
GET  /players/proof-real-player/shares/events -> 200
POST /players/proof-real-player/shares/buy -> 201
GET  /players/proof-real-player/shares/events -> 200
```

Issue response excerpt:

```json
{
  "player_id": "proof-real-player",
  "total_shares": 1000,
  "share_price_coin": "0.5000",
  "status": "active",
  "metadata_json": {
    "player_name": "Victor Osimhen",
    "issued_by_user_id": "proof-admin",
    "is_real_player": true,
    "real_player_tier": "featured"
  }
}
```

Events after issuance:

```json
[
  {
    "event_type": "issue",
    "metadata_json": {
      "market_id": "75a59c7c-62eb-45ca-b270-a8cd6adc0b9d",
      "total_shares": 1000,
      "status": "active",
      "is_real_player": true
    }
  }
]
```

Buy response excerpt:

```json
{
  "market": {
    "player_id": "proof-real-player",
    "circulating_shares": 10,
    "share_price_coin": "0.5000"
  },
  "holding": {
    "user_id": "proof-fan",
    "player_id": "proof-real-player",
    "share_count": 10,
    "average_cost_coin": "0.5000"
  },
  "gross_amount_coin": "5.0000"
}
```

Events after buy:

```json
[
  {
    "event_type": "buy",
    "share_delta": 10,
    "gross_amount_coin": "5.0000",
    "metadata_json": {
      "market_id": "75a59c7c-62eb-45ca-b270-a8cd6adc0b9d",
      "circulating_shares": 10,
      "total_shares": 1000
    }
  },
  {
    "event_type": "issue"
  }
]
```

## Automated Verification

Executed successfully:

```text
python -m pytest tests/players/test_player_share_market_routes.py -q
3 passed in 46.90s

python -m pytest tests/players/test_player_token_market_service.py -q
2 passed in 33.24s

python -m pytest tests/persistence/test_postgres_live_economy_schema_doc.py -q
1 passed in 0.73s

python -m pytest tests/persistence/test_migrations.py -q
2 passed in 97.23s
```

Coverage added:

- [`tests/players/test_player_share_market_routes.py`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/tests/players/test_player_share_market_routes.py)
  - market issuance
  - market read
  - buy mutation
- [`tests/persistence/test_migrations.py`](/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/backend/tests/persistence/test_migrations.py)
  - repair migration recreates dropped player-share tables on upgrade
  - repair migration backfills a market plus `issue` event for an imported real player
