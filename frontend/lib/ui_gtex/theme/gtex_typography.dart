import 'dart:ui';

import 'package:flutter/material.dart';

class GtexText {
  const GtexText._();

  static const String displayFamily = 'BarlowCondensed';
  static const String monoFamily = 'DMMono';
  static const String bodyFamily = 'Inter';

  static const double maxDecorativeTextScaleFactor = 1.3;
  static const double maxSupportedTextScaleFactor = 2.0;

  static const TextStyle display2XL = TextStyle(
    fontFamily: displayFamily,
    fontSize: 56,
    fontWeight: FontWeight.w700,
  );
  static const TextStyle displayXL = TextStyle(
    fontFamily: displayFamily,
    fontSize: 40,
    fontWeight: FontWeight.w700,
  );
  static const TextStyle displayLG = TextStyle(
    fontFamily: displayFamily,
    fontSize: 32,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle displayMD = TextStyle(
    fontFamily: displayFamily,
    fontSize: 24,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle displaySM = TextStyle(
    fontFamily: displayFamily,
    fontSize: 18,
    fontWeight: FontWeight.w500,
  );

  /// Canonical Document F4 typography tokens (`display.l`, `display.m`,
  /// `title.l`, `title.m`, `title.s`, `body`, `body.s`, `label`, `numeric.l/m/s`).
  static const TextStyle displayL = TextStyle(
    fontFamily: displayFamily,
    fontSize: 40,
    height: 44 / 40,
    fontWeight: FontWeight.w700,
  );
  static const TextStyle displayM = TextStyle(
    fontFamily: displayFamily,
    fontSize: 28,
    height: 32 / 28,
    fontWeight: FontWeight.w700,
  );
  static const TextStyle titleL = TextStyle(
    fontFamily: displayFamily,
    fontSize: 22,
    height: 26 / 22,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle titleM = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 17,
    height: 22 / 17,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle titleS = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 15,
    height: 20 / 15,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle body = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 14,
    height: 20 / 14,
    fontWeight: FontWeight.w400,
  );
  static const TextStyle bodyS = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 13,
    height: 18 / 13,
    fontWeight: FontWeight.w400,
  );
  static const TextStyle label = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.4,
  );
  static const TextStyle numericL = TextStyle(
    fontFamily: monoFamily,
    fontSize: 20,
    height: 24 / 20,
    fontWeight: FontWeight.w500,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
  static const TextStyle numericM = TextStyle(
    fontFamily: monoFamily,
    fontSize: 15,
    height: 20 / 15,
    fontWeight: FontWeight.w500,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
  static const TextStyle numericS = TextStyle(
    fontFamily: monoFamily,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w500,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );

  static const TextStyle bodyLG = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.6,
  );
  static const TextStyle bodyMD = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.5,
  );
  static const TextStyle bodySM = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.4,
  );

  static const TextStyle labelLG = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 14,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle labelMD = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 12,
    fontWeight: FontWeight.w600,
  );
  static const TextStyle labelSM = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 11,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.4,
  );

  static const TextStyle monoXL = TextStyle(
    fontFamily: monoFamily,
    fontSize: 28,
    fontWeight: FontWeight.w500,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
  static const TextStyle monoLG = TextStyle(
    fontFamily: monoFamily,
    fontSize: 20,
    fontWeight: FontWeight.w400,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
  static const TextStyle monoMD = TextStyle(
    fontFamily: monoFamily,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
  static const TextStyle monoSM = TextStyle(
    fontFamily: monoFamily,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
}
