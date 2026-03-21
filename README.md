# Global Talent Exchange

See also:
- `Docs/README.md`
- `API_DOCUMENTATION.md`
- `DEPLOYMENT_GUIDE.md`
- `ADMIN_SETUP_GUIDE.md`

Local backend workflow for SQLite demos, seeded exchange liquidity, deterministic simulation ticks, and repeatable verification.

## Local setup

Commands below assume:

- repository root: `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`
- Python 3.14
- SQLite for local development
- no Redis server is required for local boot

Use the checked-in backend dependency manifest when you are starting from a clean virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

## Frontend quick start

Flutter commands are run from `frontend/`. The app reads `GTE_API_BASE_URL` and `GTE_BACKEND_MODE` from `--dart-define`; `frontend/.env.example` is a reference file and is not auto-loaded by Flutter.

```powershell
cd frontend
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000 --dart-define=GTE_BACKEND_MODE=live
```

If the Android wrapper is incomplete, regenerate it locally with `flutter create . --platforms=android`.

For the full local setup, smoke-test matrix, migration freeze notes, and Android file-lock recovery steps, use the canonical docs in `Docs/`.

## Fast path

Reset the local SQLite DB, migrate to head, seed demo users/players/holdings, and add demo exchange liquidity:

```powershell
python backend/scripts/dev.py rebuild-demo-market
python backend/scripts/dev.py runserver --demo-simulation
```

This creates:

- a small seeded player universe subset
- precomputed value snapshots and player summaries
- synthetic local-only QA users for market and portfolio checks
- seeded market holdings for the synthetic QA users' `/api/portfolio/snapshot` view
- wallet balances and ledger entries for the synthetic QA users
- seeded buy ladders and sell ladders in the exchange order book
- seeded trade executions for ticker volume/history
- liquid and illiquid player examples for local demos and tests

The demo rebuild command writes the exchange-side state into the database. `runserver --demo-simulation` then replays that seeded market into the in-memory market engine so `/api/market/ticker/{player_id}` shows spread and volume immediately on boot.

## Demo operator runbook

Use the same `--seed` across rebuild, liquidity, ticks, and `runserver --demo-simulation` when you want repeatable QA data and screenshots.

Full clean-room operator workflow:

```powershell
python backend/scripts/dev.py reset-db
python backend/scripts/dev.py migrate
python backend/scripts/dev.py rebuild-demo-market --seed 20260311
python backend/scripts/dev.py seed-demo-liquidity --seed 20260311
python backend/scripts/dev.py simulation-ticks --count 5 --start-tick 1 --seed 20260311
python backend/scripts/dev.py runserver --demo-simulation --seed 20260311
```

Notes:

- `rebuild-demo-market` already resets the SQLite database, migrates to head, seeds demo users/players/holdings, and adds demo liquidity. Use the explicit `reset-db` and `migrate` steps when you want to verify the database lifecycle or recover a dirty local DB.
- `seed-demo-liquidity` is safe to rerun after a rebuild when you want to refresh only the exchange-side order book and trade history.
- If you run tick commands from a separate terminal, restart `runserver --demo-simulation` afterwards so the in-memory ticker projection replays the updated database state.

## Dev commands

Wrapper commands:

```powershell
python backend/scripts/dev.py reset-db
python backend/scripts/dev.py migrate
python backend/scripts/dev.py seed-demo
python backend/scripts/dev.py bootstrap-demo
python backend/scripts/dev.py seed-demo-liquidity
python backend/scripts/dev.py simulation-tick
python backend/scripts/dev.py simulation-ticks
python backend/scripts/dev.py rebuild-demo-market
python backend/scripts/dev.py runserver
python backend/scripts/dev.py test
```

Useful variants:

