# GTEX Frontend Verification Report

Generated: 2026-06-04

Log directory: `tmp/production_readiness_wave`

## Commands Executed

| Command | Result | Duration |
|---|---:|---:|
| `flutter analyze --no-pub` from `frontend` | Exit 1 | 00:29:28 |
| `flutter test --no-pub --concurrency=1 -r expanded` from `frontend` | Exit 1 | 06:45:59 |

## Analyzer Result

`flutter analyze --no-pub` reported `23 issues found`.

Hard errors:

| File | Failure |
|---|---|
| `frontend/test/match/broadcast_package_screen_test.dart:6` | Missing import `package:gte_frontend/features/match_center/models/match_monetization.dart`. |
| `frontend/test/match/broadcast_package_screen_test.dart:28` | Removed/undefined `monetization` parameter and missing `MatchViewerMonetization` class. |
| `frontend/test/match_viewer_monetization_test.dart:35` | `monetizationService` is no longer a `GtexMatchViewerScreen` parameter. |
| `frontend/test/surface_runtime_proof_test.dart:1544` | `HostedCompetitionFinance` call is missing required `settlementReadiness`. |
| `frontend/test/surface_runtime_proof_test.dart:1847` | Removed `MatchViewState.monetization` getter/parameter still referenced. |

Warnings:

- `unreachable_switch_case`: club hub formation/editor/content/readiness, home dashboard, navigation shell, player card marketplace, market players screen.
- `duplicate_export`: `frontend/lib/features/squad/squad.dart:4`, `:5`, `:8`.
- `unused_local_variable`: `frontend/test/match_3d_screen_test.dart:50` variable `competition`.

## Full Flutter Test Result

Final line: `+795 -21`, `Some tests failed`.

Failures:

| # | File | Feature | Failure |
|---:|---|---|---|
| 1 | `frontend/test/active_shell_adjacent_flows_test.dart` | Active shell/wallet nav | `Club funds` tooltip not found. |
| 2 | `frontend/test/active_shell_adjacent_flows_test.dart` | Portfolio/wallet deep links | Expected `Funds`, found none. |
| 3 | `frontend/test/active_shell_adjacent_flows_test.dart` | Wallet actions | `pumpAndSettle` timeout. |
| 4 | `frontend/test/active_shell_adjacent_flows_test.dart` | Wallet compliance | Timed out waiting for `Wallet actions`. |
| 5 | `frontend/test/active_shell_adjacent_flows_test.dart` | Withdrawal workspace | `GteMockApi.capitalFixtures` disabled; expected `Withdrawal WDR-`, found none. |
| 6 | `frontend/test/club_identity_routing_test.dart` | Club hub routing | Expected `Owner offer inbox`, found none. |
| 7 | `frontend/test/competitions/competition_hub_happy_path_test.dart` | Competition arena | `Bad state: No element` in fixture snapshot scroll. |
| 8 | `frontend/test/competitions/competition_hub_happy_path_test.dart` | Competition arena | Same `Bad state: No element` for live/final/replay sections. |
| 9 | `frontend/test/gte_controlled_merge_contract_test.dart` | App bootstrap contract | Expected old `child: GtexApp(themeController: themeController),` source snippet in `main.dart`. |
| 10 | `frontend/test/live_visibility_contract_test.dart` | National teams | `GteParsingException`; missing required `generation_index` / `generationIndex`. |
| 11 | `frontend/test/match/broadcast_package_screen_test.dart` | Match broadcast monetization | Test file failed to load due missing monetization model/API. |
| 12 | `frontend/test/match/gtex_match_simulation_screen_test.dart` | Legacy match simulation | Throws `Unsupported operation: Canonical match state must come from backend-authored realtime payloads.` |
| 13 | `frontend/test/match/match_simulation_engine_test.dart` | Legacy match simulation | Throws `Unsupported operation: Local match event generation is disabled`. |
| 14 | `frontend/test/match/match_simulation_engine_test.dart` | Local preview | Same local generation disabled error. |
| 15 | `frontend/test/match_broadcast_route_screen_test.dart` | Legacy route blocking | Expected `Coming soon`, found none. |
| 16 | `frontend/test/match_simulate_route_screen_test.dart` | Legacy route blocking | Expected `Coming soon`, found none. |
| 17 | `frontend/test/match_simulate_screen_test.dart` | Legacy wrapper | Expected `Coming soon`, found none. |
| 18 | `frontend/test/match_viewer_monetization_test.dart` | Viewer monetization | Test file failed to load; removed `monetizationService`. |
| 19 | `frontend/test/surface_runtime_proof_test.dart` | Runtime proof | File failed to load; missing `settlementReadiness`, removed match monetization state. |
| 20 | `frontend/test/trader/trader_dashboard_screen_test.dart` | Trader blocked state | Expected one `Order book blocked`, found two. |
| 21 | `frontend/test/widget_test.dart` | Root shell smoke | Expected `Home`, found none. |

Non-failing warning:

- `frontend/test/viral_feed/viral_feed_screen_test.dart:378`: tap on `Share to WhatsApp` landed outside the `800x600` root. This did not increment the final failure count but is visual/interaction risk.

## Suite Coverage Confirmed

The repository contains tests for route coverage, role guards, active shell mounting, widget suites, Match Center realtime/contracts, compete bracket models/widgets, wallet truth, transfer transport, Build-a-Son, trader, and guardrails. The full suite did execute broadly, but failed before production acceptance.

## Frontend Readiness Verdict

Frontend is not production-verifiable today. Analyzer fails, full tests fail, root shell smoke fails, stale tests still reference removed monetization APIs, and active shell/wallet/competition route behavior has regressions.

