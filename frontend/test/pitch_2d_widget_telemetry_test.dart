import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_telemetry.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';

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

      final Pitch2dTelemetryStyle style = MatchPitch2D.describeTelemetryStyle(
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
    },
  );

  test('2D marker and ball sizing stays in launch bounds', () {
    expect(MatchPitch2D.playerMarkerRadiusFor(const Size(180, 120)), 6);
    expect(MatchPitch2D.playerMarkerRadiusFor(const Size(1200, 760)), 10);
    expect(MatchPitch2D.ballRadiusFor(const Size(180, 120)), 4);
    expect(MatchPitch2D.ballRadiusFor(const Size(1200, 760)), 6);
  });

  test('pass and shot movement can draw a subtle ball trail', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame previous = viewState.frames[1].copyWith(
      ball: viewState.frames[1].ball.copyWith(
        position: const MatchViewerPoint(x: 42, y: 50),
        state: 'rolling',
      ),
    );
    final MatchTimelineFrame current = viewState.frames[2].copyWith(
      ball: viewState.frames[2].ball.copyWith(
        position: const MatchViewerPoint(x: 58, y: 50),
        state: 'pass',
      ),
    );
    final MatchEvent passEvent = viewState.events[1].copyWith(
      type: MatchViewerEventType.pass,
    );

    expect(
      MatchPitch2D.shouldShowBallTrail(
        previousFrame: previous,
        frame: current,
        activeEvent: passEvent,
      ),
      isTrue,
    );
    expect(
      MatchPitch2D.shouldShowBallTrail(
        previousFrame: previous,
        frame: previous,
        activeEvent: passEvent,
      ),
      isFalse,
    );
  });

  testWidgets('MatchPitch2D paints a scaled full pitch canvas', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 525,
              child: MatchPitch2D(
                viewState: viewState,
                frame: viewState.frames[1],
                previousFrame: viewState.frames.first,
                activeEvent: viewState.events[1],
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('match-pitch-2d-canvas')), findsOneWidget);
    final Size size = tester.getSize(find.byType(MatchPitch2D));
    expect(size.width, closeTo(525, 0.1));
    expect(size.width / size.height, closeTo(105 / 68, 0.01));
  });
}
