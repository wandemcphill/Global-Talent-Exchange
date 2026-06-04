import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_telemetry.dart';

@immutable
class PlayerMarkerVisualStyle {
  const PlayerMarkerVisualStyle({
    required this.fillColor,
    required this.ringColor,
    required this.labelColor,
    required this.haloColor,
    required this.badgeColor,
    required this.shadowColor,
    required this.haloScale,
    required this.markerScale,
    required this.borderWidth,
    required this.showHalo,
    required this.showPulseRing,
    required this.showBadge,
  });

  final Color fillColor;
  final Color ringColor;
  final Color labelColor;
  final Color haloColor;
  final Color badgeColor;
  final Color shadowColor;
  final double haloScale;
  final double markerScale;
  final double borderWidth;
  final bool showHalo;
  final bool showPulseRing;
  final bool showBadge;
}

class PlayerMarkerWidget extends StatelessWidget {
  const PlayerMarkerWidget({
    super.key,
    required this.player,
    required this.team,
    required this.size,
    required this.telemetryStyle,
    this.ballOwnerPlayerId,
  });

  static const Key haloKey = Key('player-marker-halo');
  static const Key pulseRingKey = Key('player-marker-pulse-ring');
  static const Key bodyKey = Key('player-marker-body');
  static const Key badgeKey = Key('player-marker-badge');

  final MatchViewerPlayerFrame player;
  final MatchViewerTeam team;
  final double size;
  final Pitch2dTelemetryStyle telemetryStyle;
  final String? ballOwnerPlayerId;

  static PlayerMarkerVisualStyle describeVisualStyle({
    required MatchViewerPlayerFrame player,
    required MatchViewerTeam team,
    required Pitch2dTelemetryStyle telemetryStyle,
    String? ballOwnerPlayerId,
  }) {
    final bool isActive =
        player.active && player.state != MatchViewerPlayerState.sentOff;
    final bool isBallOwner = ballOwnerPlayerId == player.playerId;
    final bool isPressing =
        player.state == MatchViewerPlayerState.pressing ||
        player.animationState == MatchPlayerAnimationState.press ||
        player.animationState == MatchPlayerAnimationState.tackle ||
        player.animationState == MatchPlayerAnimationState.intercept;
    final bool isHighSpeed =
        player.animationState == MatchPlayerAnimationState.sprint ||
        player.animationState == MatchPlayerAnimationState.run ||
        player.speedRatio >= 0.68;
    final double pressureIndex = telemetryStyle.pressureIndex.clamp(0.08, 1.0);
    final double staminaFactor = ((player.staminaPct.clamp(35, 100) - 35) / 65)
        .clamp(0.0, 1.0);
    final Color baseColor =
        player.isGoalkeeper
            ? _parseColor(team.goalkeeperColorHex)
            : _parseColor(team.primaryColorHex);
    final Color borderColor = _parseColor(team.accentColorHex);
    final Color labelColor = _parseColor(team.secondaryColorHex);
    final Color temperedBase =
        Color.lerp(
          baseColor,
          const Color(0xFF101828),
          (1 - staminaFactor) * 0.18,
        ) ??
        baseColor;
    final double focusBlend =
        isBallOwner
            ? 0.18 + (pressureIndex * 0.28)
            : isPressing
            ? 0.08 + (pressureIndex * 0.18)
            : isHighSpeed
            ? 0.05 + (pressureIndex * 0.10)
            : 0;
    final Color focusTint =
        Color.lerp(temperedBase, telemetryStyle.accentColor, focusBlend) ??
        temperedBase;
    final Color fillColor =
        isActive
            ? focusTint.withValues(alpha: 0.68 + (staminaFactor * 0.24))
            : focusTint.withValues(alpha: 0.24);
    final Color ringColor =
        Color.lerp(
          borderColor,
          telemetryStyle.accentColor,
          isBallOwner
              ? 0.56
              : isPressing
              ? 0.24
              : isHighSpeed
              ? 0.14
              : 0,
        ) ??
        borderColor;
    final bool showHalo =
        player.highlighted ||
        isBallOwner ||
        isPressing ||
        (isHighSpeed && pressureIndex >= 0.58);
    final bool showPulseRing =
        player.highlighted ||
        (isBallOwner &&
            (telemetryStyle.showDangerOverlay ||
                telemetryStyle.showSetPieceOverlay ||
                telemetryStyle.showTransitionLane)) ||
        (isPressing && pressureIndex >= 0.48);
    final bool showBadge = isBallOwner || isPressing || isHighSpeed;
    final Color haloColor =
        isBallOwner
            ? telemetryStyle.accentColor.withValues(
              alpha: 0.16 + (pressureIndex * 0.14),
            )
            : isPressing
            ? ringColor.withValues(alpha: 0.12 + (pressureIndex * 0.12))
            : ringColor.withValues(alpha: 0.08 + (pressureIndex * 0.08));
    final Color badgeColor =
        isBallOwner
            ? telemetryStyle.accentColor
            : isPressing
            ? ringColor
            : labelColor.withValues(alpha: 0.92);
    return PlayerMarkerVisualStyle(
      fillColor: fillColor,
      ringColor: isActive ? ringColor : ringColor.withValues(alpha: 0.28),
      labelColor: labelColor,
      haloColor: haloColor,
      badgeColor: badgeColor,
      shadowColor: haloColor,
      haloScale: (1.18 +
              (pressureIndex * 0.22) +
              (isBallOwner ? 0.20 : 0) +
              (isPressing ? 0.10 : 0))
          .clamp(1.16, 1.72),
      markerScale: (1 +
              (player.isGoalkeeper ? 0.04 : 0) +
              (player.speedRatio.clamp(0.0, 1.0) * 0.08) +
              (isBallOwner ? 0.10 : 0))
          .clamp(1.0, 1.26),
      borderWidth: (1.6 + (isBallOwner ? 0.5 : 0) + (isPressing ? 0.24 : 0))
          .clamp(1.4, 2.6),
      showHalo: showHalo,
      showPulseRing: showPulseRing,
      showBadge: showBadge,
    );
  }

