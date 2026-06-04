import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';
import 'package:gte_frontend/features/match_center/widgets/player_marker_widget.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test(
    'player marker visual style emphasizes possession carrier in danger',
    () {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame frame = viewState.frames[2].copyWith(
        possessionPhase: MatchPossessionPhase.boxAttack,
        transitionState: MatchTransitionState.homeBreak,
        dangerZone: 'box',
        pressureIndex: 0.9,
        frameTags: const <String>['counter', 'box_entry'],
        ball: viewState.frames[2].ball.copyWith(ownerPlayerId: 'home-9'),
      );
      final MatchViewerPlayerFrame striker = frame.players
          .firstWhere(
            (MatchViewerPlayerFrame player) => player.playerId == 'home-9',
          )
          .copyWith(
            animationState: MatchPlayerAnimationState.sprint,
            speedRatio: 0.88,
            staminaPct: 84,
          );

      final PlayerMarkerVisualStyle style =
          PlayerMarkerWidget.describeVisualStyle(
            player: striker,
            team: viewState.homeTeam,
            telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
            ballOwnerPlayerId: frame.ball.ownerPlayerId,
          );

      expect(style.showHalo, isTrue);
      expect(style.showPulseRing, isTrue);
      expect(style.showBadge, isTrue);
      expect(style.haloScale, greaterThan(1.45));
      expect(style.markerScale, greaterThan(1.12));
      expect(style.borderWidth, greaterThan(2.0));
    },
  );

  test(
    'player marker visual style keeps pressing defender visible off-ball',
    () {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame frame = viewState.frames[4].copyWith(
        possessionSide: MatchViewerSide.home,
        possessionPhase: MatchPossessionPhase.transition,
        transitionState: MatchTransitionState.homeBreak,
        dangerZone: 'middle_third',
        pressureIndex: 0.76,
        frameTags: const <String>['counter'],
        ball: viewState.frames[4].ball.copyWith(ownerPlayerId: 'home-9'),
      );
      final MatchViewerPlayerFrame defender = frame.players
          .firstWhere(
            (MatchViewerPlayerFrame player) => player.playerId == 'away-4',
          )
          .copyWith(
            state: MatchViewerPlayerState.pressing,
            animationState: MatchPlayerAnimationState.press,
            speedRatio: 0.73,
            staminaPct: 71,
          );

      final PlayerMarkerVisualStyle style =
          PlayerMarkerWidget.describeVisualStyle(
            player: defender,
            team: viewState.awayTeam,
            telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
            ballOwnerPlayerId: frame.ball.ownerPlayerId,
          );

      expect(style.showHalo, isTrue);
      expect(style.showPulseRing, isTrue);
      expect(style.showBadge, isTrue);
      expect(style.markerScale, lessThan(1.16));
      expect(style.haloScale, greaterThan(1.3));
    },
  );

  testWidgets('player marker renders telemetry halo and badge for carrier', (
    WidgetTester tester,
  ) async {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[2].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.88,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[2].ball.copyWith(ownerPlayerId: 'home-9'),
    );
    final MatchViewerPlayerFrame striker = frame.players
        .firstWhere(
          (MatchViewerPlayerFrame player) => player.playerId == 'home-9',
        )
        .copyWith(
          animationState: MatchPlayerAnimationState.control,
          speedRatio: 0.82,
        );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: PlayerMarkerWidget(
              player: striker,
              team: viewState.homeTeam,
              size: 24,
              telemetryStyle: Pitch2dWidget.describeTelemetryStyle(frame),
              ballOwnerPlayerId: frame.ball.ownerPlayerId,
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(PlayerMarkerWidget.haloKey), findsOneWidget);
    expect(find.byKey(PlayerMarkerWidget.pulseRingKey), findsOneWidget);
    expect(find.byKey(PlayerMarkerWidget.badgeKey), findsOneWidget);

    final Container body = tester.widget<Container>(
      find.byKey(PlayerMarkerWidget.bodyKey),
    );
    final BoxDecoration decoration = body.decoration! as BoxDecoration;
    expect(decoration.boxShadow, isNotEmpty);
  });
}
