# World clock and autonomous fixture execution

## Clock contract

GTEX has one persisted world clock in `world_clock_state` (the `default` row). Its persisted real-world epoch, virtual start time, progression rate, pause state, and months-per-season setting are shared by API and worker processes. A process restart must not reset this clock.

`GTE_WORLD_CLOCK_PROGRESSION_RATE` controls virtual seconds per real second. The current default is `1.0` (one-to-one elapsed time); this is a configuration default, **not** a claim that GTEX has an accelerated time economy. No accelerated rate or season-length rule should be introduced without an authoritative product decision.

When `GTE_WORLD_CLOCK_VIRTUAL_START_DATE` is unset, a newly initialized clock anchors to the current UTC instant. That keeps newly scheduled calendar-date fixtures comparable to the virtual clock under the one-to-one default. If an explicit ISO date is supplied, the new virtual clock starts at midnight UTC on that date. That override is intentional: operators must ensure competition kickoff dates use the same virtual calendar before enabling execution. Existing persisted clock rows are not silently rewritten when configuration changes.

`GTE_WORLD_CLOCK_VIRTUAL_MONTHS_PER_SEASON` controls the season-age mapping. It is persisted into the clock row and used for virtual-age metadata; changing it is a game-rule decision and should be planned, not casually changed in production.

## Fixture execution

The autonomous scanner finds scheduled matches, resolves an authoritative kickoff from `scheduled_at` or the supported match-date/window fields, and excludes fixtures whose kickoff cannot be resolved or is still in the future. Execution goes through the canonical match simulation and lifecycle path. Strict persisted-squad resolution is enabled in production; there is no synthetic-squad fallback for missing production squads.

A fixture attempt runs inside a database savepoint so partial result/event/replay/settlement writes roll back together on a failed attempt. Failed fixtures remain retryable and have attempt/error metadata recorded. The scanner reports `success`, `partial_failure`, or `failure` according to the outcomes, and the worker logs failed-only cycles as errors rather than quietly treating them as idle.

When Kafka brokers are absent and autonomous execution is enabled, `gtex-simulation-worker` polls the database on `GTE_AUTONOMOUS_FIXTURE_INTERVAL_SECONDS`. Row locking is used on PostgreSQL to prevent concurrent workers from claiming the same due fixture. The configured Render services and CI checks do not, by themselves, prove production end-to-end execution: production verification still requires evidence from the deployed clock row, worker health/logs, persisted results, standings, and idempotent settlement.

## Owner-console simulation ticks

The owner-console simulation tick is scheduled by `process_due_owner_world_ticks()`, which compares each active club's persisted `last_world_tick_date` with the current virtual date. The autonomous database-polling simulation worker runs this in its own transaction/session after the canonical fixture scan. It does not depend on the owner opening the control centre. Owner visits may trigger the same catch-up logic, but cannot advance an isolated club ahead of the shared virtual calendar.

Catch-up is bounded per cycle. Backlogged clubs remain eligible on later cycles, and each day is isolated in a database savepoint so a failed club-day can be retried without rolling back another club's successful day. PostgreSQL row locks avoid concurrent worker/request ticks for the same club. SQLite tests do not prove PostgreSQL lock behavior or production worker health; those require separate verification.

Legacy owner-console states only tracked a local `world_day` and wall-clock `last_tick_at`. Their historical world dates cannot be reconstructed honestly. The first scheduler pass preserves `world_day` and anchors previously ticked states to the current shared world date instead of replaying fabricated history. New active states with no tick receive one initial scheduled tick. Academy intake has its own persisted sequence, so an owner decision to request an intake does not advance the world date or private simulation day.

## Operational checks

- Confirm the `world_clock_state` row exists and inspect the persisted UTC epoch, virtual start, rate, and pause state.
- Inspect autonomous-worker logs for scan cycles, failed fixture attempts, and retry metadata.
- Verify the oldest overdue fixture and execution counts with the service health telemetry.
- Run a due fixture through canonical execution in an isolated test database; verify the persisted result, match events/replay, standings, completion, and settlement are consistent and idempotent.
- Do not claim live Render validation unless the deployed worker and actual persisted result/settlement path were observed.
