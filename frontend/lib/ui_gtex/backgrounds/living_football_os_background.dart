import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme/gtex_colors.dart';

enum LivingFootballOSDensity { automatic, quiet, standard, rich }

class LivingFootballOSBackground extends StatefulWidget {
  const LivingFootballOSBackground({
    super.key,
    required this.child,
    this.motionEnabledOverride,
    this.density = LivingFootballOSDensity.automatic,
  });

  final Widget child;
  final bool? motionEnabledOverride;
  final LivingFootballOSDensity density;

  @override
  State<LivingFootballOSBackground> createState() =>
      _LivingFootballOSBackgroundState();
}

class _LivingFootballOSBackgroundState extends State<LivingFootballOSBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _isAnimating = false;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 36),
    )..value = 0.32;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncMotion();
  }

  @override
  void didUpdateWidget(covariant LivingFootballOSBackground oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.motionEnabledOverride != widget.motionEnabledOverride) {
      _syncMotion();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _syncMotion() {
    final bool shouldAnimate =
        widget.motionEnabledOverride ??
        (!_isTestBinding &&
            TickerMode.of(context) &&
            !MediaQuery.of(context).disableAnimations);
    if (shouldAnimate == _isAnimating) {
      return;
    }
    _isAnimating = shouldAnimate;
    if (shouldAnimate) {
      _controller.repeat();
    } else {
      _controller.stop();
      _controller.value = 0.32;
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final _FootballOSDensity resolvedDensity = _FootballOSDensity.resolve(
      widget.density,
      viewport.width,
    );

    return RepaintBoundary(
      key: const Key('living-football-os-background'),
      child: ColoredBox(
        color: GtexColors.stadiumBlack,
        child: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final double progress = _isAnimating ? _controller.value : 0.32;
            return Stack(
              fit: StackFit.expand,
              children: <Widget>[
                Positioned.fill(
                  child: _StaticFallbackWallpaper(enabled: !_isAnimating),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      key: const Key('living-football-os-atmosphere'),
                      painter: _FootballAtmospherePainter(
                        progress: progress,
                        motionEnabled: _isAnimating,
                      ),
                    ),
                  ),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      key: const Key('living-football-os-tactics'),
                      painter: _TacticalPitchPainter(
                        progress: progress,
                        motionEnabled: _isAnimating,
                      ),
                    ),
                  ),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      key: const Key('living-football-os-particles'),
                      painter: _FootballActivityPainter(
                        progress: progress,
                        motionEnabled: _isAnimating,
                        particleCount: resolvedDensity.particleCount,
                        activityDotCount: resolvedDensity.activityDotCount,
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
                            GtexColors.stadiumBlack.withValues(alpha: 0.10),
                            Colors.transparent,
                            GtexColors.stadiumBlack.withValues(alpha: 0.30),
                            GtexColors.stadiumBlack.withValues(alpha: 0.82),
                          ],
                          stops: const <double>[0, 0.32, 0.72, 1],
                        ),
                      ),
                    ),
                  ),
                ),
                child!,
              ],
            );
          },
          child: widget.child,
        ),
      ),
    );
  }
}

class _StaticFallbackWallpaper extends StatelessWidget {
  const _StaticFallbackWallpaper({required this.enabled});

  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) {
      return const SizedBox.expand();
    }
    return Opacity(
      key: const Key('living-football-os-static-wallpaper'),
      opacity: 0.58,
      child: SvgPicture.asset(
        'assets/media/gtex_living_football_os_wallpaper.svg',
        fit: BoxFit.cover,
        placeholderBuilder: (_) => const SizedBox.expand(),
      ),
    );
  }
}

class _FootballOSDensity {
  const _FootballOSDensity({
    required this.particleCount,
    required this.activityDotCount,
  });

  final int particleCount;
  final int activityDotCount;

