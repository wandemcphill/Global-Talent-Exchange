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
