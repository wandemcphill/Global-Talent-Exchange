import 'dart:math' as math;
import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_telemetry.dart';

class GtexPseudo3DProjectedPoint {
  const GtexPseudo3DProjectedPoint({
    required this.offset,
    required this.depth,
    required this.scale,
  });

  final Offset offset;
  final double depth;
  final double scale;
}

class GtexPseudo3DPitchProjection {
  const GtexPseudo3DPitchProjection({
    required this.size,
    required this.topLeft,
    required this.topRight,
    required this.bottomLeft,
    required this.bottomRight,
  });

  factory GtexPseudo3DPitchProjection.forSize(Size size) {
    return GtexPseudo3DPitchProjection(
      size: size,
      topLeft: Offset(size.width * 0.18, size.height * 0.08),
      topRight: Offset(size.width * 0.82, size.height * 0.08),
      bottomLeft: Offset(size.width * 0.04, size.height * 0.94),
      bottomRight: Offset(size.width * 0.96, size.height * 0.94),
    );
  }

  final Size size;
  final Offset topLeft;
  final Offset topRight;
  final Offset bottomLeft;
  final Offset bottomRight;

  GtexPseudo3DProjectedPoint project(MatchViewerPoint point) {
    final double depth = (point.y / 100).clamp(0, 1).toDouble();
    final Offset leftEdge = Offset.lerp(topLeft, bottomLeft, depth)!;
    final Offset rightEdge = Offset.lerp(topRight, bottomRight, depth)!;
    final double xFraction = (point.x / 100).clamp(0, 1).toDouble();
    final Offset offset = Offset.lerp(leftEdge, rightEdge, xFraction)!;
    return GtexPseudo3DProjectedPoint(
      offset: offset,
      depth: depth,
      scale: lerpDouble(0.58, 1.18, depth)!,
    );
  }

  Path rectPath({
    required double left,
    required double top,
    required double right,
    required double bottom,
  }) {
    final MatchViewerPoint topLeftPoint = MatchViewerPoint(x: left, y: top);
    final MatchViewerPoint topRightPoint = MatchViewerPoint(x: right, y: top);
    final MatchViewerPoint bottomRightPoint = MatchViewerPoint(
      x: right,
      y: bottom,
    );
    final MatchViewerPoint bottomLeftPoint = MatchViewerPoint(
      x: left,
      y: bottom,
    );
    return Path()
      ..moveTo(project(topLeftPoint).offset.dx, project(topLeftPoint).offset.dy)
      ..lineTo(
        project(topRightPoint).offset.dx,
        project(topRightPoint).offset.dy,
      )
      ..lineTo(
        project(bottomRightPoint).offset.dx,
        project(bottomRightPoint).offset.dy,
      )
      ..lineTo(
        project(bottomLeftPoint).offset.dx,
        project(bottomLeftPoint).offset.dy,
      )
      ..close();
  }

  Path linePath(List<MatchViewerPoint> points) {
    final Path path = Path();
    for (int index = 0; index < points.length; index += 1) {
      final Offset offset = project(points[index]).offset;
      if (index == 0) {
        path.moveTo(offset.dx, offset.dy);
      } else {
        path.lineTo(offset.dx, offset.dy);
      }
    }
    return path;
  }

  Path circlePath({
    required MatchViewerPoint center,
    required double radiusX,
    required double radiusY,
    int samples = 36,
  }) {
    final Path path = Path();
    for (int index = 0; index <= samples; index += 1) {
      final double radians = (index / samples) * math.pi * 2;
      final MatchViewerPoint point = MatchViewerPoint(
        x: center.x + (math.cos(radians) * radiusX),
        y: center.y + (math.sin(radians) * radiusY),
      );
      final Offset offset = project(point).offset;
      if (index == 0) {
        path.moveTo(offset.dx, offset.dy);
      } else {
        path.lineTo(offset.dx, offset.dy);
      }
    }
    path.close();
    return path;
  }
}

class GtexPseudo3DPitch extends StatelessWidget {
  const GtexPseudo3DPitch({
    super.key,
    required this.projection,
    required this.telemetryStyle,
    required this.frame,
  });

