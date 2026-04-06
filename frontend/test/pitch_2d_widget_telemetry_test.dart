import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/ball_widget.dart';
import 'package:gte_frontend/widgets/match/formation_overlay_widget.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_telemetry.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/player_marker_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test(
    'pitch telemetry style reflects pressure, danger, transition, and shape',
    () {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame frame = viewState.frames[1].copyWith(
        possessionPhase: MatchPossessionPhase.boxAttack,
        transitionState: MatchTransitionState.homeBreak,
        dangerZone: 'box',
        pressureIndex: 0.88,
        compactnessHome: 0.72,
        compactnessAway: 0.39,
        frameTags: const <String>['counter', 'box_entry'],
        ball: viewState.frames[1].ball.copyWith(
          position: const MatchViewerPoint(x: 82, y: 44),
        ),
      );

      final Pitch2dTelemetryStyle style = Pitch2dWidget.describeTelemetryStyle(
        frame,
      );

      expect(style.pressureIndex, closeTo(0.88, 0.0001));
      expect(style.showDangerOverlay, isTrue);
      expect(style.showBoxOverlay, isTrue);
      expect(style.showTransitionLane, isTrue);
      expect(style.showSetPieceOverlay, isFalse);
      expect(style.attacksRight, isTrue);
      expect(style.homeCompactness, closeTo(0.72, 0.0001));
      expect(style.awayCompactness, closeTo(0.39, 0.0001));
      expect(style.accentColor, const Color(0xFFF97066));
      expect(style.fieldGradient, hasLength(3));
    },
  );

  test('pitch telemetry style flags restart and away attack orientation', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[4].copyWith(
      possessionSide: MatchViewerSide.away,
      possessionPhase: MatchPossessionPhase.setPiece,
      transitionState: MatchTransitionState.awayReset,
      dangerZone: 'set_piece',
      pressureIndex: 0.64,
      frameTags: const <String>['set_piece'],
      ball: viewState.frames[4].ball.copyWith(
        position: const MatchViewerPoint(x: 18, y: 62),
        state: 'placed',
      ),
    );

    final Pitch2dTelemetryStyle style = Pitch2dWidget.describeTelemetryStyle(
      frame,
    );

    expect(style.showSetPieceOverlay, isTrue);
    expect(style.showTransitionLane, isFalse);
    expect(style.showDangerOverlay, isFalse);
    expect(style.attacksRight, isFalse);
    expect(style.accentColor, const Color(0xFFFDB022));
  });

  testWidgets('pitch widget wires telemetry style into the overlay layer', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[1].copyWith(
      possessionPhase: MatchPossessionPhase.finalThird,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'final_third',
      pressureIndex: 0.74,
      compactnessHome: 0.67,
      compactnessAway: 0.44,
      frameTags: const <String>['counter'],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 900,
              child: Pitch2dWidget(viewState: viewState, frame: frame),
            ),
          ),
        ),
      ),
    );

    expect(find.byType(Pitch2dTelemetryOverlay), findsOneWidget);
    final Pitch2dTelemetryOverlay overlay = tester
        .widget<Pitch2dTelemetryOverlay>(find.byType(Pitch2dTelemetryOverlay));
    expect(overlay.style.showDangerOverlay, isTrue);
    expect(overlay.style.showTransitionLane, isTrue);
    expect(overlay.style.showSetPieceOverlay, isFalse);
    expect(overlay.style.dangerZone, 'final_third');
    expect(overlay.style.pressureIndex, closeTo(0.74, 0.0001));

    final DecoratedBox decoratedBox = tester.widget<DecoratedBox>(
      find
          .descendant(
            of: find.byType(Pitch2dWidget),
            matching: find.byType(DecoratedBox),
          )
          .first,
    );
    final BoxDecoration decoration = decoratedBox.decoration as BoxDecoration;
    final LinearGradient gradient = decoration.gradient! as LinearGradient;
    expect(gradient.colors, overlay.style.fieldGradient);
  });

  testWidgets('pitch widget passes telemetry style into actor widgets', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[2].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.91,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[2].ball.copyWith(
        ownerPlayerId: 'home-9',
        state: 'shot',
        elevation: 2.4,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 900,
              child: Pitch2dWidget(viewState: viewState, frame: frame),
            ),
          ),
        ),
      ),
    );

    final Pitch2dTelemetryOverlay overlay = tester
        .widget<Pitch2dTelemetryOverlay>(find.byType(Pitch2dTelemetryOverlay));
    final List<PlayerMarkerWidget> playerWidgets = tester
        .widgetList<PlayerMarkerWidget>(find.byType(PlayerMarkerWidget))
        .toList(growable: false);
    final FormationOverlayWidget formationOverlay = tester
        .widget<FormationOverlayWidget>(find.byType(FormationOverlayWidget));
    final BallWidget ballWidget = tester.widget<BallWidget>(
      find.byType(BallWidget),
    );

    expect(playerWidgets, isNotEmpty);
    expect(
      playerWidgets.every(
        (PlayerMarkerWidget widget) =>
            identical(widget.telemetryStyle, overlay.style),
      ),
      isTrue,
    );
    expect(
      playerWidgets.any(
        (PlayerMarkerWidget widget) =>
            widget.ballOwnerPlayerId == frame.ball.ownerPlayerId,
      ),
      isTrue,
    );
    expect(formationOverlay.frame.id, frame.id);
    expect(formationOverlay.style.possessionSide, MatchViewerSide.home);
    expect(formationOverlay.style.showTransitionGuide, isTrue);
    expect(identical(ballWidget.telemetryStyle, overlay.style), isTrue);
    expect(ballWidget.ball.state, 'shot');
    expect(ballWidget.ball.ownerPlayerId, 'home-9');
  });
}
