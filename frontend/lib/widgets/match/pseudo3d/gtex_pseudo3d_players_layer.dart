import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_ball.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_pitch.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_player.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_shadow.dart';

class GtexPseudo3DPlayersLayer extends StatelessWidget {
  const GtexPseudo3DPlayersLayer({
    super.key,
    required this.viewState,
    required this.frame,
    required this.projection,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final GtexPseudo3DPitchProjection projection;

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
        .toList(growable: false)
      ..sort(
        (_ProjectedPlayer left, _ProjectedPlayer right) =>
            left.point.depth.compareTo(right.point.depth),
      );
    final GtexPseudo3DProjectedPoint ballPoint =
        projection.project(frame.ball.position);
    final double ballSize = 7 * ballPoint.scale;
    final double ballElevation = frame.ball.elevation * 10 * ballPoint.scale;
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        for (final _ProjectedPlayer projected in players)
          Positioned(
            left: projected.point.offset.dx - (10 * projected.point.scale),
            top: projected.point.offset.dy - (38 * projected.point.scale),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                SizedBox(height: 2 * projected.point.scale),
                GtexPseudo3DPlayer(
                  primaryColor: _kitColor(projected),
                  trimColor: _trimColor(projected),
                  scale: projected.point.scale,
                  highlighted: projected.player.highlighted,
                  label: projected.player.label,
                ),
                Transform.translate(
                  offset: Offset(0, -6 * projected.point.scale),
                  child: GtexPseudo3DShadow(
                    width: 14 * projected.point.scale,
                    height: 5 * projected.point.scale,
                    opacity: 0.22 + (projected.point.depth * 0.18),
                  ),
                ),
              ],
            ),
          ),
        Positioned(
          left: ballPoint.offset.dx - (ballSize / 2),
          top: ballPoint.offset.dy - ballSize - (ballElevation * 0.65),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              GtexPseudo3DBall(size: ballSize, elevation: ballElevation),
              Transform.translate(
                offset: Offset(0, -ballElevation * 0.15),
                child: GtexPseudo3DShadow(
                  width: ballSize * 1.5,
                  height: ballSize * 0.55,
                  opacity: 0.16,
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

Color _kitColor(_ProjectedPlayer projected) {
  final String value = projected.player.isGoalkeeper
      ? projected.team.goalkeeperColorHex
      : projected.team.primaryColorHex;
  return _parseColor(value);
}

Color _trimColor(_ProjectedPlayer projected) {
  return _parseColor(projected.team.secondaryColorHex);
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
