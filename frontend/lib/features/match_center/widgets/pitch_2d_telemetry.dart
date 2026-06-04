import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

@immutable
class Pitch2dTelemetryStyle {
  const Pitch2dTelemetryStyle({
    required this.pressureIndex,
    required this.homeCompactness,
    required this.awayCompactness,
    required this.dangerZone,
    required this.transitionState,
    required this.frameTags,
    required this.attacksRight,
    required this.ballPosition,
    required this.fieldGradient,
    required this.accentColor,
    required this.stripeDarkAlpha,
    required this.stripeLightAlpha,
    required this.lineAlpha,
    required this.borderAlpha,
    required this.dangerOverlayAlpha,
    required this.transitionOverlayAlpha,
    required this.setPieceOverlayAlpha,
    required this.homeShapeAlpha,
    required this.awayShapeAlpha,
    required this.showDangerOverlay,
    required this.showBoxOverlay,
    required this.showTransitionLane,
    required this.showSetPieceOverlay,
  });

  factory Pitch2dTelemetryStyle.fromFrame(MatchTimelineFrame frame) {
    final double pressureIndex =
        (frame.pressureIndex ?? _fallbackPressureIndex(frame))
            .clamp(0.08, 1.0)
            .toDouble();
    final double homeCompactness =
        (frame.compactnessHome ?? 0.58).clamp(0.16, 0.96).toDouble();
    final double awayCompactness =
        (frame.compactnessAway ?? 0.58).clamp(0.16, 0.96).toDouble();
    final String? dangerZone = frame.dangerZone ?? _fallbackDangerZone(frame);
    final MatchTransitionState transitionState =
        frame.transitionState ?? MatchTransitionState.stable;
    final List<String> frameTags = List<String>.unmodifiable(frame.frameTags);
    final bool attacksRight =
        frame.possessionSide == MatchViewerSide.home
            ? frame.homeAttacksRight
            : !frame.homeAttacksRight;
    final bool showBoxOverlay =
        dangerZone == 'box' ||
        frame.possessionPhase == MatchPossessionPhase.boxAttack ||
        frameTags.contains('box_entry');
    final bool showDangerOverlay =
        showBoxOverlay ||
        dangerZone == 'final_third' ||
        frame.possessionPhase == MatchPossessionPhase.finalThird;
    final bool showTransitionLane =
        transitionState.isBreak ||
        frame.possessionPhase == MatchPossessionPhase.transition;
    final bool showSetPieceOverlay =
        frame.phase == MatchViewerPhase.setPiece ||
        frame.possessionPhase == MatchPossessionPhase.restart ||
        frame.possessionPhase == MatchPossessionPhase.setPiece ||
        transitionState.isReset ||
        frameTags.contains('set_piece');
    final Color accentColor =
        showBoxOverlay
            ? const Color(0xFFF97066)
            : showDangerOverlay
            ? const Color(0xFFF79009)
            : showSetPieceOverlay
            ? const Color(0xFFFDB022)
            : showTransitionLane
            ? const Color(0xFF53B1FD)
            : const Color(0xFF22C55E);

    return Pitch2dTelemetryStyle(
      pressureIndex: pressureIndex,
      homeCompactness: homeCompactness,
      awayCompactness: awayCompactness,
      dangerZone: dangerZone,
      transitionState: transitionState,
      frameTags: frameTags,
      attacksRight: attacksRight,
      ballPosition: frame.ball.position,
      fieldGradient: <Color>[
        Color.lerp(
              const Color(0xFF0F5132),
              const Color(0xFF0B3B26),
              pressureIndex * 0.30,
            ) ??
            const Color(0xFF0F5132),
        Color.lerp(
              const Color(0xFF19683D),
              accentColor.withValues(alpha: 0.22),
              0.10 + (pressureIndex * 0.14),
            ) ??
            const Color(0xFF19683D),
        Color.lerp(
              const Color(0xFF0D4A2D),
              const Color(0xFF082E1B),
              pressureIndex * 0.34,
            ) ??
            const Color(0xFF0D4A2D),
      ],
      accentColor: accentColor,
      stripeDarkAlpha: 0.05 + (pressureIndex * 0.08),
      stripeLightAlpha: 0.03 + (pressureIndex * 0.06),
      lineAlpha: 0.80 + (pressureIndex * 0.16),
      borderAlpha: 0.12 + (pressureIndex * 0.08),
      dangerOverlayAlpha:
          showBoxOverlay
              ? 0.14 + (pressureIndex * 0.14)
              : showDangerOverlay
              ? 0.10 + (pressureIndex * 0.10)
              : 0,
      transitionOverlayAlpha:
          showTransitionLane ? 0.10 + (pressureIndex * 0.12) : 0,
      setPieceOverlayAlpha:
          showSetPieceOverlay ? 0.12 + (pressureIndex * 0.08) : 0,
      homeShapeAlpha: 0.05 + (homeCompactness * 0.10) + (pressureIndex * 0.03),
      awayShapeAlpha: 0.05 + (awayCompactness * 0.10) + (pressureIndex * 0.03),
      showDangerOverlay: showDangerOverlay,
      showBoxOverlay: showBoxOverlay,
      showTransitionLane: showTransitionLane,
      showSetPieceOverlay: showSetPieceOverlay,
    );
  }