  final GtexPseudo3DPitchProjection projection;
  final GtexPseudo3DTelemetryStyle telemetryStyle;
  final MatchTimelineFrame frame;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        painter: _GtexPseudo3DPitchPainter(
          projection,
          telemetryStyle: telemetryStyle,
          frame: frame,
        ),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _GtexPseudo3DPitchPainter extends CustomPainter {
  const _GtexPseudo3DPitchPainter(
    this.projection, {
    required this.telemetryStyle,
    required this.frame,
  });

  final GtexPseudo3DPitchProjection projection;
  final GtexPseudo3DTelemetryStyle telemetryStyle;
  final MatchTimelineFrame frame;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect bounds = Offset.zero & size;
    final Paint stadiumPaint =
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: telemetryStyle.stadiumGradient,
          ).createShader(bounds);
    canvas.drawRect(bounds, stadiumPaint);

    final Paint crowdGlowPaint =
        Paint()
          ..shader = RadialGradient(
            center: Alignment.topCenter,
            radius: 1.1,
            colors: <Color>[
              telemetryStyle.accentColor.withValues(
                alpha: telemetryStyle.crowdGlowAlpha,
              ),
              Colors.transparent,
            ],
          ).createShader(
            Rect.fromLTWH(
              size.width * 0.08,
              -size.height * 0.24,
              size.width * 0.84,
              size.height * 0.72,
            ),
          );
    canvas.drawRect(bounds, crowdGlowPaint);

    final Path field =
        Path()
          ..moveTo(projection.topLeft.dx, projection.topLeft.dy)
          ..lineTo(projection.topRight.dx, projection.topRight.dy)
          ..lineTo(projection.bottomRight.dx, projection.bottomRight.dy)
          ..lineTo(projection.bottomLeft.dx, projection.bottomLeft.dy)
          ..close();

