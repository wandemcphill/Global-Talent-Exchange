# ChatGPT Calendar + Lifecycle Engine Pass

This pass adds a larger calendar and lifecycle surface to GTEX so the platform can treat competitions as scheduled operating events instead of loose standalone records.

## Added
- `backend/app/models/calendar_engine.py`
  - `CalendarSeason`
  - `CalendarEvent`
  - `CompetitionLifecycleRun`
- `backend/app/calendar_engine/`
  - `schemas.py`
  - `service.py`
  - `router.py`
  - `__init__.py`
- `backend/migrations/versions/20260314_0029_calendar_engine.py`
- `backend/tests/calendar_engine/test_calendar_engine_placeholder.py`

## Wiring
- `backend/app/modules.py`
  - registered public/admin calendar engine routers
  - added startup seeding for default season
- `backend/app/models/__init__.py`
  - registered new calendar/lifecycle models

## Capability Highlights
- season registry with default GTEX 2026 season
- calendar event publishing
- pause-status dashboard for GTEX-wide blackout windows
- hosted competition launch into a lifecycle run
- national team competition launch into a lifecycle run
- story feed generation for launches
- persisted lifecycle summaries with generated rounds/matches and scheduled dates

## Notes
- This pass is intentionally rules-driven and works as orchestration glue around existing hosted and national competition surfaces.
- Runtime validation was not fully executed in this container because the Python environment is incomplete for the full app dependency graph.
