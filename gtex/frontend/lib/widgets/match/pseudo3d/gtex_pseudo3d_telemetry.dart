import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_telemetry.dart';

@immutable
class GtexPseudo3DTelemetryStyle {
  const GtexPseudo3DTelemetryStyle({
    required this.pressureIndex,
    required this.dangerZone,
    required this.transitionState,
    required this.attacksRight,
    required this.accentColor,
    required this.stadiumGradient,
    required this.grassGradient,
    required this.borderAlpha,
    required this.lineAlpha,
    required this.stripeDarkAlpha,
    required this.stripeLightAlpha,
    required this.showDangerOverlay,
    required this.showBoxOverlay,
    required this.showTransitionLane,
    required this.showSetPieceOverlay,
    required this.cameraZoomBias,
    required this.cameraLeadX,
    required this.cameraLeadY,
    required this.playerFocusBoost,
    required this.ballFocusBoost,
    required this.crowdGlowAlpha,
  });

  factory GtexPseudo3DTelemetryStyle.fromFrame({
    required MatchTimelineFrame frame,
    required GtexMatchRenderMode mode,
  }) {
    final Pitch2dTelemetryStyle base = Pitch2dTelemetryStyle.fromFrame(frame);
    final double pressureIndex = base.pressureIndex;
    final double ballX = (frame.ball.position.x / 100).clamp(0, 1).toDouble();
    final double ballY = (frame.ball.position.y / 100).clamp(0, 1).toDouble();
    double focusX = ballX;
    double focusY = ballY;
    if (base.showBoxOverlay) {
      focusX =
          base.attacksRight ? math.max(ballX, 0.82) : math.min(ballX, 0.18);
    } else if (base.showDangerOverlay) {
      focusX =
          base.attacksRight ? math.max(ballX, 0.72) : math.min(ballX, 0.28);
    } else if (base.showTransitionLane) {
      focusX =
          base.attacksRight ? math.max(ballX, 0.60) : math.min(ballX, 0.40);
      focusY = (ballY - 0.04).clamp(0.20, 0.80).toDouble();
    }
    if (base.showSetPieceOverlay) {
      focusY = (ballY - 0.05).clamp(0.18, 0.76).toDouble();
    }

    final double modeBias = switch (mode) {
      GtexMatchRenderMode.quick => 0.014,
      GtexMatchRenderMode.standard => 0.028,
      GtexMatchRenderMode.cinematic => 0.044,
    };
    final double eventBias =
        base.showBoxOverlay
            ? 0.056
            : base.showDangerOverlay
            ? 0.036
            : base.showSetPieceOverlay
            ? 0.028
            : base.showTransitionLane
            ? 0.024
            : 0.010;
    final double cameraZoomBias =
        (modeBias + eventBias + (pressureIndex * 0.035))
            .clamp(0.02, 0.17)
            .toDouble();

    final double cameraLeadX =
        ((focusX - 0.5) * (0.9 + (pressureIndex * 0.45)))
            .clamp(-0.40, 0.40)
            .toDouble();
    final double cameraLeadY =
        (((focusY - 0.5) * 0.55) -
                (base.showSetPieceOverlay ? 0.04 : 0) -
                (base.showDangerOverlay ? 0.02 : 0))
            .clamp(-0.18, 0.18)
            .toDouble();

    final Color accentColor =
        base.showBoxOverlay
            ? const Color(0xFFF97066)
            : base.showSetPieceOverlay
            ? const Color(0xFFFDB022)
            : base.showTransitionLane
            ? const Color(0xFF53B1FD)
            : base.accentColor;

    return GtexPseudo3DTelemetryStyle(
      pressureIndex: pressureIndex,
      dangerZone: base.dangerZone,
      transitionState: base.transitionState,
      attacksRight: base.attacksRight,
      accentColor: accentColor,
      stadiumGradient: <Color>[
        Color.lerp(
              const Color(0xFF12283A),
              accentColor.withValues(alpha: 0.18),
              0.08 + (pressureIndex * 0.10),
            ) ??
            const Color(0xFF12283A),
        Color.lerp(
              const Color(0xFF0C1721),
              accentColor.withValues(alpha: 0.10),
              0.06 + (pressureIndex * 0.08),
            ) ??
            const Color(0xFF0C1721),
        const Color(0xFF050B12),
      ],
      grassGradient: <Color>[
        Color.lerp(
              const Color(0xFF21824C),
              accentColor.withValues(alpha: 0.18),
              0.04 + (pressureIndex * 0.12),
            ) ??
            const Color(0xFF21824C),
        Color.lerp(
              const Color(0xFF14643B),
              accentColor.withValues(alpha: 0.10),
              0.03 + (pressureIndex * 0.10),
            ) ??
            const Color(0xFF14643B),
        const Color(0xFF0A3A22),
      ],
      borderAlpha: 0.10 + (pressureIndex * 0.10),
      lineAlpha: 0.82 + (pressureIndex * 0.16),
      stripeDarkAlpha: 0.05 + (pressureIndex * 0.08),
      stripeLightAlpha: 0.03 + (pressureIndex * 0.06),
      showDangerOverlay: base.showDangerOverlay,
      showBoxOverlay: base.showBoxOverlay,
      showTransitionLane: base.showTransitionLane,
      showSetPieceOverlay: base.showSetPieceOverlay,
      cameraZoomBias: cameraZoomBias,
      cameraLeadX: cameraLeadX,
      cameraLeadY: cameraLeadY,
      playerFocusBoost: (0.08 + (pressureIndex * 0.18)).clamp(0.08, 0.28),
      ballFocusBoost: (0.14 + (pressureIndex * 0.24)).clamp(0.16, 0.36),
      crowdGlowAlpha:
          (0.08 +
                  (pressureIndex * 0.12) +
                  (base.showDangerOverlay ? 0.06 : 0) +
                  (base.showSetPieceOverlay ? 0.04 : 0))
              .clamp(0.08, 0.28)
              .toDouble(),
    );
  }

  final double pressureIndex;
  final String? dangerZone;
  final MatchTransitionState transitionState;
  final bool attacksRight;
  final Color accentColor;
  final List<Color> stadiumGradient;
  final List<Color> grassGradient;
  final double borderAlpha;
  final double lineAlpha;
  final double stripeDarkAlpha;
  final double stripeLightAlpha;
  final bool showDangerOverlay;
  final bool showBoxOverlay;
  final bool showTransitionLane;
  final bool showSetPieceOverlay;
  final double cameraZoomBias;
  final double cameraLeadX;
  final double cameraLeadY;
  final double playerFocusBoost;
  final double ballFocusBoost;
  final double crowdGlowAlpha;
}
