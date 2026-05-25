import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexSkeleton extends StatefulWidget {
  const GtexSkeleton({
    super.key,
    this.width,
    this.height = 16,
    this.borderRadius,
  });

  const GtexSkeleton.box({
    super.key,
    this.width,
    required this.height,
    this.borderRadius,
  });

  const GtexSkeleton.text({super.key, this.width, this.height = 12})
    : borderRadius = GtexRadius.sm;

  final double? width;
  final double height;
  final double? borderRadius;

  @override
  State<GtexSkeleton> createState() => _GtexSkeletonState();
}

class _GtexSkeletonState extends State<GtexSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens colors = GtexColors.of(context);
    final bool reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final BorderRadius radius = BorderRadius.circular(
      widget.borderRadius ?? GtexRadius.md,
    );
    final Widget box = Container(
      key: const Key('gtex-skeleton-box'),
      width: widget.width,
      height: widget.height,
      decoration: BoxDecoration(color: colors.bgOverlay, borderRadius: radius),
    );
    if (reduceMotion) {
      return box;
    }
    return ClipRRect(
      borderRadius: radius,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          return ShaderMask(
            blendMode: BlendMode.srcATop,
            shaderCallback: (Rect bounds) {
              final double shift = (_controller.value * 2) - 1;
              return LinearGradient(
                begin: Alignment(-1 + shift, 0),
                end: Alignment(1 + shift, 0),
                colors: <Color>[
                  colors.bgOverlay,
                  colors.bgBorder,
                  colors.bgOverlay,
                ],
                stops: const <double>[0.18, 0.5, 0.82],
              ).createShader(bounds);
            },
            child: child,
          );
        },
        child: box,
      ),
    );
  }
}
