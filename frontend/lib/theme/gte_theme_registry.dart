import 'package:flutter/material.dart';

import 'gte_theme_metadata.dart';
import 'gte_theme_tokens.dart';

@immutable
class GteThemeDefinition {
  const GteThemeDefinition({
    required this.metadata,
    required this.tokens,
  });

  final GteThemeMetadata metadata;
  final GteThemeTokens tokens;
}

class GteThemeRegistry {
  const GteThemeRegistry._();

  static const GteThemeDefinition darkGold = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.darkGold,
      label: 'Dark Gold',
      tagline: 'Premium transfer lounge',
      description:
          'Black-gold surfaces with warm highlights for a premium club-builder feel.',
      icon: Icons.workspace_premium_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF080604),
      backgroundSoft: Color(0xFF120D08),
      panel: Color(0xFF17100B),
      panelStrong: Color(0xFF24170E),
      panelElevated: Color(0xFF322012),
      stroke: Color(0xFF5C4632),
      outline: Color(0xFF7A6046),
      surfaceHighlight: Color(0xFFF9F3EA),
      shadow: Color(0xFF000000),
      accent: Color(0xFFF6C453),
      accentWarm: Color(0xFFFFE18A),
      accentArena: Color(0xFFFF8A3D),
      accentCommunity: Color(0xFF6BE3B4),
      accentCapital: Color(0xFFF0D17A),
      accentClub: Color(0xFF7EC4FF),
      accentAdmin: Color(0xFFFF906B),
      textPrimary: Color(0xFFF9F3EA),
      textMuted: Color(0xFFC8B49B),
      textInverse: Color(0xFF140C05),
      positive: Color(0xFF63E79C),
      negative: Color(0xFFFF8E7A),
      warning: Color(0xFFFFD36F),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 20,
      spaceXl: 28,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
  );

  static const GteThemeDefinition stadiumNight = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.stadiumNight,
      label: 'Stadium Night',
      tagline: 'Floodlights and matchday neon',
      description:
          'Cool midnight surfaces with teal and arena-light energy across the shell.',
      icon: Icons.stadium_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF041019),
      backgroundSoft: Color(0xFF081923),
      panel: Color(0xFF0C1F2C),
      panelStrong: Color(0xFF123142),
      panelElevated: Color(0xFF18455A),
      stroke: Color(0xFF2D556C),
      outline: Color(0xFF4B738C),
      surfaceHighlight: Color(0xFFF2FAFF),
      shadow: Color(0xFF01060B),
      accent: Color(0xFF54F3D5),
      accentWarm: Color(0xFFFFE08A),
      accentArena: Color(0xFF9A7CFF),
      accentCommunity: Color(0xFF62F0A8),
      accentCapital: Color(0xFFF2D470),
      accentClub: Color(0xFF7CCBFF),
      accentAdmin: Color(0xFFFF8B76),
      textPrimary: Color(0xFFF2FAFF),
      textMuted: Color(0xFF97B7C8),
      textInverse: Color(0xFF041019),
      positive: Color(0xFF6AE7A6),
      negative: Color(0xFFFF8D8D),
      warning: Color(0xFFFFD56C),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 20,
      spaceXl: 28,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
  );

  static const GteThemeDefinition ultraRed = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.ultraRed,
      label: 'Ultra Red',
      tagline: 'Derby-day intensity',
      description:
          'Red-black contrast that pushes the transfer market and live arena toward matchday tension.',
      icon: Icons.local_fire_department_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF140407),
      backgroundSoft: Color(0xFF1D090E),
      panel: Color(0xFF251016),
      panelStrong: Color(0xFF36141C),
      panelElevated: Color(0xFF4B1823),
      stroke: Color(0xFF7B3040),
      outline: Color(0xFFA14C62),
      surfaceHighlight: Color(0xFFFFF3F5),
      shadow: Color(0xFF050102),
      accent: Color(0xFFFF4D6D),
      accentWarm: Color(0xFFFFA85C),
      accentArena: Color(0xFFFF6A5E),
      accentCommunity: Color(0xFF73E7A2),
      accentCapital: Color(0xFFFFC55E),
      accentClub: Color(0xFF8AB4FF),
      accentAdmin: Color(0xFFFF9A7A),
      textPrimary: Color(0xFFFFF3F5),
      textMuted: Color(0xFFD0A8B0),
      textInverse: Color(0xFF21080D),
      positive: Color(0xFF67E6A5),
      negative: Color(0xFFFF6D7F),
      warning: Color(0xFFFFB35C),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 20,
      spaceXl: 28,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
  );

  static const GteThemeDefinition iceWhite = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.iceWhite,
      label: 'Ice White',
      tagline: 'Clean match control room',
      description:
          'Bright, readable panels with cold-blue structure and warm market accents.',
      icon: Icons.ac_unit_outlined,
      brightness: Brightness.light,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFFF5F8FC),
      backgroundSoft: Color(0xFFE9EEF6),
      panel: Color(0xFFFFFFFF),
      panelStrong: Color(0xFFF1F5FA),
      panelElevated: Color(0xFFE6EDF6),
      stroke: Color(0xFFD1DCE8),
      outline: Color(0xFFB2C4D7),
      surfaceHighlight: Color(0xFF0E1B2A),
      shadow: Color(0xFF11233B),
      accent: Color(0xFF1295D8),
      accentWarm: Color(0xFFFFB454),
      accentArena: Color(0xFF556BFF),
      accentCommunity: Color(0xFF0FAF7A),
      accentCapital: Color(0xFFD6A11C),
      accentClub: Color(0xFF2280FF),
      accentAdmin: Color(0xFFE86C52),
      textPrimary: Color(0xFF0E1B2A),
      textMuted: Color(0xFF5F7387),
      textInverse: Color(0xFFFFFFFF),
      positive: Color(0xFF1E9A67),
      negative: Color(0xFFD64545),
      warning: Color(0xFFD9911A),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 20,
      spaceXl: 28,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
  );

  static const GteThemeDefinition defaultTheme = darkGold;

  static const List<GteThemeDefinition> themes = <GteThemeDefinition>[
    darkGold,
    stadiumNight,
    ultraRed,
    iceWhite,
  ];

  static GteThemeDefinition resolve(GteThemeId id) {
    switch (id) {
      case GteThemeId.darkGold:
        return darkGold;
      case GteThemeId.stadiumNight:
        return stadiumNight;
      case GteThemeId.ultraRed:
        return ultraRed;
      case GteThemeId.iceWhite:
        return iceWhite;
    }
  }
}
