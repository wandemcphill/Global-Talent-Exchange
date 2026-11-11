# Project: GTEX 3D Football Engine

## Goals
- Stable Unity builds (Windows first)
- 15-minute match simulation
- Event-driven match system
- Lightweight performance
- Matchday 3D visual bar: Football Manager 23 class (not Flutter 2.5D)

## Rules
- Never break batchmode builds
- Avoid heavy assets unless necessary
- Prioritize performance over realism
- Keep systems modular
- Canonical FM23-class 3D path is `GTEX_OriginalVisualRuntime` + `VisualBridge` only
- Do not ship canvas/2.5D as the product match visual
- See `Docs/GTEX_VISUAL_QUALITY_BAR.md`

## Key Files
- `Assets/Scenes/GTEX_OriginalVisualRuntime.unity`
- `Assets/Code/GTEX/VisualBridge/`
- `Assets/Code/GTEX/GtexMatchRuntime.cs`
- `Assets/Code/Editor/GtexBuildTools.cs`

## Build Command
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe' `
  -batchmode -quit -nographics `
  -buildTarget StandaloneWindows64 `
  -projectPath 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration' `
  -executeMethod FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine `
  -logFile 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_test_migration_windows_build.log'
```

## Execution Order
- Follow `GTEX_TASKS.md` for implementation order
- Only implement phases marked `READY`
- Do not start blocked phases early
- Use `GTEX_PHASED_PROMPTS.md` as the source of truth for rewritten GTEX prompts

## Cursor Cloud specific instructions

The local product loop is the Python API plus the Flutter web app. Unity batch builds stay on Windows (`Gtex_Test_Migration`, Unity 6000.3) and are not installed here. The Android SDK is not installed; use `flutter test` and the web device.

- Python is `python3.14`. The virtualenv is `.venv` at the repo root. `pytest==9.1.1` is installed there because it is not listed in `backend/requirements.txt`.
- `backend/scripts/dev.py` defaults `--database-url` to an empty string. Pass `--database-url sqlite+pysqlite:////workspace/gte_backend.db` (or set `DATABASE_URL` to that value and pass it explicitly).
- Seed once: `.venv/bin/python backend/scripts/dev.py rebuild-demo-market --seed 20260311 --database-url "$DATABASE_URL"`.
- Boot the API with `runserver` and without `--demo-simulation`, on `0.0.0.0:8000`, with `--no-reload`. That process mounts `/health` and the CORS policy the Flutter web client needs. `--demo-simulation` serves `app.simulation.app_factory`, which does not answer browser preflight, so the web app cannot log in against it.
- Flutter web: from `frontend/`, `flutter run -d web-server --web-hostname 0.0.0.0 --web-port 8080 --dart-define=GTE_API_BASE_URL=http://127.0.0.1:8000 --dart-define=GTE_BACKEND_MODE=live`. Open `http://127.0.0.1:8080/auth/login`. Demo accounts are in `docs/RUNBOOK_LOCAL_DEV.md`.
- Checks that passed in this environment: `GET /health`, `POST /api/v2/auth/login` as `seed.fan@gte.local`, `flutter test test/widget_test.dart`, and `pytest backend/tests/app/test_health_root.py`.
- `npm run lint:js` still reports existing issues under `services/player-ingestion` and `qa/playwright`. `.venv` is excluded so the virtualenv does not add more.

## Football Legends & Market Invariants (STRICT GOVERNANCE)
All agents working on GTEX must adhere to the following rules permanently:
1. **1-of-1 In-Game Legend Assets**:
   - Every single legend (ex-players from the 50s through 2000s and recently retired players) MUST have `real_player_tier = 'legend'`, `is_tradable = true`, and exactly 1 share in the market (`total_shares = 1`, `released_shares = 1`).
   - They MUST display the badge `ICON · 1 OF 1` in the UI.
   - When a legend unit is purchased, NO additional shares may be minted.
2. **Duplicate Player Elimination**:
   - No duplicate copies of legends are permitted in the game.
   - Specific retired duplicate IDs:
     - `106bbc0a-a8b3-408e-b856-a4dad15799fd` (Eric Cantona fake portrait, retired in favor of authentic `b421109b-b268-49cc-b2cb-0fe6cf40ce4a`)
     - `55f70b9b-dae9-4a55-8721-ccf9bdaa0154` (Andrés Iniesta duplicate, retired in favor of authentic `b496213b-ff42-4feb-878f-55389ae7a50c`)
     - `0704b985-6e51-49fc-bf74-45820da69183` (Luís Figo duplicate, retired in favor of authentic `5220d191-0220-4d93-87c2-e47d15929d7d`)
     - `862d907b-917a-4508-a19d-da3481ae778d` (Émerson duplicate, retired in favor of authentic `88580a67-b712-4c17-a69d-579d44f9fb69`)
   - All duplicate records have `real_player_tier = 'archived_duplicate'`, `is_tradable = false`, and are excluded from all search queries, markets, and read models.
3. **Active Players Are NOT Legends**:
   - Active superstars (Harry Kane, Kylian Mbappé, Jude Bellingham, Vinícius Júnior, Rodri, Thibaut Courtois, etc.) are active players, NOT legends.
   - They must maintain `real_player_tier = 'marquee'`, `legendary_profile_id = NULL`, and 200 units available (`total_shares = 200`, `released_shares = 200`) so they can be traded multiple times.
4. **Ratings (GSI) Calibration Rules**:
   - **Only 4 players in history are rated 98**: Pelé, Diego Maradona, Cristiano Ronaldo, and Lionel Messi.
   - Lionel Messi and Cristiano Ronaldo maintain peak age (age 20).
   - Tier 2 Pantheon (rating 96): Ronaldo Nazário (R9), Zinedine Zidane, Ronaldinho, Marco van Basten, Alfredo Di Stéfano, Paolo Maldini.
   - Ballon d'Or winners and top podium finishers are calibrated across 90-95.
   - Minimum rating floor: **No legend may be rated below 80**. The floor for all legends is **80 on the dot**.
   - No uniform clumping: ratings are spread across 80-96 according to individual achievements, international tournaments, and career honors.

## Competition Entry (STRICT)
Every GTEX competition is free to enter. Club competitions and national-team competitions. Nobody pays a buy-in, an entry fee, or a league tier fee.
- National team: the user rents the squad. That rental is the only cost. Entering the competition itself is free.
- Club: the user already owns the club and already bought the players. Entering the league is a right, not a purchase.
- Division is the only difference: 1st, 2nd, 3rd, and on down to foundation. A new club starts in foundation and moves only by promotion and relegation. Money never chooses the division.
- Prize coin is funded by GTEX. It is never calculated as buy-in times the number of clubs, and it is never taken from the entrants.
