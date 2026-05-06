import 'package:flutter/material.dart';

import 'gte_theme_extensions.dart';
import 'gte_theme_metadata.dart';
import 'gte_theme_specs.dart';
import 'gte_theme_tokens.dart';

@immutable
class GteThemeDefinition {
  const GteThemeDefinition({
    required this.metadata,
    required this.tokens,
    required this.visuals,
    required this.typography,
    required this.button,
    required this.motion,
    required this.usage,
  });

  final GteThemeMetadata metadata;
  final GteThemeTokens tokens;
  final GteThemeVisuals visuals;
  final GteThemeTypography typography;
  final GteThemeButtonSpec button;
  final GteThemeMotion motion;
  final GteThemeUsageGuidance usage;

  Color get primaryColor => tokens.accent;
  Color get secondaryColor => tokens.accentWarm;
  Color get backgroundColor => tokens.background;
  Color get surfaceColor => tokens.panel;
  Color get accentColor => tokens.accentArena;

  Color get onPrimaryColor => _foregroundOn(primaryColor, tokens);
  Color get onSecondaryColor => _foregroundOn(secondaryColor, tokens);
  Color get onAccentColor => _foregroundOn(accentColor, tokens);

  Map<String, String> get colorHexCodes => <String, String>{
    'primary': _hexColor(primaryColor),
    'secondary': _hexColor(secondaryColor),
    'background': _hexColor(backgroundColor),
    'surface': _hexColor(surfaceColor),
    'accent': _hexColor(accentColor),
  };

  Map<String, double> get typographyScale => typography.scale;
}

class GteThemeRegistry {
  const GteThemeRegistry._();