  static _FootballOSDensity resolve(
    LivingFootballOSDensity density,
    double width,
  ) {
    switch (density) {
      case LivingFootballOSDensity.quiet:
        return const _FootballOSDensity(particleCount: 12, activityDotCount: 8);
      case LivingFootballOSDensity.standard:
        return const _FootballOSDensity(
          particleCount: 20,
          activityDotCount: 12,
        );
      case LivingFootballOSDensity.rich:
        return const _FootballOSDensity(
          particleCount: 30,
          activityDotCount: 16,
        );
      case LivingFootballOSDensity.automatic:
        if (width < 720) {
          return const _FootballOSDensity(
            particleCount: 12,
            activityDotCount: 7,
          );
        }
        if (width < 1280) {
          return const _FootballOSDensity(
            particleCount: 18,
            activityDotCount: 10,
          );
        }
        return const _FootballOSDensity(
          particleCount: 24,
          activityDotCount: 14,
        );
    }
  }
}

class _FootballAtmospherePainter extends CustomPainter {
  const _FootballAtmospherePainter({
    required this.progress,
    required this.motionEnabled,
  });

  final double progress;
  final bool motionEnabled;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) {
      return;
    }
    final Rect bounds = Offset.zero & size;
    canvas.drawRect(
      bounds,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF020506),
            Color(0xFF061316),
            Color(0xFF091D18),
            Color(0xFF030607),
          ],
          stops: <double>[0, 0.34, 0.68, 1],
        ).createShader(bounds),
    );

    final double phase = progress * math.pi * 2;
    _drawFloodlight(
      canvas,
      size,
      center: Offset(
        size.width * 0.17,
        size.height * (0.12 + math.sin(phase) * 0.018),
      ),
      color: GtexColors.cyan.withValues(alpha: 0.13),
      radius: size.shortestSide * 0.34,
    );
    _drawFloodlight(
      canvas,
      size,
      center: Offset(
        size.width * 0.86,
        size.height * (0.13 + math.cos(phase) * 0.018),
      ),
      color: GtexColors.pitch.withValues(alpha: 0.13),
      radius: size.shortestSide * 0.32,
    );
    _drawFloodlight(
      canvas,
      size,
      center: Offset(size.width * 0.52, size.height * 0.08),
      color: GtexColors.gold.withValues(alpha: 0.07),
      radius: size.shortestSide * 0.24,
    );

    _drawAuroraRibbon(
      canvas,
      size,
      phase: phase,
      yBase: 0.28,
      amplitude: 18,
      colors: <Color>[
        GtexColors.pitch.withValues(alpha: 0.11),
        GtexColors.cyan.withValues(alpha: 0.06),
        Colors.transparent,
      ],
    );
    _drawAuroraRibbon(
      canvas,
      size,
      phase: phase + 1.7,
      yBase: 0.44,
      amplitude: 12,
      colors: <Color>[
        GtexColors.gold.withValues(alpha: 0.07),
        GtexColors.mint.withValues(alpha: 0.08),
        Colors.transparent,
      ],
    );

    final Paint vignette =
        Paint()
          ..shader = RadialGradient(
            center: Alignment.center,
            radius: 0.9,
            colors: <Color>[
              Colors.transparent,
              GtexColors.stadiumBlack.withValues(alpha: 0.78),
            ],
            stops: const <double>[0.42, 1],
          ).createShader(bounds);
    canvas.drawRect(bounds, vignette);
  }

  void _drawFloodlight(
    Canvas canvas,
    Size size, {
    required Offset center,
    required Color color,
    required double radius,
  }) {
    final Paint paint =
        Paint()
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 48)
          ..shader = RadialGradient(
            colors: <Color>[color, color.withValues(alpha: 0)],
          ).createShader(Rect.fromCircle(center: center, radius: radius));
    canvas.drawCircle(center, radius, paint);
  }

  void _drawAuroraRibbon(
    Canvas canvas,
    Size size, {
    required double phase,
    required double yBase,
    required double amplitude,
    required List<Color> colors,
  }) {
    final Path top = Path()..moveTo(-40, size.height * yBase);
    for (double x = -40; x <= size.width + 40; x += 56) {
      top.lineTo(
        x,
        size.height * yBase +
            math.sin((x / size.width * math.pi * 3) + phase) * amplitude,
      );
    }
    final Path ribbon = Path.from(top);
    for (double x = size.width + 40; x >= -40; x -= 56) {
      ribbon.lineTo(
        x,
        size.height * (yBase + 0.12) +
            math.cos((x / size.width * math.pi * 2.6) + phase) *
                (amplitude * 0.74),
      );
    }
    ribbon.close();
    canvas.drawPath(
      ribbon,
      Paint()
        ..style = PaintingStyle.fill
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28)
        ..shader = LinearGradient(colors: colors).createShader(
          Rect.fromLTWH(0, size.height * yBase, size.width, size.height * 0.2),
        ),
    );
  }

  @override
  bool shouldRepaint(covariant _FootballAtmospherePainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.motionEnabled != motionEnabled;
  }
}

