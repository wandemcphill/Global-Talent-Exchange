import 'dart:ui';

import 'package:flutter/material.dart';

@immutable
class GteThemeTokens extends ThemeExtension<GteThemeTokens> {
  const GteThemeTokens({
    required this.background,
    required this.backgroundSoft,
    required this.panel,
    required this.panelStrong,
    required this.panelElevated,
    required this.stroke,
    required this.outline,
    required this.surfaceHighlight,
    required this.shadow,
    required this.accent,
    required this.accentWarm,
    required this.accentArena,
    required this.accentCommunity,
    required this.accentCapital,
    required this.accentClub,
    required this.accentAdmin,
    required this.textPrimary,
    required this.textMuted,
    required this.textInverse,
    required this.positive,
    required this.negative,
    required this.warning,
    required this.spaceXs,
    required this.spaceSm,
    required this.spaceMd,
    required this.spaceLg,
    required this.spaceXl,
    required this.radiusSmall,
    required this.radiusMedium,
    required this.radiusLarge,
    required this.radiusPill,
  });

  final Color background;
  final Color backgroundSoft;
  final Color panel;
  final Color panelStrong;
  final Color panelElevated;
  final Color stroke;
  final Color outline;
  final Color surfaceHighlight;
  final Color shadow;
  final Color accent;
  final Color accentWarm;
  final Color accentArena;
  final Color accentCommunity;
  final Color accentCapital;
  final Color accentClub;
  final Color accentAdmin;
  final Color textPrimary;
  final Color textMuted;
  final Color textInverse;
  final Color positive;
  final Color negative;
  final Color warning;
  final double spaceXs;
  final double spaceSm;
  final double spaceMd;
  final double spaceLg;
  final double spaceXl;
  final double radiusSmall;
  final double radiusMedium;
  final double radiusLarge;
  final double radiusPill;

  Color get surfaceElevated => panelElevated;
  Color get textSecondary => textMuted;

  @override
  GteThemeTokens copyWith({
    Color? background,
    Color? backgroundSoft,
    Color? panel,
    Color? panelStrong,
    Color? panelElevated,
    Color? stroke,
    Color? outline,
    Color? surfaceHighlight,
    Color? shadow,
    Color? accent,
    Color? accentWarm,
    Color? accentArena,
    Color? accentCommunity,
    Color? accentCapital,
    Color? accentClub,
    Color? accentAdmin,
    Color? textPrimary,
    Color? textMuted,
    Color? textInverse,
    Color? positive,
    Color? negative,
    Color? warning,
    double? spaceXs,
    double? spaceSm,
    double? spaceMd,
    double? spaceLg,
    double? spaceXl,
    double? radiusSmall,
    double? radiusMedium,
    double? radiusLarge,
    double? radiusPill,
  }) {
    return GteThemeTokens(
      background: background ?? this.background,
      backgroundSoft: backgroundSoft ?? this.backgroundSoft,
      panel: panel ?? this.panel,
      panelStrong: panelStrong ?? this.panelStrong,
      panelElevated: panelElevated ?? this.panelElevated,
      stroke: stroke ?? this.stroke,
      outline: outline ?? this.outline,
      surfaceHighlight: surfaceHighlight ?? this.surfaceHighlight,
      shadow: shadow ?? this.shadow,
      accent: accent ?? this.accent,
      accentWarm: accentWarm ?? this.accentWarm,
      accentArena: accentArena ?? this.accentArena,
      accentCommunity: accentCommunity ?? this.accentCommunity,
      accentCapital: accentCapital ?? this.accentCapital,
      accentClub: accentClub ?? this.accentClub,
      accentAdmin: accentAdmin ?? this.accentAdmin,
      textPrimary: textPrimary ?? this.textPrimary,
      textMuted: textMuted ?? this.textMuted,
      textInverse: textInverse ?? this.textInverse,
      positive: positive ?? this.positive,
      negative: negative ?? this.negative,
      warning: warning ?? this.warning,
      spaceXs: spaceXs ?? this.spaceXs,
      spaceSm: spaceSm ?? this.spaceSm,
      spaceMd: spaceMd ?? this.spaceMd,
      spaceLg: spaceLg ?? this.spaceLg,
      spaceXl: spaceXl ?? this.spaceXl,
      radiusSmall: radiusSmall ?? this.radiusSmall,
      radiusMedium: radiusMedium ?? this.radiusMedium,
      radiusLarge: radiusLarge ?? this.radiusLarge,
      radiusPill: radiusPill ?? this.radiusPill,
    );
  }

  @override
  GteThemeTokens lerp(ThemeExtension<GteThemeTokens>? other, double t) {
    if (other is! GteThemeTokens) {
      return this;
    }
    return GteThemeTokens(
      background: Color.lerp(background, other.background, t) ?? background,
      backgroundSoft:
          Color.lerp(backgroundSoft, other.backgroundSoft, t) ?? backgroundSoft,
      panel: Color.lerp(panel, other.panel, t) ?? panel,
      panelStrong: Color.lerp(panelStrong, other.panelStrong, t) ?? panelStrong,
      panelElevated:
          Color.lerp(panelElevated, other.panelElevated, t) ?? panelElevated,
      stroke: Color.lerp(stroke, other.stroke, t) ?? stroke,
      outline: Color.lerp(outline, other.outline, t) ?? outline,
      surfaceHighlight:
          Color.lerp(surfaceHighlight, other.surfaceHighlight, t) ??
              surfaceHighlight,
      shadow: Color.lerp(shadow, other.shadow, t) ?? shadow,
      accent: Color.lerp(accent, other.accent, t) ?? accent,
      accentWarm: Color.lerp(accentWarm, other.accentWarm, t) ?? accentWarm,
      accentArena: Color.lerp(accentArena, other.accentArena, t) ?? accentArena,
      accentCommunity: Color.lerp(accentCommunity, other.accentCommunity, t) ??
          accentCommunity,
      accentCapital:
          Color.lerp(accentCapital, other.accentCapital, t) ?? accentCapital,
      accentClub: Color.lerp(accentClub, other.accentClub, t) ?? accentClub,
      accentAdmin: Color.lerp(accentAdmin, other.accentAdmin, t) ?? accentAdmin,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t) ?? textPrimary,
      textMuted: Color.lerp(textMuted, other.textMuted, t) ?? textMuted,
      textInverse: Color.lerp(textInverse, other.textInverse, t) ?? textInverse,
      positive: Color.lerp(positive, other.positive, t) ?? positive,
      negative: Color.lerp(negative, other.negative, t) ?? negative,
      warning: Color.lerp(warning, other.warning, t) ?? warning,
      spaceXs: lerpDouble(spaceXs, other.spaceXs, t) ?? spaceXs,
      spaceSm: lerpDouble(spaceSm, other.spaceSm, t) ?? spaceSm,
      spaceMd: lerpDouble(spaceMd, other.spaceMd, t) ?? spaceMd,
      spaceLg: lerpDouble(spaceLg, other.spaceLg, t) ?? spaceLg,
      spaceXl: lerpDouble(spaceXl, other.spaceXl, t) ?? spaceXl,
      radiusSmall: lerpDouble(radiusSmall, other.radiusSmall, t) ?? radiusSmall,
      radiusMedium:
          lerpDouble(radiusMedium, other.radiusMedium, t) ?? radiusMedium,
      radiusLarge: lerpDouble(radiusLarge, other.radiusLarge, t) ?? radiusLarge,
      radiusPill: lerpDouble(radiusPill, other.radiusPill, t) ?? radiusPill,
    );
  }
}
