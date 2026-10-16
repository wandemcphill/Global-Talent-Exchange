import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

class PitchProjection {
  const PitchProjection({
    required this.size,
    required this.farLeft,
    required this.farRight,
    required this.nearRight,
    required this.nearLeft,
    required this.lineWidth,
  });

  final Size size;
  final Offset farLeft;
  final Offset farRight;
  final Offset nearRight;
  final Offset nearLeft;
  final double lineWidth;

  static PitchProjection lerp(
    PitchProjection from,
    PitchProjection to,
    double t,
  ) {
    final double resolvedT = t.clamp(0, 1).toDouble();
    return PitchProjection(
      size: Size.lerp(from.size, to.size, resolvedT) ?? to.size,
      farLeft: Offset.lerp(from.farLeft, to.farLeft, resolvedT) ?? to.farLeft,
      farRight:
          Offset.lerp(from.farRight, to.farRight, resolvedT) ?? to.farRight,
      nearRight:
          Offset.lerp(from.nearRight, to.nearRight, resolvedT) ?? to.nearRight,
      nearLeft:
          Offset.lerp(from.nearLeft, to.nearLeft, resolvedT) ?? to.nearLeft,
      lineWidth: _lerp(from.lineWidth, to.lineWidth, resolvedT),
    );
  }

  Path get fieldPath {
    return Path()
      ..moveTo(farLeft.dx, farLeft.dy)
      ..lineTo(farRight.dx, farRight.dy)
      ..lineTo(nearRight.dx, nearRight.dy)
      ..lineTo(nearLeft.dx, nearLeft.dy)
      ..close();
  }

  Rect get bounds => fieldPath.getBounds();

  Offset projectPercent(MatchViewerPoint point) {
    return projectFraction(
      x: (point.x / 100).clamp(0, 1).toDouble(),
      y: (point.y / 100).clamp(0, 1).toDouble(),
    );
  }

  Offset projectField(Offset point) {
    return projectFraction(
      x: point.dx / PitchEntity.lengthMeters,
      y: point.dy / PitchEntity.widthMeters,
    );
  }

  Offset projectFraction({required double x, required double y}) {
    final Offset left = Offset(
      _lerp(farLeft.dx, nearLeft.dx, y),
      _lerp(farLeft.dy, nearLeft.dy, y),
    );
    final Offset right = Offset(
      _lerp(farRight.dx, nearRight.dx, y),
      _lerp(farRight.dy, nearRight.dy, y),
    );
    return Offset(_lerp(left.dx, right.dx, x), _lerp(left.dy, right.dy, x));
  }

  Path projectPolygon(List<Offset> points) {
    final Path path = Path();
    for (int index = 0; index < points.length; index += 1) {
      final Offset projected = projectField(points[index]);
      if (index == 0) {
        path.moveTo(projected.dx, projected.dy);
      } else {
        path.lineTo(projected.dx, projected.dy);
      }
    }
    path.close();
    return path;
  }

  Path projectPolyline(List<Offset> points) {
    final Path path = Path();
    for (int index = 0; index < points.length; index += 1) {
      final Offset projected = projectField(points[index]);
      if (index == 0) {
        path.moveTo(projected.dx, projected.dy);
      } else {
        path.lineTo(projected.dx, projected.dy);
      }
    }
    return path;
  }

  double depthForPercent(double y) {
    return (y / 100).clamp(0, 1).toDouble();
  }

  double scaleForDepth(double depth) {
    return _lerp(0.58, 1.06, depth);
  }
}

class PitchEntity {
  const PitchEntity({required this.projection});

  static const double lengthMeters = 105;
  static const double widthMeters = 68;
  static const double aspectRatio = lengthMeters / widthMeters;

  final PitchProjection projection;

