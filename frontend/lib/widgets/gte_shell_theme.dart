import 'package:flutter/material.dart';

import '../theme/gte_theme_registry.dart';
import '../theme/gte_theme_scope.dart';
import '../theme/gte_theme_tokens.dart';

class GteShellTheme {
  const GteShellTheme._();

  // Dark Gold stays as the compatibility fallback for legacy static references.
  static const Color background = Color(0xFF080604);
  static const Color backgroundSoft = Color(0xFF120D08);
  static const Color panel = Color(0xFF17100B);
  static const Color panelStrong = Color(0xFF24170E);
  static const Color panelElevated = Color(0xFF322012);
  static const Color stroke = Color(0xFF5C4632);
  static const Color accent = Color(0xFFF6C453);
  static const Color accentWarm = Color(0xFFFFE18A);
  static const Color accentArena = Color(0xFFFF8A3D);
  static const Color accentCapital = Color(0xFFF0D17A);
  static const Color accentCommunity = Color(0xFF6BE3B4);
  static const Color accentClub = Color(0xFF7EC4FF);
  static const Color accentAdmin = Color(0xFFFF906B);
  static const Color textPrimary = Color(0xFFF9F3EA);
  static const Color textMuted = Color(0xFFC8B49B);
  static const Color textSecondary = textMuted;
  static const Color positive = Color(0xFF63E79C);
  static const Color negative = Color(0xFFFF8E7A);
  static const Color warning = Color(0xFFFFD36F);

  static GteThemeDefinition _activeDefinition = GteThemeRegistry.defaultTheme;

  static GteThemeDefinition get activeDefinition => _activeDefinition;
  static GteThemeTokens get activeTokens => _activeDefinition.tokens;

  static ThemeData build([GteThemeDefinition? definition]) {
    final GteThemeDefinition resolvedDefinition =
        definition ?? GteThemeRegistry.defaultTheme;
    _activeDefinition = resolvedDefinition;
    final GteThemeTokens tokens = resolvedDefinition.tokens;
    final bool isDark =
        resolvedDefinition.metadata.brightness == Brightness.dark;
    final ColorScheme colorScheme = ColorScheme.fromSeed(
      seedColor: tokens.accent,
      brightness: resolvedDefinition.metadata.brightness,
    ).copyWith(
      primary: tokens.accent,
      onPrimary: tokens.textInverse,
      secondary: tokens.accentWarm,
      onSecondary: tokens.textInverse,
      tertiary: tokens.accentArena,
      onTertiary: tokens.textInverse,
      surface: tokens.panel,
      onSurface: tokens.textPrimary,
      error: tokens.negative,
      onError: tokens.textInverse,
      outline: tokens.stroke,
      shadow: tokens.shadow,
      surfaceTint: Colors.transparent,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: resolvedDefinition.metadata.brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: tokens.background,
      cardColor: tokens.panel,
      dividerColor: tokens.stroke,
      shadowColor: tokens.shadow,
      splashColor: tokens.accent.withValues(alpha: isDark ? 0.12 : 0.08),
      extensions: <ThemeExtension<dynamic>>[tokens],
      textTheme: _textTheme(tokens),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        foregroundColor: tokens.textPrimary,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: tokens.panelStrong,
        side: BorderSide(color: tokens.stroke),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusPill),
        ),
        labelStyle: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: tokens.textPrimary,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: _surfaceTint(tokens, isDark ? 0.05 : 0.04),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          borderSide: BorderSide(color: tokens.stroke),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          borderSide: BorderSide(color: tokens.stroke),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          borderSide: BorderSide(color: tokens.accent, width: 1.4),
        ),
        contentPadding: EdgeInsets.symmetric(
          horizontal: tokens.spaceLg - 2,
          vertical: tokens.spaceLg - 2,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: tokens.accent,
          foregroundColor: tokens.textInverse,
          padding: EdgeInsets.symmetric(
            horizontal: tokens.spaceLg - 2,
            vertical: tokens.spaceMd,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(tokens.radiusMedium - 2),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: tokens.textPrimary,
          padding: EdgeInsets.symmetric(
            horizontal: tokens.spaceLg - 2,
            vertical: tokens.spaceMd,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(tokens.radiusMedium - 2),
          ),
          side: BorderSide(color: tokens.stroke),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: tokens.panel,
        indicatorColor: tokens.accent.withValues(alpha: isDark ? 0.22 : 0.16),
        labelTextStyle: const WidgetStatePropertyAll<TextStyle>(
          TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: tokens.panel,
        modalBackgroundColor: tokens.panel,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(tokens.radiusLarge),
          ),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: tokens.stroke,
        thickness: 1,
        space: 1,
      ),
    );
  }

  static GteThemeTokens tokensOf(BuildContext context) {
    final GteThemeTokens? tokens =
        Theme.of(context).extension<GteThemeTokens>();
    return tokens ?? activeTokens;
  }

  static GteThemeDefinition definitionOf(BuildContext context) {
    return GteThemeControllerScope.maybeOf(context)?.activeTheme ??
        _activeDefinition;
  }

  static TextTheme _textTheme(GteThemeTokens tokens) {
    return TextTheme(
      displaySmall: TextStyle(
        fontSize: 34,
        fontWeight: FontWeight.w800,
        letterSpacing: -1.5,
        color: tokens.textPrimary,
        height: 1.04,
      ),
      headlineSmall: TextStyle(
        fontSize: 24,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.9,
        color: tokens.textPrimary,
      ),
      titleLarge: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
        color: tokens.textPrimary,
      ),
      titleMedium: TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w700,
        color: tokens.textPrimary,
      ),
      bodyLarge: TextStyle(
        fontSize: 15,
        height: 1.55,
        color: tokens.textPrimary,
      ),
      bodyMedium: TextStyle(
        fontSize: 13,
        height: 1.5,
        color: tokens.textMuted,
      ),
      bodySmall: TextStyle(
        fontSize: 12,
        height: 1.4,
        color: tokens.textMuted,
      ),
      labelLarge: TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.25,
        color: tokens.textPrimary,
      ),
    );
  }
}

Color _surfaceTint(GteThemeTokens tokens, double alpha) {
  return Color.alphaBlend(
    tokens.surfaceHighlight.withValues(alpha: alpha),
    tokens.panelStrong,
  );
}

BoxDecoration gteBackdropDecoration() {
  final GteThemeTokens tokens = GteShellTheme.activeTokens;
  return BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        tokens.background,
        Color.alphaBlend(
          tokens.accent.withValues(alpha: 0.06),
          tokens.backgroundSoft,
        ),
        tokens.backgroundSoft,
        Color.alphaBlend(
          tokens.accentArena.withValues(alpha: 0.08),
          tokens.panelElevated,
        ),
      ],
      stops: const <double>[0.02, 0.28, 0.68, 1],
    ),
  );
}
