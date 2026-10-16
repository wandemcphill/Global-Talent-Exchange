# GTEX Creator Foundation Runbook

## Scope

This runbook records the merged backend foundation for:

- creator foundation and account provisioning
- creator league core
- club-social
- creator monetization
- creator fan engagement

This is a documentation-only lane. Do not use this file as approval to edit product code or rewrite migrations.

## Merge order

Apply or verify the staged merge in this order:

1. Thread A + Thread B
2. Club-Social isolated slice
3. Thread C
4. Thread D

## Observed migration chain

The following merge-pack revisions are present in `backend/migrations/versions/`:

- `20260316_0012_thread_a_creator_league_core.py`
- `20260316_0012b_creator_account_system.py`
- `20260316_0013_merge_creator_heads.py`
- `20260316_0014_thread_c_creator_broadcast_revenue.py`
- `20260317_0015_thread_d_creator_fan_engagement.py`

Observed from this workspace on `2026-03-17`:

- `python -m alembic -c backend/migrations/alembic.ini heads` -> `20260317_0015 (head)`
- `python -m alembic -c backend/migrations/alembic.ini current` -> `20260316_0013 (mergepoint)`

The local SQLite database in this workspace has not yet been advanced through Thread C and Thread D. Run `upgrade head` before validating those routes against the local app database.

## Backend surfaces now present

- Creator foundation and account system:
  - `/creator`
  - `/api/creator`
  - `/admin/creator`
  - `/api/admin/creator`
  - email/phone verification, creator applications, admin review, creator-card inventory/listing/buy/swap/loan flows
- Creator league core:
  - `/creator-league`
  - config, tiers, reset, seasons, pause, standings, live priority
- Club-Social isolated slice:
  - `/api/clubs/{club_id}/challenges`
  - `/api/challenges/{challenge_id}/publish`
  - `/api/challenges/{challenge_id}/accept`
  - `/api/challenges/{challenge_id}/links`
  - `/api/challenges/{challenge_id}/share-events`
  - `/api/clubs/{club_id}/identity/metrics`
  - `/api/matches/{match_id}/reactions`
  - `/api/clubs/{club_id}/rivalries`
  - `/api/rivalries/matches`
- Creator monetization:
  - `/media-engine/creator-league/...`
  - `/admin/media-engine/creator-league/...`
  - `/sponsorship`
  - `/admin/sponsorship`
  - creator broadcast modes, match access quotes, broadcast purchase, season passes, gifts, analytics, settlement, highlight-share exports
- Creator fan engagement:
  - `/community/digest`
  - `/community/watchlist`
  - `/community/live-threads`
  - `/community/private-messages/...`
  - `/community/creator-matches/...`
  - `/community/creator-clubs/...`
  - `/community/fan-groups/...`
  - `/community/fan-competitions/...`

## Validation commands

Run from the repository root:

```powershell
python -m alembic -c backend/migrations/alembic.ini heads
python -m alembic -c backend/migrations/alembic.ini current
python -m alembic -c backend/migrations/alembic.ini history --verbose
python -m alembic -c backend/migrations/alembic.ini upgrade head
python -m pytest backend/tests/persistence/test_migrations.py -q
python -m pytest backend/tests/creator_league -q
python -m pytest backend/tests/creator backend/tests/player_cards/test_card_access_service.py -q
python -m pytest backend/tests/club_social -q
python -m pytest backend/tests/media_engine/test_creator_broadcast_service.py backend/tests/media_engine/test_highlight_share_service.py backend/tests/sponsorship_engine/test_club_sponsor_offer_service.py -q
python -m pytest backend/tests/community_engine -q
```

## Evidence recorded in this docs lane

- `backend/tests/persistence/test_migrations.py -q` -> `1 passed, 4 warnings in 24.50s`
- `backend/tests/creator_league -q` -> `6 passed, 4 warnings in 17.79s`
- `backend/tests/creator backend/tests/player_cards/test_card_access_service.py -q` -> `9 passed, 4 warnings in 140.63s`
- `backend/tests/club_social -q` -> `4 passed, 4 warnings in 11.19s`
- `backend/tests/media_engine/test_creator_broadcast_service.py backend/tests/media_engine/test_highlight_share_service.py backend/tests/sponsorship_engine/test_club_sponsor_offer_service.py -q` -> `8 passed, 4 warnings in 23.28s`
- `backend/tests/community_engine -q` -> `8 passed, 4 warnings in 13.10s`

All targeted suites above emitted the same four Pydantic v2 deprecation warnings from `backend/app/governance_engine/schemas.py` and `backend/app/dispute_engine/schemas.py`.

## Operational caveats

- Validation in this docs lane was SQLite-backed. `backend/tests/persistence/test_migrations.py` provisions a temporary `sqlite+pysqlite` database, and `alembic current` inspected the local SQLite app database.
- Creator season passes are creator-league scoped. The implementation rejects non-creator-league season or club combinations and marks access metadata with `creator_league_only`.
- Creator tactical advice is advisory only. The backend stores and surfaces the advice but explicitly marks it with `authority = advisory_only`.
- Rivalry outputs are additive signals. The backend computes output rows and target audiences, but this docs lane did not verify a downstream notification delivery worker or push transport.
- Creator routes are mounted both with and without `/api`. Frontend clients should standardize on one mount during wiring.
