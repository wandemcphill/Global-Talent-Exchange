# ChatGPT Hosted Competition Finance Pass

This pass expanded the hosted competition engine from template + join flow into a more complete ledger-backed competition finance surface.

## Added
- Entry fee collection into a dedicated competition escrow ledger account
- Host entry-fee collection during competition creation
- Participant fee collection during join
- Competition launch endpoint with seeded standings
- Competition standings persistence
- Competition finance snapshot endpoint
- Admin finalize endpoint that settles prize payouts and platform fee from escrow
- Settlement records and standings records
- Story feed publication for launch and completion
- Migration `20260314_0030_hosted_competition_finance.py`

## Main files updated
- `backend/app/models/hosted_competition.py`
- `backend/app/hosted_competition_engine/service.py`
- `backend/app/hosted_competition_engine/router.py`
- `backend/app/hosted_competition_engine/schemas.py`
- `backend/app/models/__init__.py`
- `backend/migrations/versions/20260314_0030_hosted_competition_finance.py`

## Validation completed here
- Python compile validation on the edited modules

## Notes
- This pass is backend-focused.
- Full runtime verification still depends on the target environment having the project dependencies installed.
