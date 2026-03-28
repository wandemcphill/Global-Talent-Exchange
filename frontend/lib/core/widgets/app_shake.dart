import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_motion.dart';

class AppShake extends StatelessWidget {
  const AppShake({
    super.key,
    required this.child,
    required this.trigger,
    this.amplitude = 12,
  });

  final Widget child;
  final int trigger;
  final double amplitude;

  @override
  Widget build(BuildContext context) {
    if (trigger <= 0) {
      return child;
    }

    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(trigger),
      tween: Tween<double>(begin: 0, end: 1),
      duration: AppMotion.slow,
      curve: AppMotion.easeInOut,
      child: child,
      builder: (BuildContext context, double value, Widget? child) {
        final double offset =
            math.sin(value * math.pi * 6) * amplitude * (1 - value);
        return Transform.translate(offset: Offset(offset, 0), child: child);
      },
    );
  }
}
