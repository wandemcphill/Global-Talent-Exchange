# CODEX Match Visual Direction Report

Date: 2026-03-30

## Executive Summary

GTEX now presents matches with a materially stronger broadcast package and a substantially more premium replay lane. The shipped result moves toward the requested EA FC / eFootball / Football Manager blend through cleaner scorebugs, commentary ribbons, formation and roster staging, context boards, tactical overlays, ratings strips, recap boards, and more coherent camera-aware scene presentation.

The 3D lane remains honestly positioned as a Flutter-rendered match presentation surface. It is not a native AAA football engine, and `/matches/native-3d` remains blocked until a verified native bridge exists.

## Visual Direction

- Premium TV framing first, with restrained gradients, darker bowls, bright pitch emphasis, and high-contrast overlays.
- Readability over fake-cinematic closeups: gameplay camera clarity, controlled motion, stable scorebug structure, and tactical legibility.
- Clean, modern sports UI language: sharp geometry, compact metadata chips, restrained transitions, and event-led lower thirds.
- Honest degradation: if data is absent, modules can be hidden instead of fabricated.

## Route Ownership

- `/matches/broadcast/:matchKey`
  - Primary screen: `frontend/lib/features/match/presentation/broadcast_package_screen.dart`
  - Owns the broadcast package sequence, header/roster/formation/context modules, scene strip, live broadcast window, halftime board, and full-time board staging.

- `/matches/3d/:matchKey`
  - Primary viewer shell: `frontend/lib/screens/match/gtex_match_viewer_screen.dart`
  - Owns the replay lane shell, render-mode switching, scorebug, commentary ribbon, tactical HUD, ratings strip, recap boards, replay controls, continuation handling, and camera-aware scene presentation.

- `/internal/dev/blocked-match-runtime`
  - Truth screen: `frontend/lib/features/match_center/blocked_match_runtime_screen.dart`
  - Remains hidden and blocked until GTEX has a verified runtime bridge.

## Broadcast Package Modules

- Match header package with competition identity, venue context, kickoff framing, team names, and phase state.
- Roster sheet module for starters, bench, and staff context where available.
- Formation boards for both teams.
- Standings and context board modules.
- Storyline/studio-wrap panel for momentum, coaching, and commentary notes.
- Live broadcast window with scorebug, commentary ribbon, camera-state label, and scene-led sequencing.
- Halftime and full-time board staging through the broadcast scene flow.

## 3D Match Presentation Modules

- Real match scorebug tuned for clearer metadata chips and tighter truncation behavior.
- Commentary lower-third ribbon for event headline, context detail, and player/event timing.
- Tactical HUD for match state, shape summary, and active presentation context.
- Ratings strip and recap board for match-flow readability.
- Match-moment banner and replay control bar.
- Responsive premium-controls rail for render mode, camera options, slow motion, highlight unlocks, and tournament boost prompts.
- Event-continuation handling that now safely merges follow-on replay segments without controller lifecycle failures.

## Technical Corrections In This Pass

- Replaced the viewer state ticker strategy so repeated controller creation is valid across reloads and continuation merges.
- Fixed `MatchViewState.copyWith` so `nextSegmentToken` can be cleared instead of sticking on stale segment tokens.
- Removed the unstable horizontal-scroll workaround from the viewer shell and kept narrow layouts vertically coherent.
- Made the shared GTEX state panel responsive so loading and failure states do not overflow on small widths.
- Hardened premium control actions and scorebug chips against narrow or rail-sized truncation cases.

## What Remains Partial

- The 3D lane is still a Flutter-rendered presentation layer, not a native match engine.
- Player motion realism is presentation-driven rather than full skeletal simulation with foot IK, momentum blending, and rich contact animation families.
- Stadium mood is premium enough for a broadcast shell, but not yet a full atmosphere stack with deeper crowd logic, tunnel staging, volumetrics, or replay-grade environmental FX.
- Replay cameras are coherent and readable, but not yet a full multi-angle cinematic system with deep event-specific shot grammar and native replay capture.
- Close-up fidelity remains intentionally secondary to gameplay readability.

## Reality Check Against The Target

GTEX now substantially matches the requested direction at the presentation-system level: broadcast polish, information density, overlay quality, tactical readability, and route honesty are all materially stronger.

GTEX does not yet fully match EA FC / eFootball / Football Manager at the underlying engine level. It now resembles that target in broadcast packaging and match-day presentation more than in low-level native animation, physics, or stadium simulation.

## Files Changed In This Pass

- `docs/CODEX_MATCH_VISUAL_DIRECTION_REPORT.md`
- `frontend/lib/screens/match/gtex_match_viewer_screen.dart`
- `frontend/lib/widgets/gte_state_panel.dart`
- `frontend/lib/models/match_view_state.dart`
- `frontend/lib/widgets/match_3d/monetization/premium_controls.dart`
- `frontend/lib/features/match/presentation/widgets/real_match_scorebug_widget.dart`

## Verification

- `flutter analyze lib/screens/match/gtex_match_viewer_screen.dart lib/widgets/gte_state_panel.dart lib/models/match_view_state.dart lib/widgets/match_3d/monetization/premium_controls.dart lib/features/match/presentation/widgets/real_match_scorebug_widget.dart`
  - Result: no issues found.

- `flutter test test/match_viewer_screen_test.dart`
  - Result: 10 tests passed.

- `flutter test test/match_viewer_monetization_test.dart`
  - Result: 4 tests passed.

- `flutter test test/match_3d_screen_test.dart`
  - Result: 2 tests passed.

- `flutter test test/match_3d_route_truth_test.dart`
  - Result: 2 tests passed.
