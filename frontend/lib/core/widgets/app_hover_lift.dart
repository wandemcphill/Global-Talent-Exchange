import 'package:flutter/material.dart';

import '../theme/app_motion.dart';

class AppHoverLift extends StatefulWidget {
  const AppHoverLift({
    super.key,
    required this.child,
    this.enabled = true,
    this.hoverScale = 1.05,
    this.hoverLift = -6,
  });

  final Widget child;
  final bool enabled;
  final double hoverScale;
  final double hoverLift;

  @override
  State<AppHoverLift> createState() => _AppHoverLiftState();
}

class _AppHoverLiftState extends State<AppHoverLift> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    if (!widget.enabled) {
      return widget.child;
    }

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedScale(
        duration: AppMotion.hover,
        curve: AppMotion.easeOut,
        scale: _hovered ? widget.hoverScale : 1,
        child: AnimatedContainer(
          duration: AppMotion.hover,
          curve: AppMotion.easeOut,
          transform: Matrix4.translationValues(
            0,
            _hovered ? widget.hoverLift : 0,
            0,
          ),
          child: RepaintBoundary(child: widget.child),
        ),
      ),
    );
  }
}
