import 'package:flutter/material.dart';

class GtexPseudo3DShadow extends StatelessWidget {
  const GtexPseudo3DShadow({
    super.key,
    required this.width,
    required this.height,
    required this.opacity,
  });

  final double width;
  final double height;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          shape: BoxShape.rectangle,
          borderRadius: BorderRadius.circular(height),
          color: Colors.black.withValues(alpha: opacity.clamp(0, 0.45)),
        ),
      ),
    );
  }
}
