# CODEX Real 3D Match Engine Report

## Executive Summary

`/matches/3d/:matchKey` has been upgraded from a generic Flutter 3D replay surface into a structured GTEX real-match presentation lane. The route now stays truthfully disclosed as `FLUTTER_3D`, uses a dedicated event-driven scene director, exposes named camera presets, renders premium on-pitch overlays, and maps live/timeline events into readable scene changes, banners, and recap moments.

This pass did not turn GTEX into a native or Unity runtime. `/matches/native-3d` remains blocked. No backend adapter fields were added because the existing `match-viewer` and session payloads were sufficient for this phase.

## Changed Files

### Route and 3D lane wiring

- `frontend/lib/features/match/match_3d_route_screen.dart`
- `frontend/lib/screens/match/gtex_match_viewer_screen.dart`
- `frontend/lib/widgets/match_3d/gtex_3d_scene.dart`

### Real match-engine presentation models and director

- `frontend/lib/models/real_match_engine_presentation.dart`
- `frontend/lib/features/match/presentation/match_scene_director.dart`
- `frontend/lib/features/match/presentation/real_match_scene_director.dart`

### Match scene graph and 3D runtime readability

- `frontend/lib/models/match_3d_scene_graph.dart`
- `frontend/lib/services/match_3d_scene_manager.dart`
- `frontend/lib/models/player_entity.dart`
- `frontend/lib/models/ball_entity.dart`
- `frontend/lib/widgets/match_3d/entities/pitch_entity.dart`
- `frontend/lib/widgets/match_3d/entities/ball_entity.dart`

### Real 3D overlay widgets

- `frontend/lib/features/match/presentation/widgets/real_match_scorebug_widget.dart`
- `frontend/lib/features/match/presentation/widgets/real_match_tactical_hud_widget.dart`
- `frontend/lib/features/match/presentation/widgets/player_ratings_strip_widget.dart`
- `frontend/lib/features/match/presentation/widgets/match_moment_banner_widget.dart`
- `frontend/lib/features/match/presentation/widgets/match_recap_board_widget.dart`

### Tests

- `frontend/test/match_3d_route_truth_test.dart`
- `frontend/test/match_3d_bridge_scene_test.dart`
- `frontend/test/match_3d_screen_test.dart`
- `frontend/test/real_match_scene_director_test.dart`
- `frontend/test/real_match_overlay_widgets_test.dart`

## Scene System Implemented

### Scene director

The new `RealMatchSceneDirector` resolves a per-frame `MatchEnginePresentationState` from:

- `MatchViewState`
- current `MatchTimelineFrame`
- optional active `MatchEvent`
- broadcast package metadata
- playback time

It drives:

- scene state
- camera preset
- moment type (`live`, `replay`, `recap`)
- possession owner and team shape
- lower-third copy
- scorebug labels
- banners
- halftime/full-time summary boards

### Named camera presets

Implemented presets:

- `stadium_wide`
- `kickoff_center`
- `tactical_high`
- `attacking_third_left`
- `attacking_third_right`
- `defensive_block`
- `set_piece_left`
- `set_piece_right`
- `goal_replay`
- `halftime_board`
- `fulltime_board`

### Event-to-scene mapping

Implemented mappings:

- kickoff
- possession phase
- chance creation
- shot
- save
- goal
- foul
- booking
- substitution
- corner
- free kick
- penalty
- halftime
- fulltime

The mapping layer also handles payload gaps safely:

- set-piece subtype is inferred from event/banner text when the payload does not provide a stronger typed distinction
- overlays hide gracefully when banner or summary data is absent

### On-pitch readability improvements

The Flutter 3D lane was strengthened with:

- stronger player spacing bias to reduce bunching
- clearer facing direction using ball and movement context
- richer ball arc and elevation for passes and shots
- camera offsets tuned per named preset
- scene graph shape metadata for both teams
- active event context and possession metadata in the bridge payload

## Overlay System Implemented

`/matches/3d/:matchKey` now renders a dedicated 3D presentation overlay stack instead of the old generic scoreboard-first lane:

- premium scorebug
- match clock
- phase/state labels
- camera label
- lower-third commentary ribbon
- tactical HUD
- player ratings strip
- substitution and set-piece banners
- halftime/full-time recap boards

The overlay language is aligned with the broadcast package so `/matches/broadcast/:matchKey` and `/matches/3d/:matchKey` read as one product family.

## What Was Borrowed Conceptually From The Unity Uploads

