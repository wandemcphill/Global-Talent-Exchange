# GTEX Broadcast Package Report

## Executive Summary

- Built a new GTEX broadcast presentation layer for `/matches/broadcast/:matchKey` on the active Flutter shell without reviving any legacy shell runtime.
- Replaced the older generic package page with a scene-driven Football Manager style broadcast layout: title banner, official roster card, formation boards, standings/context board, storyline side panel, live scorebug, commentary ribbon, and halftime/full-time studio wrap.
- Kept the live route grounded in existing GTEX contracts by reusing the active `match-viewer` and `match-viewer/session` payloads, then deriving frontend presentation state from those payloads.
- Limited backend contract churn to presentation-safe identity fields on the existing `presentation_package`: team crest metadata and team color fields. Also removed fallback reaction copy so the frontend can hide absent modules instead of narrating invented states.
- Preserved the truth boundary around `/matches/native-3d`; no native bridge was introduced and native 3D remains blocked outside the verified route gate.

## Changed Files

### Backend

- `backend/app/schemas/match_viewer.py`
- `backend/app/services/match_viewer_presentation_service.py`
- `backend/tests/test_match_viewer_route.py`

### Frontend route and presentation layer

- `frontend/lib/features/match/match_broadcast_screen.dart`
- `frontend/lib/features/match/presentation/broadcast_package_models.dart`
- `frontend/lib/features/match/presentation/broadcast_package_repository.dart`
- `frontend/lib/features/match/presentation/broadcast_package_screen.dart`
- `frontend/lib/features/match/presentation/broadcast_scene_director.dart`
- `frontend/lib/features/match/presentation/match_scene_director.dart`
- `frontend/lib/features/match/presentation/pre_match_package_screen.dart`
- `frontend/lib/features/match/presentation/widgets/commentary_ribbon_widget.dart`
- `frontend/lib/features/match/presentation/widgets/formation_board_widget.dart`
- `frontend/lib/features/match/presentation/widgets/match_header_widget.dart`
- `frontend/lib/features/match/presentation/widgets/match_scorebar_widget.dart`
- `frontend/lib/features/match/presentation/widgets/reaction_panel_widget.dart`
- `frontend/lib/features/match/presentation/widgets/roster_card_widget.dart`
- `frontend/lib/features/match/presentation/widgets/scorebug_widget.dart`
- `frontend/lib/features/match/presentation/widgets/standings_context_widget.dart`
- `frontend/lib/features/match/presentation/widgets/storyline_panel_widget.dart`

### Frontend tests and fixtures

- `frontend/test/match_broadcast_route_screen_test.dart`
- `frontend/test/match_presentation_widgets_test.dart`
- `frontend/test/match_scene_director_test.dart`
- `frontend/test/support/gtex_match_broadcast_fixture.dart`

## Module Ownership Map

- `backend/app/services/match_viewer_presentation_service.py`
  - Owns backend presentation-package enrichment for crest/color identity and safe no-fake fallback behavior.

- `frontend/lib/features/match/presentation/broadcast_package_models.dart`
  - Owns raw presentation DTO parsing plus derived broadcast-storyline panel models.

- `frontend/lib/features/match/presentation/broadcast_package_repository.dart`
  - Owns safe frontend derivation from `MatchViewState`: fallback lineup extraction, context normalization, and storyline bucket assembly from verified live/session data.

- `frontend/lib/features/match/presentation/broadcast_package_screen.dart`
  - Owns `/matches/broadcast/:matchKey` page composition, scene switching, layout, live broadcast lane, and graceful module gating.

- `frontend/lib/features/match/presentation/broadcast_scene_director.dart`
  - Owns package sequencing: pre-match, lineup, context, kickoff transition, live, halftime, and full-time scene selection plus camera-state mapping.

- `frontend/lib/features/match/presentation/widgets/match_header_widget.dart`
  - Owns the title banner and team crest rendering.

- `frontend/lib/features/match/presentation/widgets/roster_card_widget.dart`
  - Owns the official roster card with starters, substitutes, managers, and referee surface.

- `frontend/lib/features/match/presentation/widgets/formation_board_widget.dart`
  - Owns the formation boards and player position layout.

- `frontend/lib/features/match/presentation/widgets/standings_context_widget.dart`
  - Owns standings snapshot, recent form, and competition context presentation.

- `frontend/lib/features/match/presentation/widgets/storyline_panel_widget.dart`
  - Owns staff notes, press/social roundup, injuries, suspensions, lineup changes, and talking-points side panel rendering.

- `frontend/lib/features/match/presentation/widgets/scorebug_widget.dart`
  - Owns the live scorebug/event ribbon.

- `frontend/lib/features/match/presentation/widgets/commentary_ribbon_widget.dart`
  - Owns the lower-third commentary strip.

## Test Commands and Results

- `flutter test test/match_presentation_widgets_test.dart test/match_broadcast_route_screen_test.dart test/match_scene_director_test.dart test/active_shell_route_mount_test.dart test/match_3d_route_truth_test.dart`
  - Passed.
  - Covered widget rendering for roster card, formation board, standings/context board, storyline panel, scorebug, commentary ribbon, the broadcast route mount, active-shell routing, scene sequencing, graceful degradation, and native-3D truth behavior.

- `python -m pytest backend/tests/test_match_viewer_route.py`
  - Passed.
  - Covered match-viewer presentation package enrichment and live/broadcast route contract alignment.

## What Remains Partial

- Player portraits are still intentionally absent because no verified portrait/image field is available on the live match payloads; the formation boards only render portraits when real image data exists.
- The storyline side panel derives injuries, suspensions, and lineup changes from verified visible live events and safe presentation-package buckets. It does not invent pre-match availability data that the current live contracts do not expose.
- Team crests now use real presentation identity when available from backend replay/visual identity data. When no crest artwork URL exists, the frontend falls back to a styled identity mark built from real team codes/colors rather than claiming a real crest image.
- `/matches/native-3d` remains blocked. No native bridge was added.
