import 'package:flutter/material.dart';

/// Semantic tokens for GTEX's football-universe command surfaces.
///
/// These extend the base palette instead of competing with it: `pitch` owns
/// live football, `coin` owns value, `fan` owns social/world signals, and the
/// status tokens describe state rather than decoration.
class GtexCommandTokens {
  const GtexCommandTokens._();

  static const Color pitch = Color(0xFF00C46A);
  static const Color coin = Color(0xFFFFB800);
  static const Color fan = Color(0xFF3D7EFF);
  static const Color prestige = Color(0xFFE6D4A2);
  static const Color reward = Color(0xFFFFA63D);
  static const Color ownership = Color(0xFF69D6A3);
  static const Color competition = Color(0xFF4CA5FF);
  static const Color live = pitch;
  static const Color pending = Color(0xFFFF9500);
  static const Color settled = Color(0xFF8A93A2);
  static const Color risk = Color(0xFFFF4D4D);

  static const double actionHeight = 44;
  static const double compactActionHeight = 36;
  static const double iconSm = 16;
  static const double iconMd = 20;
  static const double iconLg = 28;
  static const double mastheadRadius = 20;
  static const double panelRadius = 14;
}
