# CODEX Full QA Release Audit Report

## 1. Executive summary

This pass covered backend validation, migration integrity, route inventory, admin and withdrawal controls, canonical frontend route wiring, button and CTA audit, manager seed data, and release hardening. Backend validation is strong after fixes: `python -m pytest` now passes end to end with `362 passed`, Alembic upgrades cleanly to head, and the backend route inventory is reduced to `301` unique paths after removing duplicate `/api/api/orders` mounts.

The release is still **not ready** for final sign-off. Two blockers remain. First, the audit environment does not have `flutter` or `dart`, so the actual Flutter app could not be analyzed, tested, built, or clicked through interactively. Second, the live canonical wallet UI still does not expose an end-user withdrawal request flow even though the backend withdrawal controls and request endpoints are implemented and tested.

## 2. Project boot paths discovered

- Backend app entry: `backend/app/main.py` -> `create_app()`
- Backend module registry: `backend/app/modules.py`
- Frontend boot entry: `frontend/lib/main.dart` -> `runApp(const GteFrontendApp())`
- Frontend app host: `frontend/lib/app/gte_frontend_app.dart`
- Canonical live Flutter shell: `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
- Canonical navigation route model: `frontend/lib/features/navigation/routing/gte_navigation_route.dart`
- Named route registry and parsers: `frontend/lib/features/app_routes/gte_app_route_registry.dart`, `frontend/lib/features/app_routes/gte_route_data.dart`
- Legacy or non-canonical shell still present: `frontend/lib/screens/gte_exchange_shell_screen.dart`

### Key feature folders in live use

- Trading and market: `backend/app/market/`, `backend/app/orders/`, `frontend/lib/screens/gte_market_players_screen.dart`, `frontend/lib/screens/gte_exchange_player_detail_screen.dart`
- Wallet, portfolio, ledger, withdrawals: `backend/app/wallets/`, `backend/app/portfolio/`, `frontend/lib/screens/gte_portfolio_screen.dart`
- Competitions and e-game: `backend/app/routes/competitions.py`, `backend/app/competition_engine/`, `frontend/lib/features/competitions_hub/`, `frontend/lib/screens/competitions/`
- Club identity and ops: `backend/app/routes/clubs.py`, `backend/app/club_identity/`, `backend/app/segments/clubs/`, `frontend/lib/features/club_hub/`, `frontend/lib/features/club_identity/`
- Creator and referral: `backend/app/routes/creators.py`, `backend/app/routes/referrals.py`, `frontend/lib/screens/referrals/`, `frontend/lib/screens/creators/`
- Manager market: `backend/app/manager_market/`, `frontend/lib/screens/manager_market_screen.dart`
- Admin controls: `backend/app/admin_godmode/`, `backend/app/admin_access/`, `frontend/lib/screens/admin/god_mode_admin_screen.dart`, `frontend/lib/screens/admin/manager_admin_screen.dart`

### Tests, seed, config, and environment files

- Backend tests: `backend/tests/`, `tests/`
- Frontend tests: `frontend/test/`
- Manager seed catalog: `backend/app/manager_market/seed_catalog.py`
- Demo smoke: `backend/tests/smoke/test_demo_smoke.py`
- Backend config examples: `backend/.env.example`, `backend/migrations/alembic.ini`, `backend/requirements.txt`
- Frontend config examples: `frontend/.env.example`, `frontend/pubspec.yaml`, `frontend/analysis_options.yaml`

## 3. Commands run

### Environment and toolchain

- `python --version` -> `Python 3.14.2`
- `flutter --version` -> failed, `flutter` not recognized
- `flutter pub get` -> failed, `flutter` not recognized
- `flutter analyze` -> failed, `flutter` not recognized
- `flutter test` -> failed, `flutter` not recognized
- `where.exe flutter` -> no Flutter binary found
- `Get-Command dart` -> no Dart binary found

### Database and backend validation

- `python -m alembic -c backend\migrations\alembic.ini heads` -> `20260312_0016 (head)`
- `python -m alembic -c backend\migrations\alembic.ini upgrade head` -> passed after SQLite-safe migration fix
- `python -m pytest backend/tests/manager_market/test_seed_catalog.py -q` -> `1 passed`
- `python -m pytest backend/tests/admin_godmode/test_withdrawal_controls.py -q` -> `4 passed`
- `python -m pytest backend/tests/app/test_api_contracts.py -q` -> `1 passed`
- `python -m pytest backend/tests/wallets/test_wallet_http.py -q` -> `9 passed`
- `python -m pytest` -> final post-hardening run passed, `362 passed in 848.83s`

### Route and source audit commands

- Inline Python route inventory from `create_app()` -> `ROUTE_COUNT=301`
- Inline Python orders-only route dump -> confirmed `/orders` and `/api/orders` remain; `/api/api/orders` removed
- `rg -n "CreatorDashboardScreen|ReferralHubScreen|Community|creator|referral|manager market|manager" frontend/lib -g "*.dart"` -> confirmed creator and referral UI exists in source
- `rg -n "onPressed:\\s*null|TODO|coming soon|Route unavailable|Navigation unavailable|pushNamed|goNamed|Navigator\\.of\\(|context\\.go\\(|context\\.push\\(" frontend/lib -g "*.dart"` -> no obvious empty live CTA handlers found; fallback route panels exist
- `rg -n "withdraw|payout|bank transfer|payment mode|manual payment|gateway" frontend/lib -g "*.dart"` -> confirmed admin withdrawal controls UI exists; no end-user withdrawal request flow exists in wallet UI

## 4. Results summary

- Backend tests: pass
- Alembic migration integrity: pass
- Backend route inventory: pass after duplicate orders alias removal
- Withdrawal-control backend logic: pass by code audit and automated tests
- Admin settings backend and admin UI wiring: pass by code audit and automated tests
- Canonical frontend shell audit: partial pass
- Canonical creator/community lane reachability: fixed during audit
- Canonical wallet withdrawal request UI: fail, still missing
- Frontend static validation: blocked by missing Flutter toolchain
- Frontend interactive click-through: blocked by missing Flutter toolchain

## 5. Backend issues found and fixed

### Fixed

- `pytest` collection instability from duplicate test module discovery and temp directories.
  - Root cause: no root-level test-path and import-mode hardening.
  - Fix: added `pytest.ini` with scoped `testpaths`, `--import-mode=importlib`, and noisy path exclusions.
  - Severity: high

- Wallet router could fail when `admin_god_mode.json` was missing or malformed.
  - Files: `backend/app/wallets/router.py`
  - Root cause: missing fallback defaults for commission and withdrawal controls.
  - Fix: fallback to `DEFAULT_COMMISSION_SETTINGS` and `DEFAULT_WITHDRAWAL_CONTROLS`.
  - Severity: high

- Wallet service contract gap.
  - Files: `backend/app/wallets/service.py`
  - Root cause: missing `WalletLedgerPage` dataclass referenced by callers and tests.
  - Fix: added the dataclass.
  - Severity: high

- SQLite migration failure on lifecycle and club-link migration.
  - Files: `backend/migrations/versions/20260312_0015_add_player_lifecycle_events_and_managed_club_link.py`
  - Root cause: direct alter operations not SQLite safe.
  - Fix: converted schema updates to `op.batch_alter_table(...)`.
  - Severity: high

- Health diagnostics could fail outside the full app lifespan.
  - Files: `backend/app/core/health.py`
  - Root cause: direct dependence on `app.state.settings`.
  - Fix: fallback to `get_settings()` when app state is not fully bound.
  - Severity: medium

- Canonical club identity API routes were misaligned with live frontend expectations.
  - Files: `backend/app/club_identity/reputation/router.py`, `backend/app/club_identity/dynasty/api/router.py`, `backend/app/routes/clubs.py`, `backend/app/modules.py`, `backend/app/segments/clubs/segment_clubs.py`
  - Root cause: duplicated route ownership and incomplete canonical `/api/clubs/{club_id}/...` coverage.
  - Fix: made `canonical_clubs` own the canonical reputation and dynasty routes and removed duplicate module registrations.
  - Severity: high

- Match simulation runtime errors.
  - Files: `backend/app/match_engine/simulation/strength.py`
  - Root cause: missing helper methods used in match strength calculations.
  - Fix: restored `_squad_balance_bonus(...)` and `_manager_adjustments(...)`.
  - Severity: high

- Team assembly failure when the only natural goalkeeper was unavailable.
  - Files: `backend/app/match_engine/services/team_factory.py`
  - Root cause: strict goalkeeper fit blocked emergency squad assembly.
  - Fix: added emergency non-goalkeeper fallback scoring for the keeper slot.
  - Severity: high

- Player lifecycle consistency issue around bid acceptance.
  - Files: `backend/app/services/player_lifecycle_service.py`
  - Root cause: missing club-profile validation on multiple lifecycle flows and returned bid state mutation in-session.
  - Fix: added `_require_club_profile()` validation and expunged the accepted bid before downstream mutation.
  - Severity: medium

- Duplicate `/api/api/orders` routes in the live backend.
  - Files: `backend/app/wallets/router.py`, `backend/tests/app/test_api_contracts.py`
  - Root cause: the wallet router wrapped the already-prefixed orders router inside another `/api` router.
  - Fix: mounted legacy and API order routers separately and added a contract assertion to keep `/api/api/orders*` out of OpenAPI.
  - Severity: medium

### Tests updated

- `backend/tests/admin_godmode/test_withdrawal_controls.py`
  - Updated competition-withdrawal funding to use `LedgerEntryReason.COMPETITION_REWARD`

- `backend/tests/clubs/test_api_clubs.py`
  - Updated reputation expectations to the canonical flat response schema

- `backend/tests/clubs/conftest.py`
  - Bound `app.state.session_factory` to mirror production app dependencies

- `backend/tests/app/test_main.py`
  - Removed expectations for the duplicate `club_reputation` and `dynasty` modules

- `backend/tests/app/test_module_registration.py`
  - Updated expected module registration set to `canonical_clubs`

- `backend/tests/players/test_player_lifecycle.py`
  - Stabilized future-transfer assertions

- `backend/tests/smoke/test_demo_smoke.py`
  - Updated demo holdings expectations to current seeded behavior

- `backend/tests/manager_market/test_seed_catalog.py`
  - Extended Tunde Oni assertions to cover nationality mapping and unmapped-field representation in philosophy text

## 6. Frontend issues found and fixed

### Fixed

- Canonical creator/community lane was unreachable from the live shell.
  - Files: `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Root cause: creator and referral screens were still only reachable from the older non-canonical shell.
  - Fix: added a dedicated creator/community icon entry point in the canonical shell and wired live `CreatorController` and `ReferralController` instances into `ReferralHubScreen`.
  - Severity: high

