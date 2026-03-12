# Frontend API Ready

## Status

The backend is ready for the frontend MVP screens listed below against seeded demo data.

Demo seed guarantees:

- at least one rising player in `/api/market/players`
- at least one falling player in `/api/market/players`
- at least one liquid player with a tight spread and multi-level order book
- at least one illiquid player with a wide spread and shallow order book
- seeded portfolio holdings for the demo user
- seeded cash wallet balance for the demo user

Auth prerequisite:

- `POST /auth/login`
- Demo credentials:
  - `fan@demo.gte.local` / `DemoPass123`
  - `scout@demo.gte.local` / `DemoPass123`
  - `admin@demo.gte.local` / `DemoPass123`

Login request:

```json
{
  "email": "fan@demo.gte.local",
  "password": "DemoPass123"
}
```

Login response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "<demo_user_id>",
    "email": "fan@demo.gte.local",
    "username": "demo_fan",
    "display_name": "Demo Fan",
    "role": "user",
    "kyc_status": "pending",
    "is_active": true
  }
}
```

Use `Authorization: Bearer <jwt>` for protected routes.

## Safe Now

These endpoints are safe for immediate UI integration:

| Screen / feature | Method | Endpoint | Auth |
| --- | --- | --- | --- |
| Market list | `GET` | `/api/market/players` | No |
| Player detail | `GET` | `/api/market/players/{player_id}` | No |
| Player ticker | `GET` | `/api/market/ticker/{player_id}` | No |
| Candles | `GET` | `/api/market/players/{player_id}/candles?interval=1h&limit=30` | No |
| Order book | `GET` | `/api/orders/book/{player_id}` | No |
| Open / recent orders | `GET` | `/api/orders?status=open&status=partially_filled&limit=20` | Yes |
| Submit order | `POST` | `/api/orders` | Yes |
| Order detail | `GET` | `/api/orders/{order_id}` | Yes |
| Cancel order | `POST` | `/api/orders/{order_id}/cancel` | Yes |
| Wallet balances | `GET` | `/api/wallets/summary` | Yes |
| Portfolio holdings-only | `GET` | `/api/portfolio` | Yes |
| Portfolio holdings + cash snapshot | `GET` | `/api/portfolio/snapshot` | Yes |
| Legacy portfolio snapshot alias | `GET` | `/portfolio` | Yes |
| Portfolio summary totals | `GET` | `/api/portfolio/summary` | Yes |

## Endpoint Contract

### 1. Market list

`GET /api/market/players?limit=20&offset=0`

Response example:

```json
{
  "items": [
    {
      "player_id": "<rising_player_id>",
      "player_name": "Arno Almeida Antunes",
      "position": "forward",
      "nationality": "Italy",
      "current_club_name": "France Tier 4 Club 01",
      "age": 19,
      "current_value_credits": 136.5,
      "movement_pct": 0.084,
      "trend_score": 55.17,
      "market_interest_score": 109,
      "average_rating": null
    },
    {
      "player_id": "<falling_player_id>",
      "player_name": "Ander Almeida Antunes",
      "position": "forward",
      "nationality": "Norway",
      "current_club_name": "France Tier 3 Club 01",
      "age": 28,
      "current_value_credits": 115.34,
      "movement_pct": -0.084,
      "trend_score": 57.85,
      "market_interest_score": 105,
      "average_rating": null
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 12
}
```

Frontend note:

- use `movement_pct > 0` for rising cards
- use `movement_pct < 0` for falling cards
- liquid vs illiquid should come from ticker and order book depth, not from this payload alone

### 2. Player detail

`GET /api/market/players/{player_id}`

Response example:

```json
{
  "player_id": "<rising_player_id>",
  "identity": {
    "player_name": "Arno Almeida Antunes",
    "first_name": "Arno",
    "last_name": "Almeida Antunes",
    "short_name": null,
    "position": "Forward",
    "normalized_position": "forward",
    "nationality": "Italy",
    "nationality_code": "IT",
    "age": 19,
    "date_of_birth": "2006-08-18",
    "preferred_foot": null,
    "shirt_number": null,
    "height_cm": null,
    "weight_kg": null,
    "current_club_id": "<club_id>",
    "current_club_name": "France Tier 4 Club 01",
    "current_competition_id": null,
    "current_competition_name": null,
    "image_url": null
  },
  "market_profile": {
    "is_tradable": true,
    "market_value_eur": null,
    "supply_tier": null,
    "liquidity_band": null,
    "holder_count": null,
    "top_holder_share_pct": null,
    "top_3_holder_share_pct": null,
    "snapshot_market_price_credits": null,
    "quoted_market_price_credits": null,
    "trusted_trade_price_credits": null,
    "trade_trust_score": null
  },
  "value": {
    "last_snapshot_id": "<snapshot_id>",
    "last_snapshot_at": "2026-03-11T12:00:00Z",
    "current_value_credits": 136.5,
    "previous_value_credits": 125.92,
    "movement_pct": 0.084,
    "football_truth_value_credits": 136.5,
    "market_signal_value_credits": 136.5,
    "published_card_value_credits": 136.5
  },
  "trend": {
    "trend_score": 55.17,
    "market_interest_score": 109,
    "average_rating": null,
    "global_scouting_index": 55.17,
    "previous_global_scouting_index": null,
    "global_scouting_index_movement_pct": null,
    "drivers": ["demo_seed_frontend_state", "demo_rising"]
  }
}
```

### 3. Player ticker

`GET /api/market/ticker/{player_id}`

Response example:

```json
{
  "player_id": "<liquid_player_id>",
  "symbol": "Baba Ait El Haj",
  "last_price": 138.0,
  "best_bid": 135.0,
  "best_ask": 139.0,
  "spread": 4.0,
  "mid_price": 137.0,
  "reference_price": 136.5,
  "day_change": 0.0,
  "day_change_percent": 0.0,
  "volume_24h": 9.0
}
```

### 4. Candles

`GET /api/market/players/{player_id}/candles?interval=1h&limit=30`

Response example:

```json
{
  "player_id": "<liquid_player_id>",
  "interval": "1h",
  "candles": [
    {
      "timestamp": "2026-03-11T19:00:00Z",
      "open": 137.0,
      "high": 137.0,
      "low": 136.5,
      "close": 137.0,
      "volume": 9.0
    }
  ]
}
```

### 5. Order book

`GET /api/orders/book/{player_id}`

Response example:

```json
{
  "player_id": "<liquid_player_id>",
  "bids": [
    {
      "price": "135.0000",
      "quantity": "4.0000",
      "order_count": 1
    },
    {
      "price": "133.0000",
      "quantity": "5.0000",
      "order_count": 1
    }
  ],
  "asks": [
    {
      "price": "139.0000",
      "quantity": "4.0000",
      "order_count": 1
    },
    {
      "price": "141.0000",
      "quantity": "5.0000",
      "order_count": 1
    }
  ],
  "generated_at": "2026-03-11T19:25:40.848450Z"
}
```

Liquid demo example:

- best bid `135.0000`
- best ask `139.0000`
- spread `4.0000`

Illiquid demo example:

- best bid `59.0000`
- best ask `79.0000`
- spread `20.0000`

### 6. Submit order

`POST /api/orders`

Request example:

```json
{
  "player_id": "<illiquid_player_id>",
  "side": "buy",
  "quantity": 1,
  "max_price": "78.0000"
}
```

Response example:

```json
{
  "id": "<order_id>",
  "user_id": "<demo_user_id>",
  "player_id": "<illiquid_player_id>",
  "side": "buy",
  "quantity": "1.0000",
  "filled_quantity": "0.0000",
  "remaining_quantity": "1.0000",
  "max_price": "78.0000",
  "currency": "credit",
  "reserved_amount": "78.0000",
  "status": "open",
  "hold_transaction_id": "<ledger_transaction_id>",
  "created_at": "2026-03-11T19:25:40.911202",
  "updated_at": "2026-03-11T19:25:40.925562",
  "execution_summary": {
    "execution_count": 0,
    "total_notional": "0.0000",
    "average_price": null,
    "last_executed_at": null,
    "executions": []
  }
}
```

Crossing seeded liquidity is also supported:

- a buy priced at the visible best ask will return `status` `filled` or `partially_filled`
- the response includes `execution_summary.executions`

### 7. Order detail

`GET /api/orders/{order_id}`

Response example:

```json
{
  "id": "<order_id>",
  "user_id": "<demo_user_id>",
  "player_id": "<illiquid_player_id>",
  "side": "buy",
  "quantity": "1.0000",
  "filled_quantity": "0.0000",
  "remaining_quantity": "1.0000",
  "max_price": "78.0000",
  "currency": "credit",
  "reserved_amount": "78.0000",
  "status": "open",
  "hold_transaction_id": "<ledger_transaction_id>",
  "created_at": "2026-03-11T19:25:40.911202",
  "updated_at": "2026-03-11T19:25:40.925562",
  "execution_summary": {
    "execution_count": 0,
    "total_notional": "0.0000",
    "average_price": null,
    "last_executed_at": null,
    "executions": []
  }
}
```

### 8. Cancel order

`POST /api/orders/{order_id}/cancel`

Request body:

- none

Response example:

```json
{
  "id": "<order_id>",
  "user_id": "<demo_user_id>",
  "player_id": "<illiquid_player_id>",
  "side": "buy",
  "quantity": "1.0000",
  "filled_quantity": "0.0000",
  "remaining_quantity": "1.0000",
  "max_price": "78.0000",
  "currency": "credit",
  "reserved_amount": "0.0000",
  "status": "cancelled",
  "hold_transaction_id": "<ledger_transaction_id>",
  "created_at": "2026-03-11T19:25:40.911202",
  "updated_at": "2026-03-11T19:25:40.968491",
  "execution_summary": {
    "execution_count": 0,
    "total_notional": "0.0000",
    "average_price": null,
    "last_executed_at": null,
    "executions": []
  }
}
```

### 9. Open / recent orders

`GET /api/orders?status=open&status=partially_filled&limit=20`

Response example:

```json
{
  "items": [
    {
      "id": "<order_id>",
      "user_id": "<demo_user_id>",
      "player_id": "<illiquid_player_id>",
      "side": "buy",
      "quantity": "1.0000",
      "filled_quantity": "0.0000",
      "remaining_quantity": "1.0000",
      "max_price": "78.0000",
      "currency": "credit",
      "reserved_amount": "78.0000",
      "status": "open",
      "hold_transaction_id": "<ledger_transaction_id>",
      "created_at": "2026-03-11T19:25:40.911202",
      "updated_at": "2026-03-11T19:25:40.925562",
      "execution_summary": {
        "execution_count": 0,
        "total_notional": "0.0000",
        "average_price": null,
        "last_executed_at": null,
        "executions": []
      }
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

Notes:

- omit `status` to get recent orders for the current user
- repeat `status` to combine filters, for example `status=open&status=partially_filled`

### 10. Wallet balances

`GET /api/wallets/summary`

Response example:

```json
{
  "available_balance": "1200.0000",
  "reserved_balance": "0.0000",
  "total_balance": "1200.0000",
  "currency": "credit"
}
```

### 11. Portfolio holdings-only

`GET /api/portfolio`

Response example:

```json
{
  "holdings": [
    {
      "player_id": "<rising_player_id>",
      "quantity": "1.0000",
      "average_cost": "136.5000",
      "current_price": "136.5000",
      "market_value": "136.5000",
      "unrealized_pl": "0.0000",
      "unrealized_pl_percent": "0.0000"
    }
  ]
}
```

### 12. Portfolio holdings + cash snapshot

`GET /api/portfolio/snapshot`

Legacy alias:

- `GET /portfolio`

Response example:

```json
{
  "user_id": "<demo_user_id>",
  "currency": "credit",
  "available_balance": "1200.0000",
  "reserved_balance": "0.0000",
  "total_balance": "1200.0000",
  "holdings": [
    {
      "player_id": "<rising_player_id>",
      "quantity": "1.0000",
      "average_cost": "136.5000",
      "current_price": "136.5000",
      "market_value": "136.5000",
      "unrealized_pl": "0.0000",
      "unrealized_pl_percent": "0.0000"
    }
  ]
}
```

### 13. Portfolio summary

`GET /api/portfolio/summary`

Response example:

```json
{
  "total_market_value": "248.1700",
  "cash_balance": "1200.0000",
  "total_equity": "1448.1700",
  "unrealized_pl_total": "0.0000",
  "realized_pl_total": "0.0000"
}
```

## Known Demo Assumptions

- Player IDs and order IDs are generated per database rebuild. Resolve real IDs from `/api/market/players` before calling detail routes.
- The demo market uses synthetic simulation users to provide seeded bids, asks, and trade prints.
- `/api/portfolio` is holdings-only. `/api/portfolio/snapshot` is the standardized combined cash-plus-holdings response. `/portfolio` remains as a backward-compatible alias for that snapshot response.
- `movement_pct` on market list and detail comes from the valuation snapshot pipeline. `day_change` and candle data come from the replayed market engine. They should not be assumed to be identical.
- Fresh demo seeds usually start with sparse candle history. Run extra simulation ticks if the UI needs deeper charts immediately.
- If simulation ticks are run from a separate CLI process, restart the demo simulation server so ticker and candle projections replay the latest persisted trade history.

## Blocking Gaps

No hard blockers remain for the requested MVP screens.

Non-blocking follow-up items:

- The login route is `/auth/login` rather than `/api/auth/login`.
- There is still no dedicated aggregated dashboard endpoint that combines market list, ticker, wallet, and portfolio into one payload; the MVP uses the endpoint set above.