  final double pressureIndex;
  final double homeCompactness;
  final double awayCompactness;
  final String? dangerZone;
  final MatchTransitionState transitionState;
  final List<String> frameTags;
  final bool attacksRight;
  final MatchViewerPoint ballPosition;
  final List<Color> fieldGradient;
  final Color accentColor;
  final double stripeDarkAlpha;
  final double stripeLightAlpha;
  final double lineAlpha;
  final double borderAlpha;
  final double dangerOverlayAlpha;
  final double transitionOverlayAlpha;
  final double setPieceOverlayAlpha;
  final double homeShapeAlpha;
  final double awayShapeAlpha;
  final bool showDangerOverlay;
  final bool showBoxOverlay;
  final bool showTransitionLane;
  final bool showSetPieceOverlay;
}

class Pitch2dTelemetryOverlay extends StatelessWidget {
  const Pitch2dTelemetryOverlay({
    super.key,
    required this.frame,
    required this.style,
  });

  final MatchTimelineFrame frame;
  final Pitch2dTelemetryStyle style;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: RepaintBoundary(
        child: CustomPaint(
          painter: _Pitch2dTelemetryPainter(frame: frame, style: style),
          size: Size.infinite,
        ),
      ),
    );
  }
}

class _Pitch2dTelemetryPainter extends CustomPainter {
  const _Pitch2dTelemetryPainter({required this.frame, required this.style});

  final MatchTimelineFrame frame;
  final Pitch2dTelemetryStyle style;

  @override
  void paint(Canvas canvas, Size size) {
    _drawShapeBand(
      canvas,
      size,
      side: MatchViewerSide.home,
      compactness: style.homeCompactness,
      alpha: style.homeShapeAlpha,
      tint: const Color(0xFF22C55E),
    );
    _drawShapeBand(
      canvas,
      size,
      side: MatchViewerSide.away,
      compactness: style.awayCompactness,
      alpha: style.awayShapeAlpha,
      tint: const Color(0xFFF97316),
    );
    if (style.showTransitionLane) {
      _drawTransitionLane(canvas, size);
    }
    if (style.showDangerOverlay) {
      _drawDangerZone(canvas, size);
    }
    if (style.showSetPieceOverlay) {
      _drawSetPieceFocus(canvas, size);
    }
  }

  void _drawTransitionLane(Canvas canvas, Size size) {
    final double laneWidth =
        size.height * (0.18 + (style.pressureIndex * 0.08));
    final double startX = size.width * 0.5;
    final double endX =
        style.attacksRight ? size.width * 0.94 : size.width * 0.06;
    final double centerY = (style.ballPosition.y / 100) * size.height;
    final Path lane =
        Path()
          ..moveTo(startX, centerY - (laneWidth * 0.36))
          ..lineTo(startX, centerY + (laneWidth * 0.36))
          ..lineTo(endX, centerY + (laneWidth * 0.72))
          ..lineTo(endX, centerY - (laneWidth * 0.72))
          ..close();
    final Rect bounds = Rect.fromPoints(
      Offset(math.min(startX, endX), centerY - laneWidth),
      Offset(math.max(startX, endX), centerY + laneWidth),
    );
    final Paint lanePaint =
        Paint()
          ..shader = LinearGradient(
            begin:
                style.attacksRight
                    ? Alignment.centerLeft
                    : Alignment.centerRight,
            end:
                style.attacksRight
                    ? Alignment.centerRight
                    : Alignment.centerLeft,
            colors: <Color>[
              style.accentColor.withValues(alpha: 0.0),
              style.accentColor.withValues(alpha: style.transitionOverlayAlpha),
            ],
          ).createShader(bounds);
    canvas.drawPath(lane, lanePaint);
  }

