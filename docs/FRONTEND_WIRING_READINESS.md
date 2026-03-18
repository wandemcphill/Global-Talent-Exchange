# GTEX Frontend Wiring Readiness

## Purpose

This note tells later frontend threads which backend subsystems now exist, which route families are available, and which areas still need UI wiring.

## Backend subsystems now available

- Creator onboarding and provisioning:
  - creator contact verification
  - creator application submit/read/admin review
  - creator club provisioning persistence
- Creator card systems:
  - creator-card inventory
  - public creator-card listings
  - buy, swap, loan, and return flows
  - player-card access services
- Creator league control plane:
  - league config
  - tier add/update/delete
  - season create/read/pause
  - standings and live priority
- Creator monetization:
  - creator-league broadcast mode catalog
  - match access quotes
  - match broadcast purchase
  - season pass purchase and self-list
  - match gifting
  - creator analytics dashboard
  - admin settlement
  - highlight-share export generation
- Fan engagement:
  - creator-match chat room and message feed
  - tactical advice feed and submit
  - fan wall
  - rivalry signal list
  - creator-club follow state
  - fan groups
  - fan competitions
- Club-Social:
  - challenge creation, publish, accept, and share links
  - club identity metrics
  - rivalry list/detail
  - rivalry match recording
  - match reactions feed

## Route families available to wire

- Creator foundation:
  - `/creator/...`
  - `/api/creator/...`
  - `/admin/creator/...`
  - `/api/admin/creator/...`
- Creator league:
  - `/creator-league/...`
- Creator monetization and media:
  - `/media-engine/creator-league/...`
  - `/admin/media-engine/creator-league/...`
  - `/media-engine/share-templates`
  - `/media-engine/share-exports`
  - `/media-engine/downloads`
- Fan engagement:
  - `/community/creator-matches/...`
  - `/community/creator-clubs/...`
  - `/community/fan-groups/...`
  - `/community/fan-competitions/...`
- Club-Social:
  - `/api/clubs/{club_id}/challenges`
  - `/api/challenges/...`
  - `/api/clubs/{club_id}/identity/metrics`
  - `/api/clubs/{club_id}/rivalries`
  - `/api/matches/{match_id}/reactions`
  - `/api/rivalries/matches`

## Areas that still need frontend wiring

- Creator application and admin-review screens for the new creator account workflow
- Creator-card listing, swap, loan, and return flows
- Creator league configuration, season admin, standings, and live-priority views
- Creator monetization purchase flows for broadcast access, season passes, gifts, analytics, and settlement surfaces
- Creator match overlay experiences for chat, tactical advice, fan wall, and rivalry signal display
- Club-Social challenge, identity-metrics, reactions, and rivalry screens

## Contract caveats for frontend work

- Creator season passes are scoped to creator-league clubs and creator-league seasons only. The backend rejects non-creator-league club-season combinations and marks access with `creator_league_only`.
- `/community/...` is the mounted family for fan-engagement features. These routes are not nested under `/media-engine` or `/creator`.
- Rivalry outputs are additive signals, not end-to-end notification delivery. The backend computes and stores signal rows, including notification-target metadata, but this docs lane did not verify a delivery transport.
- Creator tactical advice is advisory only and is surfaced with `authority = advisory_only`.
- Creator routes are mounted twice: once directly under `/creator` and once under `/api/creator`. Frontend work should choose one canonical mount and stay consistent.
- Club-Social routes are mounted directly under `/api/...`; there is no separate `/club-social` prefix to target.

## Readiness caveat

The merged migration files through `20260317_0015` are present, but the local SQLite database inspected in this workspace was still at `20260316_0013 (mergepoint)` when this note was written. Frontend/API integration against a local app instance should run `python -m alembic -c backend/migrations/alembic.ini upgrade head` first.
