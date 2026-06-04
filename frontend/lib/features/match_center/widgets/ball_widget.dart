import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_telemetry.dart';

@immutable
class BallVisualStyle {
  const BallVisualStyle({
    required this.fillColor,
    required this.outlineColor,
    required this.haloColor,
    required this.shadowColor,
    required this.trailColor,
    required this.lift,
    required this.haloScale,
    required this.showHalo,
    required this.showRing,
    required this.showTrail,
  });

  final Color fillColor;
  final Color outlineColor;
  final Color haloColor;
  final Color shadowColor;
  final Color trailColor;
  final double lift;
  final double haloScale;
  final bool showHalo;
  final bool showRing;
  final bool showTrail;
}

class BallWidget extends StatelessWidget {
  const BallWidget({
    super.key,
    required this.ball,
    required this.size,
    required this.telemetryStyle,
  });

  static const Key shadowKey = Key('ball-shadow');
  static const Key trailKey = Key('ball-trail');
  static const Key haloKey = Key('ball-halo');
  static const Key ringKey = Key('ball-ring');
  static const Key bodyKey = Key('ball-body');

  final MatchViewerBallFrame ball;
  final double size;
  final Pitch2dTelemetryStyle telemetryStyle;

  static BallVisualStyle describeVisualStyle({
    required MatchViewerBallFrame ball,
    required Pitch2dTelemetryStyle telemetryStyle,
  }) {
    final String normalizedState = ball.state.trim().toLowerCase();
    final double pressureIndex = telemetryStyle.pressureIndex.clamp(0.08, 1.0);
    final bool isShotState = switch (normalizedState) {
      'shot' || 'saved' || 'missed' || 'in_goal' => true,
      _ => false,
    };
    final bool isPlacedState =
        normalizedState == 'placed' || normalizedState == 'set_piece';
    final Color fillColor = switch (normalizedState) {
      'saved' => const Color(0xFFD1E9FF),
      'missed' => const Color(0xFFFEE4A8),
      'in_goal' => const Color(0xFFFDE2E2),
      'placed' || 'set_piece' => const Color(0xFFFFF4CC),
      'shot' => const Color(0xFFFFFFFF),
      _ => Colors.white,
    };
    final Color accentColor = switch (normalizedState) {
      'saved' => const Color(0xFF53B1FD),
      'missed' => const Color(0xFFF79009),
      'in_goal' => const Color(0xFFF04438),
      'placed' || 'set_piece' => const Color(0xFFFDB022),
      'shot' => telemetryStyle.accentColor,
      _ =>
        telemetryStyle.showSetPieceOverlay
            ? const Color(0xFFFDB022)
            : telemetryStyle.showDangerOverlay
            ? telemetryStyle.accentColor
            : telemetryStyle.showTransitionLane
            ? const Color(0xFF53B1FD)
            : const Color(0xFFEAECF0),
    };
    return BallVisualStyle(
      fillColor: fillColor,
      outlineColor:
          Color.lerp(const Color(0xFF0F172A), accentColor, 0.34) ??
          const Color(0xFF0F172A),
      haloColor: accentColor.withValues(
        alpha: 0.12 + (pressureIndex * (isShotState ? 0.16 : 0.10)),
      ),
      shadowColor: const Color(
        0xFF0F172A,
      ).withValues(alpha: 0.14 + (pressureIndex * 0.10)),
      trailColor: accentColor.withValues(
        alpha:
            isShotState
                ? 0.24 + (pressureIndex * 0.14)
                : 0.14 + (pressureIndex * 0.10),
      ),
      lift: (ball.elevation.clamp(0, 6) * 0.22).clamp(0, 1.2),
      haloScale: (1.14 +
              (pressureIndex * 0.22) +
              (isShotState ? 0.12 : 0) +
              (isPlacedState ? 0.08 : 0))
          .clamp(1.12, 1.56),
      showHalo:
          telemetryStyle.showDangerOverlay ||
          telemetryStyle.showSetPieceOverlay ||
          telemetryStyle.showTransitionLane ||
          isShotState ||
          ball.elevation > 0.18,
      showRing:
          isShotState ||
          isPlacedState ||
          telemetryStyle.showDangerOverlay ||
          pressureIndex >= 0.72,
      showTrail:
          isShotState ||
          telemetryStyle.showTransitionLane ||
          (telemetryStyle.showDangerOverlay && pressureIndex >= 0.62),
    );
  }

  @override
  Widget build(BuildContext context) {
    final BallVisualStyle style = describeVisualStyle(
      ball: ball,
      telemetryStyle: telemetryStyle,
    );
    final Alignment trailAlignment =
        telemetryStyle.attacksRight
            ? Alignment.centerLeft
            : Alignment.centerRight;
    return IgnorePointer(
      child: SizedBox(
        width: size * 1.8,
        height: size * 1.8,
        child: Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.center,
          children: <Widget>[
            Container(
              key: shadowKey,
              width: size * (0.76 - (style.lift * 0.14)),
              height: size * 0.32,
              decoration: BoxDecoration(
                color: style.shadowColor,
                borderRadius: BorderRadius.circular(size),
              ),
            ),
            if (style.showTrail)
              Align(
                alignment: trailAlignment,
                child: Container(
                  key: trailKey,
                  width: size * 1.12,
                  height: size * 0.58,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin:
                          telemetryStyle.attacksRight
                              ? Alignment.centerLeft
                              : Alignment.centerRight,
                      end:
                          telemetryStyle.attacksRight
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
              Transform.translate(
                offset: Offset(0, -size * style.lift * 0.5),
                child: Container(
                  key: haloKey,
                  width: size * style.haloScale,
                  height: size * style.haloScale,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: style.haloColor,
                  ),
                ),
              ),
            if (style.showRing)
              Transform.translate(
                offset: Offset(0, -size * style.lift),
                child: Container(
                  key: ringKey,
                  width: size * 1.26,
                  height: size * 1.26,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: style.haloColor.withValues(alpha: 0.92),
                      width: 1.1,
                    ),
                  ),
                ),
              ),
            Transform.translate(
              offset: Offset(0, -(size * style.lift)),
              child: Container(
                key: bodyKey,
                width: size,
                height: size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: style.fillColor,
                  border: Border.all(color: style.outlineColor, width: 1),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: style.haloColor.withValues(alpha: 0.26),
                      blurRadius: 8,
                      spreadRadius: 0.4,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
