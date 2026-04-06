import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_ball.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_match_canvas.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_players_layer.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('pseudo-3D telemetry style tightens camera for danger moments', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[2].copyWith(
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.9,
      frameTags: const <String>['counter', 'box_entry'],
      ball: viewState.frames[2].ball.copyWith(
        position: const MatchViewerPoint(x: 83, y: 43),
        ownerPlayerId: 'home-9',
        state: 'shot',
        elevation: 2.6,
      ),
    );

    final style = GtexPseudo3DMatchCanvas.describeTelemetryStyle(
      frame: frame,
      mode: GtexMatchRenderMode.cinematic,
    );

    expect(style.showDangerOverlay, isTrue);
    expect(style.showBoxOverlay, isTrue);
    expect(style.showTransitionLane, isTrue);
    expect(style.showSetPieceOverlay, isFalse);
    expect(style.cameraZoomBias, greaterThan(0.12));
    expect(style.cameraLeadX, greaterThan(0));
    expect(style.crowdGlowAlpha, greaterThan(0.18));
  });

  test('pseudo-3D player and ball styles reflect possession and restarts', () {
    final viewState = buildBroadcastTestViewState();
    final MatchTimelineFrame frame = viewState.frames[4].copyWith(
      possessionSide: MatchViewerSide.away,
      possessionPhase: MatchPossessionPhase.setPiece,
      transitionState: MatchTransitionState.awayReset,
      dangerZone: 'set_piece',
      pressureIndex: 0.66,
      frameTags: const <String>['set_piece'],
      ball: viewState.frames[4].ball.copyWith(
        ownerPlayerId: 'away-9',
        state: 'placed',
      ),
    );
    final style = GtexPseudo3DMatchCanvas.describeTelemetryStyle(
      frame: frame,
      mode: GtexMatchRenderMode.standard,
    );
    final MatchViewerPlayerFrame taker = frame.players
        .firstWhere(
          (MatchViewerPlayerFrame player) => player.playerId == 'away-9',
        )
        .copyWith(
          animationState: MatchPlayerAnimationState.setPiece,
          speedRatio: 0.24,
        );

    final playerStyle = GtexPseudo3DPlayersLayer.describePlayerStyle(
      player: taker,
      team: viewState.awayTeam,
      telemetryStyle: style,
      ballOwnerPlayerId: frame.ball.ownerPlayerId,
    );
    final ballStyle = GtexPseudo3DBall.describeVisualStyle(
      ball: frame.ball,
      telemetryStyle: style,
    );

    expect(style.showSetPieceOverlay, isTrue);
    expect(style.cameraLeadX, lessThan(0));
    expect(playerStyle.showHalo, isTrue);
    expect(playerStyle.showBadge, isTrue);
    expect(playerStyle.scaleMultiplier, greaterThan(1.1));
    expect(ballStyle.showHalo, isTrue);
    expect(ballStyle.showRing, isTrue);
    expect(ballStyle.showTrail, isFalse);
    expect(ballStyle.fillColor, const Color(0xFFFFF4CC));
  });
}
