# Match Lifecycle Backend Notes

## Local wiring

The local execution path is intentionally helper-based because this thread does not own `backend/app/main.py`.

- `ensure_local_match_execution_runtime(app)` attaches:
  - `competition_queue_publisher`
  - `match_dispatcher`
  - `match_execution_worker`
  - `league_match_execution`
- `ensure_replay_archive(app)` attaches the replay archive subscriber.

When both helpers are active, queue publication immediately drives the full local lifecycle.

## Lifecycle events

The worker now emits these canonical events in addition to the existing queue and replay events:

- `competition.match.execution.started`
- `competition.match.simulation.completed`
- `competition.match.commentary.generated`
- `competition.match.result.generated`
- `competition.match.standings.updated`
- `competition.match.advancement.requested`
- `competition.match.advancement.dispatched`
- `competition.match.replay.prepared`
- `competition.match.notifications.dispatched`
- `competition.match.settlement.dispatched`
- `competition.match.execution.completed`
- `competition.match.execution.failed`

Existing compatibility events remain authoritative for current integrations:

- `competition.match.scheduled`
- `competition.match.live`
- `competition.replay.archived`
- `competition.notification`
- `competition.season.settlement.completed`

## Queue contracts

`BracketAdvancementJob` now supports optional result metadata so cup pipelines can carry the winner and scoreline across the queue seam without modifying competition rules:

- `winner_club_id`
- `home_goals`
- `away_goals`
- `decided_by_penalties`

League fixtures still update standings inline through `LeagueSeasonLifecycleService`. Cup fixtures emit `competition.match.advancement.requested` for downstream competition consumers.

## Local developer expectations

- Queue publication is synchronous in local mode.
- Notification dispatch happens immediately after queue publication because the local worker is subscribed to queue events.
- Replay archive updates are persisted from the same event stream, so `replays/*` endpoints are available as soon as simulation completes.
- Settlement dispatch is emitted only when a league season reaches `completed`.