    final Paint grassPaint =
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: telemetryStyle.grassGradient,
          ).createShader(bounds);
    canvas.drawPath(field, grassPaint);

    final Paint stripePaint = Paint()..style = PaintingStyle.fill;
    for (int stripe = 0; stripe < 10; stripe += 1) {
      final double top = stripe * 10;
      final double bottom = top + 10;
      stripePaint.color =
          stripe.isEven
              ? Colors.black.withValues(alpha: telemetryStyle.stripeDarkAlpha)
              : Colors.white.withValues(alpha: telemetryStyle.stripeLightAlpha);
      canvas.drawPath(
        projection.rectPath(left: 0, top: top, right: 100, bottom: bottom),
        stripePaint,
      );
    }

    if (telemetryStyle.showDangerOverlay) {
      _drawDangerOverlay(canvas);
    }
    if (telemetryStyle.showTransitionLane) {
      _drawTransitionLane(canvas);
    }
    if (telemetryStyle.showSetPieceOverlay) {
      _drawSetPieceFocus(canvas);
    }

    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: telemetryStyle.lineAlpha)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2;

    canvas.drawPath(field, linePaint);
    canvas.drawPath(
      projection.linePath(const <MatchViewerPoint>[
        MatchViewerPoint(x: 50, y: 0),
        MatchViewerPoint(x: 50, y: 100),
      ]),
      linePaint,
    );
    canvas.drawPath(
      projection.rectPath(left: 0, top: 21, right: 16, bottom: 79),
      linePaint,
    );
    canvas.drawPath(
      projection.rectPath(left: 84, top: 21, right: 100, bottom: 79),
      linePaint,
    );
    canvas.drawPath(
      projection.rectPath(left: 0, top: 34, right: 7, bottom: 66),
      linePaint,
    );
    canvas.drawPath(
      projection.rectPath(left: 93, top: 34, right: 100, bottom: 66),
      linePaint,
    );
    canvas.drawPath(
      projection.circlePath(
        center: const MatchViewerPoint(x: 50, y: 50),
        radiusX: 9.15,
        radiusY: 9.15,
      ),
      linePaint,
    );

    final Paint dotPaint = Paint()..color = Colors.white.withValues(alpha: 0.9);
    canvas.drawCircle(
      projection.project(const MatchViewerPoint(x: 50, y: 50)).offset,
      3,
      dotPaint,
    );
    canvas.drawCircle(
      projection.project(const MatchViewerPoint(x: 11, y: 50)).offset,
      2.6,
      dotPaint,
    );
    canvas.drawCircle(
      projection.project(const MatchViewerPoint(x: 89, y: 50)).offset,
      2.6,
      dotPaint,
    );
  }

  void _drawDangerOverlay(Canvas canvas) {
    final Paint finalThirdPaint =
        Paint()
          ..color = telemetryStyle.accentColor.withValues(
            alpha: telemetryStyle.showBoxOverlay ? 0.18 : 0.12,
          );
    final double left = telemetryStyle.attacksRight ? 63 : 0;
    final double right = telemetryStyle.attacksRight ? 100 : 37;
    canvas.drawPath(
      projection.rectPath(left: left, top: 0, right: right, bottom: 100),
      finalThirdPaint,
    );
    if (!telemetryStyle.showBoxOverlay) {
      return;
    }
    final Paint boxPaint =
        Paint()
          ..color = const Color(
            0xFFF04438,
          ).withValues(alpha: 0.16 + (telemetryStyle.pressureIndex * 0.08));
    canvas.drawPath(
      projection.rectPath(
        left: telemetryStyle.attacksRight ? 84 : 0,
        top: 21,
        right: telemetryStyle.attacksRight ? 100 : 16,
        bottom: 79,
      ),
      boxPaint,
    );
  }

  void _drawTransitionLane(Canvas canvas) {
    final double centerY = frame.ball.position.y;
    final double laneHalf = 7 + (telemetryStyle.pressureIndex * 5);
    final double startX = 50;
    final double endX = telemetryStyle.attacksRight ? 96 : 4;
    final Path lane =
        Path()
          ..moveTo(
            projection
                .project(MatchViewerPoint(x: startX, y: centerY - laneHalf))
                .offset
                .dx,
            projection
                .project(MatchViewerPoint(x: startX, y: centerY - laneHalf))
                .offset
                .dy,
          )
          ..lineTo(
            projection
                .project(MatchViewerPoint(x: startX, y: centerY + laneHalf))
                .offset
                .dx,
            projection
                .project(MatchViewerPoint(x: startX, y: centerY + laneHalf))
                .offset
                .dy,
          )
          ..lineTo(
            projection
                .project(
                  MatchViewerPoint(x: endX, y: centerY + (laneHalf * 1.5)),
                )
                .offset
                .dx,
            projection
                .project(
                  MatchViewerPoint(x: endX, y: centerY + (laneHalf * 1.5)),
                )
                .offset
                .dy,
          )
          ..lineTo(
            projection
                .project(
                  MatchViewerPoint(x: endX, y: centerY - (laneHalf * 1.5)),
                )
                .offset
                .dx,
            projection
                .project(
                  MatchViewerPoint(x: endX, y: centerY - (laneHalf * 1.5)),
                )
                .offset
                .dy,
          )
          ..close();
    final Rect shaderBounds = Rect.fromLTWH(
      0,
      projection
          .project(
            MatchViewerPoint(x: 50, y: (centerY - laneHalf).clamp(0, 100)),
          )
          .offset
          .dy,
      projection.size.width,
      projection.size.height * 0.45,
    );
    final Paint lanePaint =
        Paint()
          ..shader = LinearGradient(
            begin:
                telemetryStyle.attacksRight
                    ? Alignment.centerLeft
                    : Alignment.centerRight,
            end:
                telemetryStyle.attacksRight
                    ? Alignment.centerRight
                    : Alignment.centerLeft,
            colors: <Color>[
              Colors.transparent,
              telemetryStyle.accentColor.withValues(
                alpha: 0.10 + (telemetryStyle.pressureIndex * 0.12),
              ),
            ],
          ).createShader(shaderBounds);
    canvas.drawPath(lane, lanePaint);
  }

  void _drawSetPieceFocus(Canvas canvas) {
    final MatchViewerPoint center = frame.ball.position;
    final Paint fillPaint =
        Paint()..color = telemetryStyle.accentColor.withValues(alpha: 0.12);
    final Paint ringPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = telemetryStyle.accentColor.withValues(alpha: 0.28);
    canvas.drawPath(
      projection.circlePath(center: center, radiusX: 8, radiusY: 8),
      fillPaint,
    );
    canvas.drawPath(
      projection.circlePath(center: center, radiusX: 11, radiusY: 11),
      ringPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _GtexPseudo3DPitchPainter oldDelegate) {
    return oldDelegate.projection.size != projection.size ||
        oldDelegate.telemetryStyle != telemetryStyle ||
        oldDelegate.frame != frame;
  }
}
