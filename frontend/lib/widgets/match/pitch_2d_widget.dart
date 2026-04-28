import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_telemetry.dart';

class Pitch2dWidget extends StatelessWidget {
  const Pitch2dWidget({
    super.key,
    required this.viewState,
    required this.frame,
    this.showFormationOverlay = true,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final bool showFormationOverlay;

  static Pitch2dTelemetryStyle describeTelemetryStyle(
    MatchTimelineFrame frame,
  ) {
    return Pitch2dTelemetryStyle.fromFrame(frame);
  }

  static double playerMarkerRadiusFor(Size size) {
    return _playerRadius(size);
  }

  static double ballRadiusFor(Size size) {
    return _ballRadius(size);
  }

  static bool shouldShowBallTrail({
    required MatchTimelineFrame? previousFrame,
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
  }) {
    return _shouldShowBallTrail(
      previousFrame: previousFrame,
      frame: frame,
      activeEvent: activeEvent,
    );
  }

  @override
  Widget build(BuildContext context) {
    return MatchPitch2D(viewState: viewState, frame: frame);
  }
}

class MatchPitch2D extends StatelessWidget {
  const MatchPitch2D({
    super.key,
    required this.viewState,
    required this.frame,
    this.previousFrame,
    this.activeEvent,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame? previousFrame;
  final MatchEvent? activeEvent;

  static const double aspectRatio = 105 / 68;

  static Pitch2dTelemetryStyle describeTelemetryStyle(
    MatchTimelineFrame frame,
  ) {
    return Pitch2dTelemetryStyle.fromFrame(frame);
  }

  static double playerMarkerRadiusFor(Size size) {
    return _playerRadius(size);
  }

  static double ballRadiusFor(Size size) {
    return _ballRadius(size);
  }

  static bool shouldShowBallTrail({
    required MatchTimelineFrame? previousFrame,
    required MatchTimelineFrame frame,
    required MatchEvent? activeEvent,
  }) {
    return _shouldShowBallTrail(
      previousFrame: previousFrame,
      frame: frame,
      activeEvent: activeEvent,
    );
  }

  @override
  Widget build(BuildContext context) {
    final Pitch2dTelemetryStyle telemetryStyle = describeTelemetryStyle(frame);
    return AspectRatio(
      aspectRatio: aspectRatio,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: RepaintBoundary(
          child: CustomPaint(
            key: const Key('match-pitch-2d-canvas'),
            painter: _MatchPitch2DPainter(
              viewState: viewState,
              frame: frame,
              previousFrame: previousFrame,
              activeEvent: activeEvent,
              telemetryStyle: telemetryStyle,
            ),
            child: const SizedBox.expand(),
          ),
        ),
      ),
    );
  }
}

class _MatchPitch2DPainter extends CustomPainter {
  const _MatchPitch2DPainter({
    required this.viewState,
    required this.frame,
    required this.previousFrame,
    required this.activeEvent,
    required this.telemetryStyle,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame? previousFrame;
  final MatchEvent? activeEvent;
  final Pitch2dTelemetryStyle telemetryStyle;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect pitch = Offset.zero & size;
    final Rect playArea = pitch.deflate(_pitchInset(size));
    _drawGrass(canvas, pitch, playArea);
    _drawPitchLines(canvas, playArea);
    _drawBallTrail(canvas, playArea);
    _drawPlayers(canvas, playArea);
    _drawBall(canvas, playArea);
  }

  void _drawGrass(Canvas canvas, Rect pitch, Rect playArea) {
    canvas.drawRect(
      pitch,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[Color(0xFF446F16), Color(0xFF6F9220)],
        ).createShader(pitch),
    );

    final Paint stripePaint = Paint()..style = PaintingStyle.fill;
    const int stripes = 14;
    for (int index = 0; index < stripes; index += 1) {
      stripePaint.color =
          index.isEven ? const Color(0x12000000) : const Color(0x11FFFFFF);
      final double left = pitch.left + pitch.width * (index / stripes);
      canvas.drawRect(
        Rect.fromLTWH(left, pitch.top, pitch.width / stripes, pitch.height),
        stripePaint,
      );
    }

    final Paint grainPaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.025)
          ..strokeWidth = 0.8;
    for (int index = 0; index < 72; index += 1) {
      final double x =
          playArea.left + ((index * 37) % 100) / 100 * playArea.width;
      final double y =
          playArea.top + ((index * 53) % 100) / 100 * playArea.height;
      canvas.drawLine(
        Offset(x, y),
        Offset(x + 8 + (index % 5), y + 1.5),
        grainPaint,
      );
    }
  }

  void _drawPitchLines(Canvas canvas, Rect r) {
    final Paint linePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = math.max(1.4, r.shortestSide * 0.004)
          ..color = const Color(0xEAF8F5C4);
    final Paint spotPaint =
        Paint()
          ..style = PaintingStyle.fill
          ..color = linePaint.color;

    canvas.drawRect(r, linePaint);
    canvas.drawLine(
      Offset(r.center.dx, r.top),
      Offset(r.center.dx, r.bottom),
      linePaint,
    );
    canvas.drawCircle(r.center, r.height * 0.16, linePaint);
    canvas.drawCircle(r.center, 2.4, spotPaint);

    final Rect leftBox = Rect.fromLTWH(
      r.left,
      r.top + r.height * 0.18,
      r.width * 0.155,
      r.height * 0.64,
    );
    final Rect rightBox = Rect.fromLTWH(
      r.right - r.width * 0.155,
      r.top + r.height * 0.18,
      r.width * 0.155,
      r.height * 0.64,
    );
    final Rect leftSix = Rect.fromLTWH(
      r.left,
      r.top + r.height * 0.34,
      r.width * 0.07,
      r.height * 0.32,
    );
    final Rect rightSix = Rect.fromLTWH(
      r.right - r.width * 0.07,
      r.top + r.height * 0.34,
      r.width * 0.07,
      r.height * 0.32,
    );
    canvas.drawRect(leftBox, linePaint);
    canvas.drawRect(rightBox, linePaint);
    canvas.drawRect(leftSix, linePaint);
    canvas.drawRect(rightSix, linePaint);

    canvas.drawCircle(
      Offset(r.left + r.width * 0.11, r.center.dy),
      2,
      spotPaint,
    );
    canvas.drawCircle(
      Offset(r.right - r.width * 0.11, r.center.dy),
      2,
      spotPaint,
    );

    final Path leftArc =
        Path()..addArc(
          Rect.fromCircle(
            center: Offset(r.left + r.width * 0.11, r.center.dy),
            radius: r.height * 0.12,
          ),
          -math.pi / 2,
          math.pi,
        );
    final Path rightArc =
        Path()..addArc(
          Rect.fromCircle(
            center: Offset(r.right - r.width * 0.11, r.center.dy),
            radius: r.height * 0.12,
          ),
          math.pi / 2,
          math.pi,
        );
    canvas.drawPath(leftArc, linePaint);
    canvas.drawPath(rightArc, linePaint);

    final Paint goalPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = linePaint.strokeWidth
          ..color = linePaint.color.withValues(alpha: 0.82);
    canvas.drawRect(
      Rect.fromLTWH(r.left - 6, r.top + r.height * 0.43, 6, r.height * 0.14),
      goalPaint,
    );
    canvas.drawRect(
      Rect.fromLTWH(r.right, r.top + r.height * 0.43, 6, r.height * 0.14),
      goalPaint,
    );
  }

  void _drawBallTrail(Canvas canvas, Rect playArea) {
    final MatchTimelineFrame? previous = previousFrame;
    if (previous == null) {
      return;
    }
    if (!MatchPitch2D.shouldShowBallTrail(
      previousFrame: previous,
      frame: frame,
      activeEvent: activeEvent,
    )) {
      return;
    }
    final Offset from = _project(previous.ball.position, playArea);
    final Offset to = _project(frame.ball.position, playArea);

    final Paint glow =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = 6
          ..color = const Color(0x66FDE68A)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    final Paint line =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = 2
          ..color = const Color(0xDDFDE68A);
    canvas.drawLine(from, to, glow);
    canvas.drawLine(from, to, line);
  }

  void _drawPlayers(Canvas canvas, Rect playArea) {
    final double radius = _playerRadius(playArea.size);
    for (final MatchViewerPlayerFrame player in frame.players) {
      if (!player.active && player.state != MatchViewerPlayerState.sentOff) {
        continue;
      }
      final MatchViewerTeam team = viewState.teamForSide(player.side);
      final bool hasBall = frame.ball.ownerPlayerId == player.playerId;
      final Offset center = _project(player.position, playArea);
      final Color fill =
          player.isGoalkeeper
              ? _parseColor(team.goalkeeperColorHex)
              : _parseColor(team.primaryColorHex);
      final Color border = _markerBorderFor(fill);
      final Color textColor = _markerTextColorFor(fill);

      if (hasBall || player.highlighted) {
        final Paint halo =
            Paint()
              ..color = const Color(
                0xAAFDE68A,
              ).withValues(alpha: hasBall ? 0.34 : 0.20)
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 7);
        canvas.drawCircle(center, radius * (hasBall ? 2.0 : 1.65), halo);
      }

      canvas.drawCircle(
        center,
        radius + 1.4,
        Paint()
          ..color = Colors.black.withValues(alpha: 0.22)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2),
      );
      canvas.drawCircle(center, radius, Paint()..color = fill);
      canvas.drawCircle(
        center,
        radius,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4
          ..color = border,
      );

      _paintCenteredText(
        canvas,
        center,
        _markerLabel(player),
        radius * 1.02,
        textColor,
        FontWeight.w800,
      );
    }
  }

