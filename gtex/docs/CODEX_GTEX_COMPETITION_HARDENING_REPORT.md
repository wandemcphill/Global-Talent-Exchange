# GTEX Competition Hardening Report

## Scope

This hardening pass targeted the live GTEX competition mutation risk called out in `Docs/CODEX_FULL_APP_VERIFICATION_REPORT.md`:

- legacy anonymous GTEX `join`
- legacy anonymous GTEX `publish`
- legacy anonymous GTEX `launch`

The audited backend entrypoint is:

- `backend/app/segments/competitions/segment_competitions.py`

## Audit Findings

Before this change, the GTEX segment router still allowed a legacy anonymous mutation path:

- `publish_competition(...)` used `Depends(get_optional_current_user)` and only enforced `manage_competitions` when a bearer token was present.
- `join_competition(...)` used `Depends(get_optional_current_user)` and only enforced session-to-payload matching when a bearer token was present.
- `launch_competition(...)` used `Depends(get_optional_current_user)` and only enforced `manage_competitions` when a bearer token was present.

That meant:

- missing bearer token did not block `publish`
- missing bearer token did not block `join`
- missing bearer token did not block `launch`

## Implemented Changes

### Backend hardening

Updated `backend/app/segments/competitions/segment_competitions.py` so that:

- `publish` now requires `get_current_user`
- `launch` now requires `get_current_user`
- `join` now requires `get_current_user`
- `publish` and `launch` always execute `_require_manage_competitions_permission(...)`
- `join` always rejects payload/session identity drift with:
  - `403 Authenticated user does not match competition join payload.`

### Regression coverage

Added explicit auth-regression coverage in:

- `backend/tests/competitions/test_active_shell_competition_auth_guards.py`

New regression assertions cover:

- anonymous `publish` returns `401`
- anonymous `join` returns `401`
- anonymous `launch` returns `401`

### Test migration

Updated legacy tests that were still using anonymous mutation calls so they now use authenticated participants and a scoped admin carrying `manage_competitions`.

Shared helpers were added in:

- `backend/tests/conftest.py`

Affected test areas updated:

- `backend/tests/competitions/test_api_create_publish_join.py`
- `backend/tests/competitions/test_api_discovery.py`
- `backend/tests/competitions/test_api_financial_summary.py`
- `backend/tests/competitions/test_api_invites.py`
- `backend/tests/competitions/test_api_treasure_chest_progression.py`
- `backend/tests/competitions/test_competition_lifecycle.py`
- `backend/tests/e2e/test_gtex_happy_path_smoke.py`
- `backend/tests/national_team_engine/test_national_team_router.py`

## Verification

Completed:

- `python -m py_compile` across all modified backend and test files
- targeted lightweight smoke verification proving anonymous `publish`, `join`, and `launch` now return `401`

Environment limitation:

- the repo's full pytest app fixture did not finish within the available execution window in this session, so the full competition pytest subset could not be completed end-to-end here

## Residual Scope Notes

This pass was intentionally scoped to the report-listed GTEX live mutation risk in `join` / `publish` / `launch`.

Other competition mutation routes in `segment_competitions.py` were not changed in this pass and should be evaluated separately if the goal expands from the reported live GTEX risk to a full mutation-auth hardening sweep.
