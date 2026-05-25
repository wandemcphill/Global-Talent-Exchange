import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';

class GreenPulseDot extends StatefulWidget {
  const GreenPulseDot({
    super.key,
    this.size = 8,
    this.color,
    this.enabled = true,
  });

  final double size;
  final Color? color;
  final bool enabled;

  @override
  State<GreenPulseDot> createState() => _GreenPulseDotState();
}

class _GreenPulseDotState extends State<GreenPulseDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Color color = widget.color ?? GtexColors.of(context).brandPitch;
    final bool reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (reduceMotion || !widget.enabled) {
      return _StaticDot(size: widget.size, color: color);
    }
    return SizedBox(
      width: widget.size * 2.25,
      height: widget.size * 2.25,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          final double value = Curves.easeOut.transform(_controller.value);
          return Stack(
            alignment: Alignment.center,
            children: <Widget>[
              Container(
                width: widget.size * (1 + 0.8 * value),
                height: widget.size * (1 + 0.8 * value),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: color.withValues(alpha: 1 - value)),
                ),
              ),
              child!,
            ],
          );
        },
        child: _StaticDot(size: widget.size, color: color),
      ),
    );
  }
}

class _StaticDot extends StatelessWidget {
  const _StaticDot({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}
