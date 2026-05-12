import 'package:flutter/material.dart';

/// Central GTEX visual identity tokens.
///
/// These colors intentionally align with the current dark GTEX shell while
/// giving the rebuild a stronger football-marketplace identity.
class GtexColors {
  const GtexColors._();

  static const Color stadiumBlack = Color(0xFF030607);
  static const Color black = stadiumBlack;
  static const Color midnight = Color(0xFF071015);
  static const Color tacticalNavy = Color(0xFF0A151D);
  static const Color panel = Color(0xFF101A20);
  static const Color panelStrong = Color(0xFF14232B);
  static const Color panelElevated = Color(0xFF1A2C35);
  static const Color panelAlt = panelElevated;
  static const Color line = Color(0xFF243942);
  static const Color lineSoft = Color(0x33243942);

  static const Color pitch = Color(0xFFB9FF2C);
  static const Color green = pitch;
  static const Color electricGreen = pitch;
  static const Color pitchDeep = Color(0xFF71E63D);
  static const Color gold = Color(0xFFFFD65A);
  static const Color cyan = Color(0xFF65D9FF);
  static const Color mint = Color(0xFF63F4B1);
  static const Color purple = Color(0xFFB979FF);
  static const Color orange = Color(0xFFFF9A55);
  static const Color red = Color(0xFFFF5F69);
  static const Color danger = red;

  static const Color text = Color(0xFFF4FFF2);
  static const Color textSecondary = Color(0xFFB2C2BC);
  static const Color textMuted = Color(0xFF72847D);

  static const List<Color> heroGradient = <Color>[
    Color(0xFF061013),
    Color(0xFF0B1D20),
    Color(0xFF10260F),
  ];

  static LinearGradient panelGlow({Color accent = pitch}) {
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        accent.withValues(alpha: 0.16),
        panel.withValues(alpha: 0.96),
        stadiumBlack.withValues(alpha: 0.98),
      ],
    );
  }

  static BoxShadow glow(Color color, {double opacity = 0.22}) {
    return BoxShadow(
      color: color.withValues(alpha: opacity),
      blurRadius: 34,
      spreadRadius: -12,
      offset: const Offset(0, 18),
    );
  }
}