  void _drawDangerZone(Canvas canvas, Size size) {
    final double outerStart = style.attacksRight ? size.width * 0.63 : 0;
    final double outerWidth = size.width * 0.37;
    final Rect finalThird = Rect.fromLTWH(
      outerStart,
      8,
      outerWidth,
      size.height - 16,
    );
    final Paint finalThirdPaint =
        Paint()
          ..color = style.accentColor.withValues(
            alpha: style.dangerOverlayAlpha * 0.68,
          );
    canvas.drawRRect(
      RRect.fromRectAndRadius(finalThird, const Radius.circular(24)),
      finalThirdPaint,
    );
    if (!style.showBoxOverlay) {
      return;
    }
    final double boxWidth = size.width * 0.18;
    final double boxHeight = size.height * 0.58;
    final double boxLeft = style.attacksRight ? size.width - 8 - boxWidth : 8;
    final Rect boxRect = Rect.fromLTWH(
      boxLeft,
      size.height * 0.21,
      boxWidth,
      boxHeight,
    );
    final Paint boxPaint =
        Paint()
          ..color = const Color(
            0xFFF04438,
          ).withValues(alpha: style.dangerOverlayAlpha);
    canvas.drawRRect(
      RRect.fromRectAndRadius(boxRect, const Radius.circular(18)),
      boxPaint,
    );
  }

  void _drawSetPieceFocus(Canvas canvas, Size size) {
    final Offset focus = Offset(
      (style.ballPosition.x / 100) * size.width,
      (style.ballPosition.y / 100) * size.height,
    );
    final Paint ringPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = style.accentColor.withValues(
            alpha: style.setPieceOverlayAlpha,
          );
    final Paint fillPaint =
        Paint()
          ..style = PaintingStyle.fill
          ..color = style.accentColor.withValues(
            alpha: style.setPieceOverlayAlpha * 0.28,
          );
    canvas.drawCircle(focus, size.shortestSide * 0.07, fillPaint);
    canvas.drawCircle(focus, size.shortestSide * 0.09, ringPaint);
    canvas.drawCircle(focus, size.shortestSide * 0.12, ringPaint);
  }

  void _drawShapeBand(
    Canvas canvas,
    Size size, {
    required MatchViewerSide side,
    required double compactness,
    required double alpha,
    required Color tint,
  }) {
    final List<MatchViewerPlayerFrame> players = frame.players
        .where((MatchViewerPlayerFrame player) => player.side == side)
        .where((MatchViewerPlayerFrame player) => player.active)
        .toList(growable: false);
    if (players.isEmpty) {
      return;
    }
    double minX = double.infinity;
    double maxX = double.negativeInfinity;
    double minY = double.infinity;
    double maxY = double.negativeInfinity;
    for (final MatchViewerPlayerFrame player in players) {
      minX = math.min(minX, player.position.x);
      maxX = math.max(maxX, player.position.x);
      minY = math.min(minY, player.position.y);
      maxY = math.max(maxY, player.position.y);
    }
    final double marginX = 7 + ((1 - compactness) * 7);
    final double marginY = 5 + ((1 - compactness) * 6);
    final Rect bounds = Rect.fromLTRB(
      (((minX - marginX).clamp(2, 98)) / 100) * size.width,
      (((minY - marginY).clamp(2, 98)) / 100) * size.height,
      (((maxX + marginX).clamp(2, 98)) / 100) * size.width,
      (((maxY + marginY).clamp(2, 98)) / 100) * size.height,
    );
    final Paint shapePaint =
        Paint()..color = tint.withValues(alpha: alpha.clamp(0.04, 0.24));
    canvas.drawRRect(
      RRect.fromRectAndRadius(bounds, const Radius.circular(20)),
      shapePaint,
    );
  }

  @override
  bool shouldRepaint(covariant _Pitch2dTelemetryPainter oldDelegate) {
    return oldDelegate.frame != frame || oldDelegate.style != style;
  }
}

double _fallbackPressureIndex(MatchTimelineFrame frame) {
  return switch (frame.possessionPhase) {
    MatchPossessionPhase.boxAttack => 0.82,
    MatchPossessionPhase.finalThird => 0.68,
    MatchPossessionPhase.attack => 0.54,
    MatchPossessionPhase.transition => 0.58,
    MatchPossessionPhase.setPiece => 0.62,
    MatchPossessionPhase.restart => 0.44,
    MatchPossessionPhase.deadBall || MatchPossessionPhase.stoppage => 0.22,
    MatchPossessionPhase.buildUp => 0.42,
    MatchPossessionPhase.control => 0.34,
    MatchPossessionPhase.recovery => 0.30,
    null => 0.34,
  };
}

String? _fallbackDangerZone(MatchTimelineFrame frame) {
  if (frame.possessionPhase == MatchPossessionPhase.boxAttack) {
    return 'box';
  }
  if (frame.possessionPhase == MatchPossessionPhase.finalThird ||
      frame.possessionPhase == MatchPossessionPhase.attack) {
    return 'final_third';
  }
  if (frame.possessionPhase == MatchPossessionPhase.transition) {
    return 'middle_third';
  }
  if (frame.possessionPhase == MatchPossessionPhase.setPiece ||
      frame.possessionPhase == MatchPossessionPhase.restart) {
    return 'set_piece';
  }
  return null;
}