class _TacticalPitchPainter extends CustomPainter {
  const _TacticalPitchPainter({
    required this.progress,
    required this.motionEnabled,
  });

  final double progress;
  final bool motionEnabled;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) {
      return;
    }
    final Rect pitch = Rect.fromLTWH(
      size.width * 0.11,
      size.height * 0.19,
      size.width * 0.78,
      size.height * 0.62,
    );
    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.055)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.1;
    final Paint accentLine =
        Paint()
          ..color = GtexColors.pitch.withValues(alpha: 0.09)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2;

    canvas.drawRRect(
      RRect.fromRectAndRadius(pitch, const Radius.circular(18)),
      linePaint,
    );
    canvas.drawLine(
      Offset(pitch.center.dx, pitch.top),
      Offset(pitch.center.dx, pitch.bottom),
      linePaint,
    );
    canvas.drawCircle(pitch.center, pitch.shortestSide * 0.13, linePaint);
    canvas.drawCircle(pitch.center, 2.6, accentLine);

    final Rect leftBox = Rect.fromLTWH(
      pitch.left,
      pitch.top + pitch.height * 0.25,
      pitch.width * 0.16,
      pitch.height * 0.5,
    );
    final Rect rightBox = Rect.fromLTWH(
      pitch.right - pitch.width * 0.16,
      pitch.top + pitch.height * 0.25,
      pitch.width * 0.16,
      pitch.height * 0.5,
    );
    canvas.drawRect(leftBox, linePaint);
    canvas.drawRect(rightBox, linePaint);

    for (int index = 1; index < 6; index += 1) {
      final double x = pitch.left + pitch.width * (index / 6);
      canvas.drawLine(
        Offset(x, pitch.top),
        Offset(x, pitch.bottom),
        Paint()
          ..color = GtexColors.mint.withValues(alpha: 0.022)
          ..strokeWidth = 0.8,
      );
    }

    final double pulse =
        motionEnabled ? 0.65 + (math.sin(progress * math.pi * 2) * 0.22) : 0.7;
    _drawTransferArc(
      canvas,
      pitch,
      start: const Offset(0.20, 0.70),
      control: const Offset(0.36, 0.30),
      end: const Offset(0.66, 0.38),
      color: GtexColors.pitch.withValues(alpha: 0.16 * pulse),
    );
    _drawTransferArc(
      canvas,
      pitch,
      start: const Offset(0.34, 0.30),
      control: const Offset(0.52, 0.12),
      end: const Offset(0.82, 0.56),
      color: GtexColors.cyan.withValues(alpha: 0.13 * pulse),
    );
    _drawTransferArc(
      canvas,
      pitch,
      start: const Offset(0.18, 0.46),
      control: const Offset(0.44, 0.82),
      end: const Offset(0.74, 0.68),
      color: GtexColors.gold.withValues(alpha: 0.10 * pulse),
    );
  }

  void _drawTransferArc(
    Canvas canvas,
    Rect pitch, {
    required Offset start,
    required Offset control,
    required Offset end,
    required Color color,
  }) {
    Offset map(Offset point) => Offset(
      pitch.left + pitch.width * point.dx,
      pitch.top + pitch.height * point.dy,
    );

    final Path path =
        Path()
          ..moveTo(map(start).dx, map(start).dy)
          ..quadraticBezierTo(
            map(control).dx,
            map(control).dy,
            map(end).dx,
            map(end).dy,
          );
    final Paint pathPaint =
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6
          ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, pathPaint);
    final Paint dotPaint =
        Paint()
          ..color = color.withValues(alpha: 0.74)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    canvas.drawCircle(map(start), 3.4, dotPaint);
    canvas.drawCircle(map(end), 4.4, dotPaint);
  }

  @override
  bool shouldRepaint(covariant _TacticalPitchPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.motionEnabled != motionEnabled;
  }
}

