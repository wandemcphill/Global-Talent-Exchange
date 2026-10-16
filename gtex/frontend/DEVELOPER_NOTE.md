# Frontend Canonicalization Note

## Canonical app path

The exchange MVP boots from:

- `frontend/lib/main.dart`
- `frontend/lib/app/gte_frontend_app.dart`
- `frontend/lib/screens/gte_exchange_shell_screen.dart`

That is the only live app path the tree should treat as canonical.

## Controller and data ownership

- `GteExchangeController` is the canonical UI controller for the MVP.
- `frontend/lib/data/gte_mock_api.dart` is a fixture/data-layer adapter, not a provider-layer file.
- `frontend/lib/data/gte_models.dart` owns the shared typed frontend models.
- `frontend/lib/data/gte_exchange_models.dart` owns market/exchange-specific view models on top of the shared base models.

## Legacy shell

The pre-exchange scouting/demo shell is still kept temporarily under:

- `frontend/lib/legacy/`
- `frontend/test/legacy/`

Those files are legacy-only and should not be used as the MVP boot flow.

## Backend contracts in active use

The canonical exchange scaffold targets these backend routes:

- Auth: `/auth/login`, `/auth/register`, `/api/auth/me`
- Market: `/api/market/players`, `/api/market/players/{player_id}`
- Ticker/candles: `/api/market/ticker/{player_id}`, `/api/market/players/{player_id}/candles`
- Orders: `/api/orders`, `/api/orders/{order_id}`, `/api/orders/{order_id}/cancel`, `/api/orders/book/{player_id}`
- Wallet: `/api/wallets/summary`
- Portfolio: `/api/portfolio`, `/api/portfolio/summary`

## Fixture strategy

`GteMockApi` remains the fixture source for:

- explicit fixture-mode runs
- live-then-fixture fallback when the backend is unavailable or returns unusable payloads
- demo-only flavor that still supplements backend data in the exchange scaffold
