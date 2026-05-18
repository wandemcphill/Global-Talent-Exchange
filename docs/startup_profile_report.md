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
| `python -m pytest backend/tests/national_team_engine/test_national_team_router.py::test_rental_pool_returns_preseeded_regen_portrait_and_restrictions -q --tb=short` | Passed: 1 test in 233.91 seconds |
| `python tools/audit/check_api_contract_violations.py` | Passed: no contract violations |
| `python -m black --check ...` and `python -m ruff check --no-cache ...` on touched backend files | Passed |
| `flutter analyze --no-pub ...` on touched frontend files | Passed: no issues |
| `flutter test test/world/football_world_pulse_widgets_test.dart --reporter expanded` | Passed: 2 tests |
| `flutter test test/ui_gtex/living_football_os_background_test.dart --reporter expanded` | Passed: 4 tests |
| `flutter test test/active_shell_route_mount_test.dart --reporter expanded --no-pub` | Passed: 3 tests |
| Full `backend/tests/e2e/test_regen_universe_end_to_end.py` | Inconclusive locally: exceeded the 300 second command timeout |
| Full `flutter analyze` | Inconclusive locally: exceeded the 300 second command timeout before retrying touched files with `--no-pub` |

## Remaining Blockers

- Some legacy tests still manually join `deferred_startup_thread`; in fast test mode the thread is `None`, so those joins become no-ops.
- Full production startup still runs the deferred graph by default for compatibility. Production profiling should be captured from staging logs before changing the production hook policy further.
