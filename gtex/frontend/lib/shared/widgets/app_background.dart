import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../widgets/gte_shell_theme.dart';

class AppBackground extends StatefulWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  State<AppBackground> createState() => _AppBackgroundState();
}

class _AppBackgroundState extends State<AppBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 24),
    );
    if (!_isTestBinding) {
      _controller.repeat();
    } else {
      _controller.value = 0.18;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return DecoratedBox(
      decoration: gteBackdropDecoration(),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          final double progress = _controller.value;
          final double zoom = 1.015 + (math.sin(progress * math.pi * 2) * 0.01);
          final double driftX = math.cos(progress * math.pi * 2) * 14;
          final double driftY = math.sin(progress * math.pi * 2) * 8;
          return Stack(
            fit: StackFit.expand,
            children: <Widget>[
              Transform.translate(
                offset: Offset(driftX, driftY),
                child: Transform.scale(
                  scale: zoom,
                  child: CustomPaint(
                    painter: _PitchLightPainter(
                      lineColor: tokens.surfaceHighlight.withValues(
                        alpha: 0.035,
                      ),
                      pulseColor: theme.primaryColor.withValues(alpha: 0.08),
                      glowColor: visuals.ambientSecondary.withValues(
                        alpha: 0.13,
                      ),
                      accentColor: tokens.accentCapital.withValues(alpha: 0.08),
                      progress: progress,
                    ),
                  ),
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
                          tokens.backgroundSoft.withValues(alpha: 0.22),
                          Colors.transparent,
                          tokens.background.withValues(alpha: 0.18),
                          tokens.background.withValues(alpha: 0.58),
                        ],
                        stops: const <double>[0, 0.32, 0.74, 1],
                      ),
                    ),
                  ),
                ),
              ),
              Positioned.fill(
                child: IgnorePointer(
                  child: CustomPaint(
                    painter: _ParticleFieldPainter(
                      primary: theme.primaryColor.withValues(alpha: 0.14),
                      secondary: tokens.accentCapital.withValues(alpha: 0.12),
                      progress: progress,
                    ),
                  ),
                ),
              ),
              if (visuals.glass)
                Positioned.fill(
                  child: IgnorePointer(
                    child: BackdropFilter(
                      filter: gtePanelBlur(visuals.surfaceBlurSigma * 0.5),
                      child: const SizedBox.expand(),
                    ),
                  ),
                ),
              child!,
            ],
          );
        },
        child: widget.child,
      ),
    );
  }
}

class _PitchLightPainter extends CustomPainter {
  const _PitchLightPainter({
    required this.lineColor,
    required this.pulseColor,
    required this.glowColor,
    required this.accentColor,
    required this.progress,
  });

  final Color lineColor;
  final Color pulseColor;
  final Color glowColor;
  final Color accentColor;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect rect = Offset.zero & size;
    final Paint basePaint =
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[
              const Color(0xFF040608),
              const Color(0xFF071016),
              const Color(0xFF05080D),
            ],
          ).createShader(rect);
    canvas.drawRect(rect, basePaint);

    final Paint floodlight =
        Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 42);
    final Offset leftFlood = Offset(
      size.width * 0.16,
      size.height * (0.14 + (math.sin(progress * math.pi * 2) * 0.03)),
    );
    final Offset rightFlood = Offset(
      size.width * 0.84,
      size.height * (0.12 + (math.cos(progress * math.pi * 2) * 0.03)),
    );
    floodlight.color = glowColor;
    canvas.drawCircle(leftFlood, size.shortestSide * 0.24, floodlight);
    canvas.drawCircle(rightFlood, size.shortestSide * 0.22, floodlight);

    final Paint gridPaint =
        Paint()
          ..color = lineColor
          ..strokeWidth = 1;
    const double gap = 64;
    for (double x = 0; x <= size.width; x += gap) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y <= size.height; y += gap) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final Paint routePaint =
        Paint()
          ..color = pulseColor
          ..strokeWidth = 1.6
          ..style = PaintingStyle.stroke;
    final Path route = Path()..moveTo(0, size.height * 0.64);
    for (double x = 0; x <= size.width; x += 18) {
      route.lineTo(
        x,
        (size.height * 0.64) +
            (math.sin((x / 72) + (progress * math.pi * 2)) * 10) -
            (math.cos((x / 36) - (progress * math.pi)) * 5),
      );
    }
    canvas.drawPath(route, routePaint);

    final Paint pitchMark =
        Paint()
          ..color = accentColor
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.3;
    final Rect centerCircle = Rect.fromCircle(
      center: Offset(size.width * 0.5, size.height * 0.5),
      radius: size.shortestSide * 0.11,
    );
    canvas.drawCircle(centerCircle.center, centerCircle.width / 2, pitchMark);
    canvas.drawLine(
      Offset(size.width * 0.5, size.height * 0.18),
      Offset(size.width * 0.5, size.height * 0.82),
      pitchMark,
    );
  }

  @override
  bool shouldRepaint(covariant _PitchLightPainter oldDelegate) {
    return oldDelegate.lineColor != lineColor ||
        oldDelegate.pulseColor != pulseColor ||
        oldDelegate.glowColor != glowColor ||
        oldDelegate.accentColor != accentColor ||
        oldDelegate.progress != progress;
  }
}

class _ParticleFieldPainter extends CustomPainter {
  const _ParticleFieldPainter({
    required this.primary,
    required this.secondary,
    required this.progress,
  });

  final Color primary;
  final Color secondary;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    for (int index = 0; index < 18; index += 1) {
      final double seed = index / 18;
      final double x =
          ((seed * size.width * 1.4) + (progress * size.width * 0.28)) %
          size.width;
      final double y =
          (((1 - seed) * size.height) +
              (math.sin((progress * math.pi * 2) + index) * 16)) %
          size.height;
      final double radius = 1.2 + ((index % 3) * 0.8);
      final Paint particle =
          Paint()
            ..color = (index.isEven ? primary : secondary).withValues(
              alpha: 0.08 + ((index % 4) * 0.02),
            )
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
      canvas.drawCircle(Offset(x, y), radius, particle);
    }
  }

  @override
  bool shouldRepaint(covariant _ParticleFieldPainter oldDelegate) {
    return oldDelegate.primary != primary ||
        oldDelegate.secondary != secondary ||
        oldDelegate.progress != progress;
  }
}