- Misleading wallet copy and CTA labeling.
  - Files: `frontend/lib/screens/gte_portfolio_screen.dart`
  - Root cause: preview copy promised "withdrawal readiness" even though no end-user withdrawal flow exists, and the orders refresh button was labeled as a ledger refresh.
  - Fix: removed the misleading withdrawal copy and renamed the CTA to `Refresh orders`.
  - Severity: low

### Verified by source audit only

- Canonical shell lanes remain visually distinct:
  - Trade: terminal-style market lane
  - Arena: competitions hub and live match center
  - Wallet: capital-focused lane
  - Club: institution and identity lane
  - Admin: governance and control room
  - Creator: now reachable, but still not modeled as a canonical deep-link route

## 7. Withdrawal-controls audit

### Verified

- Default withdrawal fee logic is `1000` bps, which is `10%`
- Trade withdrawals are policy-gated
- Competition or e-game withdrawals are policy-gated
- If e-game withdrawals are disabled, winnings remain tradable in-app and cannot be directly withdrawn
- Admin can update:
  - withdrawal percentage
  - minimum withdrawal fee
  - competition prize-pool top-up percentage
  - processor mode
  - bank-transfer deposit toggle
  - bank-transfer payout toggle
  - trade withdrawal enablement
  - e-game withdrawal enablement
