import 'package:flutter/material.dart';

class GtexPseudo3DPlayer extends StatelessWidget {
  const GtexPseudo3DPlayer({
    super.key,
    required this.primaryColor,
    required this.trimColor,
    required this.scale,
    required this.highlighted,
    required this.label,
  });

  final Color primaryColor;
  final Color trimColor;
  final double scale;
  final bool highlighted;
  final String label;

  @override
  Widget build(BuildContext context) {
    final double width = 18 * scale;
    final double height = 40 * scale;
    final Color glowColor =
        highlighted ? trimColor.withValues(alpha: 0.35) : Colors.transparent;
    return SizedBox(
      width: width,
      height: height,
      child: Stack(
        alignment: Alignment.bottomCenter,
        children: <Widget>[
          Positioned(
            bottom: 0,
            child: Container(
              width: width,
              height: height * 0.68,
              decoration: BoxDecoration(
                color: primaryColor,
                borderRadius: BorderRadius.circular(width),
                border: Border.all(color: trimColor, width: mathMax(1, scale)),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: glowColor,
                    blurRadius: highlighted ? 12 : 0,
                    spreadRadius: highlighted ? 1 : 0,
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: Text(
                label,
                style: TextStyle(
                  color: trimColor.computeLuminance() > 0.55
                      ? Colors.black
                      : Colors.white,
                  fontSize: 8 * scale,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          Positioned(
            top: 0,
            child: Container(
              width: width * 0.72,
              height: width * 0.72,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: primaryColor.withValues(alpha: 0.96),
                border: Border.all(
                    color: trimColor, width: mathMax(1, scale * 0.7)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

double mathMax(num left, num right) =>
    left > right ? left.toDouble() : right.toDouble();
