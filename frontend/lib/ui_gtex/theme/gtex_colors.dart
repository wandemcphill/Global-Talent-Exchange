import 'package:flutter/material.dart';

@immutable
class GtexColorTokens {
  const GtexColorTokens({
    required this.bgBase,
    required this.bgSurface,
    required this.bgElevated,
    required this.bgOverlay,
    required this.bgBorder,
    required this.brandPitch,
    required this.brandCoin,
    required this.brandFan,
    required this.brandAlert,
    required this.brandWarn,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.textInverse,
    required this.positive,
    required this.negative,
    required this.neutral,
    required this.pending,
    required this.scrim,
  });

  final Color bgBase;
  final Color bgSurface;
  final Color bgElevated;
  final Color bgOverlay;
  final Color bgBorder;
  final Color brandPitch;
  final Color brandCoin;
  final Color brandFan;
  final Color brandAlert;
  final Color brandWarn;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color textInverse;
  final Color positive;
  final Color negative;
  final Color neutral;
  final Color pending;
  final Color scrim;
}

enum GtexRoleAccent { admin, clubOwner, trader, creator, user, guest }

/// GTEX design-bible color tokens.
///
/// The canonical palette is a professional football-economy system: dark
/// institutional surfaces, semantic accents, and no decorative neon/gloss.
class GtexColors {
  const GtexColors._();

  static const GtexColorTokens dark = GtexColorTokens(
    bgBase: Color(0xFF0A0C0F),
    bgSurface: Color(0xFF111418),
    bgElevated: Color(0xFF181C22),
    bgOverlay: Color(0xFF1E232B),
    bgBorder: Color(0xFF262C36),
    brandPitch: Color(0xFF00C46A),
    brandCoin: Color(0xFFFFB800),
    brandFan: Color(0xFF3D7EFF),
    brandAlert: Color(0xFFFF4D4D),
    brandWarn: Color(0xFFFF9500),
    textPrimary: Color(0xFFF0F2F5),
    textSecondary: Color(0xFF8A93A2),
    textMuted: Color(0xFF4A5568),
    textInverse: Color(0xFF0A0C0F),
    positive: Color(0xFF00C46A),
    negative: Color(0xFFFF4D4D),
    neutral: Color(0xFF8A93A2),
    pending: Color(0xFFFF9500),
    scrim: Color(0xCC0A0C0F),
  );

  static const GtexColorTokens light = GtexColorTokens(
    bgBase: Color(0xFFF4F6F9),
    bgSurface: Color(0xFFFFFFFF),
    bgElevated: Color(0xFFF9FAFB),
    bgOverlay: Color(0xFFEDF0F4),
    bgBorder: Color(0xFFDDE1E8),
    brandPitch: Color(0xFF00924E),
    brandCoin: Color(0xFFCC9200),
    brandFan: Color(0xFF2563EB),
    brandAlert: Color(0xFFDC2626),
    brandWarn: Color(0xFFD97706),
    textPrimary: Color(0xFF0F1319),
    textSecondary: Color(0xFF4A5568),
    textMuted: Color(0xFF9CA3AF),
    textInverse: Color(0xFFF0F2F5),
    positive: Color(0xFF00924E),
    negative: Color(0xFFDC2626),
    neutral: Color(0xFF4A5568),
    pending: Color(0xFFD97706),
    scrim: Color(0xCC1A1F2B),
  );

  static GtexColorTokens of(BuildContext context) {
    return Theme.of(context).brightness == Brightness.light ? light : dark;
  }

  static const Color surfaceBase = Color(0xFF0A0C0F);
  static const Color surfaceRaised = Color(0xFF111418);
  static const Color surfaceOverlay = Color(0xFF181C22);
  static const Color surfaceInput = Color(0xFF1C2128);
  static const Color surfaceHover = Color(0xFF1E232B);
  static const Color surfaceBorder = Color(0xFF262C36);
  static const Color surfaceBorderStrong = Color(0xFF313844);

  static const Color textPrimary = Color(0xFFF0F2F5);
  static const Color textSecondary = Color(0xFF8A93A2);
  static const Color textTertiary = Color(0xFF4A5568);
  static const Color textInverse = Color(0xFF0A0C0F);