The uploaded Unity projects were used as reference material only. No Unity assets or runtime code were transplanted into Flutter.

Concepts borrowed:

- staged match flow from `Fixture.cs` style phases such as possession buildup, advancement, chance creation, and scoring attempt
- manager-led simulation and presentation separation from `GameManager.cs`
- data-driven team/player ownership from the `Assets/Data/Teams` style organization in later episodes
- match UI layering from `MatchSimPageUI.cs` and event feed patterns from `MatchEventUI.cs`
- football-manager-style emphasis on information hierarchy over photoreal fidelity

Practical translation into GTEX:

- a Flutter scene director/state machine instead of Unity scene switching
- data-derived team shape and event context instead of prefab composition
- camera choreography and overlays tuned for tactical readability rather than close-up character fidelity

## What Remains Partial

- player rendering is still stylized Flutter 3D, not skeletal character animation
- replay moments are presentation reframes, not true buffered multi-angle replays
- set-piece subtype detection still uses heuristic text mapping when payload typing is limited
- no native `match_3d` runtime was introduced for `/matches/3d/:matchKey`
- `/matches/native-3d` remains blocked because there is still no shipped, verified native runtime lane behind that route

## Flutter 3D Phase 1 Assessment

Flutter 3D is now strong enough for GTEX phase 1 if the target is:

- tactical readability
- event choreography
- premium overlays
- coherent match-engine presentation
- honest shipped runtime behavior

Flutter 3D is not enough for:

- high-fidelity player animation
- realistic close-up replays
- complex collision/IK-heavy football motion
- console-style cinematic presentation

## Whether A Future Unity/Native Module Is Justified

Yes, but only for a later fidelity tier, not for this shipped phase.

A future Unity or native module becomes justified if GTEX wants:

- skeletal animation and animation blending beyond abstract motion states
- stored replay buffers with alternate angles
- richer ball physics and contact resolution
- crowd, lighting, and stadium effects beyond lightweight Flutter rendering
- a true native runtime lane that can honestly power `/matches/native-3d`

Current recommendation:

- keep shipping the upgraded Flutter 3D lane for phase 1
- keep `/matches/native-3d` blocked
- only introduce a Unity/native bridge when a real runtime module is ready end to end

## Backend Adapter Fields

No backend adapter fields were added in this pass.

Result:

- no backend code changes were required
- no backend tests were added because there was no backend surface change

## Test Commands And Results

Executed from `frontend/`:

- `flutter test test/match_3d_route_truth_test.dart` - passed
- `flutter test test/match_3d_bridge_scene_test.dart` - passed
- `flutter test test/match_3d_screen_test.dart` - passed
- `flutter test test/real_match_scene_director_test.dart` - passed
- `flutter test test/real_match_overlay_widgets_test.dart` - passed
- `flutter test test/navigation_surface_truth_test.dart` - passed

Coverage delivered by those tests:

- `/matches/3d/:matchKey` route truth
- scene director behavior
- event-to-scene mapping
- overlay widget rendering
- Flutter 3D bridge payload truth
- `/matches/native-3d` blocked truth

## Phase 1 Polish Addendum

This follow-up polish pass kept GTEX on the shipped Flutter 3D lane and focused on presentation quality rather than scope expansion.

### Polish areas completed

- smoother locomotion interpolation using curved movement and structured-phase easing in `frontend/lib/models/player_entity.dart`
- cleaner body orientation and momentum cues in `frontend/lib/widgets/match_3d/entities/player_entity.dart`
- better ball-flight readability with trajectory-aware trails and carry/pass/shot heuristics in `frontend/lib/controllers/match_3d_timeline_controller.dart` and `frontend/lib/widgets/match_3d/entities/ball_entity.dart`
- stronger camera easing by blending between pitch projections during preset changes in `frontend/lib/widgets/match_3d/gtex_3d_scene.dart`
- richer set-piece and replay handling in `frontend/lib/features/match/presentation/real_match_scene_director.dart`
- calmer overlay pacing and clearer hierarchy in `frontend/lib/screens/match/gtex_match_viewer_screen.dart`

### Polish pass test run

Executed from `frontend/`:

- `flutter test test/match_3d_route_truth_test.dart test/match_3d_bridge_scene_test.dart test/match_3d_screen_test.dart test/real_match_scene_director_test.dart test/real_match_overlay_widgets_test.dart test/navigation_surface_truth_test.dart` - passed
