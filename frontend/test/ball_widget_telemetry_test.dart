import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/ball_widget.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('ball visual style reacts to a high-pressure shot sequence', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[2].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.92,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[2].ball.copyWith(
        state: 'shot',
        elevation: 3.4,
        ownerPlayerId: 'home-9',
      ),
    );

    final BallVisualStyle style = BallWidget.describeVisualStyle(
      ball: frame.ball,
      telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
    );

    expect(style.showHalo, isTrue);
    expect(style.showRing, isTrue);
    expect(style.showTrail, isTrue);
    expect(style.lift, greaterThan(0.6));
    expect(style.haloScale, greaterThan(1.35));
    expect(style.fillColor, Colors.white);
  });

  test('ball visual style highlights set-piece placement without a trail', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[4].copyWith(
      possessionSide: MatchViewerSide.away,
      possessionPhase: MatchPossessionPhase.setPiece,
      transitionState: MatchTransitionState.awayReset,
      dangerZone: 'set_piece',
      pressureIndex: 0.64,
      frameTags: const <String>['set_piece'],
      ball: viewState.frames[4].ball.copyWith(
        state: 'placed',
        elevation: 0,
        ownerPlayerId: 'away-9',
      ),
    );

    final BallVisualStyle style = BallWidget.describeVisualStyle(
      ball: frame.ball,
      telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
    );

    expect(style.showHalo, isTrue);
    expect(style.showRing, isTrue);
    expect(style.showTrail, isFalse);
    expect(style.lift, 0);
    expect(style.fillColor, const Color(0xFFFFF4CC));
  });

  testWidgets('ball widget renders telemetry trail and ring for shot states', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[2].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.88,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[2].ball.copyWith(
        state: 'shot',
        elevation: 2.8,
        ownerPlayerId: 'home-9',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: BallWidget(
              ball: frame.ball,
              size: 14,
              telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(BallWidget.shadowKey), findsOneWidget);
    expect(find.byKey(BallWidget.trailKey), findsOneWidget);
    expect(find.byKey(BallWidget.haloKey), findsOneWidget);
    expect(find.byKey(BallWidget.ringKey), findsOneWidget);
    expect(find.byKey(BallWidget.bodyKey), findsOneWidget);

    final Container body = tester.widget<Container>(
      find.byKey(BallWidget.bodyKey),
    );
    final BoxDecoration decoration = body.decoration! as BoxDecoration;
    expect(decoration.boxShadow, isNotEmpty);
  });
}
