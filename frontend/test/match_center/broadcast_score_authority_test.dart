import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/controllers/gtex_match_overlay_controller.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/models/match_viewer_presentation.dart';
import 'package:gte_frontend/features/match_center/presentation/broadcast_package_repository.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_scoreboard_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast_overlays.dart';
import 'package:gte_frontend/features/match_center/widgets/scoreboard_widget.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('broadcast overlays mask absent score authority', (
    WidgetTester tester,
  ) async {
    final MatchViewState viewState = buildBroadcastTestViewState();
    const GtexBroadcastHudState hudState = GtexBroadcastHudState(
      clockLabel: "64'",
      statusLabel: 'LIVE',
      scoreMasked: false,
      controlsVisible: false,
      isPaused: false,
      speedLabel: '1x',
      mode: GtexMatchRenderMode.standard,
      viewType: GtexMatchViewType.twoD,
    );

    await tester.pumpWidget(
      _app(GtexScoreboardOverlay(viewState: viewState, hudState: hudState)),
    );

    expect(find.text('--'), findsNWidgets(2));
    expect(find.text('--:--'), findsOneWidget);
    expect(find.text("64'"), findsNothing);
    expect(find.text('0'), findsNothing);

    await tester.pumpWidget(
      _app(
        BroadcastScoreboardWidget(
          viewState: viewState,
          clockLabel: "64'",
          homeScore: null,
          awayScore: null,
          scoreMasked: false,
          statusLabel: 'LIVE',
          cameraPreset: BroadcastCameraPreset.broadcast,
        ),
      ),
    );

    expect(find.text('--'), findsNWidgets(2));
    expect(find.text('--:--'), findsOneWidget);
    expect(find.text("64'"), findsNothing);
    expect(find.text('0'), findsNothing);
  });

  testWidgets('timeline scoreboard masks score-reveal locked matches', (
    WidgetTester tester,
  ) async {
    final MatchViewState viewState = buildBroadcastTestViewState().copyWith(
      scoreRevealLocked: true,
    );

    await tester.pumpWidget(
      _app(
        ScoreboardWidget(
          viewState: viewState,
          frame: viewState.lastFrame,
          activeEvent: null,
        ),
      ),
    );

    expect(find.text('--'), findsNWidgets(3));
    expect(find.text('--:--'), findsOneWidget);
    expect(find.text('1H'), findsNothing);
    expect(find.text('2H'), findsNothing);
    expect(find.text('1'), findsNothing);
    expect(find.text('0'), findsNothing);
  });

  test('broadcast hud hides event overlays without score authority', () {
    final MatchViewState viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames.firstWhere(
      (MatchTimelineFrame frame) => frame.activeEventId == 'goal-home',
    );
    final GtexMatchOverlayController controller = GtexMatchOverlayController();

    final GtexBroadcastHudState maskedHud = controller.buildHudState(
      viewState: viewState,
      mode: GtexMatchRenderMode.standard,
      viewType: GtexMatchViewType.twoD,
      frame: frame,
      viewerSeconds: frame.timeSeconds,
      isPaused: false,
      speedLabel: '1x',
      scoreMasked: true,
      homeScore: null,
      awayScore: null,
      spectatorMode: true,
      isFullTime: false,
    );

    expect(maskedHud.scoreMasked, isTrue);
    expect(maskedHud.clockLabel, '--:--');
    expect(maskedHud.eventOverlay, isNull);
    expect(maskedHud.varOverlay, isNull);
    expect(maskedHud.commentary, isNull);
    expect(maskedHud.commentaryDetail, isNull);

    final GtexBroadcastHudState absentScoreHud = controller.buildHudState(
      viewState: viewState,
      mode: GtexMatchRenderMode.standard,
      viewType: GtexMatchViewType.twoD,
      frame: frame,
      viewerSeconds: frame.timeSeconds,
      isPaused: false,
      speedLabel: '1x',
      scoreMasked: false,
      homeScore: null,
      awayScore: null,
      spectatorMode: true,
      isFullTime: false,
    );

    expect(absentScoreHud.scoreMasked, isTrue);
    expect(absentScoreHud.eventOverlay, isNull);
    expect(absentScoreHud.varOverlay, isNull);
    expect(absentScoreHud.commentary, isNull);
    expect(absentScoreHud.commentaryDetail, isNull);
  });

  test('storyline panel omits event-derived timeline lines while locked', () {
    final MatchViewState baseViewState = buildBroadcastTestViewState();
    final MatchViewState eventfulViewState = baseViewState.copyWith(
      events: <MatchEvent>[...baseViewState.events, _redCardEvent()],
    );
    const BroadcastPackageRepository repository = BroadcastPackageRepository();

    final unlocked = repository.resolveBroadcastData(
      matchKey: 'authority-unlocked',
      viewState: eventfulViewState,
    );
    expect(
      unlocked.storylinePanel.suspensions,
      contains("77' Lagos Stars: Test Defender sent off"),
    );

    final locked = repository.resolveBroadcastData(
      matchKey: 'authority-locked',
      viewState: eventfulViewState.copyWith(scoreRevealLocked: true),
    );
    expect(locked.storylinePanel.suspensions, isEmpty);
    expect(
      locked.storylinePanel.visibleBuckets
          .expand((bucket) => bucket.items)
          .where((String item) => item.contains("77'")),
      isEmpty,
    );
  });
}

MatchEvent _redCardEvent() {
  return const MatchEvent(
    id: 'red-card-authority-test',
    sequence: 99,
    type: MatchViewerEventType.redCard,
    minute: 77,
    addedTime: 0,
    clockLabel: "77'",
    timeSeconds: 77,
    homeScore: 1,
    awayScore: 0,
    bannerText: 'Red card',
    commentary: 'Test Defender is sent off.',
    emphasisLevel: 4,
    highlightedPlayerIds: <String>['home-5'],
    flags: <String>[],
    teamId: 'home',
    teamName: 'Lagos Stars',
    primaryPlayerId: 'home-5',
    primaryPlayerName: 'Test Defender',
  );
}

Widget _app(Widget child) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: Scaffold(body: Center(child: child)),
  );
}