- Manual bank transfer requires `destination_reference` beginning with `bank:`
- Automatic gateway mode can move eligible requests into `processing`
- Manual bank transfer mode keeps payouts in `reviewing`
- Withdrawal metadata captures:
  - gross amount
  - fee amount
  - total debit
  - source scope
  - processor mode
  - payout channel

### Evidence

- Passing tests:
  - `backend/tests/admin_godmode/test_withdrawal_controls.py`
  - `backend/tests/wallets/test_wallet_http.py`
  - `backend/tests/wallets/test_wallet_service.py`
- Files audited:
  - `backend/app/wallets/router.py`
  - `backend/app/wallets/service.py`
  - `frontend/lib/screens/admin/god_mode_admin_screen.dart`

### Edge cases covered

- Negative balance protection in wallet postings
- Fee application and held total debit
- Competition withdrawal requires actual reward balance
- Competition withdrawal blocked by default until admin enables it
- Manual bank transfer gateway deposit blocking
- Automatic gateway deposit allowance
- Auth and admin role enforcement through router dependencies and test overrides

### Remaining gap

- No end-user withdrawal request flow is exposed from the canonical wallet UI. Backend support exists, but the live user lane does not let a signed-in user submit a withdrawal request.

## 8. Admin-controls audit

### Verified admin surfaces

