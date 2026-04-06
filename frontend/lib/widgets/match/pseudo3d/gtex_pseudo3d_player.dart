import 'package:flutter/material.dart';

@immutable
class GtexPseudo3DPlayerVisualStyle {
  const GtexPseudo3DPlayerVisualStyle({
    required this.bodyColor,
    required this.trimColor,
    required this.outlineColor,
    required this.glowColor,
    required this.scaleMultiplier,
    required this.borderWidth,
    required this.showHalo,
    required this.showPulseRing,
    required this.showBadge,
    required this.badgeColor,
    required this.labelColor,
    required this.shadowOpacity,
  });

  final Color bodyColor;
  final Color trimColor;
  final Color outlineColor;
  final Color glowColor;
  final double scaleMultiplier;
  final double borderWidth;
  final bool showHalo;
  final bool showPulseRing;
  final bool showBadge;
  final Color badgeColor;
  final Color labelColor;
  final double shadowOpacity;
}

class GtexPseudo3DPlayer extends StatelessWidget {
  const GtexPseudo3DPlayer({
    super.key,
    required this.scale,
    required this.label,
    required this.style,
  });

  static const Key haloKey = Key('pseudo3d-player-halo');
  static const Key pulseRingKey = Key('pseudo3d-player-pulse-ring');
  static const Key bodyKey = Key('pseudo3d-player-body');
  static const Key badgeKey = Key('pseudo3d-player-badge');

  final double scale;
  final String label;
  final GtexPseudo3DPlayerVisualStyle style;

  @override
  Widget build(BuildContext context) {
    final double width = 18 * scale * style.scaleMultiplier;
    final double height = 40 * scale * style.scaleMultiplier;
    return SizedBox(
      width: width,
      height: height,
      child: Stack(
        alignment: Alignment.bottomCenter,
        children: <Widget>[
          if (style.showHalo)
            Positioned(
              key: haloKey,
              bottom: height * 0.12,
              child: Container(
                width: width * 1.34,
                height: height * 0.62,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(width),
                  color: style.glowColor,
                ),
              ),
            ),
          if (style.showPulseRing)
            Positioned(
              key: pulseRingKey,
              bottom: height * 0.20,
              child: Container(
                width: width * 1.16,
                height: height * 0.54,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(width),
                  border: Border.all(
                    color: style.outlineColor.withValues(alpha: 0.72),
                    width: style.borderWidth,
                  ),
                ),
              ),
            ),
          Positioned(
            bottom: 0,
            child: Container(
              key: bodyKey,
              width: width,
              height: height * 0.68,
              decoration: BoxDecoration(
                color: style.bodyColor,
                borderRadius: BorderRadius.circular(width),
                border: Border.all(
                  color: style.outlineColor,
                  width: mathMax(style.borderWidth, scale * 0.8),
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: style.glowColor,
                    blurRadius: style.showHalo ? 14 : 7,
                    spreadRadius: style.showHalo ? 1.2 : 0.2,
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: Text(
                label,
                style: TextStyle(
                  color: style.labelColor,
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
                color: style.bodyColor.withValues(alpha: 0.96),
                border: Border.all(
                  color: style.outlineColor,
                  width: mathMax(1, scale * 0.7),
                ),
              ),
            ),
          ),
          if (style.showBadge)
            Positioned(
              key: badgeKey,
              top: height * 0.14,
              right: width * 0.02,
              child: Container(
                width: width * 0.18,
                height: width * 0.18,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: style.badgeColor,
                  border: Border.all(
                    color: style.labelColor.withValues(alpha: 0.84),
                    width: 1,
                  ),
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
