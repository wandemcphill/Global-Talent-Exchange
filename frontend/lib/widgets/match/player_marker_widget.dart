import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class PlayerMarkerWidget extends StatelessWidget {
  const PlayerMarkerWidget({
    super.key,
    required this.player,
    required this.team,
    required this.size,
  });

  final MatchViewerPlayerFrame player;
  final MatchViewerTeam team;
  final double size;

  @override
  Widget build(BuildContext context) {
    final bool isActive =
        player.active && player.state != MatchViewerPlayerState.sentOff;
    final Color baseColor = player.isGoalkeeper
        ? _parseColor(team.goalkeeperColorHex)
        : _parseColor(team.primaryColorHex);
    final Color borderColor = _parseColor(team.accentColorHex);
    final Color fillColor =
        isActive ? baseColor : baseColor.withValues(alpha: 0.24);
    final Color ringColor =
        isActive ? borderColor : borderColor.withValues(alpha: 0.24);
    final double markerSize = player.isGoalkeeper ? size * 1.04 : size;
    return IgnorePointer(
      child: SizedBox(
        width: markerSize * 1.8,
        height: markerSize * 1.8,
        child: Stack(
          alignment: Alignment.center,
          children: <Widget>[
            if (player.highlighted)
              Container(
                width: markerSize * 1.75,
                height: markerSize * 1.75,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: ringColor.withValues(alpha: 0.65),
                    width: 2,
                  ),
                ),
              ),
            Container(
              width: markerSize,
              height: markerSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: fillColor,
                border: Border.all(color: ringColor, width: 1.6),
              ),
              alignment: Alignment.center,
              child: Text(
                player.label,
                style: TextStyle(
                  color: _parseColor(team.secondaryColorHex),
                  fontSize: markerSize * 0.34,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
