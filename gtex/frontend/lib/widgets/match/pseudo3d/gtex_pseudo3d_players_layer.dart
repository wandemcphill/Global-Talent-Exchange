import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_ball.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_pitch.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_player.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_shadow.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_telemetry.dart';

class GtexPseudo3DPlayersLayer extends StatelessWidget {
  const GtexPseudo3DPlayersLayer({
    super.key,
    required this.viewState,
    required this.frame,
    required this.projection,
    required this.telemetryStyle,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final GtexPseudo3DPitchProjection projection;
  final GtexPseudo3DTelemetryStyle telemetryStyle;

  static GtexPseudo3DPlayerVisualStyle describePlayerStyle({
    required MatchViewerPlayerFrame player,
    required MatchViewerTeam team,
    required GtexPseudo3DTelemetryStyle telemetryStyle,
    required String? ballOwnerPlayerId,
  }) {
    final bool isBallOwner = ballOwnerPlayerId == player.playerId;
    final bool isPressing =
        player.state == MatchViewerPlayerState.pressing ||
        player.animationState == MatchPlayerAnimationState.press ||
        player.animationState == MatchPlayerAnimationState.tackle ||
        player.animationState == MatchPlayerAnimationState.intercept;
    final bool isBurstRunner =
        player.animationState == MatchPlayerAnimationState.sprint ||
        player.animationState == MatchPlayerAnimationState.run ||
        player.speedRatio >= 0.72;
    final Color baseColor = _parseColor(
      player.isGoalkeeper ? team.goalkeeperColorHex : team.primaryColorHex,
    );
    final Color trimColor = _parseColor(team.secondaryColorHex);
    final Color accentColor =
        isBallOwner
            ? telemetryStyle.accentColor
            : isPressing
            ? _parseColor(team.accentColorHex)
            : trimColor;
    return GtexPseudo3DPlayerVisualStyle(
      bodyColor:
          Color.lerp(
            baseColor,
            telemetryStyle.accentColor,
            isBallOwner
                ? 0.34
                : isPressing
                ? 0.16
                : isBurstRunner
                ? 0.10
                : 0,
          ) ??
          baseColor,
      trimColor: trimColor,
      outlineColor: accentColor,
      glowColor: accentColor.withValues(
        alpha:
            (player.highlighted || isBallOwner || isPressing)
                ? 0.18 + (telemetryStyle.playerFocusBoost * 0.50)
                : 0.08 + (telemetryStyle.playerFocusBoost * 0.24),
      ),
      scaleMultiplier:
          (1.0 +
                  (isBallOwner ? 0.14 : 0.0) +
                  (isPressing ? 0.08 : 0.0) +
                  (isBurstRunner ? 0.06 : 0.0))
              .clamp(1.0, 1.28)
              .toDouble(),
      borderWidth:
          (1.0 + (isBallOwner ? 0.4 : 0.0) + (isPressing ? 0.2 : 0.0))
              .clamp(1.0, 1.8)
              .toDouble(),
      showHalo: player.highlighted || isBallOwner || isPressing,
      showPulseRing:
          isBallOwner &&
          (telemetryStyle.showDangerOverlay ||
              telemetryStyle.showSetPieceOverlay ||
              telemetryStyle.showTransitionLane),
      showBadge: isBallOwner || isPressing || isBurstRunner,
      badgeColor: accentColor,
      labelColor:
          trimColor.computeLuminance() > 0.55 ? Colors.black : Colors.white,
      shadowOpacity: (0.20 +
              (telemetryStyle.pressureIndex * 0.12) +
              (isBallOwner ? 0.05 : 0))
          .clamp(0.18, 0.42),
    );
  }

  @override
  Widget build(BuildContext context) {
    final List<_ProjectedPlayer> players = frame.players
      .where(
        (MatchViewerPlayerFrame player) =>
            player.active || player.state == MatchViewerPlayerState.sentOff,
      )
      .map(
        (MatchViewerPlayerFrame player) => _ProjectedPlayer(
          player: player,
          point: projection.project(player.position),
          team: viewState.teamForSide(player.side),
        ),
      )
      .toList(growable: false)..sort(
      (_ProjectedPlayer left, _ProjectedPlayer right) =>
          left.point.depth.compareTo(right.point.depth),
    );
    final GtexPseudo3DProjectedPoint ballPoint = projection.project(
      frame.ball.position,
    );
    final double ballSize = 7 * ballPoint.scale;
    final double ballElevation = frame.ball.elevation * 10 * ballPoint.scale;
    final GtexPseudo3DBallVisualStyle ballStyle =
        GtexPseudo3DBall.describeVisualStyle(
          ball: frame.ball,
          telemetryStyle: telemetryStyle,
        );
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        for (final _ProjectedPlayer projected in players)
          Builder(
            builder: (BuildContext context) {
              final GtexPseudo3DPlayerVisualStyle playerStyle =
                  describePlayerStyle(
                    player: projected.player,
                    team: projected.team,
                    telemetryStyle: telemetryStyle,
                    ballOwnerPlayerId: frame.ball.ownerPlayerId,
                  );
              return Positioned(
                left: projected.point.offset.dx - (10 * projected.point.scale),
                top: projected.point.offset.dy - (38 * projected.point.scale),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    SizedBox(height: 2 * projected.point.scale),
                    GtexPseudo3DPlayer(
                      scale: projected.point.scale,
                      label: projected.player.label,
                      style: playerStyle,
                    ),
                    Transform.translate(
                      offset: Offset(0, -6 * projected.point.scale),
                      child: GtexPseudo3DShadow(
                        width:
                            14 *
                            projected.point.scale *
                            playerStyle.scaleMultiplier,
                        height: 5 * projected.point.scale,
                        opacity:
                            playerStyle.shadowOpacity +
                            (projected.point.depth * 0.12),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        Positioned(
          left: ballPoint.offset.dx - (ballSize / 2),
          top: ballPoint.offset.dy - ballSize - (ballElevation * 0.65),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              GtexPseudo3DBall(
                size: ballSize,
                elevation: ballElevation,
                style: ballStyle,
              ),
              Transform.translate(
                offset: Offset(0, -ballElevation * 0.15),
                child: GtexPseudo3DShadow(
                  width: ballSize * (ballStyle.showTrail ? 1.8 : 1.5),
                  height: ballSize * 0.55,
                  opacity: ballStyle.shadowOpacity,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProjectedPlayer {
  const _ProjectedPlayer({
    required this.player,
    required this.point,
    required this.team,
  });

  final MatchViewerPlayerFrame player;
  final GtexPseudo3DProjectedPoint point;
  final MatchViewerTeam team;
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
