# GTEX Local Development Runbook

## Scope

Use this when bringing up the current GTEX tree locally without changing product code or migrations.

## Backend quick start

Repository root: `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`

No Redis server is required for the local paths below.

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

2. Optional: review `backend/.env.example`. Defaults already point to local SQLite at `gte_backend.db`.
3. Fresh demo market boot:

```powershell
python backend/scripts/dev.py rebuild-demo-market --seed 20260311
python backend/scripts/dev.py runserver --demo-simulation --seed 20260311
```

4. Standard API boot without demo simulation:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

5. Verify the service:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/diagnostics
```

## Seeded accounts

- Demo bootstrap users: `fan@demo.gte.local`, `scout@demo.gte.local`, `admin@demo.gte.local`
- Demo bootstrap password: `DemoPass123`
- Auto-seeded super admin: `vidvimedialtd@gmail.com` / `NewPass1234!`

## Frontend quick start

The Flutter app reads runtime config from `--dart-define`. `frontend/.env.example` is reference-only and is not auto-loaded by the app.

Flutter was not installed in this audit environment, so the commands below still need to be run locally on a machine with the Flutter SDK.

```powershell
cd frontend
flutter pub get
flutter run --dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000 --dart-define=GTE_BACKEND_MODE=liveThenFixture
```

Useful variants:

```powershell
flutter run --dart-define=GTE_BACKEND_MODE=fixture
flutter analyze
flutter test
flutter build apk --debug
```

If `frontend/android/` is incomplete, regenerate the wrapper locally:

```powershell
flutter create . --platforms=android
```

## Deterministic demo data refresh

Use the same seed value when you want repeatable QA data and screenshots.

```powershell
python backend/scripts/dev.py reset-db
python backend/scripts/dev.py migrate
python backend/scripts/dev.py rebuild-demo-market --seed 20260311
python backend/scripts/dev.py seed-demo-liquidity --seed 20260311
python backend/scripts/dev.py simulation-ticks --count 5 --start-tick 1 --seed 20260311
python backend/scripts/dev.py runserver --demo-simulation --seed 20260311
```

Notes:

- `rebuild-demo-market` already resets the SQLite DB, migrates to head, seeds demo users, and adds demo liquidity.
- Restart `runserver --demo-simulation` after running tick commands from another terminal so the in-memory ticker projection replays the updated database state.

## Where to go next

- Migration usage: `BACKEND_MIGRATION_RUNBOOK.md`
- Smoke commands: `SMOKE_TEST_RUNBOOK.md`
- Android cleanup: `ANDROID_BUILD_TROUBLESHOOTING.md`
- Release gate: `LOCAL_BUILD_CHECKLIST.md`
