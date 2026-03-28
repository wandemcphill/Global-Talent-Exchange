import 'dart:ui';

import 'package:flutter/material.dart';

@immutable
class GteThemeTypography {
  const GteThemeTypography({
    required this.styleName,
    required this.displaySize,
    required this.displayWeight,
    required this.displayLetterSpacing,
    required this.displayHeight,
    required this.headlineSize,
    required this.headlineWeight,
    required this.headlineLetterSpacing,
    required this.titleSize,
    required this.titleWeight,
    required this.titleLetterSpacing,
    required this.bodySize,
    required this.bodyWeight,
    required this.bodyHeight,
    required this.bodyLetterSpacing,
    required this.captionSize,
    required this.captionLetterSpacing,
    required this.labelSize,
    required this.labelWeight,
    required this.labelLetterSpacing,
  });

  final String styleName;
  final double displaySize;
  final FontWeight displayWeight;
  final double displayLetterSpacing;
  final double displayHeight;
  final double headlineSize;
  final FontWeight headlineWeight;
  final double headlineLetterSpacing;
  final double titleSize;
  final FontWeight titleWeight;
  final double titleLetterSpacing;
  final double bodySize;
  final FontWeight bodyWeight;
  final double bodyHeight;
  final double bodyLetterSpacing;
  final double captionSize;
  final double captionLetterSpacing;
  final double labelSize;
  final FontWeight labelWeight;
  final double labelLetterSpacing;

  Map<String, double> get scale => <String, double>{
    'display': displaySize,
    'headline': headlineSize,
    'title': titleSize,
    'body': bodySize,
    'caption': captionSize,
    'label': labelSize,
  };

  TextTheme buildTextTheme({required Color primary, required Color muted}) {
    final TextStyle displayBase = TextStyle(
      fontSize: displaySize,
      fontWeight: displayWeight,
      letterSpacing: displayLetterSpacing,
      height: displayHeight,
      color: primary,
    );
    final TextStyle headlineBase = TextStyle(
      fontSize: headlineSize,
      fontWeight: headlineWeight,
      letterSpacing: headlineLetterSpacing,
      color: primary,
    );
    final TextStyle titleBase = TextStyle(
      fontSize: titleSize,
      fontWeight: titleWeight,
      letterSpacing: titleLetterSpacing,
      color: primary,
    );
    final TextStyle bodyBase = TextStyle(
      fontSize: bodySize,
      fontWeight: bodyWeight,
      letterSpacing: bodyLetterSpacing,
      height: bodyHeight,
      color: primary,
    );
    final TextStyle captionBase = TextStyle(
      fontSize: captionSize,
      letterSpacing: captionLetterSpacing,
      height: bodyHeight - 0.08,
      color: muted,
    );
    final TextStyle labelBase = TextStyle(
      fontSize: labelSize,
      fontWeight: labelWeight,
      letterSpacing: labelLetterSpacing,
      color: primary,
    );

    return TextTheme(
      displayLarge: displayBase.copyWith(
        fontSize: displaySize + 6,
        letterSpacing: displayLetterSpacing - 0.2,
      ),
      displayMedium: displayBase.copyWith(fontSize: displaySize + 2),
      displaySmall: displayBase,
      headlineMedium: headlineBase.copyWith(fontSize: headlineSize + 3),
      headlineSmall: headlineBase,
      titleLarge: titleBase.copyWith(fontSize: titleSize + 1),
      titleMedium: titleBase,
      bodyLarge: bodyBase.copyWith(fontSize: bodySize + 1),
      bodyMedium: bodyBase.copyWith(color: muted),
      bodySmall: captionBase,
      labelLarge: labelBase,
      labelMedium: labelBase.copyWith(fontSize: labelSize - 1),
    );
  }
}

@immutable
class GteThemeButtonSpec {
  const GteThemeButtonSpec({
    required this.styleName,
    required this.cornerRadius,
    required this.strokeWidth,
    required this.horizontalPadding,
    required this.verticalPadding,
    required this.filledElevation,
    required this.labelWeight,
    required this.labelLetterSpacing,
  });

  final String styleName;
  final double cornerRadius;
  final double strokeWidth;
  final double horizontalPadding;
  final double verticalPadding;
  final double filledElevation;
  final FontWeight labelWeight;
  final double labelLetterSpacing;
}

@immutable
class GteThemeMotion extends ThemeExtension<GteThemeMotion> {
  const GteThemeMotion({
    required this.feel,
    required this.fast,
    required this.medium,
    required this.slow,
    required this.emphasizedCurve,
    required this.standardCurve,
  });

  final String feel;
  final Duration fast;
  final Duration medium;
  final Duration slow;
  final Curve emphasizedCurve;
  final Curve standardCurve;

  @override
  GteThemeMotion copyWith({
    String? feel,
    Duration? fast,
    Duration? medium,
    Duration? slow,
    Curve? emphasizedCurve,
    Curve? standardCurve,
  }) {
    return GteThemeMotion(
      feel: feel ?? this.feel,
      fast: fast ?? this.fast,
      medium: medium ?? this.medium,
      slow: slow ?? this.slow,
      emphasizedCurve: emphasizedCurve ?? this.emphasizedCurve,
      standardCurve: standardCurve ?? this.standardCurve,
    );
  }

  @override
  GteThemeMotion lerp(ThemeExtension<GteThemeMotion>? other, double t) {
    if (other is! GteThemeMotion) {
      return this;
    }
    return GteThemeMotion(
      feel: t < 0.5 ? feel : other.feel,
      fast: Duration(
        microseconds:
            (lerpDouble(
                      fast.inMicroseconds.toDouble(),
                      other.fast.inMicroseconds.toDouble(),
                      t,
                    ) ??
                    fast.inMicroseconds)
                .round(),
      ),
      medium: Duration(
        microseconds:
            (lerpDouble(
                      medium.inMicroseconds.toDouble(),
                      other.medium.inMicroseconds.toDouble(),
                      t,
                    ) ??
                    medium.inMicroseconds)
                .round(),
      ),
      slow: Duration(
        microseconds:
            (lerpDouble(
                      slow.inMicroseconds.toDouble(),
                      other.slow.inMicroseconds.toDouble(),
                      t,
                    ) ??
                    slow.inMicroseconds)
                .round(),
      ),
      emphasizedCurve: t < 0.5 ? emphasizedCurve : other.emphasizedCurve,
      standardCurve: t < 0.5 ? standardCurve : other.standardCurve,
    );
  }
}

@immutable
class GteThemeUsageGuidance {
  const GteThemeUsageGuidance({
    required this.feed,
    required this.dashboard,
    required this.profile,
    required this.accessibility,
  });

  final String feed;
  final String dashboard;
  final String profile;
  final String accessibility;
}
