# GTEX Backend Merge Status

## Snapshot

Observer lane: `THREAD M1-DOCS`

Snapshot date: `2026-03-17`

This file records what is present in the workspace and what was directly verified from this documentation-only thread.

## Merge sequence in scope

1. Thread A creator league core
2. Thread B creator account, provisioning, and card system
3. Club-Social isolated slice
4. Thread C creator broadcast, season pass, revenue, and analytics
5. Thread D fan engagement, chat, tactical advice, fan wall, and rivalry outputs

Operational merge order for validation remains:

1. Thread A + Thread B
2. Club-Social
3. Thread C
4. Thread D

## Migration status

Observed migration files:

- `20260316_0012_thread_a_creator_league_core.py`
- `20260316_0012b_creator_account_system.py`
- `20260316_0013_merge_creator_heads.py`
- `20260316_0014_thread_c_creator_broadcast_revenue.py`
- `20260317_0015_thread_d_creator_fan_engagement.py`

Observed commands and results:

- `python -m alembic -c backend/migrations/alembic.ini heads` -> `20260317_0015 (head)`
- `python -m alembic -c backend/migrations/alembic.ini current` -> `20260316_0013 (mergepoint)`

Current implication:

- the merged migration chain is present in the repository
- the local SQLite database inspected in this workspace is not yet migrated through Thread C and Thread D

## Subsystems observed in the backend tree

- Creator foundation:
  - creator application workflow
  - contact verification
  - creator club provisioning tables
  - creator squad and regen support
- Creator card systems:
  - creator-card ownership, listings, sales, swaps, and loans
  - player-card access services and player-card market routes
- Creator league core:
  - creator league config
  - creator league tiers
  - creator league seasons and season tiers
  - standings and live priority endpoints
- Club-Social:
  - club-vs-club challenge pages
  - challenge share links and share-event capture
  - club identity metrics refresh
  - rivalry detail and rivalry match recording
- Creator monetization:
  - broadcast mode catalog
  - match access quotes and purchases
  - season passes
  - creator gifts
  - per-match analytics
  - revenue settlement
  - highlight export templates and share exports
- Creator fan engagement:
  - creator-match chat room and messages
  - tactical advice
  - fan wall aggregation
  - creator-club follow state
  - fan groups and fan competitions
  - rivalry signal outputs

## Route families observed

- `/creator`, `/api/creator`, `/admin/creator`, `/api/admin/creator`
- `/creator-league`
- `/player-cards`
- `/media-engine`, `/admin/media-engine`
- `/community`
- `/sponsorship`, `/admin/sponsorship`
- direct `/api/...` club-social routes for challenges, metrics, reactions, and rivalries

## Verification executed from this lane

- `python -m pytest backend/tests/persistence/test_migrations.py -q` -> passed
- `python -m pytest backend/tests/creator_league -q` -> passed
- `python -m pytest backend/tests/creator backend/tests/player_cards/test_card_access_service.py -q` -> passed
- `python -m pytest backend/tests/club_social -q` -> passed
- `python -m pytest backend/tests/media_engine/test_creator_broadcast_service.py backend/tests/media_engine/test_highlight_share_service.py backend/tests/sponsorship_engine/test_club_sponsor_offer_service.py -q` -> passed
- `python -m pytest backend/tests/community_engine -q` -> passed

## Not revalidated here

- full frontend wiring
- Flutter analyze/test/build
- non-SQLite database engines
- end-to-end local API behavior after migrating the workspace database from `20260316_0013` to head
