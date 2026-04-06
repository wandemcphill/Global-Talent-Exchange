import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_telemetry.dart';

@immutable
class GtexPseudo3DBallVisualStyle {
  const GtexPseudo3DBallVisualStyle({
    required this.fillColor,
    required this.outlineColor,
    required this.haloColor,
    required this.trailColor,
    required this.shadowOpacity,
    required this.showHalo,
    required this.showRing,
    required this.showTrail,
    required this.attacksRight,
  });

  final Color fillColor;
  final Color outlineColor;
  final Color haloColor;
  final Color trailColor;
  final double shadowOpacity;
  final bool showHalo;
  final bool showRing;
  final bool showTrail;
  final bool attacksRight;
}

class GtexPseudo3DBall extends StatelessWidget {
  const GtexPseudo3DBall({
    super.key,
    required this.size,
    required this.elevation,
    required this.style,
  });

  static const Key trailKey = Key('pseudo3d-ball-trail');
  static const Key haloKey = Key('pseudo3d-ball-halo');
  static const Key ringKey = Key('pseudo3d-ball-ring');
  static const Key bodyKey = Key('pseudo3d-ball-body');

  final double size;
  final double elevation;
  final GtexPseudo3DBallVisualStyle style;

  static GtexPseudo3DBallVisualStyle describeVisualStyle({
    required MatchViewerBallFrame ball,
    required GtexPseudo3DTelemetryStyle telemetryStyle,
  }) {
    final String normalizedState = ball.state.trim().toLowerCase();
    final bool isShotState = switch (normalizedState) {
      'shot' || 'saved' || 'missed' || 'in_goal' => true,
      _ => false,
    };
    return GtexPseudo3DBallVisualStyle(
      fillColor: switch (normalizedState) {
        'saved' => const Color(0xFFD1E9FF),
        'missed' => const Color(0xFFFEE4A8),
        'in_goal' => const Color(0xFFFDE2E2),
        'placed' || 'set_piece' => const Color(0xFFFFF4CC),
        _ => Colors.white,
      },
      outlineColor:
          Color.lerp(
            const Color(0xFF101828),
            telemetryStyle.accentColor,
            isShotState ? 0.42 : 0.24,
          ) ??
          const Color(0xFF101828),
      haloColor: telemetryStyle.accentColor.withValues(
        alpha: 0.12 + (telemetryStyle.ballFocusBoost * 0.48),
      ),
      trailColor: telemetryStyle.accentColor.withValues(
        alpha:
            isShotState
                ? 0.24 + (telemetryStyle.pressureIndex * 0.16)
                : 0.14 + (telemetryStyle.pressureIndex * 0.10),
      ),
      shadowOpacity: (0.14 +
              (telemetryStyle.pressureIndex * 0.10) +
              (ball.elevation.clamp(0, 4) * 0.015))
          .clamp(0.14, 0.34),
      showHalo:
          telemetryStyle.showDangerOverlay ||
          telemetryStyle.showSetPieceOverlay ||
          isShotState ||
          ball.elevation > 0.2,
      showRing:
          isShotState ||
          telemetryStyle.showDangerOverlay ||
          telemetryStyle.showSetPieceOverlay,
      showTrail:
          isShotState ||
          telemetryStyle.showTransitionLane ||
          (telemetryStyle.showDangerOverlay &&
              telemetryStyle.pressureIndex >= 0.62),
      attacksRight: telemetryStyle.attacksRight,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Transform.translate(
      offset: Offset(0, -elevation),
      child: SizedBox(
        width: size * 1.9,
        height: size * 1.9,
        child: Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: <Widget>[
            if (style.showTrail)
              Align(
                alignment:
                    style.attacksRight
                        ? Alignment.centerLeft
                        : Alignment.centerRight,
                child: Container(
                  key: trailKey,
                  width: size * 1.25,
                  height: size * 0.62,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin:
                          style.attacksRight
                              ? Alignment.centerLeft
                              : Alignment.centerRight,
                      end:
                          style.attacksRight
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                      colors: <Color>[
                        style.trailColor,
                        style.trailColor.withValues(alpha: 0),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(size),
                  ),
                ),
              ),
            if (style.showHalo)
              Container(
                key: haloKey,
                width: size * 1.35,
                height: size * 1.35,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: style.haloColor,
                ),
              ),
            if (style.showRing)
              Container(
                key: ringKey,
                width: size * 1.15,
                height: size * 1.15,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: style.haloColor.withValues(alpha: 0.86),
                    width: 1.1,
                  ),
                ),
              ),
            Container(
              key: bodyKey,
              width: size,
              height: size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: style.fillColor,
                border: Border.all(color: style.outlineColor, width: 1.1),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: Colors.black.withValues(alpha: style.shadowOpacity),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
