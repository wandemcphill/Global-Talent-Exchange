import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';

/// Mown-grass stripes: alternating 56px bands of the night-pitch surface.
class GtexTurfStripesPainter extends CustomPainter {
  const GtexTurfStripesPainter({this.band = 56, this.opacity = 0.025});

  final double band;
  final double opacity;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = GtexFloodlit.chalk.withValues(alpha: opacity);
    for (double x = 0; x < size.width; x += band * 2) {
      canvas.drawRect(Rect.fromLTWH(x, 0, band, size.height), paint);
    }
  }

  @override
  bool shouldRepaint(covariant GtexTurfStripesPainter oldDelegate) =>
      oldDelegate.band != band || oldDelegate.opacity != opacity;
}

/// A chalk centre circle with its spot, used behind ratings and portraits.
class GtexCentreCirclePainter extends CustomPainter {
  const GtexCentreCirclePainter({
    this.color = GtexFloodlit.chalk,
    this.opacity = 0.2,
    this.dashed = false,
    this.strokeWidth = 1,
  });

  final Color color;
  final double opacity;
  final bool dashed;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset centre = size.center(Offset.zero);
    final double radius = size.shortestSide / 2 - strokeWidth;
    final Paint stroke = Paint()
      ..color = color.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;
    if (!dashed) {
      canvas.drawCircle(centre, radius, stroke);
    } else {
      const double dash = 0.09;
      for (double a = 0; a < 6.283; a += dash * 2) {
        canvas.drawArc(
          Rect.fromCircle(center: centre, radius: radius),
          a,
          dash,
          false,
          stroke,
        );
      }
    }
    canvas.drawCircle(
      centre,
      strokeWidth * 1.6,
      Paint()..color = color.withValues(alpha: opacity),
    );
  }

  @override
  bool shouldRepaint(covariant GtexCentreCirclePainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.opacity != opacity ||
      oldDelegate.dashed != dashed ||
      oldDelegate.strokeWidth != strokeWidth;
}

/// A dashed chalk rectangle inset inside a card, like a touchline.
class GtexChalkFramePainter extends CustomPainter {
  const GtexChalkFramePainter({
    this.inset = 10,
    this.radius = 10,
    this.opacity = 0.28,
  });

  final double inset;
  final double radius;
  final double opacity;

  @override
  void paint(Canvas canvas, Size size) {
    final RRect frame = RRect.fromRectAndRadius(
      Rect.fromLTWH(inset, inset, size.width - inset * 2, size.height - inset * 2),
      Radius.circular(radius),
    );
    final Paint paint = Paint()
      ..color = GtexFloodlit.chalk.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final Path path = Path()..addRRect(frame);
    for (final metric in path.computeMetrics()) {
      double distance = 0;
      while (distance < metric.length) {
        canvas.drawPath(metric.extractPath(distance, distance + 6), paint);
        distance += 11;
      }
    }
  }

  @override
  bool shouldRepaint(covariant GtexChalkFramePainter oldDelegate) =>
      oldDelegate.inset != inset ||
      oldDelegate.radius != radius ||
      oldDelegate.opacity != opacity;
}
