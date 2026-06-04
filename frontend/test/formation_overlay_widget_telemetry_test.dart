import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/formation_overlay_widget.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('formation overlay style reflects compactness and possession focus', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[1].copyWith(
      possessionSide: MatchViewerSide.home,
      possessionPhase: MatchPossessionPhase.finalThird,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'final_third',
      pressureIndex: 0.74,
      compactnessHome: 0.71,
      compactnessAway: 0.42,
      frameTags: const <String>['counter'],
    );

    final FormationOverlayStyle style = FormationOverlayWidget.describeStyle(
      frame,
      Pitch2dWidget.describeTelemetryStyle(frame),
    );

    expect(style.pressureIndex, closeTo(0.74, 0.0001));
    expect(style.homeCompactness, closeTo(0.71, 0.0001));
    expect(style.awayCompactness, closeTo(0.42, 0.0001));
    expect(style.possessionSide, MatchViewerSide.home);
    expect(style.showTransitionGuide, isTrue);
    expect(style.showSetPieceGuide, isFalse);
  });

  testWidgets('formation overlay mounts with telemetry-aware style', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[4].copyWith(
      possessionSide: MatchViewerSide.away,
      possessionPhase: MatchPossessionPhase.setPiece,
      transitionState: MatchTransitionState.awayReset,
      dangerZone: 'set_piece',
      pressureIndex: 0.66,
      compactnessHome: 0.58,
      compactnessAway: 0.64,
      frameTags: const <String>['set_piece'],
      ball: viewState.frames[4].ball.copyWith(ownerPlayerId: 'away-9'),
    );
    final FormationOverlayStyle style = FormationOverlayWidget.describeStyle(
      frame,
      Pitch2dWidget.describeTelemetryStyle(frame),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox.expand(
            child: FormationOverlayWidget(
              frame: frame,
              players: frame.players,
              style: style,
            ),
          ),
        ),
      ),
    );

    final FormationOverlayWidget overlay = tester
        .widget<FormationOverlayWidget>(find.byType(FormationOverlayWidget));
    expect(overlay.style.possessionSide, MatchViewerSide.away);
    expect(overlay.style.showSetPieceGuide, isTrue);
    expect(overlay.players, hasLength(frame.players.length));
  });
}
