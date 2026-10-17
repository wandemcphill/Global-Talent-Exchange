# GTEX Sponsorship + Creator Campaign Pass

This pass added two larger engines on top of the existing full archive:

## 1) Sponsorship Engine
- seeded sponsorship package defaults
- sponsorship lead intake
- club sponsorship contract request flow
- club sponsorship dashboard
- admin review actions: approve, reject, pause, resume, complete
- sponsorship payout settlement into the club owner's wallet via ledger posting
- story feed publishing for request, review, and payout moments

### Main files
- `backend/app/sponsorship_engine/*`
- `backend/app/models/sponsorship_engine.py`
- `backend/migrations/versions/20260314_0034_sponsorship_and_creator_campaign_engines.py`

## 2) Creator Campaign Engine
- creator-owned campaign creation and update flow
- campaign share code generation
- campaign metrics rollup view
- snapshot persistence for campaign performance history
- admin metrics read surface
- story feed publishing for campaign launches

### Main files
- `backend/app/creator_campaign_engine/*`
- `backend/app/models/creator_campaign_engine.py`
- `backend/migrations/versions/20260314_0034_sponsorship_and_creator_campaign_engines.py`

## Platform wiring
- module registration in `backend/app/modules.py`
- model registry updates in `backend/app/models/__init__.py`

## Validation completed here
- Python compile check for the newly added modules and registry wiring
- `python -m compileall -q backend/app`

## Honest caveat
- I did not run full runtime pytest in this container, so this remains a substantial build pass plus compile validation, not a fully integration-tested release.