  void _drawBall(Canvas canvas, Rect playArea) {
    final Offset center = _project(frame.ball.position, playArea);
    final double radius = _ballRadius(playArea.size);
    final Paint shadow =
        Paint()
          ..color = Colors.black.withValues(alpha: 0.28)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    canvas.drawOval(
      Rect.fromCenter(
        center: center.translate(1.2, 2.2),
        width: radius * 2.2,
        height: radius * 1.05,
      ),
      shadow,
    );
    canvas.drawCircle(
      center,
      radius * 1.9,
      Paint()
        ..color = const Color(0x66FDE68A)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 7),
    );
    canvas.drawCircle(center, radius, Paint()..color = const Color(0xFFFFF176));
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2
        ..color = const Color(0xFF172033),
    );
  }

  @override
  bool shouldRepaint(covariant _MatchPitch2DPainter oldDelegate) {
    return oldDelegate.viewState != viewState ||
        oldDelegate.frame != frame ||
        oldDelegate.previousFrame != previousFrame ||
        oldDelegate.activeEvent != activeEvent ||
        oldDelegate.telemetryStyle != telemetryStyle;
  }
}

double _pitchInset(Size size) {
  return (size.shortestSide * 0.04).clamp(10.0, 24.0).toDouble();
}

Offset _project(MatchViewerPoint point, Rect playArea) {
  return Offset(
    playArea.left + (point.x.clamp(0, 100) / 100) * playArea.width,
    playArea.top + (point.y.clamp(0, 100) / 100) * playArea.height,
  );
}

