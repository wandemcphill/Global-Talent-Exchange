import 'dart:math' as math;
import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

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
    final MatchViewerPoint bottomRightPoint =
        MatchViewerPoint(x: right, y: bottom);
    final MatchViewerPoint bottomLeftPoint =
        MatchViewerPoint(x: left, y: bottom);
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
  });

  final GtexPseudo3DPitchProjection projection;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        painter: _GtexPseudo3DPitchPainter(projection),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _GtexPseudo3DPitchPainter extends CustomPainter {
  const _GtexPseudo3DPitchPainter(this.projection);

  final GtexPseudo3DPitchProjection projection;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect bounds = Offset.zero & size;
    final Paint stadiumPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: <Color>[
          Color(0xFF112433),
          Color(0xFF08131D),
        ],
      ).createShader(bounds);
    canvas.drawRect(bounds, stadiumPaint);

    final Path field = Path()
      ..moveTo(projection.topLeft.dx, projection.topLeft.dy)
      ..lineTo(projection.topRight.dx, projection.topRight.dy)
      ..lineTo(projection.bottomRight.dx, projection.bottomRight.dy)
      ..lineTo(projection.bottomLeft.dx, projection.bottomLeft.dy)
      ..close();

    final Paint grassPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: <Color>[
          Color(0xFF1E7A45),
          Color(0xFF0E4D2D),
        ],
      ).createShader(bounds);
    canvas.drawPath(field, grassPaint);

    final Paint stripePaint = Paint()..style = PaintingStyle.fill;
    for (int stripe = 0; stripe < 10; stripe += 1) {
      final double top = stripe * 10;
      final double bottom = top + 10;
      stripePaint.color =
          stripe.isEven ? const Color(0x12000000) : const Color(0x0DFFFFFF);
      canvas.drawPath(
        projection.rectPath(
          left: 0,
          top: top,
          right: 100,
          bottom: bottom,
        ),
        stripePaint,
      );
    }

    final Paint linePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.86)
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
        dotPaint);
    canvas.drawCircle(
        projection.project(const MatchViewerPoint(x: 11, y: 50)).offset,
        2.6,
        dotPaint);
    canvas.drawCircle(
        projection.project(const MatchViewerPoint(x: 89, y: 50)).offset,
        2.6,
        dotPaint);
  }

  @override
  bool shouldRepaint(covariant _GtexPseudo3DPitchPainter oldDelegate) {
    return oldDelegate.projection.size != projection.size;
  }
}
