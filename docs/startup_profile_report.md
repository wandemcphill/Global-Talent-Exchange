# GTEX Startup Profile Report

## Summary

The recurring admin bootstrap timeout came from tests waiting for the deferred startup thread, which runs admin creation plus the full module startup hook graph. The fast test profile now disables that deferred graph by default and lets admin fixtures create their own user directly.

## Bottlenecks Found

| Area | Startup Work | Repair |
| --- | --- | --- |
| Admin test auth | `bootstrap_admin_headers` waited up to 30 seconds for `deferred_startup_thread` before creating its own admin user. | The fixture now creates/logs in the admin user directly without waiting on deferred startup. |
| Deferred module hooks | Startup hooks mixed seed jobs, preload work, workers, and critical setup in one synchronous graph. | Hooks are classified as `critical`, `seed`, `preload`, or `worker`, with timing records on `app.state.startup_hook_records`. |
| Regen preload | Preseeded senior/U17/U20 national regen pools lived in startup hook flow. | Fast test startup skips preload hooks and exposes `GTE_REGEN_PRELOAD_ENABLED`. |
| Portrait preload | No global portrait boot hook was found in the current startup graph; portrait generation remains request/service scoped. | `GTE_PORTRAIT_PRELOAD_ENABLED` is available for any future portrait boot path. |
| Background services | Redis health, metrics refresh, outbox relay, and deferred startup could run even when tests only needed route/auth fixtures. | Fast startup skips Redis when no Redis URL exists, skips metrics refresh, skips outbox start, and disables deferred startup. |
| v2 session bootstrap | `/api/v2/session/bootstrap` was missing from the lazy-hydration bypass list, so auth/persona tests could still hydrate the full module graph during session bootstrap. One local run spent 185.69 seconds in module hydration before trader signup. | Added v2 auth, session, competition, broadcast, match, and match-viewer bypass prefixes plus regression coverage. The focused auth bootstrap/lazy-module group now passes in 53.95 seconds without full graph hydration. |

## Runtime Controls

| Setting | Production Default | Test Default |
| --- | --- | --- |
| `GTE_STARTUP_PROFILE` | `production` | `test` |
| `GTE_DEFERRED_STARTUP_ENABLED` | `1` | `0` |
| `GTE_REGEN_PRELOAD_ENABLED` | `1` | `0` |
| `GTE_PORTRAIT_PRELOAD_ENABLED` | `1` | `0` |
| `GTE_TEST_AUTH_FIXTURE_MODE` | `0` | `1` |

## Timing Output

Startup step timing is recorded on `app.state.startup_profile_records`.
Module hook timing is recorded on `app.state.startup_hook_records`.
Each record includes the step or hook name, stage, status, and elapsed milliseconds.

## Local Validation Snapshot

| Check | Result |
| --- | --- |
| `python -m pytest backend/tests/app/test_auth_lazy_module_bypass.py backend/tests/app/test_config.py -q --tb=short -x` | Passed: 15 tests in 98.53 seconds |
| `python -m pytest backend/tests/app/test_auth_lazy_module_bypass.py backend/tests/auth/test_auth_router.py::test_user_creator_and_trader_signup_sessions_include_public_account_type -q --tb=short` | Passed: 4 tests in 53.95 seconds |
| `python -m pytest backend/tests/app/test_auth_lazy_module_bypass.py backend/tests/app/test_module_registration_hydration.py backend/tests/app/test_module_registration.py::test_streamer_tournaments_route_does_not_force_global_lazy_hydration backend/tests/app/test_module_registration.py::test_live_broadcast_and_match_viewer_routes_do_not_force_global_lazy_hydration backend/tests/competitions/test_api_discovery.py::test_discovery_route_bypasses_lazy_module_hydration backend/tests/hosted_competitions/test_api_discovery.py::test_hosted_discovery_api_route_bypasses_lazy_module_hydration -q --tb=short` | Passed: 11 tests in 1093.70 seconds. This protects the lazy-hydration behavior, but the mounted real-app module registration cases remain too slow for frequent local smoke runs. |
| `python -m pytest backend/tests/auth/test_auth_router.py::test_user_creator_and_trader_signup_sessions_include_public_account_type -q --tb=short` | Passed: 1 test in 135.88 seconds before the v2 bypass repair; retained as evidence the just-in-time TOTP payload fix handles slow test hosts. |
| `python -m pytest backend/tests/coin_traders/test_coin_trader_service.py -q --tb=short` | Passed: 15 tests in 294.47 seconds |
| `python -m pytest backend/tests/coin_traders/test_coin_trader_router.py::test_coin_trader_router_admin_liquidity_issue_and_redeem backend/tests/coin_traders/test_coin_trader_router.py::test_coin_trader_router_order_lifecycle -q --tb=short` | Passed: 2 tests in 179.89 seconds |
| `python -m pytest backend/tests/national_team_engine/test_national_team_router.py::test_rental_pool_returns_preseeded_regen_portrait_and_restrictions -q --tb=short` | Passed: 1 test in 233.91 seconds |
| `python tools/audit/check_api_contract_violations.py` | Passed: no contract violations |
| `python -m black --check ...` and `python -m ruff check --no-cache ...` on touched backend files | Passed |
| `flutter analyze --no-pub` | Passed: no issues in 639.2 seconds |
| `flutter test --no-pub test/router/route_coverage_test.dart test/gte_feature_routing_test.dart test/gte_frontend_app_auth_sync_test.dart test/gte_session_identity_test.dart test/active_session_provider_test.dart test/competitions/competition_hub_provider_test.dart` | Passed: 41 tests |
| `flutter test --no-pub test/coin_trader_redesign/coin_trader_panels_test.dart test/referrals/referral_hub_test.dart test/system_profile_redesign/gtex_system_profile_smoke_test.dart test/creator_social_redesign/gtex_awards_screen_test.dart test/gtex_jackpot_route_screen_test.dart test/competition_redesign/gtex_competitions_hub_screen_v2_test.dart test/creators/creator_dashboard_test.dart test/competitions/live_match_center_screen_test.dart test/admin_command_redesign/gtex_admin_command_screen_test.dart` | Passed: 21 tests |
| `flutter test test/world/football_world_pulse_widgets_test.dart --reporter expanded` | Passed: 2 tests |
| `flutter test test/ui_gtex/living_football_os_background_test.dart --reporter expanded` | Passed: 4 tests |
| `flutter test test/active_shell_route_mount_test.dart --reporter expanded --no-pub` | Passed: 3 tests |
| Full `backend/tests/e2e/test_regen_universe_end_to_end.py` | Inconclusive locally: exceeded the 300 second command timeout |

## Remaining Blockers

- Some legacy tests still manually join `deferred_startup_thread`; in fast test mode the thread is `None`, so those joins become no-ops.
- Full production startup still runs the deferred graph by default for compatibility. Production profiling should be captured from staging logs before changing the production hook policy further.
- Coin-trader router tests still take roughly three minutes locally because they exercise DB-backed wallet, escrow, and ledger flows. That is slower than ideal but no longer caused by v2 session bootstrap hydration.
- The mounted real-app module registration tests still take roughly 18 minutes as a combined local batch. They are useful as a deeper regression suite, while `test_auth_lazy_module_bypass.py` is the practical fast guard for v2 session/auth lazy-hydration behavior.