double _playerRadius(Size size) {
  return (size.shortestSide * 0.017).clamp(6.0, 10.0).toDouble();
}

double _ballRadius(Size size) {
  return (size.shortestSide * 0.010).clamp(4.0, 6.0).toDouble();
}

bool _shouldShowBallTrail({
  required MatchTimelineFrame? previousFrame,
  required MatchTimelineFrame frame,
  required MatchEvent? activeEvent,
}) {
  final MatchTimelineFrame? previous = previousFrame;
  if (previous == null) {
    return false;
  }
  final double dx = frame.ball.position.x - previous.ball.position.x;
  final double dy = frame.ball.position.y - previous.ball.position.y;
  final double distance = math.sqrt((dx * dx) + (dy * dy));
  final String ballState = frame.ball.state.toLowerCase();
  final bool eventTrail =
      activeEvent?.type == MatchViewerEventType.pass ||
      activeEvent?.type == MatchViewerEventType.attack ||
      activeEvent?.type == MatchViewerEventType.goal ||
      activeEvent?.type == MatchViewerEventType.miss ||
      ballState == 'pass' ||
      ballState == 'shot' ||
      ballState == 'cross' ||
      ballState == 'lob';
  return distance >= 2.0 && eventTrail;
}

String _markerLabel(MatchViewerPlayerFrame player) {
  final int? shirtNumber = player.shirtNumber;
  if (shirtNumber != null) {
    return shirtNumber.toString();
  }
  final String label = player.label.trim();
  if (label.isEmpty) {
    return '?';
  }
  return label.length <= 2 ? label : label.substring(0, 2);
}

void _paintCenteredText(
  Canvas canvas,
  Offset center,
  String text,
  double fontSize,
  Color color,
  FontWeight weight,
) {
  final TextPainter painter = TextPainter(
    text: TextSpan(
      text: text,
      style: TextStyle(
        color: color,
        fontSize: fontSize,
        fontWeight: weight,
        height: 1,
        letterSpacing: 0,
      ),
    ),
    textAlign: TextAlign.center,
    textDirection: TextDirection.ltr,
    maxLines: 1,
  )..layout();
  painter.paint(canvas, center - Offset(painter.width / 2, painter.height / 2));
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFF31572C);
}

Color _markerBorderFor(Color fill) {
  return fill.computeLuminance() > 0.45
      ? const Color(0xFF172033)
      : Colors.white;
}

Color _markerTextColorFor(Color fill) {
  return fill.computeLuminance() > 0.45
      ? const Color(0xFF172033)
      : Colors.white;
}
