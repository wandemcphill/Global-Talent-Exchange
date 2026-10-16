import 'dart:math' as math;

import 'jersey_set_dto.dart';
import 'jersey_variant_dto.dart';

class ClubIdentityValidation {
  static String? homeAwayClashWarning(JerseySetDto jerseys) {
    if (_colorDistance(jerseys.home.primaryColor, jerseys.away.primaryColor) <
        60) {
      return 'Home and away kits are too close in tone. Push the away kit lighter or darker.';
    }
    if (jerseys.home.primaryColor == jerseys.away.primaryColor &&
        jerseys.home.secondaryColor == jerseys.away.secondaryColor &&
        jerseys.home.patternType == jerseys.away.patternType) {
      return 'Home and away kits should never look identical in standings or key moments.';
    }
    return null;
  }

  static List<String> lowContrastWarnings(JerseySetDto jerseys) {
    final List<String> warnings = <String>[];
    for (final JerseyVariantDto variant in jerseys.all) {
      if (_colorDistance(variant.primaryColor, variant.secondaryColor) < 45) {
        warnings.add(
          '${variant.label} kit trim is too close to the shirt body for quick match-readability.',
        );
      } else if (math.max(
            _contrastRatio(variant.primaryColor, variant.secondaryColor),
            _contrastRatio(variant.primaryColor, variant.accentColor),
          ) <
          1.25) {
        warnings.add(
          '${variant.label} kit text and trim need stronger contrast to stay readable on replay cards.',
        );
      }
    }
    return warnings;
  }

  static double _colorDistance(String colorA, String colorB) {
    final List<int> a = _toRgb(colorA);
    final List<int> b = _toRgb(colorB);
    return math.sqrt(
      math.pow(a[0] - b[0], 2) +
          math.pow(a[1] - b[1], 2) +
          math.pow(a[2] - b[2], 2),
    );
  }

  static double _contrastRatio(String colorA, String colorB) {
    final double luminanceA = _relativeLuminance(colorA);
    final double luminanceB = _relativeLuminance(colorB);
    final double lighter = math.max(luminanceA, luminanceB);
    final double darker = math.min(luminanceA, luminanceB);
    return (lighter + 0.05) / (darker + 0.05);
  }

  static double _relativeLuminance(String color) {
    final List<int> rgb = _toRgb(color);
    final List<double> normalized = rgb.map((int value) {
      final double scaled = value / 255;
      if (scaled <= 0.03928) {
        return scaled / 12.92;
      }
      return math.pow((scaled + 0.055) / 1.055, 2.4).toDouble();
    }).toList(growable: false);
    return (0.2126 * normalized[0]) +
        (0.7152 * normalized[1]) +
        (0.0722 * normalized[2]);
  }

  static List<int> _toRgb(String color) {
    final String normalized =
        color.replaceAll('#', '').padLeft(6, '0').substring(0, 6);
    return <int>[
      int.parse(normalized.substring(0, 2), radix: 16),
      int.parse(normalized.substring(2, 4), radix: 16),
      int.parse(normalized.substring(4, 6), radix: 16),
    ];
  }
}