  static const GteThemeDefinition foundersBlack = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.foundersBlack,
      label: 'Founders Black',
      tagline: 'Power-user market terminal',
      description:
          'Near-black graphite surfaces with electric lime energy for GTEX operators, markets, and live command-center work.',
      icon: Icons.stadium_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF040608),
      backgroundSoft: Color(0xFF0A0E11),
      panel: Color(0xFF101518),
      panelStrong: Color(0xFF151C20),
      panelElevated: Color(0xFF1B2328),
      stroke: Color(0xFF2B363B),
      outline: Color(0xFF3A484E),
      surfaceHighlight: Color(0xFFF4FFF6),
      shadow: Color(0xFF010202),
      accent: Color(0xFFB9FF2C),
      accentWarm: Color(0xFF70F0C0),
      accentArena: Color(0xFFE7FF79),
      accentCommunity: Color(0xFF49DDA1),
      accentCapital: Color(0xFFFFD75B),
      accentClub: Color(0xFF66D7FF),
      accentAdmin: Color(0xFFFF7B5C),
      textPrimary: Color(0xFFF4F7F4),
      textMuted: Color(0xFF93A39D),
      textInverse: Color(0xFF071108),
      positive: Color(0xFF69F3A4),
      negative: Color(0xFFFF6A6A),
      warning: Color(0xFFFFC857),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 24,
      spaceXl: 34,
      radiusSmall: 12,
      radiusMedium: 18,
      radiusLarge: 24,
      radiusPill: 999,
    ),
    visuals: GteThemeVisuals(
      shellStyle: 'Bloomberg terminal meets elite football broadcast',
      glass: false,
      surfaceOpacity: 0.96,
      surfaceBlurSigma: 6,
      ambientPrimary: Color(0xFFB9FF2C),
      ambientSecondary: Color(0xFF66D7FF),
      ambientTertiary: Color(0xFFFFD75B),
      heroStart: Color(0xFF121A1B),
      heroEnd: Color(0xFF081013),
      heroAccent: Color(0xFFB9FF2C),
      shellFill: Color(0xEE0F1418),
      shellBorder: Color(0xFF283237),
      navGlow: Color(0xFFB9FF2C),
      chartPositive: Color(0xFF69F3A4),
      chartNegative: Color(0xFFFF6A6A),
      chartNeutral: Color(0xFF93A39D),
      chartHighlight: Color(0xFFB9FF2C),
      chartSecondary: Color(0xFF66D7FF),
      scorebugBackground: Color(0xFF080B0E),
      scorebugBorder: Color(0xFF2E3C42),
      scorebugAccent: Color(0xFFB9FF2C),
      scorebugText: Color(0xFFF4F7F4),
    ),
    typography: GteThemeTypography(
      styleName: 'Condensed matchday sans',
      displaySize: 42,
      displayWeight: FontWeight.w900,
      displayLetterSpacing: -2.1,
      displayHeight: 0.95,
      headlineSize: 29,
      headlineWeight: FontWeight.w800,
      headlineLetterSpacing: -0.92,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: 0.12,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.5,
      bodyLetterSpacing: 0.02,
      captionSize: 12,
      captionLetterSpacing: 0.18,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.62,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Terminal capsule',
      cornerRadius: 14,
      strokeWidth: 1.2,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 1.2,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.36,
    ),
    motion: GteThemeMotion(
      feel: 'Fast, athletic, high-contrast',
      fast: Duration(milliseconds: 100),
      medium: Duration(milliseconds: 170),
      slow: Duration(milliseconds: 260),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Default shell for market, admin, and live power-user surfaces where clarity and urgency need to dominate.',
      dashboard:
          'Use lime for the highest-priority state change, with cyan reserved for supporting analytics and charts.',
      profile:
          'Best for operator identities, settings, and trust-heavy control surfaces that should feel serious and expensive.',
      accessibility:
          'High-luminance copy on graphite panels keeps command surfaces readable while bright accents remain isolated and contrast-safe.',
    ),
  );

  static const GteThemeDefinition paloAltoGlass = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.paloAltoGlass,
      label: 'Palo Alto Glass',
      tagline: 'Executive frosted broadcast shell',
      description:
          'Frosted midnight cards, soft blue-cyan accents, and layered translucency for elegant world, profile, and broadcast surfaces.',
      icon: Icons.blur_on_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF07131C),
      backgroundSoft: Color(0xFF0B1A25),
      panel: Color(0xFF132433),
      panelStrong: Color(0xFF172B3E),
      panelElevated: Color(0xFF1C3550),
      stroke: Color(0xFF35516A),
      outline: Color(0xFF4C7292),
      surfaceHighlight: Color(0xFFF3FAFF),
      shadow: Color(0xFF01060B),
      accent: Color(0xFF85D8FF),
      accentWarm: Color(0xFF4CEBFF),
      accentArena: Color(0xFFDDF5FF),
      accentCommunity: Color(0xFF69E3C6),
      accentCapital: Color(0xFFFFD99A),
      accentClub: Color(0xFFA8C8FF),
      accentAdmin: Color(0xFFFFA27A),
      textPrimary: Color(0xFFF2F8FF),
      textMuted: Color(0xFFA7BDCE),
      textInverse: Color(0xFF08141D),
      positive: Color(0xFF72E3B0),
      negative: Color(0xFFFF8297),
      warning: Color(0xFFFFC976),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 24,
      spaceXl: 34,
      radiusSmall: 18,
      radiusMedium: 24,
      radiusLarge: 32,
      radiusPill: 999,
    ),
    visuals: GteThemeVisuals(
      shellStyle: 'Apple-ish glass executive deck',
      glass: true,
      surfaceOpacity: 0.84,
      surfaceBlurSigma: 22,
      ambientPrimary: Color(0xFF85D8FF),
      ambientSecondary: Color(0xFF4CEBFF),
      ambientTertiary: Color(0xFFDDF5FF),
      heroStart: Color(0xFF183246),
      heroEnd: Color(0xFF0C1924),
      heroAccent: Color(0xFF4CEBFF),
      shellFill: Color(0xCC112232),
      shellBorder: Color(0xFF35516A),
      navGlow: Color(0xFF85D8FF),
      chartPositive: Color(0xFF72E3B0),
      chartNegative: Color(0xFFFF8297),
      chartNeutral: Color(0xFFA7BDCE),
      chartHighlight: Color(0xFF85D8FF),
      chartSecondary: Color(0xFF4CEBFF),
      scorebugBackground: Color(0xCC0D1B27),
      scorebugBorder: Color(0xFF3C617C),
      scorebugAccent: Color(0xFF85D8FF),
      scorebugText: Color(0xFFF2F8FF),
    ),
    typography: GteThemeTypography(
      styleName: 'Executive editorial sans',
      displaySize: 40,
      displayWeight: FontWeight.w800,
      displayLetterSpacing: -1.8,
      displayHeight: 0.98,
      headlineSize: 28,
      headlineWeight: FontWeight.w700,
      headlineLetterSpacing: -0.72,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: -0.1,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.58,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.14,
      labelSize: 13,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.3,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Frosted executive rectangle',
      cornerRadius: 22,
      strokeWidth: 1.0,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 0.6,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.24,
    ),
    motion: GteThemeMotion(
      feel: 'Floating, layered, polished',
      fast: Duration(milliseconds: 110),
      medium: Duration(milliseconds: 190),
      slow: Duration(milliseconds: 300),
      emphasizedCurve: Curves.easeOutQuart,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Best for profile, world, competitions, and premium broadcast surfaces where calm depth matters more than aggression.',
      dashboard:
          'Lean on light cyan for focus states, with transparent layering and breathing room across dense modules.',
      profile:
          'Ideal for executive identity, account settings, and premium membership surfaces that need refinement without softness.',
      accessibility:
          'The cyan-blue stack sits on dark glass layers with high-contrast text and restrained translucency that stays readable.',
    ),
  );

  static const GteThemeDefinition sandHillGold = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.sandHillGold,
      label: 'Sand Hill Gold',
      tagline: 'Luxury ownership finance tone',
      description:
          'Matte charcoal surfaces with restrained warm gold for ownership, wallet, premium competitions, and portfolio moments.',
      icon: Icons.workspace_premium_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF090807),
      backgroundSoft: Color(0xFF100E0C),
      panel: Color(0xFF161310),
      panelStrong: Color(0xFF1D1814),
      panelElevated: Color(0xFF261E18),
      stroke: Color(0xFF46392D),
      outline: Color(0xFF675241),
      surfaceHighlight: Color(0xFFFFF6E7),
      shadow: Color(0xFF020101),
      accent: Color(0xFFDEBE6B),
      accentWarm: Color(0xFFF8DDA3),
      accentArena: Color(0xFFFFE29D),
      accentCommunity: Color(0xFF73D4A7),
      accentCapital: Color(0xFFFFD35B),
      accentClub: Color(0xFFB9C6D8),
      accentAdmin: Color(0xFFFFA16C),
      textPrimary: Color(0xFFF9F2E8),
      textMuted: Color(0xFFBCA991),
      textInverse: Color(0xFF110D08),
      positive: Color(0xFF70D9A2),
      negative: Color(0xFFFF8178),
      warning: Color(0xFFFFC86D),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 24,
      spaceXl: 34,
      radiusSmall: 16,
      radiusMedium: 20,
      radiusLarge: 28,
      radiusPill: 999,
    ),
    visuals: GteThemeVisuals(
      shellStyle: 'Premium ownership lounge',
      glass: false,
      surfaceOpacity: 0.95,
      surfaceBlurSigma: 8,
      ambientPrimary: Color(0xFFDEBE6B),
      ambientSecondary: Color(0xFFF8DDA3),
      ambientTertiary: Color(0xFFFFD35B),
      heroStart: Color(0xFF241C16),
      heroEnd: Color(0xFF100E0C),
      heroAccent: Color(0xFFDEBE6B),
      shellFill: Color(0xEE151210),
      shellBorder: Color(0xFF46392D),
      navGlow: Color(0xFFDEBE6B),
      chartPositive: Color(0xFF70D9A2),
      chartNegative: Color(0xFFFF8178),
      chartNeutral: Color(0xFFBCA991),
      chartHighlight: Color(0xFFDEBE6B),
      chartSecondary: Color(0xFFF8DDA3),
      scorebugBackground: Color(0xFF120F0C),
      scorebugBorder: Color(0xFF574638),
      scorebugAccent: Color(0xFFDEBE6B),
      scorebugText: Color(0xFFF9F2E8),
    ),
    typography: GteThemeTypography(
      styleName: 'Luxury condensed sans',
      displaySize: 41,
      displayWeight: FontWeight.w900,
      displayLetterSpacing: -1.9,
      displayHeight: 0.96,
      headlineSize: 29,
      headlineWeight: FontWeight.w800,
      headlineLetterSpacing: -0.8,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: 0.06,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.54,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.16,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.46,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Luxury matte tab',
      cornerRadius: 18,
      strokeWidth: 1.1,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 0.9,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.28,
    ),
    motion: GteThemeMotion(
      feel: 'Measured, premium, assured',
      fast: Duration(milliseconds: 110),
      medium: Duration(milliseconds: 180),
      slow: Duration(milliseconds: 290),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Reserve this for wallet, premium event, portfolio, and club ownership surfaces where value needs luxury framing.',
      dashboard:
          'Gold should carry the highest-value KPIs and trust markers, with warm neutrals handling the rest of the information density.',
      profile:
          'Works for premium account hubs and club ownership identity where authority matters more than speed.',
      accessibility:
          'Cream text on charcoal surfaces preserves readability, while gold actions use automatic contrast-safe foreground pairing.',
    ),
  );

  static const GteThemeDefinition menloNightBlue = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.menloNightBlue,
      label: 'Menlo Night Blue',
      tagline: 'Analytics command center',
      description:
          'Midnight blue system with cobalt and icy white contrast for standings, world dashboards, and tactical data-heavy surfaces.',
      icon: Icons.analytics_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF07111C),
      backgroundSoft: Color(0xFF0C1828),
      panel: Color(0xFF122033),
      panelStrong: Color(0xFF182942),
      panelElevated: Color(0xFF203553),
      stroke: Color(0xFF2C486E),
      outline: Color(0xFF446893),
      surfaceHighlight: Color(0xFFF2F7FF),
      shadow: Color(0xFF010409),
      accent: Color(0xFF4B7BFF),
      accentWarm: Color(0xFF89E1FF),
      accentArena: Color(0xFFE7F2FF),
      accentCommunity: Color(0xFF6DDFD0),
      accentCapital: Color(0xFFFFD66B),
      accentClub: Color(0xFFB9D1FF),
      accentAdmin: Color(0xFFFF9271),
      textPrimary: Color(0xFFF2F7FF),
      textMuted: Color(0xFFA4B6D3),
      textInverse: Color(0xFF07111C),
      positive: Color(0xFF74E5B0),
      negative: Color(0xFFFF8196),
      warning: Color(0xFFFFC96D),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 24,
      spaceXl: 34,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
    visuals: GteThemeVisuals(
      shellStyle: 'Technical SaaS war room',
      glass: false,
      surfaceOpacity: 0.95,
      surfaceBlurSigma: 10,
      ambientPrimary: Color(0xFF4B7BFF),
      ambientSecondary: Color(0xFF89E1FF),
      ambientTertiary: Color(0xFFE7F2FF),
      heroStart: Color(0xFF182A43),
      heroEnd: Color(0xFF0A1423),
      heroAccent: Color(0xFF4B7BFF),
      shellFill: Color(0xEE101C2D),
      shellBorder: Color(0xFF2C486E),
      navGlow: Color(0xFF4B7BFF),
      chartPositive: Color(0xFF74E5B0),
      chartNegative: Color(0xFFFF8196),
      chartNeutral: Color(0xFFA4B6D3),
      chartHighlight: Color(0xFF4B7BFF),
      chartSecondary: Color(0xFF89E1FF),
      scorebugBackground: Color(0xFF0B1523),
      scorebugBorder: Color(0xFF31527E),
      scorebugAccent: Color(0xFF4B7BFF),
      scorebugText: Color(0xFFF2F7FF),
    ),
    typography: GteThemeTypography(
      styleName: 'Technical sports sans',
      displaySize: 40,
      displayWeight: FontWeight.w900,
      displayLetterSpacing: -1.8,
      displayHeight: 0.97,
      headlineSize: 28,
      headlineWeight: FontWeight.w800,
      headlineLetterSpacing: -0.74,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: 0.02,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.54,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.16,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.52,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Command pill',
      cornerRadius: 18,
      strokeWidth: 1.1,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 1.1,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.3,
    ),
    motion: GteThemeMotion(
      feel: 'Confident, precise, broadcast-clean',
      fast: Duration(milliseconds: 105),
      medium: Duration(milliseconds: 175),
      slow: Duration(milliseconds: 275),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Use on standings, tactical, world, and analytics surfaces where density needs structure without visual heaviness.',
      dashboard:
          'Cobalt should mark selection and focus, while icy whites guide secondary hierarchy and data labels.',
      profile:
          'Best for capability-heavy profiles and data-rich club summaries that should feel technical rather than luxurious.',
      accessibility:
          'Blue hierarchy stays crisp on midnight surfaces, with high-luminance text and strong edge contrast across cards and controls.',
    ),
  );

  static const GteThemeDefinition ultraRed = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.ultraRed,
      label: 'Ultra Red',
      tagline: 'High-intensity stadium night',
      description:
          'Black, deep crimson, and silver contrast for matchday, clips, finals, and emotional event-heavy storytelling surfaces.',
      icon: Icons.flash_on_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF070607),
      backgroundSoft: Color(0xFF0F0B0E),
      panel: Color(0xFF161014),
      panelStrong: Color(0xFF1F151B),
      panelElevated: Color(0xFF2A1B23),
      stroke: Color(0xFF4A2D39),
      outline: Color(0xFF68404E),
      surfaceHighlight: Color(0xFFF8F1F4),
      shadow: Color(0xFF010101),
      accent: Color(0xFFFF465F),
      accentWarm: Color(0xFFC9CFDA),
      accentArena: Color(0xFFFFA6B5),
      accentCommunity: Color(0xFF7BE0A2),
      accentCapital: Color(0xFFFFC15F),
      accentClub: Color(0xFFDDE2EA),
      accentAdmin: Color(0xFFFF8D72),
      textPrimary: Color(0xFFF8F1F4),
      textMuted: Color(0xFFB8A7AF),
      textInverse: Color(0xFF130A0E),
      positive: Color(0xFF7BE0A2),
      negative: Color(0xFFFF6B82),
      warning: Color(0xFFFFC15F),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 24,
      spaceXl: 34,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
    visuals: GteThemeVisuals(
      shellStyle: 'Stadium-night drama package',
      glass: false,
      surfaceOpacity: 0.95,
      surfaceBlurSigma: 8,
      ambientPrimary: Color(0xFFFF465F),
      ambientSecondary: Color(0xFFC9CFDA),
      ambientTertiary: Color(0xFFFFA6B5),
      heroStart: Color(0xFF24141D),
      heroEnd: Color(0xFF0D090B),
      heroAccent: Color(0xFFFF465F),
      shellFill: Color(0xEE130E12),
      shellBorder: Color(0xFF4A2D39),
      navGlow: Color(0xFFFF465F),
      chartPositive: Color(0xFF7BE0A2),
      chartNegative: Color(0xFFFF6B82),
      chartNeutral: Color(0xFFB8A7AF),
      chartHighlight: Color(0xFFFF465F),
      chartSecondary: Color(0xFFC9CFDA),
      scorebugBackground: Color(0xFF100B0E),
      scorebugBorder: Color(0xFF633946),
      scorebugAccent: Color(0xFFFF465F),
      scorebugText: Color(0xFFF8F1F4),
    ),
    typography: GteThemeTypography(
      styleName: 'Broadcast impact sans',
      displaySize: 42,
      displayWeight: FontWeight.w900,
      displayLetterSpacing: -2.0,
      displayHeight: 0.95,
      headlineSize: 29,
      headlineWeight: FontWeight.w800,
      headlineLetterSpacing: -0.82,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: 0.08,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.5,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.18,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.56,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Match night capsule',
      cornerRadius: 20,
      strokeWidth: 1.15,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 1.1,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.34,
    ),
    motion: GteThemeMotion(
      feel: 'Emotional, premium, stadium-fast',
      fast: Duration(milliseconds: 100),
      medium: Duration(milliseconds: 165),
      slow: Duration(milliseconds: 255),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Use for clips, matchday cards, finals, and high-intensity moments that need drama without turning noisy.',
      dashboard:
          'Crimson should mark match-critical states, with silver acting as the control-plane neutral and data support tone.',
      profile:
          'Use sparingly for celebratory profile modules and event credentials rather than everyday account management.',
      accessibility:
          'The dark crimson stack keeps primary text clear and reserves saturated red for focal moments with readable automatic foregrounds.',
    ),
  );

  static const GteThemeDefinition defaultTheme = foundersBlack;

  static const List<GteThemeDefinition> themes = <GteThemeDefinition>[
    foundersBlack,
    paloAltoGlass,
    sandHillGold,
    menloNightBlue,
    ultraRed,
  ];

  static GteThemeDefinition resolve(GteThemeId id) {
    switch (id) {
      case GteThemeId.foundersBlack:
        return foundersBlack;
      case GteThemeId.paloAltoGlass:
        return paloAltoGlass;
      case GteThemeId.sandHillGold:
        return sandHillGold;
      case GteThemeId.menloNightBlue:
        return menloNightBlue;
      case GteThemeId.ultraRed:
        return ultraRed;
    }
  }
}

Color _foregroundOn(Color background, GteThemeTokens tokens) {
  final double contrastWithPrimaryText = _contrastRatio(
    background,
    tokens.textPrimary,
  );
  final double contrastWithInverseText = _contrastRatio(
    background,
    tokens.textInverse,
  );
  return contrastWithInverseText >= contrastWithPrimaryText
      ? tokens.textInverse
      : tokens.textPrimary;
}

double _contrastRatio(Color a, Color b) {
  final double luminanceA = a.computeLuminance();
  final double luminanceB = b.computeLuminance();
  final double lighter = luminanceA > luminanceB ? luminanceA : luminanceB;
  final double darker = luminanceA > luminanceB ? luminanceB : luminanceA;
  return (lighter + 0.05) / (darker + 0.05);
}

String _hexColor(Color color) {
  final String raw = color.value.toRadixString(16).padLeft(8, '0');
  return '#${raw.substring(2).toUpperCase()}';
}