class _FootballActivityPainter extends CustomPainter {
  const _FootballActivityPainter({
    required this.progress,
    required this.motionEnabled,
    required this.particleCount,
    required this.activityDotCount,
  });

  final double progress;
  final bool motionEnabled;
  final int particleCount;
  final int activityDotCount;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) {
      return;
    }
    _drawParticles(canvas, size);
    _drawActivityDots(canvas, size);
  }

  void _drawParticles(Canvas canvas, Size size) {
    for (int index = 0; index < particleCount; index += 1) {
      final double seed = (index + 1) * 0.61803398875;
      final double drift = motionEnabled ? progress : 0.32;
      final double x =
          ((seed % 1) * size.width + (drift * size.width * 0.10)) % size.width;
      final double y =
          (((seed * 1.73) % 1) * size.height) +
          math.sin((drift * math.pi * 2) + index) * 8;
      final Color color =
          index % 3 == 0
              ? GtexColors.pitch
              : index % 3 == 1
              ? GtexColors.cyan
              : GtexColors.gold;
      canvas.drawCircle(
        Offset(x, y.clamp(0, size.height).toDouble()),
        1.0 + (index % 3) * 0.55,
        Paint()
          ..color = color.withValues(alpha: 0.08)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
      );
    }
  }

  void _drawActivityDots(Canvas canvas, Size size) {
    const List<Offset> anchors = <Offset>[
      Offset(0.22, 0.28),
      Offset(0.34, 0.64),
      Offset(0.48, 0.38),
      Offset(0.58, 0.72),
      Offset(0.70, 0.30),
      Offset(0.82, 0.56),
      Offset(0.18, 0.76),
      Offset(0.76, 0.78),
      Offset(0.42, 0.24),
      Offset(0.62, 0.48),
      Offset(0.28, 0.46),
      Offset(0.88, 0.34),
      Offset(0.12, 0.52),
      Offset(0.52, 0.18),
      Offset(0.66, 0.62),
      Offset(0.38, 0.82),
    ];
    final int count = math.min(activityDotCount, anchors.length);
    for (int index = 0; index < count; index += 1) {
      final Offset anchor = anchors[index];
      final double wave =
          motionEnabled
              ? 0.68 +
                  math.sin((progress * math.pi * 2) + (index * 0.72)) * 0.24
              : 0.68;
      final Color color = index.isEven ? GtexColors.pitch : GtexColors.mint;
      final Offset center = Offset(
        anchor.dx * size.width,
        anchor.dy * size.height,
      );
      canvas.drawCircle(
        center,
        5.5 + wave * 2.2,
        Paint()..color = color.withValues(alpha: 0.035),
      );
      canvas.drawCircle(
        center,
        2.0 + wave,
        Paint()
          ..color = color.withValues(alpha: 0.22)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FootballActivityPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.motionEnabled != motionEnabled ||
        oldDelegate.particleCount != particleCount ||
        oldDelegate.activityDotCount != activityDotCount;
  }
}
