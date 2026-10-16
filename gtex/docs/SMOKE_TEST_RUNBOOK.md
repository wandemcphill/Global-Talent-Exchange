# GTEX Smoke Test Runbook

## Backend targeted merge suites

Run these from the repository root. If you are validating the local app database instead of the isolated test database, migrate to head first.

- `python -m pytest backend/tests/persistence/test_migrations.py -q`
  Docs-lane result on `2026-03-17`: `1 passed, 4 warnings in 24.50s`
- `python -m pytest backend/tests/creator_league -q`
  Thread A result on `2026-03-17`: `6 passed, 4 warnings in 17.79s`
- `python -m pytest backend/tests/creator backend/tests/player_cards/test_card_access_service.py -q`
  Thread B result on `2026-03-17`: `9 passed, 4 warnings in 140.63s`
- `python -m pytest backend/tests/club_social -q`
  Club-Social result on `2026-03-17`: `4 passed, 4 warnings in 11.19s`
- `python -m pytest backend/tests/media_engine/test_creator_broadcast_service.py backend/tests/media_engine/test_highlight_share_service.py backend/tests/sponsorship_engine/test_club_sponsor_offer_service.py -q`
  Thread C result on `2026-03-17`: `8 passed, 4 warnings in 23.28s`
- `python -m pytest backend/tests/community_engine -q`
  Thread D result on `2026-03-17`: `8 passed, 4 warnings in 13.10s`

All targeted suites above emitted the same four Pydantic v2 deprecation warnings from:

- `backend/app/governance_engine/schemas.py`
- `backend/app/dispute_engine/schemas.py`

## Historical smoke notes not revalidated in this lane

- `python -m pytest backend/tests/smoke/test_demo_smoke.py -q` was not re-run from this docs thread.
- Previous local docs recorded a `coin` vs `credit` mismatch in `test_seeded_portfolio_works`; treat that note as historical until the suite is re-run.

## Backend demo and API checks

With the backend running:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/diagnostics
curl "http://127.0.0.1:8000/api/market/players?limit=5"
```

Recommended merge-pack API spot checks after migrating the local DB to head:

```powershell
curl http://127.0.0.1:8000/creator-league
curl http://127.0.0.1:8000/media-engine/creator-league/broadcast-modes
curl http://127.0.0.1:8000/community/digest
curl http://127.0.0.1:8000/api/clubs/<club_id>/challenges
curl http://127.0.0.1:8000/api/clubs/<club_id>/rivalries
```

## Frontend smoke commands

Flutter is not installed in this audit environment, so the commands below still need local execution on a machine with the Flutter SDK.

```powershell
cd frontend
flutter analyze
flutter test
flutter test test/gte_frontend_app_test.dart
flutter test test/club_ops/scouting_dashboard_test.dart
flutter test test/competitions/competition_create_flow_test.dart
flutter test test/competitions/competition_detail_test.dart
flutter test test/competitions/competition_discovery_test.dart
```

## Manual release smoke flow

1. Boot the backend and frontend against the same local API base URL.
2. Login as a standard user.
3. Verify creator application and creator-card inventory screens if they are wired in the current client.
4. Verify creator-league overview, standings, and any admin control-plane screens that are wired.
5. Verify creator broadcast access, season pass, gift, and analytics flows if wired.
6. Verify creator-match chat, tactical advice, fan wall, and rivalry-signal presentation if wired.
7. Verify club-social challenge and rivalry paths if wired.
8. If you need exchange realism data, use the seeded demo market flow from `RUNBOOK_LOCAL_DEV.md`.

## Merge-owned smoke lane

`frontend/test/competitions/competition_discovery_test.dart` and the UI text it validates are owned by GTEX MERGE in this release window. If discovery text mismatches remain, record them as a blocker and do not resolve them from a parallel thread.
