import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match_3d/entities/pitch_entity.dart';

class BallEntity {
  const BallEntity({
    required this.center,
    required this.depth,
    required this.radius,
    required this.fillColor,
    required this.elevation,
  });

  final Offset center;
  final double depth;
  final double radius;
  final Color fillColor;
  final double elevation;

  static BallEntity fromFrame({
    required MatchViewerBallFrame ball,
    required PitchProjection projection,
  }) {
    final double depth = projection.depthForPercent(ball.position.y);
    final double scale = projection.scaleForDepth(depth);
    final double elevation = ball.elevation.clamp(0, 3.2);
    final Offset projected = projection.projectPercent(ball.position);
    return BallEntity(
      center: Offset(projected.dx, projected.dy - (elevation * scale * 3.8)),
      depth: depth,
      radius: (2.8 + (elevation * 0.12)) * scale,
      fillColor: _fillColor(ball.state),
      elevation: elevation,
    );
  }

  void paint(Canvas canvas) {
    final Paint shadowPaint = Paint()
      ..color = Colors.black.withValues(
        alpha: (0.18 - (elevation * 0.03)).clamp(0.06, 0.18),
      );
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(center.dx, center.dy + (radius * 0.8)),
        width: radius * (2.2 - (elevation * 0.12)).clamp(1.7, 2.2),
        height: radius * (0.95 - (elevation * 0.09)).clamp(0.55, 0.95),
      ),
      shadowPaint,
    );

    final Paint ballPaint = Paint()..color = fillColor;
    final Paint seamPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = radius * 0.28
      ..color = const Color(0xFF0F172A).withValues(alpha: 0.88);
    canvas.drawCircle(center, radius, ballPaint);
    canvas.drawCircle(center, radius, seamPaint);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius * 0.62),
      0.4,
      2.3,
      false,
      seamPaint,
    );
    canvas.drawCircle(
      Offset(center.dx - (radius * 0.3), center.dy - (radius * 0.32)),
      radius * 0.24,
      Paint()..color = Colors.white.withValues(alpha: 0.72),
    );
  }

  static Color _fillColor(String state) {
    return switch (state) {
      'saved' => const Color(0xFFD1E9FF),
      'missed' => const Color(0xFFFEE4A8),
      'shot' => const Color(0xFFFFFFFF),
      'in_goal' => const Color(0xFFF2F4F7),
      _ => Colors.white,
    };
  }
}
