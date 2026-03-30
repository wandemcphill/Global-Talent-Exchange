import 'dart:ui';

import 'package:flutter/material.dart';

@immutable
class GteThemeVisuals extends ThemeExtension<GteThemeVisuals> {
  const GteThemeVisuals({
    required this.shellStyle,
    required this.glass,
    required this.surfaceOpacity,
    required this.surfaceBlurSigma,
    required this.ambientPrimary,
    required this.ambientSecondary,
    required this.ambientTertiary,
    required this.heroStart,
    required this.heroEnd,
    required this.heroAccent,
    required this.shellFill,
    required this.shellBorder,
    required this.navGlow,
    required this.chartPositive,
    required this.chartNegative,
    required this.chartNeutral,
    required this.chartHighlight,
    required this.chartSecondary,
    required this.scorebugBackground,
    required this.scorebugBorder,
    required this.scorebugAccent,
    required this.scorebugText,
  });

  final String shellStyle;
  final bool glass;
  final double surfaceOpacity;
  final double surfaceBlurSigma;
  final Color ambientPrimary;
  final Color ambientSecondary;
  final Color ambientTertiary;
  final Color heroStart;
  final Color heroEnd;
  final Color heroAccent;
  final Color shellFill;
  final Color shellBorder;
  final Color navGlow;
  final Color chartPositive;
  final Color chartNegative;
  final Color chartNeutral;
  final Color chartHighlight;
  final Color chartSecondary;
  final Color scorebugBackground;
  final Color scorebugBorder;
  final Color scorebugAccent;
  final Color scorebugText;

  List<Color> get chartPalette => <Color>[
    chartHighlight,
    chartSecondary,
    chartPositive,
    chartNeutral,
    chartNegative,
  ];

  @override
  GteThemeVisuals copyWith({
    String? shellStyle,
    bool? glass,
    double? surfaceOpacity,
    double? surfaceBlurSigma,
    Color? ambientPrimary,
    Color? ambientSecondary,
    Color? ambientTertiary,
    Color? heroStart,
    Color? heroEnd,
    Color? heroAccent,
    Color? shellFill,
    Color? shellBorder,
    Color? navGlow,
    Color? chartPositive,
    Color? chartNegative,
    Color? chartNeutral,
    Color? chartHighlight,
    Color? chartSecondary,
    Color? scorebugBackground,
    Color? scorebugBorder,
    Color? scorebugAccent,
    Color? scorebugText,
  }) {
    return GteThemeVisuals(
      shellStyle: shellStyle ?? this.shellStyle,
      glass: glass ?? this.glass,
      surfaceOpacity: surfaceOpacity ?? this.surfaceOpacity,
      surfaceBlurSigma: surfaceBlurSigma ?? this.surfaceBlurSigma,
      ambientPrimary: ambientPrimary ?? this.ambientPrimary,
      ambientSecondary: ambientSecondary ?? this.ambientSecondary,
      ambientTertiary: ambientTertiary ?? this.ambientTertiary,
      heroStart: heroStart ?? this.heroStart,
      heroEnd: heroEnd ?? this.heroEnd,
      heroAccent: heroAccent ?? this.heroAccent,
      shellFill: shellFill ?? this.shellFill,
      shellBorder: shellBorder ?? this.shellBorder,
      navGlow: navGlow ?? this.navGlow,
      chartPositive: chartPositive ?? this.chartPositive,
      chartNegative: chartNegative ?? this.chartNegative,
      chartNeutral: chartNeutral ?? this.chartNeutral,
      chartHighlight: chartHighlight ?? this.chartHighlight,
      chartSecondary: chartSecondary ?? this.chartSecondary,
      scorebugBackground: scorebugBackground ?? this.scorebugBackground,
      scorebugBorder: scorebugBorder ?? this.scorebugBorder,
      scorebugAccent: scorebugAccent ?? this.scorebugAccent,
      scorebugText: scorebugText ?? this.scorebugText,
    );
  }

  @override
  GteThemeVisuals lerp(ThemeExtension<GteThemeVisuals>? other, double t) {
    if (other is! GteThemeVisuals) {
      return this;
    }
    return GteThemeVisuals(
      shellStyle: t < 0.5 ? shellStyle : other.shellStyle,
      glass: t < 0.5 ? glass : other.glass,
      surfaceOpacity:
          lerpDouble(surfaceOpacity, other.surfaceOpacity, t) ?? surfaceOpacity,
      surfaceBlurSigma:
          lerpDouble(surfaceBlurSigma, other.surfaceBlurSigma, t) ??
          surfaceBlurSigma,
      ambientPrimary:
          Color.lerp(ambientPrimary, other.ambientPrimary, t) ?? ambientPrimary,
      ambientSecondary:
          Color.lerp(ambientSecondary, other.ambientSecondary, t) ??
          ambientSecondary,
      ambientTertiary:
          Color.lerp(ambientTertiary, other.ambientTertiary, t) ??
          ambientTertiary,
      heroStart: Color.lerp(heroStart, other.heroStart, t) ?? heroStart,
      heroEnd: Color.lerp(heroEnd, other.heroEnd, t) ?? heroEnd,
      heroAccent: Color.lerp(heroAccent, other.heroAccent, t) ?? heroAccent,
      shellFill: Color.lerp(shellFill, other.shellFill, t) ?? shellFill,
      shellBorder: Color.lerp(shellBorder, other.shellBorder, t) ?? shellBorder,
      navGlow: Color.lerp(navGlow, other.navGlow, t) ?? navGlow,
      chartPositive:
          Color.lerp(chartPositive, other.chartPositive, t) ?? chartPositive,
      chartNegative:
          Color.lerp(chartNegative, other.chartNegative, t) ?? chartNegative,
      chartNeutral:
          Color.lerp(chartNeutral, other.chartNeutral, t) ?? chartNeutral,
      chartHighlight:
          Color.lerp(chartHighlight, other.chartHighlight, t) ?? chartHighlight,
      chartSecondary:
          Color.lerp(chartSecondary, other.chartSecondary, t) ?? chartSecondary,
      scorebugBackground:
          Color.lerp(scorebugBackground, other.scorebugBackground, t) ??
          scorebugBackground,
      scorebugBorder:
          Color.lerp(scorebugBorder, other.scorebugBorder, t) ?? scorebugBorder,
      scorebugAccent:
          Color.lerp(scorebugAccent, other.scorebugAccent, t) ?? scorebugAccent,
      scorebugText:
          Color.lerp(scorebugText, other.scorebugText, t) ?? scorebugText,
    );
  }
}
