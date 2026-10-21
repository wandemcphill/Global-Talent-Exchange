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
    this.bgInset = const Color(0xFF081120),
    this.lineStrong = const Color(0xFF2F4C75),
    this.gold300 = const Color(0xFFE8C766),
    this.gold500 = const Color(0xFFD4AF37),
    this.gold700 = const Color(0xFFA8862A),
    this.info = const Color(0xFF5B8DEF),
    this.live = const Color(0xFFFF5B3A),
  });

  final Color bgBase;
  final Color bgSurface;
  final Color bgElevated;
  final Color bgOverlay;
  final Color bgBorder;
  final Color bgInset;
  final Color lineStrong;
  final Color brandPitch;
  final Color brandCoin;
  final Color brandFan;
  final Color brandAlert;
  final Color brandWarn;
  final Color gold300;
  final Color gold500;
  final Color gold700;
  final Color info;
  final Color live;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color textInverse;
  final Color positive;
  final Color negative;
  final Color neutral;
  final Color pending;
  final Color scrim;

  /// Canonical Document F3 aliases.
  Color get bgRaised => bgSurface;
  Color get lineSubtle => bgBorder;
  Color get textTertiary => textMuted;
  Color get success => positive;
  Color get warning => brandWarn;
  Color get danger => negative;
  Color get coinGtc => info;
  Color get coinGtx => info;
  Color get coinFnc => gold300;
  Color get coinFanToken => gold300;
}

/// Canonical "GTEX Navy" colour palette (Master Plan Document F3, Decision O-06).
///
/// Deep navy surfaces (`#0B1626` -> `#13233A` -> `#1A2E4A`), warm gold signal
/// accents (`#D4AF37`), and WCAG 2.x AA-verified text/status pairings.
class GtexNavyColors {
  const GtexNavyColors._();

  static const Color bgBase = Color(0xFF0B1626);
  static const Color bgRaised = Color(0xFF13233A);
  static const Color bgOverlay = Color(0xFF1A2E4A);
  static const Color bgInset = Color(0xFF081120);
  static const Color lineSubtle = Color(0xFF22385A);
  static const Color lineStrong = Color(0xFF2F4C75);

  static const Color textPrimary = Color(0xFFF2F4F8);
  static const Color textSecondary = Color(0xFF9AA7BD);
  static const Color textTertiary = Color(0xFF6B7A93);
  static const Color textInverse = Color(0xFF081120);

  static const Color gold500 = Color(0xFFD4AF37);
  static const Color gold300 = Color(0xFFE8C766);
  static const Color gold700 = Color(0xFFA8862A);

  static const Color info = Color(0xFF5B8DEF);
  static const Color success = Color(0xFF3DBE8B);
  static const Color warning = Color(0xFFF0A93B);
  static const Color danger = Color(0xFFE5534B);
  static const Color live = Color(0xFFFF5B3A);

  static const Color currencyGtc = info;
  static const Color currencyGtx = info;
  static const Color currencyFnc = gold300;
  static const Color currencyFan = gold300;
  static const Color scrim = Color(0xCC081120);
}

enum GtexRoleAccent { admin, clubOwner, trader, creator, user, guest }

/// "Floodlit" card surfaces: night-pitch greens, chalk-line foreground,
/// floodlight gold for coin and 1-of-1 prestige. Used by the collectible
/// player and regen cards so they read as football objects, not panels.
class GtexFloodlit {
  const GtexFloodlit._();

  static const Color night = Color(0xFF08140F);
  static const Color card = Color(0xFF0E1F17);
  static const Color turf = Color(0xFF13291E);
  static const Color line = Color(0xFF20402F);
  static const Color chalk = Color(0xFFEDF1E8);
  static const Color chalkMuted = Color(0xFF8EA596);
  static const Color pitch = Color(0xFF34D57F);
  static const Color gold = Color(0xFFF4C24D);
  static const Color scoreboard = Color(0xFFFF5B3A);

  static const String display = 'BarlowCondensed';
}

/// GTEX design-bible color tokens.
///
/// The canonical palette is a professional football-economy system: dark
/// institutional surfaces, semantic accents, and no decorative neon/gloss.
class GtexColors {
  const GtexColors._();

  /// Canonical "GTEX Navy" token set (Master Plan Document F3, Decision O-06).
  static const GtexColorTokens navy = GtexColorTokens(
    bgBase: GtexNavyColors.bgBase,
    bgSurface: GtexNavyColors.bgRaised,
    bgElevated: GtexNavyColors.bgOverlay,
    bgOverlay: GtexNavyColors.bgOverlay,
    bgBorder: GtexNavyColors.lineSubtle,
    bgInset: GtexNavyColors.bgInset,
    lineStrong: GtexNavyColors.lineStrong,
    brandPitch: GtexNavyColors.success,
    brandCoin: GtexNavyColors.gold500,
    brandFan: GtexNavyColors.info,
    brandAlert: GtexNavyColors.danger,
    brandWarn: GtexNavyColors.warning,
    gold300: GtexNavyColors.gold300,
    gold500: GtexNavyColors.gold500,
    gold700: GtexNavyColors.gold700,
    info: GtexNavyColors.info,
    live: GtexNavyColors.live,
    textPrimary: GtexNavyColors.textPrimary,
    textSecondary: GtexNavyColors.textSecondary,
    textMuted: GtexNavyColors.textTertiary,
    textInverse: GtexNavyColors.textInverse,
    positive: GtexNavyColors.success,
    negative: GtexNavyColors.danger,
    neutral: GtexNavyColors.textSecondary,
    pending: GtexNavyColors.warning,
    scrim: GtexNavyColors.scrim,
  );

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

  static GtexColorTokens of(BuildContext context, {bool preferNavy = false}) {
    if (Theme.of(context).brightness == Brightness.light) {
      return light;
    }
    if (preferNavy ||
        Theme.of(context).scaffoldBackgroundColor == GtexNavyColors.bgBase) {
      return navy;
    }
    return dark;
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
