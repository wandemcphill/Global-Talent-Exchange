# Match Lifecycle Runbook

## What is safe to replay

- `match_simulation` jobs are idempotent by fixture id, match date, and window.
- `notification` jobs are idempotent by template key, resource id, and audience.
- `payout_settlement` jobs are idempotent by competition, date, and source scope.
- `bracket_advancement` jobs are idempotent by competition, stage, and source fixture.

## Local recovery steps

1. Confirm the queue event exists in `app.state.event_publisher.published_events`.
2. Confirm the queue record exists in `app.state.competition_queue_publisher.list_published(...)`.
3. If replay detail is missing, inspect whether `competition.replay.archived` fired.
4. If notifications are missing, inspect whether `competition.notification` fired for the relevant `template_key`.
5. If league progression is missing, inspect:
   - `competition.match.standings.updated`
   - `competition.season.settlement.completed`
6. If cup progression is missing, inspect `competition.match.advancement.requested`.

## Production alert suggestions

- Queue lag above target for `match_simulation`
- Replay archive write failures
- Notification dead-letter growth
- Duplicate idempotency key collision spikes
- Missing `execution.completed` within expected SLA after `match_simulation.queued`

## Rebuild strategy

- Rebuild replay summaries from archived replay payloads or the durable match lifecycle event stream.
- Rebuild standings and qualification from competition event stores, not from notification history.
- Re-drive notification fan-out only from durable lifecycle events with original idempotency keys preserved.