  static PitchProjection project(
    Size size, {
    MatchEngineCameraPreset cameraPreset =
        MatchEngineCameraPreset.tactical_high,
  }) {
    final double centerX = size.width / 2;
    final double topY = switch (cameraPreset) {
      MatchEngineCameraPreset.stadium_wide => size.height * 0.08,
      MatchEngineCameraPreset.kickoff_center => size.height * 0.11,
      MatchEngineCameraPreset.tactical_high => size.height * 0.06,
      MatchEngineCameraPreset.attacking_third_left ||
      MatchEngineCameraPreset.attacking_third_right => size.height * 0.14,
      MatchEngineCameraPreset.defensive_block => size.height * 0.10,
      MatchEngineCameraPreset.set_piece_left ||
      MatchEngineCameraPreset.set_piece_right => size.height * 0.14,
      MatchEngineCameraPreset.goal_replay => size.height * 0.17,
      MatchEngineCameraPreset.halftime_board ||
      MatchEngineCameraPreset.fulltime_board => size.height * 0.12,
    };
    final double bottomY = switch (cameraPreset) {
      MatchEngineCameraPreset.stadium_wide => size.height * 0.93,
      MatchEngineCameraPreset.kickoff_center => size.height * 0.95,
      MatchEngineCameraPreset.tactical_high => size.height * 0.89,
      MatchEngineCameraPreset.attacking_third_left ||
      MatchEngineCameraPreset.attacking_third_right => size.height * 0.96,
      MatchEngineCameraPreset.defensive_block => size.height * 0.95,
      MatchEngineCameraPreset.set_piece_left ||
      MatchEngineCameraPreset.set_piece_right => size.height * 0.96,
      MatchEngineCameraPreset.goal_replay => size.height * 0.95,
      MatchEngineCameraPreset.halftime_board ||
      MatchEngineCameraPreset.fulltime_board => size.height * 0.90,
    };
    final double farHalfWidth = switch (cameraPreset) {
      MatchEngineCameraPreset.stadium_wide => size.width * 0.43,
      MatchEngineCameraPreset.kickoff_center => size.width * 0.37,
      MatchEngineCameraPreset.tactical_high => size.width * 0.41,
      MatchEngineCameraPreset.attacking_third_left ||
      MatchEngineCameraPreset.attacking_third_right => size.width * 0.25,
      MatchEngineCameraPreset.defensive_block => size.width * 0.31,
      MatchEngineCameraPreset.set_piece_left ||
      MatchEngineCameraPreset.set_piece_right => size.width * 0.27,
      MatchEngineCameraPreset.goal_replay => size.width * 0.24,
      MatchEngineCameraPreset.halftime_board ||
      MatchEngineCameraPreset.fulltime_board => size.width * 0.35,
    };
    final double nearHalfWidth = switch (cameraPreset) {
      MatchEngineCameraPreset.stadium_wide => size.width * 0.49,
      MatchEngineCameraPreset.kickoff_center => size.width * 0.52,
      MatchEngineCameraPreset.tactical_high => size.width * 0.48,
      MatchEngineCameraPreset.attacking_third_left ||
      MatchEngineCameraPreset.attacking_third_right => size.width * 0.62,
      MatchEngineCameraPreset.defensive_block => size.width * 0.54,
      MatchEngineCameraPreset.set_piece_left ||
      MatchEngineCameraPreset.set_piece_right => size.width * 0.61,
      MatchEngineCameraPreset.goal_replay => size.width * 0.65,
      MatchEngineCameraPreset.halftime_board ||
      MatchEngineCameraPreset.fulltime_board => size.width * 0.50,
    };
    final double horizonShift = switch (cameraPreset) {
      MatchEngineCameraPreset.stadium_wide => 0,
      MatchEngineCameraPreset.kickoff_center => 0,
      MatchEngineCameraPreset.tactical_high => 0,
      MatchEngineCameraPreset.attacking_third_left => size.width * -0.05,
      MatchEngineCameraPreset.attacking_third_right => size.width * 0.05,
      MatchEngineCameraPreset.defensive_block => 0,
      MatchEngineCameraPreset.set_piece_left => size.width * -0.03,
      MatchEngineCameraPreset.set_piece_right => size.width * 0.03,
      MatchEngineCameraPreset.goal_replay => 0,
      MatchEngineCameraPreset.halftime_board => 0,
      MatchEngineCameraPreset.fulltime_board => 0,
    };
    return PitchProjection(
      size: size,
      farLeft: Offset(centerX - farHalfWidth + horizonShift, topY),
      farRight: Offset(centerX + farHalfWidth + horizonShift, topY),
      nearRight: Offset(centerX + nearHalfWidth, bottomY),
      nearLeft: Offset(centerX - nearHalfWidth, bottomY),
      lineWidth: size.shortestSide * 0.0046,
    );
  }

  void paint(Canvas canvas) {
    final Rect viewport = Offset.zero & projection.size;
    final Path fieldPath = projection.fieldPath;
    final Rect fieldBounds = projection.bounds;

    final Paint backdropPaint =
        Paint()
          ..shader = const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[
              Color(0xFF08141E),
              Color(0xFF0A1F29),
              Color(0xFF07131B),
            ],
          ).createShader(viewport);
    canvas.drawRect(viewport, backdropPaint);

