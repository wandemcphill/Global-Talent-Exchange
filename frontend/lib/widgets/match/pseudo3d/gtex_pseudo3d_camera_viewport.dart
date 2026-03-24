import 'package:flutter/material.dart';

class GtexPseudo3DCameraViewport extends StatelessWidget {
  const GtexPseudo3DCameraViewport({
    super.key,
    required this.zoom,
    required this.pan,
    required this.child,
  });

  final double zoom;
  final Offset pan;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: Transform(
        alignment: Alignment.center,
        transform: Matrix4.identity()
          ..translate(pan.dx, pan.dy)
          ..scale(zoom, zoom),
        child: child,
      ),
    );
  }
}
