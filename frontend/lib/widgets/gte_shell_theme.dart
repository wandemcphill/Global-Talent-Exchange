import 'package:flutter/material.dart';

class GteShellTheme {
  static const Color background = Color(0xFF070B12);
  static const Color panel = Color(0xFF101827);
  static const Color panelStrong = Color(0xFF16243A);
  static const Color stroke = Color(0xFF2A3A56);
  static const Color accent = Color(0xFF7DE2D1);
  static const Color accentWarm = Color(0xFFFFC76B);
  static const Color textPrimary = Color(0xFFF4F7FB);
  static const Color textMuted = Color(0xFF9EADC8);
  static const Color positive = Color(0xFF73F7AF);
  static const Color negative = Color(0xFFFF8B8B);

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
          fontWeight: FontWeight.w700,
          letterSpacing: -1.4,
          color: textPrimary,
        ),
        headlineSmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.8,
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
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyLarge: TextStyle(
          fontSize: 15,
          height: 1.45,
          color: textPrimary,
        ),
        bodyMedium: TextStyle(
          fontSize: 13,
          height: 1.45,
          color: textMuted,
        ),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
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
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
      ),
      navigationBarTheme: const NavigationBarThemeData(
        backgroundColor: panel,
        indicatorColor: Color(0x2E7DE2D1),
        labelTextStyle: WidgetStatePropertyAll<TextStyle>(
          TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}

BoxDecoration gteBackdropDecoration() {
  return const BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[
        Color(0xFF09111D),
        Color(0xFF070B12),
        Color(0xFF0D1724),
      ],
    ),
  );
}
