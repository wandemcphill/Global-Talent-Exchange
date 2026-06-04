import 'package:flutter/material.dart';
import 'package:gte_frontend/features/3d/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/entities/pitch_entity.dart';

class BallEntity {
  const BallEntity({
    required this.center,
    required this.depth,
    required this.radius,
    required this.fillColor,
    required this.elevation,
    required this.spin,
    required this.trajectoryType,
    required this.trailStart,
    required this.trailStrength,
  });

  final Offset center;
  final double depth;
  final double radius;
  final Color fillColor;
  final double elevation;
  final double spin;
  final String trajectoryType;
  final Offset trailStart;
  final double trailStrength;

  static BallEntity fromNode({
    required Match3dSceneNode node,
    required Match3dBallPayload payload,
    required PitchProjection projection,
  }) {
    final MatchViewerPoint position = _percentFromWorld(node.position);
    final double depth = projection.depthForPercent(position.y);
    final double scale = projection.scaleForDepth(depth);
    final double elevation = payload.elevation.clamp(0, 3.2);
    final Offset projected = projection.projectPercent(position);
    final MatchViewerPoint previousPosition = _percentFromWorld(
      node.position - node.velocity.scale(0.28),
    );
    final Offset previousProjected = projection.projectPercent(
      previousPosition,
    );
    final double trailStrength =
        ((node.velocity.magnitude / 14).clamp(0, 1).toDouble() +
                (elevation > 0.35 ? 0.22 : 0))
            .clamp(0, 1)
            .toDouble();
    return BallEntity(
      center: Offset(projected.dx, projected.dy - (elevation * scale * 3.8)),
      depth: depth,
      radius: (2.8 + (elevation * 0.12)) * scale,
      fillColor: _fillColor(payload.state),
      elevation: elevation,
      spin: payload.spin,
      trajectoryType: payload.trajectoryType,
      trailStart: Offset.lerp(projected, previousProjected, 0.88) ?? projected,
      trailStrength: trailStrength,
    );
  }

  void paint(Canvas canvas) {
    if (trailStrength > 0.06) {
      final Paint streakPaint =
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: <Color>[
                _trailColor(trajectoryType).withValues(alpha: 0),
                _trailColor(
                  trajectoryType,
                ).withValues(alpha: 0.1 + (trailStrength * 0.14)),
                fillColor.withValues(alpha: 0.3 + (trailStrength * 0.22)),
              ],
            ).createShader(Rect.fromPoints(trailStart, center))
            ..strokeWidth = radius * (0.9 + (trailStrength * 0.85))
            ..strokeCap = StrokeCap.round;
      canvas.drawLine(trailStart, center, streakPaint);
    }

    if (elevation > 0.18) {
      final Paint trailPaint =
          Paint()
            ..shader = RadialGradient(
              colors: <Color>[
                fillColor.withValues(alpha: 0.26),
                fillColor.withValues(alpha: 0),
              ],
            ).createShader(
              Rect.fromCircle(
                center: center,
                radius: radius * (2.8 + elevation),
              ),
            );
      canvas.drawCircle(center, radius * (2.8 + elevation), trailPaint);
    }

    final Paint shadowPaint =
        Paint()
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
    final Paint seamPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = radius * 0.28
          ..color = const Color(0xFF0F172A).withValues(alpha: 0.88);
    canvas.drawCircle(center, radius, ballPaint);
    canvas.drawCircle(center, radius, seamPaint);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius * 0.62),
      0.4 + (spin * 0.22),
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

  static Color _trailColor(String trajectoryType) {
    return switch (trajectoryType) {
      'shot' => const Color(0xFFF97316),
      'pass' => const Color(0xFF53B1FD),
      'reset' => const Color(0xFFFDB022),
      _ => const Color(0xFFD0D5DD),
    };
  }
}

MatchViewerPoint _percentFromWorld(Match3dVector3 position) {
  return MatchViewerPoint(
    x:
        (((position.x + (PitchEntity.lengthMeters / 2)) /
                    PitchEntity.lengthMeters) *
                100)
            .clamp(0, 100)
            .toDouble(),
    y:
        (((position.z + (PitchEntity.widthMeters / 2)) /
                    PitchEntity.widthMeters) *
                100)
            .clamp(0, 100)
            .toDouble(),
  );
}
