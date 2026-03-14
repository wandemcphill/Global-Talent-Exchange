# ChatGPT Governance + Dispute Long Pass Report

This pass extended the full GTEX repository with two larger operational surfaces:

## 1. Governance Engine
- supporter-token powered governance proposals
- supporter-weighted voting
- proposal eligibility checks based on supporter holdings
- admin proposal closure / acceptance / rejection
- story feed publication for proposal open and close events

### Main routes
- `GET /governance/proposals`
- `GET /governance/me/overview`
- `POST /governance/proposals`
- `GET /governance/proposals/{proposal_id}`
- `POST /governance/proposals/{proposal_id}/vote`
- `POST /admin/governance/proposals/{proposal_id}/status`

## 2. Dispute Engine
- persistent dispute case intake
- threaded dispute messaging
- admin assignment and status workflows
- notification record fan-out for dispute events

### Main routes
- `POST /disputes`
- `GET /disputes/me`
- `GET /disputes/{dispute_id}`
- `POST /disputes/{dispute_id}/messages`
- `GET /admin/disputes`
- `POST /admin/disputes/{dispute_id}/assign`
- `POST /admin/disputes/{dispute_id}/status`

## Database / wiring
- added migration `20260314_0035_governance_and_dispute_engine.py`
- registered new models in `backend/app/models/__init__.py`
- registered new routers in `backend/app/modules.py`

## Validation performed here
- Python compile validation on `backend/app`
- lightweight placeholder test files added for the new engine surfaces

## Truth note
- Full runtime integration tests were not executed in this container.
