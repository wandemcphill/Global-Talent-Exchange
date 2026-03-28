import 'package:flutter/material.dart';

import '../theme/gte_theme_registry.dart';
import '../theme/gte_theme_scope.dart';
import '../theme/gte_theme_specs.dart';
import '../theme/gte_theme_tokens.dart';

class GteShellTheme {
  const GteShellTheme._();

  // Creator Gold stays as the compatibility fallback for legacy static refs.
  static const Color background = Color(0xFF120C07);
  static const Color backgroundSoft = Color(0xFF1A120B);
  static const Color panel = Color(0xFF22180F);
  static const Color panelStrong = Color(0xFF2F2114);
  static const Color panelElevated = Color(0xFF412C18);
  static const Color stroke = Color(0xFF6B5132);
  static const Color accent = Color(0xFFD7A43B);
  static const Color accentWarm = Color(0xFFFF8E4D);
  static const Color accentArena = Color(0xFF5DD5C1);
  static const Color accentCapital = Color(0xFFF2D470);
  static const Color accentCommunity = Color(0xFF5FD49B);
  static const Color accentClub = Color(0xFF8BBEFF);
  static const Color accentAdmin = Color(0xFFFF9B75);
  static const Color textPrimary = Color(0xFFFFF8ED);
  static const Color textMuted = Color(0xFFD0B796);
  static const Color textSecondary = textMuted;
  static const Color positive = Color(0xFF6BDE9C);
  static const Color negative = Color(0xFFFF8B82);
  static const Color warning = Color(0xFFF9C96D);

  static GteThemeDefinition _activeDefinition = GteThemeRegistry.defaultTheme;

  static GteThemeDefinition get activeDefinition => _activeDefinition;
  static GteThemeTokens get activeTokens => _activeDefinition.tokens;

  static ThemeData build([GteThemeDefinition? definition]) {
    final GteThemeDefinition resolvedDefinition =
        definition ?? GteThemeRegistry.defaultTheme;
    _activeDefinition = resolvedDefinition;
    final GteThemeTokens tokens = resolvedDefinition.tokens;
    final GteThemeButtonSpec button = resolvedDefinition.button;
    final GteThemeMotion motion = resolvedDefinition.motion;
    final bool isDark =
        resolvedDefinition.metadata.brightness == Brightness.dark;
    final ColorScheme colorScheme = ColorScheme.fromSeed(
      seedColor: resolvedDefinition.primaryColor,
      brightness: resolvedDefinition.metadata.brightness,
    ).copyWith(
      primary: resolvedDefinition.primaryColor,
      onPrimary: resolvedDefinition.onPrimaryColor,
      secondary: resolvedDefinition.secondaryColor,
      onSecondary: resolvedDefinition.onSecondaryColor,
      tertiary: resolvedDefinition.accentColor,
      onTertiary: resolvedDefinition.onAccentColor,
      surface: resolvedDefinition.surfaceColor,
      onSurface: tokens.textPrimary,
      error: tokens.negative,
      onError: _foregroundOn(tokens.negative, tokens),
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
      extensions: <ThemeExtension<dynamic>>[tokens, motion],
      textTheme: resolvedDefinition.typography.buildTextTheme(
        primary: tokens.textPrimary,
        muted: tokens.textMuted,
      ),
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
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(color: tokens.stroke),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(color: tokens.stroke),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(
            color: resolvedDefinition.primaryColor,
            width: 1.4,
          ),
        ),
        contentPadding: EdgeInsets.symmetric(
          horizontal: button.horizontalPadding,
          vertical: button.verticalPadding,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: resolvedDefinition.primaryColor,
          foregroundColor: resolvedDefinition.onPrimaryColor,
          elevation: button.filledElevation,
          padding: EdgeInsets.symmetric(
            horizontal: button.horizontalPadding,
            vertical: button.verticalPadding,
          ),
          textStyle: TextStyle(
            fontSize: resolvedDefinition.typography.scale['label'],
            fontWeight: button.labelWeight,
            letterSpacing: button.labelLetterSpacing,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(button.cornerRadius),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: tokens.textPrimary,
          padding: EdgeInsets.symmetric(
            horizontal: button.horizontalPadding,
            vertical: button.verticalPadding,
          ),
          textStyle: TextStyle(
            fontSize: resolvedDefinition.typography.scale['label'],
            fontWeight: button.labelWeight,
            letterSpacing: button.labelLetterSpacing,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(button.cornerRadius),
          ),
          side: BorderSide(
            color: resolvedDefinition.secondaryColor.withValues(alpha: 0.72),
            width: button.strokeWidth,
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: resolvedDefinition.accentColor,
          foregroundColor: resolvedDefinition.onAccentColor,
          elevation: button.filledElevation,
          padding: EdgeInsets.symmetric(
            horizontal: button.horizontalPadding,
            vertical: button.verticalPadding,
          ),
          textStyle: TextStyle(
            fontSize: resolvedDefinition.typography.scale['label'],
            fontWeight: button.labelWeight,
            letterSpacing: button.labelLetterSpacing,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(button.cornerRadius),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: tokens.panel,
        indicatorColor: resolvedDefinition.primaryColor.withValues(
          alpha: isDark ? 0.2 : 0.12,
        ),
        labelTextStyle: WidgetStatePropertyAll<TextStyle>(
          TextStyle(
            fontWeight: button.labelWeight,
            letterSpacing: button.labelLetterSpacing,
          ),
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

  static GteThemeMotion motionOf(BuildContext context) {
    final GteThemeMotion? motion =
        Theme.of(context).extension<GteThemeMotion>();
    return motion ?? activeDefinition.motion;
  }

  static GteThemeDefinition definitionOf(BuildContext context) {
    return GteThemeControllerScope.maybeOf(context)?.activeTheme ??
        _activeDefinition;
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
  final GteThemeDefinition definition = GteShellTheme.activeDefinition;
  return BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        tokens.background,
        Color.alphaBlend(
          definition.primaryColor.withValues(alpha: 0.08),
          tokens.backgroundSoft,
        ),
        Color.alphaBlend(
          definition.secondaryColor.withValues(alpha: 0.05),
          tokens.backgroundSoft,
        ),
        Color.alphaBlend(
          definition.accentColor.withValues(alpha: 0.1),
          tokens.panelElevated,
        ),
      ],
      stops: const <double>[0.02, 0.28, 0.68, 1],
    ),
  );
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
