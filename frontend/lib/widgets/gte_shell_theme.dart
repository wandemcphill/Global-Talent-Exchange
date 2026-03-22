import 'package:flutter/material.dart';

class GteShellTheme {
  static const Color background = Color(0xFF03060C);
  static const Color backgroundSoft = Color(0xFF09111B);
  static const Color panel = Color(0xFF0C1521);
  static const Color panelStrong = Color(0xFF122235);
  static const Color panelElevated = Color(0xFF152B43);
  static const Color stroke = Color(0xFF243654);
  static const Color accent = Color(0xFF72F0D8);
  static const Color accentWarm = Color(0xFFFFC56A);
  static const Color accentArena = Color(0xFFB26DFF);
  static const Color accentCapital = Color(0xFFFFD66B);
  static const Color accentCommunity = Color(0xFF5FE3A1);
  static const Color accentAdmin = Color(0xFFFF8F6B);
  static const Color textPrimary = Color(0xFFF4F7FB);
  static const Color textMuted = Color(0xFF9EADC8);
  static const Color positive = Color(0xFF73F7AF);
  static const Color negative = Color(0xFFFF8B8B);
  static const Color warning = Color(0xFFFFC56A);

  static ThemeData build() {
    const ColorScheme colorScheme = ColorScheme.dark(
      primary: accent,
      secondary: accentWarm,
      surface: panel,
      onPrimary: background,
      onSecondary: background,
      onSurface: textPrimary,
      error: negative,
      onError: textPrimary,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: background,
      cardColor: panel,
      dividerColor: stroke,
      textTheme: const TextTheme(
        displaySmall: TextStyle(
          fontSize: 34,
          fontWeight: FontWeight.w800,
          letterSpacing: -1.5,
          color: textPrimary,
          height: 1.04,
        ),
        headlineSmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.9,
          color: textPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          color: textPrimary,
        ),
        titleMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
        bodyLarge: TextStyle(
          fontSize: 15,
          height: 1.55,
          color: textPrimary,
        ),
        bodyMedium: TextStyle(
          fontSize: 13,
          height: 1.5,
          color: textMuted,
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          height: 1.4,
          color: textMuted,
        ),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.25,
          color: textPrimary,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        foregroundColor: textPrimary,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: panelStrong,
        side: const BorderSide(color: stroke),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
        labelStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.045),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: const BorderSide(color: stroke),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: const BorderSide(color: stroke),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: const BorderSide(color: accent, width: 1.4),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          side: const BorderSide(color: stroke),
        ),
      ),
      navigationBarTheme: const NavigationBarThemeData(
        backgroundColor: panel,
        indicatorColor: Color(0x2E7DE2D1),
        labelTextStyle: WidgetStatePropertyAll<TextStyle>(
          TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      dividerTheme: const DividerThemeData(color: stroke, thickness: 1, space: 1),
    );
  }
}

BoxDecoration gteBackdropDecoration() {
  return const BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        Color(0xFF03060C),
        Color(0xFF07101A),
        Color(0xFF0D1725),
        Color(0xFF152638),
      ],
      stops: <double>[0.02, 0.28, 0.68, 1],
    ),
  );
}
