import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/gte_theme_controller.dart';
import '../theme/gte_theme_extensions.dart';
import '../theme/gte_theme_registry.dart';
import '../theme/gte_theme_scope.dart';
import '../theme/gte_theme_specs.dart';
import '../theme/gte_theme_tokens.dart';

class GteShellTheme {
  const GteShellTheme._();

  static const Color background = Color(0xFF040608);
  static const Color backgroundSoft = Color(0xFF0A0E11);
  static const Color panel = Color(0xFF101518);
  static const Color panelStrong = Color(0xFF151C20);
  static const Color panelElevated = Color(0xFF1B2328);
  static const Color stroke = Color(0xFF2B363B);
  static const Color accent = Color(0xFFB9FF2C);
  static const Color accentWarm = Color(0xFF70F0C0);
  static const Color accentArena = Color(0xFFE7FF79);
  static const Color accentCapital = Color(0xFFFFD75B);
  static const Color accentCommunity = Color(0xFF49DDA1);
  static const Color accentClub = Color(0xFF66D7FF);
  static const Color accentAdmin = Color(0xFFFF7B5C);
  static const Color textPrimary = Color(0xFFF4F7F4);
  static const Color textMuted = Color(0xFF93A39D);
  static const Color textSecondary = textMuted;
  static const Color positive = Color(0xFF69F3A4);
  static const Color negative = Color(0xFFFF6A6A);
  static const Color warning = Color(0xFFFFC857);

  static GteThemeDefinition _activeDefinition = GteThemeRegistry.defaultTheme;

  static GteThemeDefinition get activeDefinition => _activeDefinition;
  static GteThemeTokens get activeTokens => _activeDefinition.tokens;
  static GteThemeVisuals get activeVisuals => _activeDefinition.visuals;