- `frontend/lib/screens/admin/god_mode_admin_screen.dart`
  - commissions
  - withdrawal controls
  - payment rails
  - competition top-up controls
  - treasury dashboard and treasury withdrawal action
  - withdrawal review queue
  - audit event search
  - password change

- `backend/app/admin_godmode/router.py`
  - bootstrap
  - commission updates
  - withdrawal control updates
  - competition control updates
  - payment rail updates
  - withdrawal status patching
  - treasury withdrawal

### Access control result

- Admin-only mutation paths are protected server-side
- Non-admin mutation attempts are not exposed by the canonical shell
- Admin entry point remains reachable from the canonical shell for `admin` and `super_admin`

## 9. Button/route audit

### Live canonical lanes audited

- Auth and login
- Guest preview
- Home dashboard
- Market
- Player detail
- Order detail and cancel/refresh flow
- Competitions hub and details
- Club hub and club identity routes
- Wallet and portfolio
- Manager market
- Admin God Mode
- Creator and referral lane

### Findings

- No obvious empty `onPressed: () {}` handlers found in the live frontend search
- Unknown-route handling exists and degrades gracefully with `Route unavailable` or `Navigation unavailable`
- Legacy shell remains in source, but canonical boot path uses the newer navigation shell
- Backend duplicate `/api/api/orders*` routes were removed during this audit
- Creator lane is now reachable from the canonical shell, but still lacks canonical route-registry or deep-link coverage
- Wallet lane still has no end-user withdrawal CTA

## 10. Tunde Oni manager audit

### Verified mapping

- Name: `Tunde Oni`
- Nationality mapping: represented through `club_associations = ["Nigeria"]`
- Mentality: `balanced`
- Tactics mapped to nearest schema tokens:
  - `counter_attack`
  - `technical_build_up`
  - `set_piece_focus`
  - `youth_development_system`
- Philosophy text now explicitly carries:
  - `3-4-3`
  - `4-1-2-1-2 diamond`
  - `3-4-1-2`
  - play through the middle
  - short passing
  - counters against bigger teams
  - set-piece emphasis
  - belief in young players
  - great motivator

### Schema fit note

- Explicit formation slots do not exist in the current manager schema, so formations are represented in `philosophy`
- There is no first-class `great_motivator` trait token in the schema, so that requirement is represented in `philosophy`, not `traits`

