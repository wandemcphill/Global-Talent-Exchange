# GTEX Release Gate Checklist

Use this after setup from `RUNBOOK_LOCAL_DEV.md` and before packaging or handoff.

## Coordination guardrails

- Migration freeze is active. Do not touch `backend/migrations/versions/*`.
- Current merge-lane migration head note: `20260316_0008`.
- GTEX MERGE owns `frontend/test/competitions/competition_discovery_test.dart`, the UI text it validates, `frontend/android/*`, and APK retry work.

## Backend gate

- [ ] `python -m pip install -r backend/requirements.txt`
- [ ] `python backend/scripts/dev.py rebuild-demo-market --seed 20260311`
- [ ] `python backend/scripts/dev.py runserver --demo-simulation --seed 20260311`
- [ ] `/health`, `/ready`, `/version`, and `/diagnostics` return 200
- [ ] `python -m pytest backend/tests/persistence/test_migrations.py -q`
- [ ] `python -m pytest backend/tests/regen -q`
- [ ] `python -m pytest backend/tests/club_ops/test_scouting_service.py -q`
- [ ] `python -m pytest backend/tests/players/test_player_lifecycle.py -q`
- [ ] `python -m pytest backend/tests/competitions/test_competition_lifecycle.py -q`

## Frontend gate

- [ ] `cd frontend`
- [ ] `flutter pub get`
- [ ] `flutter analyze`
- [ ] `flutter test`
- [ ] `flutter test test/gte_frontend_app_test.dart`
- [ ] `flutter test test/club_ops/scouting_dashboard_test.dart`
- [ ] `flutter test test/competitions/competition_create_flow_test.dart`
- [ ] `flutter test test/competitions/competition_detail_test.dart`
- [ ] `flutter test test/competitions/competition_discovery_test.dart`
- [ ] `flutter build apk --debug`

## Known remaining issues

- Environmental: Flutter SDK is not installed in the current audit environment, so frontend analyze, test, and build steps still need to be run locally.
- Environmental: `frontend/android/gradle/wrapper/gradle-wrapper.jar` may need regeneration via `flutter create . --platforms=android`.
- Environmental: Windows `mergeDebugNativeLibs` and `libflutter.so` failures are usually stale file locks; use `ANDROID_BUILD_TROUBLESHOOTING.md`.
- Code follow-up: `python -m pytest backend/tests/smoke/test_demo_smoke.py -q` currently fails because the smoke test expects portfolio currency `credit`, while the current API response returns `coin`.
- Merge-owned follow-up: any competition discovery text mismatch belongs to GTEX MERGE and should be tracked there instead of fixed from a parallel thread.
