import 'package:flutter/material.dart';

class GtexPseudo3DBall extends StatelessWidget {
  const GtexPseudo3DBall({
    super.key,
    required this.size,
    required this.elevation,
  });

  final double size;
  final double elevation;

  @override
  Widget build(BuildContext context) {
    return Transform.translate(
      offset: Offset(0, -elevation),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white,
          border: Border.all(color: const Color(0xFF101828), width: 1.1),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.18),
              blurRadius: 8,
              offset: const Offset(0, 3),
            ),
          ],
        ),
      ),
    );
  }
}