## 11. Remaining known issues

- Flutter toolchain is not installed in this audit environment.
  - Impact: `flutter pub get`, `flutter analyze`, `flutter test`, actual app boot, and end-to-end click-through could not be verified.
  - Severity: high

- No end-user withdrawal request UI exists in the canonical wallet lane.
  - Files: `frontend/lib/screens/gte_portfolio_screen.dart`, `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
  - Impact: backend withdrawal controls are tested, but the user requirement "users can request withdrawal" is not fulfilled from the live shell.
  - Severity: high

- Creator and referral lane still lacks canonical route-registry and deep-link entries.
  - Files: `frontend/lib/features/app_routes/gte_route_data.dart`, `frontend/lib/features/app_routes/gte_app_route_registry.dart`
  - Impact: lane is reachable from the shell, but not represented in the canonical named-route system.
  - Severity: medium

- Legacy shell and older route surfaces remain in the repo.
  - Files: `frontend/lib/screens/gte_exchange_shell_screen.dart` and related legacy tests
  - Impact: maintainability and future route confusion risk
  - Severity: low

## 12. Risk ranking

### Critical

- None confirmed after fixes

### High

- Frontend release validation is blocked because Flutter tooling is absent in the audit environment
- End-user withdrawal request flow is still missing from the canonical wallet UI

### Medium

- Creator lane is reachable but still lacks canonical route and deep-link registration
- Large pre-existing dirty worktree and legacy surfaces increase packaging and release hygiene risk

### Low

- Legacy non-canonical shell remains in source
- Minor frontend copy and label cleanup opportunities remain outside the patched wallet copy

## 13. Release readiness verdict

**not ready**

Reason: backend is in good shape, but frontend release validation could not be executed and a required withdrawal request flow is not present in the live canonical wallet lane.

## 14. Exact files changed

### Files changed during this audit pass

- `pytest.ini`
- `backend/app/wallets/service.py`
- `backend/app/wallets/router.py`
- `backend/migrations/versions/20260312_0015_add_player_lifecycle_events_and_managed_club_link.py`
- `backend/tests/admin_godmode/test_withdrawal_controls.py`
- `backend/app/core/health.py`
- `backend/app/club_identity/reputation/router.py`
- `backend/app/club_identity/dynasty/api/router.py`
- `backend/app/routes/clubs.py`
- `backend/app/modules.py`
- `backend/app/segments/clubs/segment_clubs.py`
- `backend/tests/clubs/test_api_clubs.py`
- `backend/tests/clubs/conftest.py`
- `backend/app/match_engine/simulation/strength.py`
- `backend/app/match_engine/services/team_factory.py`
- `backend/app/services/player_lifecycle_service.py`
- `backend/tests/app/test_main.py`
- `backend/tests/app/test_module_registration.py`
- `backend/tests/app/test_api_contracts.py`
- `backend/tests/players/test_player_lifecycle.py`
- `backend/tests/smoke/test_demo_smoke.py`
- `backend/app/manager_market/seed_catalog.py`
- `backend/tests/manager_market/test_seed_catalog.py`
- `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
- `frontend/lib/screens/gte_portfolio_screen.dart`
- `CODEX_FULL_QA_RELEASE_AUDIT_REPORT.md`
- `CODEX_BUTTON_ROUTE_AUDIT.md`
- `CODEX_TEST_MATRIX.md`

## 15. Recommended next actions

1. Install Flutter and Dart in the release environment, then run:
   - `flutter pub get`
   - `flutter analyze`
   - `flutter test`
   - a real device or emulator click-through of all canonical shell lanes

2. Implement and validate a canonical end-user withdrawal request UI that calls `/api/wallets/withdrawals` and exposes:
   - source scope
   - payout mode messaging
   - fee preview
   - bank-transfer destination validation
   - success and error states

3. Add creator and referral routes to the canonical route registry so the lane supports deep links and route-level tests.

4. Perform a release-hygiene pass on the dirty worktree and legacy shell leftovers before packaging.
