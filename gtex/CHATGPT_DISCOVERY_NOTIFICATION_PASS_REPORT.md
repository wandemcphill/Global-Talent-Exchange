# ChatGPT Discovery + Notification Expansion Pass

This pass added two larger cross-cutting surfaces to the full GTEX project zip:

## 1) Discovery Engine
- saved searches
- featured rails
- `/discovery/home`
- `/discovery/search`
- `/discovery/saved-searches`
- admin featured rail management under `/admin/discovery/featured-rails`
- startup seeding for default discovery rails

The discovery layer aggregates from:
- story feed
- hosted competitions
- national team competitions
- live threads
- youth prospects
- daily challenges

## 2) Notification Center Expansion
- notification preferences
- notification subscriptions
- platform announcements
- user endpoints for preferences/subscriptions/announcements
- admin endpoint to publish announcements
- announcement fan-out into persistent notification records

## Data / Migration
Added migration:
- `backend/migrations/versions/20260314_0032_discovery_and_notification_center.py`

## Wiring
Updated:
- `backend/app/modules.py`
- `backend/app/models/__init__.py`

## Validation
- Python compile pass completed for the new/updated discovery and notification modules.
- Full runtime test execution was not completed in this container.