  static ThemeData build([GteThemeDefinition? definition]) {
    final GteThemeDefinition resolvedDefinition =
        definition ?? GteThemeRegistry.defaultTheme;
    _activeDefinition = resolvedDefinition;
    final GteThemeTokens tokens = resolvedDefinition.tokens;
    final GteThemeVisuals visuals = resolvedDefinition.visuals;
    final GteThemeButtonSpec button = resolvedDefinition.button;
    final GteThemeMotion motion = resolvedDefinition.motion;
    final ColorScheme colorScheme = ColorScheme.fromSeed(
      seedColor: resolvedDefinition.primaryColor,
      brightness: Brightness.dark,
    ).copyWith(
      primary: resolvedDefinition.primaryColor,
      onPrimary: resolvedDefinition.onPrimaryColor,
      secondary: resolvedDefinition.secondaryColor,
      onSecondary: resolvedDefinition.onSecondaryColor,
      tertiary: resolvedDefinition.accentColor,
      onTertiary: resolvedDefinition.onAccentColor,
      surface: tokens.panel,
      onSurface: tokens.textPrimary,
      error: tokens.negative,
      onError: _foregroundOn(tokens.negative, tokens),
      outline: tokens.stroke,
      shadow: tokens.shadow,
      surfaceTint: Colors.transparent,
      inverseSurface: tokens.surfaceHighlight,
      inversePrimary: tokens.accentCapital,
    );

    final TextTheme textTheme = resolvedDefinition.typography.buildTextTheme(
      primary: tokens.textPrimary,
      muted: tokens.textMuted,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: resolvedDefinition.metadata.brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: tokens.background,
      canvasColor: tokens.background,
      cardColor: tokens.panel,
      dividerColor: tokens.stroke,
      shadowColor: tokens.shadow,
      textTheme: textTheme,
      iconTheme: IconThemeData(color: tokens.textPrimary),
      primaryIconTheme: IconThemeData(color: tokens.textPrimary),
      splashColor: resolvedDefinition.primaryColor.withValues(alpha: 0.1),
      highlightColor: resolvedDefinition.primaryColor.withValues(alpha: 0.06),
      disabledColor: tokens.textMuted.withValues(alpha: 0.46),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: <TargetPlatform, PageTransitionsBuilder>{
          TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.linux: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.windows: FadeForwardsPageTransitionsBuilder(),
        },
      ),
      extensions: <ThemeExtension<dynamic>>[tokens, motion, visuals],
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        foregroundColor: tokens.textPrimary,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
      cardTheme: CardThemeData(
        color: _surfaceTint(tokens, visuals, 0.08),
        elevation: 0,
        margin: EdgeInsets.zero,
        shadowColor: tokens.shadow,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusLarge),
          side: BorderSide(color: tokens.stroke.withValues(alpha: 0.88)),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: _surfaceTint(tokens, visuals, 0.1),
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusLarge),
          side: BorderSide(color: tokens.stroke.withValues(alpha: 0.94)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: Color.alphaBlend(
          tokens.panelStrong.withValues(alpha: 0.96),
          tokens.background,
        ),
        contentTextStyle: textTheme.bodyMedium?.copyWith(
          color: tokens.textPrimary,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          side: BorderSide(color: tokens.stroke.withValues(alpha: 0.9)),
        ),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: resolvedDefinition.primaryColor,
        linearTrackColor: tokens.panelElevated,
        circularTrackColor: tokens.panelStrong,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Color.alphaBlend(
          resolvedDefinition.secondaryColor.withValues(alpha: 0.08),
          tokens.panelStrong,
        ),
        selectedColor: Color.alphaBlend(
          resolvedDefinition.primaryColor.withValues(alpha: 0.16),
          tokens.panelElevated,
        ),
        side: BorderSide(color: tokens.stroke.withValues(alpha: 0.96)),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusPill),
        ),
        labelStyle: textTheme.labelMedium?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        secondaryLabelStyle: textTheme.labelMedium?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        secondarySelectedColor: resolvedDefinition.primaryColor.withValues(
          alpha: 0.16,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Color.alphaBlend(
          visuals.heroAccent.withValues(alpha: visuals.glass ? 0.06 : 0.03),
          tokens.panelStrong,
        ),
        labelStyle: textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
        hintStyle: textTheme.bodyMedium?.copyWith(
          color: tokens.textMuted.withValues(alpha: 0.88),
        ),
        prefixIconColor: tokens.textMuted,
        suffixIconColor: tokens.textMuted,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(color: tokens.stroke),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(color: tokens.stroke.withValues(alpha: 0.92)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(
            color: resolvedDefinition.primaryColor,
            width: 1.4,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(button.cornerRadius),
          borderSide: BorderSide(color: tokens.negative),
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
          disabledBackgroundColor: tokens.panelElevated,
          disabledForegroundColor: tokens.textMuted,
          elevation: button.filledElevation,
          shadowColor: resolvedDefinition.primaryColor.withValues(alpha: 0.4),
          padding: EdgeInsets.symmetric(
            horizontal: button.horizontalPadding,
            vertical: button.verticalPadding,
          ),
          textStyle: textTheme.labelLarge?.copyWith(
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
          textStyle: textTheme.labelLarge?.copyWith(
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
          shadowColor: resolvedDefinition.accentColor.withValues(alpha: 0.3),
          padding: EdgeInsets.symmetric(
            horizontal: button.horizontalPadding,
            vertical: button.verticalPadding,
          ),
          textStyle: textTheme.labelLarge?.copyWith(
            fontWeight: button.labelWeight,
            letterSpacing: button.labelLetterSpacing,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(button.cornerRadius),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: resolvedDefinition.primaryColor,
          textStyle: textTheme.labelLarge?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.transparent,
        indicatorColor: resolvedDefinition.primaryColor.withValues(alpha: 0.17),
        labelTextStyle: WidgetStateProperty.resolveWith<TextStyle>((
          Set<WidgetState> states,
        ) {
          final bool selected = states.contains(WidgetState.selected);
          return textTheme.labelMedium!.copyWith(
            color: selected ? tokens.textPrimary : tokens.textMuted,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
            letterSpacing: 0.18,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith<IconThemeData>((
          Set<WidgetState> states,
        ) {
          final bool selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color:
                selected ? resolvedDefinition.primaryColor : tokens.textMuted,
            size: selected ? 24 : 22,
          );
        }),
        surfaceTintColor: Colors.transparent,
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: Colors.transparent,
        indicatorColor: resolvedDefinition.primaryColor.withValues(alpha: 0.16),
        selectedIconTheme: IconThemeData(
          color: resolvedDefinition.primaryColor,
          size: 24,
        ),
        unselectedIconTheme: IconThemeData(color: tokens.textMuted, size: 20),
        selectedLabelTextStyle: textTheme.labelLarge?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w800,
        ),
        unselectedLabelTextStyle: textTheme.labelMedium?.copyWith(
          color: tokens.textMuted,
          fontWeight: FontWeight.w600,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: Color.alphaBlend(
          tokens.panel.withValues(alpha: visuals.glass ? 0.92 : 0.98),
          tokens.background,
        ),
        modalBackgroundColor: Color.alphaBlend(
          tokens.panel.withValues(alpha: visuals.glass ? 0.92 : 0.98),
          tokens.background,
        ),
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(tokens.radiusLarge),
          ),
          side: BorderSide(color: tokens.stroke.withValues(alpha: 0.94)),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: tokens.stroke.withValues(alpha: 0.88),
        thickness: 1,
        space: 1,
      ),
      listTileTheme: ListTileThemeData(
        iconColor: tokens.textMuted,
        textColor: tokens.textPrimary,
        titleTextStyle: textTheme.titleMedium?.copyWith(
          color: tokens.textPrimary,
        ),
        subtitleTextStyle: textTheme.bodySmall?.copyWith(
          color: tokens.textMuted,
        ),
      ),
      tabBarTheme: TabBarThemeData(
        dividerColor: tokens.stroke.withValues(alpha: 0.7),
        indicator: UnderlineTabIndicator(
          borderSide: BorderSide(
            color: resolvedDefinition.primaryColor,
            width: 2.5,
          ),
        ),
        labelColor: tokens.textPrimary,
        unselectedLabelColor: tokens.textMuted,
        labelStyle: textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
        unselectedLabelStyle: textTheme.labelMedium?.copyWith(
          fontWeight: FontWeight.w700,
        ),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: Color.alphaBlend(tokens.panelStrong, tokens.background),
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          border: Border.all(color: tokens.stroke.withValues(alpha: 0.9)),
        ),
        textStyle: textTheme.bodySmall?.copyWith(color: tokens.textPrimary),
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

  static GteThemeVisuals visualsOf(BuildContext context) {
    final GteThemeVisuals? visuals =
        Theme.of(context).extension<GteThemeVisuals>();
    return visuals ?? activeVisuals;
  }

  static GteThemeDefinition definitionOf(BuildContext context) {
    return GteThemeControllerScope.maybeOf(context)?.activeTheme ??
        _activeDefinition;
  }
}

Color _surfaceTint(
  GteThemeTokens tokens,
  GteThemeVisuals visuals,
  double alpha,
) {
  return Color.alphaBlend(
    visuals.heroAccent.withValues(alpha: alpha),
    tokens.panelStrong,
  );
}

Color _surfaceTint(GteThemeTokens tokens, double alpha) {
  return Color.alphaBlend(
    tokens.surfaceHighlight.withValues(alpha: alpha),
    tokens.panelStrong,
  );
}

BoxDecoration gteBackdropDecoration() {
  final GteThemeTokens tokens = GteShellTheme.activeTokens;
  final GteThemeVisuals visuals = GteShellTheme.activeVisuals;
  return BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        tokens.background,
        Color.alphaBlend(
          visuals.ambientPrimary.withValues(alpha: 0.08),
          tokens.backgroundSoft,
        ),
        Color.alphaBlend(
          visuals.ambientSecondary.withValues(alpha: 0.06),
          tokens.backgroundSoft,
        ),
        Color.alphaBlend(
          visuals.ambientTertiary.withValues(alpha: 0.08),
          tokens.panelElevated,
        ),
      ],
      stops: const <double>[0.03, 0.28, 0.68, 1],
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

ImageFilter gtePanelBlur(double sigma) {
  return ImageFilter.blur(sigmaX: sigma, sigmaY: sigma);
}