  static const Color accentPrimary = Color(0xFF00C46A);
  static const Color accentAmber = Color(0xFFFFB800);
  static const Color accentRed = Color(0xFFFF4D4D);
  static const Color accentBlue = Color(0xFF3D7EFF);
  static const Color accentViolet = Color(0xFFE040FB);
  static const Color accentWarn = Color(0xFFFF9500);

  static const Color statusLive = accentPrimary;
  static const Color statusLocked = accentWarn;
  static const Color statusBlocked = accentRed;
  static const Color statusIdle = textTertiary;
  static const Color statusLoading = accentBlue;

  static const Color coinGtex = accentAmber;
  static const Color coinFan = accentBlue;

  static const Color roleAdmin = Color(0xFFE040FB);
  static const Color roleClubOwner = accentPrimary;
  static const Color roleTrader = accentAmber;
  static const Color roleCreator = Color(0xFF00B4D8);
  static const Color roleUser = Color(0xFF8A93A2);
  static const Color roleGuest = Color(0xFF4A5568);

  static const Color positionGoalkeeper = accentAmber;
  static const Color positionDefender = accentBlue;
  static const Color positionMidfielder = accentPrimary;
  static const Color positionAttacker = accentRed;

  /// Backward-compatible aliases used by older GTEX widgets.
  static const Color stadiumBlack = surfaceBase;
  static const Color black = surfaceBase;
  static const Color midnight = surfaceBase;
  static const Color tacticalNavy = surfaceRaised;
  static const Color panel = surfaceRaised;
  static const Color panelStrong = surfaceOverlay;
  static const Color panelElevated = surfaceHover;
  static const Color panelAlt = surfaceHover;
  static const Color line = surfaceBorder;
  static const Color lineSoft = Color(0x33252D38);
  static const Color pitch = accentPrimary;
  static const Color green = accentPrimary;
  static const Color electricGreen = accentPrimary;
  static const Color pitchDeep = accentPrimary;
  static const Color gold = accentAmber;
  static const Color cyan = accentBlue;
  static const Color mint = accentPrimary;
  static const Color purple = accentViolet;
  static const Color orange = accentWarn;
  static const Color red = accentRed;
  static const Color danger = accentRed;
  static const Color text = textPrimary;
  static const Color textSecondaryAlias = textSecondary;
  static const Color textMuted = textTertiary;

  static const List<Color> heroGradient = <Color>[
    surfaceBase,
    surfaceRaised,
    surfaceOverlay,
  ];

  static Color positionColor(String position) {
    final String normalized = position.trim().toUpperCase();
    if (normalized == 'GK') {
      return positionGoalkeeper;
    }
    if (normalized == 'CB' ||
        normalized == 'LB' ||
        normalized == 'RB' ||
        normalized == 'LWB' ||
        normalized == 'RWB' ||
        normalized == 'DEF' ||
        normalized == 'DF') {
      return positionDefender;
    }
    if (normalized == 'ST' ||
        normalized == 'CF' ||
        normalized == 'LW' ||
        normalized == 'RW' ||
        normalized == 'ATT' ||
        normalized == 'FW') {
      return positionAttacker;
    }
    return positionMidfielder;
  }

  static Color roleColor(GtexRoleAccent role) {
    return switch (role) {
      GtexRoleAccent.admin => roleAdmin,
      GtexRoleAccent.clubOwner => roleClubOwner,
      GtexRoleAccent.trader => roleTrader,
      GtexRoleAccent.creator => roleCreator,
      GtexRoleAccent.user => roleUser,
      GtexRoleAccent.guest => roleGuest,
    };
  }

  static LinearGradient panelGlow({Color accent = accentPrimary}) {
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        surfaceRaised,
        surfaceBase,
        accent.withValues(alpha: 0.06),
      ],
    );
  }

  static BoxShadow glow(Color color, {double opacity = 0.18}) {
    return BoxShadow(
      color: Colors.black.withValues(alpha: opacity),
      blurRadius: 12,
      spreadRadius: -8,
      offset: const Offset(0, 4),
    );
  }
}
