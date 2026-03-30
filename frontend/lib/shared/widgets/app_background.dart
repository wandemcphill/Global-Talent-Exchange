import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../widgets/gte_shell_theme.dart';

class AppBackground extends StatelessWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return DecoratedBox(
      decoration: gteBackdropDecoration(),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Positioned(
            top: -180,
            right: -110,
            child: _GlowOrb(
              size: 360,
              color: visuals.ambientPrimary.withValues(alpha: 0.14),
            ),
          ),
          Positioned(
            left: -100,
            bottom: -120,
            child: _GlowOrb(
              size: 320,
              color: visuals.ambientSecondary.withValues(alpha: 0.14),
            ),
          ),
          Positioned(
            top: 140,
            left: 36,
            child: _GlowOrb(
              size: 200,
              color: visuals.ambientTertiary.withValues(alpha: 0.08),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: <Color>[
                      visuals.heroAccent.withValues(alpha: 0.04),
                      Colors.transparent,
                      Colors.transparent,
                      tokens.background.withValues(alpha: 0.22),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(
                painter: _BackgroundGridPainter(
                  lineColor: tokens.surfaceHighlight.withValues(alpha: 0.04),
                  pulseColor: theme.primaryColor.withValues(alpha: 0.05),
                ),
              ),
            ),
          ),
          if (visuals.glass)
            Positioned.fill(
              child: IgnorePointer(
                child: BackdropFilter(
                  filter: gtePanelBlur(visuals.surfaceBlurSigma * 0.45),
                  child: const SizedBox.expand(),
                ),
              ),
            ),
          child,
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ClipOval(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 36, sigmaY: 36),
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: <Color>[color, color.withValues(alpha: 0)],
            ),
          ),
        ),
      ),
    );
  }
}

class _BackgroundGridPainter extends CustomPainter {
  const _BackgroundGridPainter({
    required this.lineColor,
    required this.pulseColor,
  });

  final Color lineColor;
  final Color pulseColor;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint linePaint =
        Paint()
          ..color = lineColor
          ..strokeWidth = 1;
    const double gap = 56;
    for (double x = 0; x <= size.width; x += gap) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), linePaint);
    }
    for (double y = 0; y <= size.height; y += gap) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
    }

    final Paint pulsePaint = Paint()..style = PaintingStyle.fill;
    final List<Offset> pulses = <Offset>[
      Offset(size.width * 0.18, size.height * 0.24),
      Offset(size.width * 0.78, size.height * 0.28),
      Offset(size.width * 0.52, size.height * 0.76),
    ];
    for (int index = 0; index < pulses.length; index += 1) {
      final double radius = size.shortestSide * (0.14 + (index * 0.04));
      pulsePaint.color = pulseColor.withValues(alpha: 0.08 - (index * 0.015));
      canvas.drawCircle(pulses[index], radius, pulsePaint);
    }

    final Paint routePaint =
        Paint()
          ..color = pulseColor.withValues(alpha: 0.07)
          ..strokeWidth = 1.4
          ..style = PaintingStyle.stroke;
    final Path path = Path()..moveTo(0, size.height * 0.62);
    for (double x = 0; x <= size.width; x += 24) {
      path.lineTo(
        x,
        (size.height * 0.62) + (math.sin(x / 96) * 10) - (math.cos(x / 54) * 4),
      );
    }
    canvas.drawPath(path, routePaint);
  }

  @override
  bool shouldRepaint(covariant _BackgroundGridPainter oldDelegate) {
    return oldDelegate.lineColor != lineColor ||
        oldDelegate.pulseColor != pulseColor;
  }
}
