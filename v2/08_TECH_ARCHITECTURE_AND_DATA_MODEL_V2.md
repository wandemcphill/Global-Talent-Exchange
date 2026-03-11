# Tech Architecture and Data Model V2

## Architecture style
Build for scale but keep launch practical.
Suggested stack:
- Flutter frontend
- FastAPI backend
- PostgreSQL
- Redis
- Celery or equivalent job system
- object storage for media

## Core services
- auth and user service
- player catalog service
- market service
- valuation service
- scouting service
- competitions service
- payments service
- notifications service
- admin service

## Key data entities
- users
- players
- player_cards
- player_market_values
- player_awards
- player_performance_events
- player_transfers
- follows
- watchlists
- shortlists
- transfer_room_entries
- transfer_announcements
- competitions
- competition_entries
- competition_leaderboards
- ledger_accounts
- ledger_entries
- payment_events
- payout_requests
- notifications

## Jobs
Periodic jobs should update:
- player value movement
- GSI movement
- competition leaderboards
- notification digests
- transfer room announcements

## Admin tools
Admin should be able to:
- edit competition entry fees
- edit prize and bonus configuration
- flag suspicious market activity
- manage featured players and featured competitions
- manage announcements
