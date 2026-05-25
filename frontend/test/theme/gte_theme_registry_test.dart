import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/theme/gte_theme_registry.dart';

void main() {
  group('GteThemeRegistry', () {
    test('registers the six production themes', () {
      expect(
        GteThemeRegistry.themes.map(
          (GteThemeDefinition theme) => theme.metadata.label,
        ),
        orderedEquals(<String>[
          'Founders Black',
          'Palo Alto Glass',
          'Sand Hill Gold',
          'Menlo Night Blue',
          'Ultra Red',
          'Matchday Light',
        ]),
      );
    });

    test(
      'exposes required palette keys, typography scale, visuals, and usage guidance',
      () {
        for (final GteThemeDefinition definition in GteThemeRegistry.themes) {
          expect(
            definition.colorHexCodes.keys,
            containsAll(<String>[
              'primary',
              'secondary',
              'background',
              'surface',
              'accent',
            ]),
          );
          expect(
            definition.typographyScale.keys,
            containsAll(<String>[
              'display',
              'headline',
              'title',
              'body',
              'caption',
              'label',
            ]),
          );
          expect(definition.visuals.chartPalette, hasLength(5));
          expect(definition.visuals.shellStyle, isNotEmpty);
          expect(definition.usage.feed, isNotEmpty);
          expect(definition.usage.dashboard, isNotEmpty);
          expect(definition.usage.profile, isNotEmpty);
          expect(definition.usage.accessibility, isNotEmpty);
        }
      },
    );

    test('meets AA contrast for primary text and button foregrounds', () {
      for (final GteThemeDefinition definition in GteThemeRegistry.themes) {
        expect(
          _contrast(
            definition.tokens.textPrimary,
            definition.tokens.background,
          ),
          greaterThanOrEqualTo(4.5),
          reason: '${definition.metadata.label} textPrimary vs background',
        );
        expect(
          _contrast(definition.tokens.textPrimary, definition.tokens.panel),
          greaterThanOrEqualTo(4.5),
          reason: '${definition.metadata.label} textPrimary vs surface',
        );
        expect(
          _contrast(definition.onPrimaryColor, definition.primaryColor),
          greaterThanOrEqualTo(4.5),
          reason: '${definition.metadata.label} onPrimary vs primary',
        );
        expect(
          _contrast(definition.onSecondaryColor, definition.secondaryColor),
          greaterThanOrEqualTo(4.5),
          reason: '${definition.metadata.label} onSecondary vs secondary',
        );
        expect(
          _contrast(definition.onAccentColor, definition.accentColor),
          greaterThanOrEqualTo(4.5),
          reason: '${definition.metadata.label} onAccent vs accent',
        );
      }
    });
  });
}

double _contrast(Color foreground, Color background) {
  final double first = foreground.computeLuminance();
  final double second = background.computeLuminance();
  final double lighter = math.max(first, second);
  final double darker = math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}