    final Paint fieldShadowPaint =
        Paint()
          ..color = Colors.black.withValues(alpha: 0.18)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16);
    canvas.drawPath(fieldPath.shift(const Offset(0, 8)), fieldShadowPaint);

    final Paint fieldPaint =
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[
              const Color(0xFF154F34),
              const Color(0xFF1D6B42),
              const Color(0xFF103E29),
            ],
          ).createShader(fieldBounds);
    canvas.drawPath(fieldPath, fieldPaint);

    canvas.save();
    canvas.clipPath(fieldPath);
    for (int index = 0; index < 8; index += 1) {
      final double yStart = (widthMeters / 8) * index;
      final double yEnd = (widthMeters / 8) * (index + 1);
      final Paint stripePaint =
          Paint()
            ..color =
                index.isEven
                    ? const Color(0x11000000)
                    : const Color(0x10FFFFFF);
      canvas.drawPath(
        projection.projectPolygon(<Offset>[
          Offset(0, yStart),
          Offset(lengthMeters, yStart),
          Offset(lengthMeters, yEnd),
          Offset(0, yEnd),
        ]),
        stripePaint,
      );
    }

    final Paint vignettePaint =
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[
              Colors.white.withValues(alpha: 0.06),
              Colors.transparent,
              Colors.black.withValues(alpha: 0.12),
            ],
            stops: const <double>[0, 0.45, 1],
          ).createShader(fieldBounds);
    canvas.drawRect(fieldBounds, vignettePaint);
    canvas.restore();

    final Paint linePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = projection.lineWidth
          ..color = Colors.white.withValues(alpha: 0.88);
    final Paint spotPaint =
        Paint()
          ..style = PaintingStyle.fill
          ..color = Colors.white.withValues(alpha: 0.88);

    canvas.drawPath(fieldPath, linePaint);
    canvas.drawPath(
      projection.projectPolyline(<Offset>[
        const Offset(lengthMeters / 2, 0),
        const Offset(lengthMeters / 2, widthMeters),
      ]),
      linePaint,
    );
    canvas.drawPath(
      _circlePath(
        center: const Offset(lengthMeters / 2, widthMeters / 2),
        radius: 9.15,
      ),
      linePaint,
    );

    _drawPenaltyArea(
      canvas,
      linePaint,
      distanceFromGoal: 16.5,
      areaWidth: 40.32,
    );
    _drawPenaltyArea(
      canvas,
      linePaint,
      distanceFromGoal: 5.5,
      areaWidth: 18.32,
    );

    canvas.drawCircle(
      projection.projectField(const Offset(11, widthMeters / 2)),
      projection.lineWidth * 1.2,
      spotPaint,
    );
    canvas.drawCircle(
      projection.projectField(const Offset(lengthMeters - 11, widthMeters / 2)),
      projection.lineWidth * 1.2,
      spotPaint,
    );
    canvas.drawCircle(
      projection.projectField(const Offset(lengthMeters / 2, widthMeters / 2)),
      projection.lineWidth * 1.2,
      spotPaint,
    );

    _drawGoals(canvas);
  }

  void _drawPenaltyArea(
    Canvas canvas,
    Paint linePaint, {
    required double distanceFromGoal,
    required double areaWidth,
  }) {
    final double yStart = (widthMeters - areaWidth) / 2;
    final double yEnd = yStart + areaWidth;
    canvas.drawPath(
      projection.projectPolygon(<Offset>[
        Offset(0, yStart),
        Offset(distanceFromGoal, yStart),
        Offset(distanceFromGoal, yEnd),
        Offset(0, yEnd),
      ]),
      linePaint,
    );
    canvas.drawPath(
      projection.projectPolygon(<Offset>[
        Offset(lengthMeters - distanceFromGoal, yStart),
        Offset(lengthMeters, yStart),
        Offset(lengthMeters, yEnd),
        Offset(lengthMeters - distanceFromGoal, yEnd),
      ]),
      linePaint,
    );
  }

  void _drawGoals(Canvas canvas) {
    final Paint goalFillPaint =
        Paint()..color = Colors.white.withValues(alpha: 0.08);
    final Paint goalLinePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = projection.lineWidth * 0.9
          ..color = Colors.white.withValues(alpha: 0.62);

    final Path leftGoal = projection.projectPolygon(<Offset>[
      const Offset(-2.6, (widthMeters / 2) - 3.66),
      const Offset(0, (widthMeters / 2) - 3.66),
      const Offset(0, (widthMeters / 2) + 3.66),
      const Offset(-2.6, (widthMeters / 2) + 3.66),
    ]);
    final Path rightGoal = projection.projectPolygon(<Offset>[
      const Offset(lengthMeters, (widthMeters / 2) - 3.66),
      const Offset(lengthMeters + 2.6, (widthMeters / 2) - 3.66),
      const Offset(lengthMeters + 2.6, (widthMeters / 2) + 3.66),
      const Offset(lengthMeters, (widthMeters / 2) + 3.66),
    ]);

    canvas.drawPath(leftGoal, goalFillPaint);
    canvas.drawPath(rightGoal, goalFillPaint);
    canvas.drawPath(leftGoal, goalLinePaint);
    canvas.drawPath(rightGoal, goalLinePaint);
  }

  Path _circlePath({required Offset center, required double radius}) {
    final Path path = Path();
    for (int index = 0; index <= 28; index += 1) {
      final double angle = (math.pi * 2 * index) / 28;
      final Offset point = Offset(
        center.dx + (math.cos(angle) * radius),
        center.dy + (math.sin(angle) * radius),
      );
      final Offset projected = projection.projectField(point);
      if (index == 0) {
        path.moveTo(projected.dx, projected.dy);
      } else {
        path.lineTo(projected.dx, projected.dy);
      }
    }
    path.close();
    return path;
  }
}

double _lerp(double begin, double end, double t) {
  return begin + ((end - begin) * t);
}
