import 'package:flutter/material.dart';

import 'gte_theme_metadata.dart';
import 'gte_theme_specs.dart';
import 'gte_theme_tokens.dart';

@immutable
class GteThemeDefinition {
  const GteThemeDefinition({
    required this.metadata,
    required this.tokens,
    required this.typography,
    required this.button,
    required this.motion,
    required this.usage,
  });

  final GteThemeMetadata metadata;
  final GteThemeTokens tokens;
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

  static const GteThemeDefinition neonVelocity = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.neonVelocity,
      label: 'Neon Velocity',
      tagline: 'High-energy creator velocity',
      description:
          'Electric pink, cyan, and acid-lime contrast built for short-form feed urgency and instant CTA recognition.',
      icon: Icons.bolt_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF070613),
      backgroundSoft: Color(0xFF0E0C1E),
      panel: Color(0xFF141129),
      panelStrong: Color(0xFF1C1738),
      panelElevated: Color(0xFF261E4A),
      stroke: Color(0xFF473C72),
      outline: Color(0xFF6E5CA7),
      surfaceHighlight: Color(0xFFF7F5FF),
      shadow: Color(0xFF02010A),
      accent: Color(0xFFFF3CAC),
      accentWarm: Color(0xFF2DE2FF),
      accentArena: Color(0xFFB7FF3C),
      accentCommunity: Color(0xFF55F5C3),
      accentCapital: Color(0xFFFFD166),
      accentClub: Color(0xFF7CB8FF),
      accentAdmin: Color(0xFFFF7A66),
      textPrimary: Color(0xFFF7F5FF),
      textMuted: Color(0xFFAEA7CB),
      textInverse: Color(0xFF0B0614),
      positive: Color(0xFF6BF7AE),
      negative: Color(0xFFFF6F8E),
      warning: Color(0xFFFFB85A),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 22,
      spaceXl: 30,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
    typography: GteThemeTypography(
      styleName: 'Compressed bold display',
      displaySize: 40,
      displayWeight: FontWeight.w900,
      displayLetterSpacing: -1.9,
      displayHeight: 0.98,
      headlineSize: 28,
      headlineWeight: FontWeight.w800,
      headlineLetterSpacing: -0.8,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: -0.3,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.5,
      bodyLetterSpacing: 0.02,
      captionSize: 12,
      captionLetterSpacing: 0.1,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.48,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Impact capsule',
      cornerRadius: 22,
      strokeWidth: 1.2,
      horizontalPadding: 22,
      verticalPadding: 16,
      filledElevation: 1.5,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.32,
    ),
    motion: GteThemeMotion(
      feel: 'Punchy, kinetic, instant',
      fast: Duration(milliseconds: 110),
      medium: Duration(milliseconds: 180),
      slow: Duration(milliseconds: 280),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Use saturated accents for creator cards, reaction rails, and primary publish actions. Keep secondary surfaces dark to avoid visual fatigue.',
      dashboard:
          'Reserve lime accent for live deltas and momentum modules. Use pink only for the highest-priority CTA per screen.',
      profile:
          'Anchor headers in deep indigo panels, with cyan used for stats and trust markers rather than full-panel fills.',
      accessibility:
          'High-chroma accents sit on near-black surfaces, and all primary text and button foregrounds clear AA contrast for feed, dashboard, and profile layouts.',
    ),
  );

  static const GteThemeDefinition midnightGlass = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.midnightGlass,
      label: 'Midnight Glass',
      tagline: 'Premium glassmorphism shell',
      description:
          'Smoky midnight layers with icy blue and aqua accents for a luxurious dark-mode command surface.',
      icon: Icons.auto_awesome_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF071018),
      backgroundSoft: Color(0xFF0C1624),
      panel: Color(0xFF111B2D),
      panelStrong: Color(0xFF152338),
      panelElevated: Color(0xFF1B2C45),
      stroke: Color(0xFF3E5B7C),
      outline: Color(0xFF5E7EA3),
      surfaceHighlight: Color(0xFFF4F8FF),
      shadow: Color(0xFF01050B),
      accent: Color(0xFF89A8FF),
      accentWarm: Color(0xFF68E4D7),
      accentArena: Color(0xFFD0BEFF),
      accentCommunity: Color(0xFF6CE2AE),
      accentCapital: Color(0xFFF2D48D),
      accentClub: Color(0xFF8EC9FF),
      accentAdmin: Color(0xFFFF9A7A),
      textPrimary: Color(0xFFF4F7FF),
      textMuted: Color(0xFFA8B7CD),
      textInverse: Color(0xFF06111A),
      positive: Color(0xFF71DEAA),
      negative: Color(0xFFFF8796),
      warning: Color(0xFFFFCA76),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 22,
      spaceXl: 30,
      radiusSmall: 18,
      radiusMedium: 24,
      radiusLarge: 32,
      radiusPill: 999,
    ),
    typography: GteThemeTypography(
      styleName: 'Editorial premium sans',
      displaySize: 38,
      displayWeight: FontWeight.w700,
      displayLetterSpacing: -1.5,
      displayHeight: 1.02,
      headlineSize: 27,
      headlineWeight: FontWeight.w700,
      headlineLetterSpacing: -0.65,
      titleSize: 18,
      titleWeight: FontWeight.w600,
      titleLetterSpacing: -0.12,
      bodySize: 15,
      bodyWeight: FontWeight.w400,
      bodyHeight: 1.58,
      bodyLetterSpacing: 0.04,
      captionSize: 12,
      captionLetterSpacing: 0.12,
      labelSize: 13,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.28,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Frosted soft rectangle',
      cornerRadius: 24,
      strokeWidth: 1.0,
      horizontalPadding: 20,
      verticalPadding: 15,
      filledElevation: 0.5,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.24,
    ),
    motion: GteThemeMotion(
      feel: 'Floating, diffused, premium',
      fast: Duration(milliseconds: 120),
      medium: Duration(milliseconds: 210),
      slow: Duration(milliseconds: 340),
      emphasizedCurve: Curves.easeOut,
      standardCurve: Curves.easeInOut,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Use elevated glass cards with restrained color pops on story tiles and highlights. Let blur-like layering come from tonal stacking, not busy backgrounds.',
      dashboard:
          'Lean on pale blue for selected tabs, data focus states, and chart callouts while keeping KPI panels calm and spacious.',
      profile:
          'Profile headers should use soft panel layering and amethyst accent for premium badges, not dense gradients.',
      accessibility:
          'Muted text still lands above contrast thresholds on the navy glass stack, while active controls automatically choose a readable foreground tone.',
    ),
  );

  static const GteThemeDefinition auroraIntelligence = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.auroraIntelligence,
      label: 'Aurora Intelligence',
      tagline: 'AI-native control surface',
      description:
          'Indigo, cyan, and aurora-green contrast aimed at predictive tools, copilots, and futuristic decision dashboards.',
      icon: Icons.psychology_alt_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF061118),
      backgroundSoft: Color(0xFF0A1C26),
      panel: Color(0xFF0F2430),
      panelStrong: Color(0xFF123342),
      panelElevated: Color(0xFF18495C),
      stroke: Color(0xFF2F6678),
      outline: Color(0xFF4A8799),
      surfaceHighlight: Color(0xFFF1FDFF),
      shadow: Color(0xFF01070A),
      accent: Color(0xFF6D7CFF),
      accentWarm: Color(0xFF2CF0FF),
      accentArena: Color(0xFF7FFFB7),
      accentCommunity: Color(0xFF4BE6A1),
      accentCapital: Color(0xFFFFD166),
      accentClub: Color(0xFF73B9FF),
      accentAdmin: Color(0xFFFF8C70),
      textPrimary: Color(0xFFF1FDFF),
      textMuted: Color(0xFF9CC3CB),
      textInverse: Color(0xFF061118),
      positive: Color(0xFF68E6A9),
      negative: Color(0xFFFF7C92),
      warning: Color(0xFFFFC35C),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 22,
      spaceXl: 30,
      radiusSmall: 16,
      radiusMedium: 22,
      radiusLarge: 30,
      radiusPill: 999,
    ),
    typography: GteThemeTypography(
      styleName: 'Geometric tech sans',
      displaySize: 39,
      displayWeight: FontWeight.w800,
      displayLetterSpacing: -1.5,
      displayHeight: 1.0,
      headlineSize: 28,
      headlineWeight: FontWeight.w700,
      headlineLetterSpacing: -0.55,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: 0.04,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.54,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.16,
      labelSize: 13,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.6,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Precision pill',
      cornerRadius: 20,
      strokeWidth: 1.15,
      horizontalPadding: 22,
      verticalPadding: 15,
      filledElevation: 1,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.36,
    ),
    motion: GteThemeMotion(
      feel: 'Predictive, precise, gliding',
      fast: Duration(milliseconds: 120),
      medium: Duration(milliseconds: 190),
      slow: Duration(milliseconds: 300),
      emphasizedCurve: Curves.easeOutCubic,
      standardCurve: Curves.easeInOut,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Apply the cyan-to-indigo relationship to AI prompts, recommendation cards, and confidence pills. Keep green reserved for model wins and successful actions.',
      dashboard:
          'Best for dense analytics surfaces, ranking modules, and assistant panels where hierarchy needs to feel machine-guided rather than decorative.',
      profile:
          'Use indigo for profile headers and aurora green for skills, verification, and AI-generated summary modules.',
      accessibility:
          'The theme keeps high-luminance copy on deep teal surfaces and uses contrast-aware foreground selection on bright predictive controls.',
    ),
  );

  static const GteThemeDefinition creatorGold = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.creatorGold,
      label: 'Creator Gold',
      tagline: 'Warm premium monetization',
      description:
          'Gold-led monetization system with warm amber and mint contrast for subscriptions, payouts, and creator status.',
      icon: Icons.workspace_premium_outlined,
      brightness: Brightness.dark,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFF120C07),
      backgroundSoft: Color(0xFF1A120B),
      panel: Color(0xFF22180F),
      panelStrong: Color(0xFF2F2114),
      panelElevated: Color(0xFF412C18),
      stroke: Color(0xFF6B5132),
      outline: Color(0xFF94704A),
      surfaceHighlight: Color(0xFFFFF8ED),
      shadow: Color(0xFF030201),
      accent: Color(0xFFD7A43B),
      accentWarm: Color(0xFFFF8E4D),
      accentArena: Color(0xFF5DD5C1),
      accentCommunity: Color(0xFF5FD49B),
      accentCapital: Color(0xFFF2D470),
      accentClub: Color(0xFF8BBEFF),
      accentAdmin: Color(0xFFFF9B75),
      textPrimary: Color(0xFFFFF8ED),
      textMuted: Color(0xFFD0B796),
      textInverse: Color(0xFF1A1008),
      positive: Color(0xFF6BDE9C),
      negative: Color(0xFFFF8B82),
      warning: Color(0xFFF9C96D),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 22,
      spaceXl: 30,
      radiusSmall: 16,
      radiusMedium: 20,
      radiusLarge: 28,
      radiusPill: 999,
    ),
    typography: GteThemeTypography(
      styleName: 'Humanist premium sans',
      displaySize: 38,
      displayWeight: FontWeight.w800,
      displayLetterSpacing: -1.55,
      displayHeight: 1.02,
      headlineSize: 27,
      headlineWeight: FontWeight.w700,
      headlineLetterSpacing: -0.48,
      titleSize: 18,
      titleWeight: FontWeight.w700,
      titleLetterSpacing: -0.08,
      bodySize: 15,
      bodyWeight: FontWeight.w500,
      bodyHeight: 1.56,
      bodyLetterSpacing: 0.03,
      captionSize: 12,
      captionLetterSpacing: 0.12,
      labelSize: 13,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.28,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Premium rounded tab',
      cornerRadius: 18,
      strokeWidth: 1.1,
      horizontalPadding: 22,
      verticalPadding: 15,
      filledElevation: 1.25,
      labelWeight: FontWeight.w800,
      labelLetterSpacing: 0.22,
    ),
    motion: GteThemeMotion(
      feel: 'Measured, confident, aspirational',
      fast: Duration(milliseconds: 120),
      medium: Duration(milliseconds: 200),
      slow: Duration(milliseconds: 320),
      emphasizedCurve: Curves.easeOut,
      standardCurve: Curves.easeInOutCubic,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Best for monetization surfaces in the feed: premium upsells, revenue milestones, and creator reward modules. Keep gold concentrated around value moments.',
      dashboard:
          'Use brighter gold for primary revenue totals and mint for positive deltas, leaving base cards warm and dark for a premium finance tone.',
      profile:
          'Profile headers should emphasize premium tier, payout eligibility, and earned badges using gold and warm orange without overpowering the avatar or bio.',
      accessibility:
          'Dark espresso surfaces support high-contrast cream text, while gold and orange actions rely on contrast-aware foregrounds for readable CTA labels.',
    ),
  );

  static const GteThemeDefinition minimalCarbon = GteThemeDefinition(
    metadata: GteThemeMetadata(
      id: GteThemeId.minimalCarbon,
      label: 'Minimal Carbon',
      tagline: 'Ultra-clean product baseline',
      description:
          'Carbon-first light system with restrained gray structure and one precise blue accent for Apple-level simplicity.',
      icon: Icons.circle_outlined,
      brightness: Brightness.light,
    ),
    tokens: GteThemeTokens(
      background: Color(0xFFF5F5F7),
      backgroundSoft: Color(0xFFECECEF),
      panel: Color(0xFFFFFFFF),
      panelStrong: Color(0xFFF2F2F5),
      panelElevated: Color(0xFFE8E8EC),
      stroke: Color(0xFFD4D6DB),
      outline: Color(0xFFB8BBC3),
      surfaceHighlight: Color(0xFF111315),
      shadow: Color(0xFF1D2129),
      accent: Color(0xFF111315),
      accentWarm: Color(0xFF5C6773),
      accentArena: Color(0xFF0A84FF),
      accentCommunity: Color(0xFF0F9F6E),
      accentCapital: Color(0xFFC28B2C),
      accentClub: Color(0xFF2874F0),
      accentAdmin: Color(0xFFD9504D),
      textPrimary: Color(0xFF111315),
      textMuted: Color(0xFF5A5E66),
      textInverse: Color(0xFFFFFFFF),
      positive: Color(0xFF0F9F6E),
      negative: Color(0xFFD9504D),
      warning: Color(0xFFB57614),
      spaceXs: 8,
      spaceSm: 12,
      spaceMd: 16,
      spaceLg: 20,
      spaceXl: 28,
      radiusSmall: 14,
      radiusMedium: 16,
      radiusLarge: 22,
      radiusPill: 999,
    ),
    typography: GteThemeTypography(
      styleName: 'Neutral system sans',
      displaySize: 36,
      displayWeight: FontWeight.w700,
      displayLetterSpacing: -1.7,
      displayHeight: 1.04,
      headlineSize: 26,
      headlineWeight: FontWeight.w600,
      headlineLetterSpacing: -0.72,
      titleSize: 17,
      titleWeight: FontWeight.w600,
      titleLetterSpacing: -0.08,
      bodySize: 15,
      bodyWeight: FontWeight.w400,
      bodyHeight: 1.6,
      bodyLetterSpacing: 0,
      captionSize: 12,
      captionLetterSpacing: 0.08,
      labelSize: 12,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.18,
    ),
    button: GteThemeButtonSpec(
      styleName: 'Minimal soft rectangle',
      cornerRadius: 16,
      strokeWidth: 1,
      horizontalPadding: 18,
      verticalPadding: 14,
      filledElevation: 0,
      labelWeight: FontWeight.w700,
      labelLetterSpacing: 0.12,
    ),
    motion: GteThemeMotion(
      feel: 'Restrained, frictionless, quiet',
      fast: Duration(milliseconds: 100),
      medium: Duration(milliseconds: 170),
      slow: Duration(milliseconds: 250),
      emphasizedCurve: Curves.easeOut,
      standardCurve: Curves.easeInOut,
    ),
    usage: GteThemeUsageGuidance(
      feed:
          'Use white cards, clean separators, and one blue accent for creator actions. Avoid stacking multiple saturated tones inside a single feed viewport.',
      dashboard:
          'Ideal for dense dashboards that need maximum readability. Use carbon for the main CTA and blue strictly for navigation, active filters, and charts.',
      profile:
          'Profile screens should feel airy and editorial, with carbon text, subtle section dividers, and minimal tinted backgrounds.',
      accessibility:
          'This light system uses dark carbon text on near-white surfaces and keeps interactive accents within accessible contrast pairings.',
    ),
  );

  static const GteThemeDefinition defaultTheme = creatorGold;

  static const List<GteThemeDefinition> themes = <GteThemeDefinition>[
    neonVelocity,
    midnightGlass,
    auroraIntelligence,
    creatorGold,
    minimalCarbon,
  ];

  static GteThemeDefinition resolve(GteThemeId id) {
    switch (id) {
      case GteThemeId.neonVelocity:
        return neonVelocity;
      case GteThemeId.midnightGlass:
        return midnightGlass;
      case GteThemeId.auroraIntelligence:
        return auroraIntelligence;
      case GteThemeId.creatorGold:
        return creatorGold;
      case GteThemeId.minimalCarbon:
        return minimalCarbon;
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
