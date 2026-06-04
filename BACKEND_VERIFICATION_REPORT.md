# GTEX Backend Verification Report

Generated: 2026-06-04

Log directory: `tmp/production_readiness_wave`

## Commands Executed

| Command | Result | Evidence |
|---|---:|---|
| `python -m pytest -q` | Stopped after 08:33:45 at 22% | 22 `F` markers, 39 `E` markers before bounded stop |
| `python -m pytest tests/imports/test_backend_import_smoke.py backend/tests/app/test_module_registration_routes.py backend/tests/app/test_api_contracts.py backend/tests/integration/test_module_mounts.py -q --tb=short --maxfail=20` | Exit 1 | 20 failures before maxfail |
| `python -m pytest tests/transfer_market backend/tests/wallets backend/tests/players/test_transfer_market.py backend/tests/players/test_transfer_bid_wallet_reservations.py -q --tb=short --maxfail=20` | Exit 1 | 132 passed, 3 failed |
| `python -m pytest backend/tests/regen backend/tests/realtime/test_regen_creation_realtime.py backend/tests/club_ops/test_regen_service.py backend/tests/club_ops/test_regen_lineage_twins.py -q --tb=short --maxfail=20` | Exit 1 | 62 passed, 2 failed, 5 errors |
| `python -m pytest backend/tests/competitions backend/tests/competition_engine backend/tests/admin_godmode backend/tests/admin_finance backend/tests/admin_engine backend/tests/admin_access -q --tb=short --maxfail=20` | Exit 1 | 9 failed, 11 errors before maxfail |

Initial attempt with bare `pytest -q` failed because `pytest` was not on PATH. `python -m pytest` was used for real validation.

## Full Pytest Runtime

The full backend suite did not complete within a usable production-validation window. It ran for 08:33:45 and reached only 22% before being stopped. The progress stream already contained at least 22 failure markers and 39 error markers.

This is itself a production blocker: the backend suite is currently too slow/noisy to certify the build in one pass.

## Contract and Module Mount Failures

The targeted contract/mount suite stopped at `--maxfail=20`.

Representative failures:

- `backend/tests/app/test_module_registration_routes.py::test_mounted_module_routes_resolve_on_the_real_app[GET /world-super-cup/countdown]`
- `GET /fast-cups/upcoming`
- `GET /replays/public/featured`
- `POST /leagues/register`
- `POST /champions-league/qualification-map`
- `POST /academy/season-summary`
- `POST /ai-manager/autopilot/run`
- `POST /match-engine/summary`
- `POST /match-engine/replay`
- `POST /matches/start`
- `POST /matches/complete`
- `GET /predictions`
- `GET /finance`
- `GET /sponsors`
- `GET /season-pass`
- `GET /live-events`
- `GET /managers`

Common failure mode: routes returned `410 Gone` where tests expected live/auth/normal route responses such as `401` or `200`.

## Wallet and Transfer-Market Validation

Result: 132 passed, 3 failed.

Failures:

- `tests/transfer_market/test_transfer_market_auth.py::test_add_watchlist_entry_rejects_actor_without_club_access`
  - Expected `transfer_market_watchlist_access_required`.
  - Actual `transfer_market_club_access_required`.
- `tests/transfer_market/test_transfer_market_auth.py::test_place_bid_rejects_actor_without_bidder_club_access`
  - Expected `transfer_market_bidder_club_access_required`.
  - Actual `transfer_market_club_access_required`.
- `backend/tests/players/test_transfer_bid_wallet_reservations.py::test_accepted_bid_settles_reserved_balance_first_then_available_shortfall`
  - `WalletService.settle_transfer_bid_reservation` raised `InsufficientBalanceError: Transfer bid settlement requires the full amount to be held in escrow.`
  - Surfaced as `PlayerLifecycleValidationError: Buying club owner does not have enough GTex Coin to settle this transfer bid`.

## Regen / Build-a-Son Validation

Result: 62 passed, 2 failed, 5 errors.

Failures/errors:

- `backend/tests/regen/test_regen_universe_expansion_api.py::test_player_story_dna_and_rivalries_routes`
- `backend/tests/regen/test_regen_universe_expansion_api.py::test_youth_tournament_routes_and_jobs`
- `backend/tests/regen/test_regen_admin_rbac.py::test_super_admin_can_run_regen_admin_routes`
- `backend/tests/regen/test_regen_admin_rbac.py::test_regen_ops_admin_can_preseed_national_regens_and_close_seasons`
- `backend/tests/regen/test_regen_admin_rbac.py::test_regen_ops_admin_can_manage_regen_portraits`
- `backend/tests/regen/test_regen_admin_rbac.py::test_support_admin_cannot_manage_regen_portraits`
- `backend/tests/regen/test_regen_admin_rbac.py::test_support_admin_cannot_preseed_or_close_regen_seasons`

Observed runtime issue: significant migration/setup churn appeared in logs before failures.

## Competition and Admin Validation

Result: 9 failed, 11 errors before `--maxfail=20`.

Representative failures:

- `backend/tests/competitions/test_active_shell_competition_auth_guards.py` auth guard cases failed or errored.
- `backend/tests/competitions/test_api_create_publish_join.py` create/patch/publish/join flow failed/errored.
- `backend/tests/competitions/test_api_discovery.py` discovery/filter/sorting/batching tests errored.
- `backend/tests/competitions/test_api_financial_summary.py::test_summary_and_detail_keep_financial_fields_visible` raised `KeyError: 'id'` after create response.
- Invite generation/list/join flow errored.

## Backend Readiness Verdict

Backend is not production-verifiable today. The full suite does not complete in a practical window, core route registration tests fail, competition/auth/discovery flows fail, transfer-market wallet reservation parity has failing edge cases, and regen/admin RBAC routes error.