  @override
  Widget build(BuildContext context) {
    final PlayerMarkerVisualStyle style = describeVisualStyle(
      player: player,
      team: team,
      telemetryStyle: telemetryStyle,
      ballOwnerPlayerId: ballOwnerPlayerId,
    );
    final double markerSize = player.isGoalkeeper ? size * 1.04 : size;
    return IgnorePointer(
      child: SizedBox(
        width: markerSize * 1.8,
        height: markerSize * 1.8,
        child: Stack(
          alignment: Alignment.center,
          children: <Widget>[
            if (style.showHalo)
              Container(
                key: haloKey,
                width: markerSize * style.haloScale,
                height: markerSize * style.haloScale,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: style.haloColor,
                ),
              ),
            if (style.showPulseRing)
              Container(
                key: pulseRingKey,
                width: markerSize * 1.62,
                height: markerSize * 1.62,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: style.ringColor.withValues(alpha: 0.7),
                    width: style.borderWidth,
                  ),
                ),
              ),
            Container(
              key: bodyKey,
              width: markerSize * style.markerScale,
              height: markerSize * style.markerScale,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: style.fillColor,
                border: Border.all(
                  color: style.ringColor,
                  width: style.borderWidth,
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: style.shadowColor,
                    blurRadius: 10,
                    spreadRadius: 0.5,
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: Text(
                player.label,
                style: TextStyle(
                  color: style.labelColor,
                  fontSize: markerSize * 0.34,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (style.showBadge)
              Positioned(
                key: badgeKey,
                top: markerSize * 0.16,
                right: markerSize * 0.16,
                child: Container(
                  width: markerSize * 0.32,
                  height: markerSize * 0.32,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: style.badgeColor,
                    border: Border.all(
                      color: style.labelColor.withValues(alpha: 0.88),
                      width: 1,
                    ),
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