```powershell
python backend/scripts/dev.py bootstrap-demo --player-count 12 --with-liquidity
python backend/scripts/dev.py seed-demo-liquidity --liquid-player-count 3 --illiquid-player-count 1
python backend/scripts/dev.py simulation-tick --tick-number 1
python backend/scripts/dev.py simulation-ticks --count 5 --start-tick 2
python backend/scripts/dev.py runserver --demo-simulation --host 127.0.0.1 --port 8000 --reload
python backend/scripts/dev.py test backend/tests/integration/test_demo_market_integration.py -q
```

Direct demo bootstrap command:

```powershell
python backend/scripts/bootstrap_demo.py --player-count 24 --with-liquidity
```

## Demo market setup

Fresh local demo:

```powershell
python backend/scripts/dev.py rebuild-demo-market
python backend/scripts/dev.py runserver --demo-simulation
```

If you already have the demo users and player universe loaded, seed only the exchange side:

```powershell
python backend/scripts/dev.py seed-demo-liquidity
python backend/scripts/dev.py runserver --demo-simulation
```

Run one or more deterministic activity ticks:

```powershell
python backend/scripts/dev.py simulation-tick --tick-number 1
python backend/scripts/dev.py simulation-ticks --count 3 --start-tick 2
```

If you run tick commands from a separate terminal, restart `runserver --demo-simulation` afterwards so the in-memory ticker projection replays the new database state.

## Migrations

Coordination note: the current merge-lane migration head is expected to be `20260316_0008`. Parallel threads should inspect and apply migrations only; do not create or rewrite files under `backend/migrations/versions/*` unless migration work is explicitly assigned.

Wrapper:

```powershell
python backend/scripts/dev.py migrate
```

Raw Alembic:

```powershell
python -m alembic -c backend/migrations/alembic.ini upgrade head
```

## Run tests

Targeted demo/bootstrap/simulation checks:

```powershell
python -m pytest backend/tests/ingestion backend/tests/simulation backend/tests/integration -q
```

Broad backend suite:

```powershell
python -m pytest backend/tests
```

Wrapper default:

```powershell
python backend/scripts/dev.py test
```

That default command targets `backend/tests/ingestion`. For a broader backend run, pass the suite explicitly:

```powershell
python backend/scripts/dev.py test backend/tests
```

## Boot the server

Wrapper:

```powershell
python backend/scripts/dev.py runserver
python backend/scripts/dev.py runserver --demo-simulation
```

Raw uvicorn:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Demo-simulation uvicorn factory:

```powershell
python -m uvicorn backend.app.simulation.app_factory:create_demo_simulation_app --factory --host 127.0.0.1 --port 8000 --reload
```

Server URL:

```text
http://127.0.0.1:8000
```

## Example local API calls

Health and readiness:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/version
```

Recent market players:

```powershell
curl "http://127.0.0.1:8000/api/market/players?limit=5"
```

Seeded order book:

```powershell
curl "http://127.0.0.1:8000/api/orders/book/<player-id>"
```

Ticker:

```powershell
curl "http://127.0.0.1:8000/api/market/ticker/<player-id>"
```

Login and capture a bearer token:

```powershell
$token = (
  Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8000/auth/login `
    -ContentType "application/json" `
    -Body '{"email":"seed.fan@gte.local","password":"DemoPass123"}'
).access_token
```

Wallet summary:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/wallets/summary
```

Portfolio snapshot:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/portfolio/snapshot
```

Portfolio holdings-only and summary totals:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/portfolio

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/portfolio/summary
```

Place a buy order against seeded liquidity:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Uri http://127.0.0.1:8000/api/orders `
  -Body '{"player_id":"<player-id>","side":"buy","quantity":1,"max_price":140}'
```

List current user open or recent orders:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri "http://127.0.0.1:8000/api/orders?status=open&status=partially_filled&limit=20"
```

Fetch and cancel an order:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/orders/<order-id>

Invoke-RestMethod `
  -Method Post `
  -Headers @{ Authorization = "Bearer $token" } `
  -Uri http://127.0.0.1:8000/api/orders/<order-id>/cancel
```
