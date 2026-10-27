import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/theme/gte_theme_controller.dart';
import 'package:gte_frontend/theme/gte_theme_metadata.dart';
import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('Phase A2 — GTEX Navy tokens & reversible theme migration', () {
    test('GtexNavyColors and GtexColors.navy expose canonical Document F3 hex palette', () {
      expect(GtexNavyColors.bgBase, const Color(0xFF0B1626));
      expect(GtexNavyColors.bgRaised, const Color(0xFF13233A));
      expect(GtexNavyColors.bgOverlay, const Color(0xFF1A2E4A));
      expect(GtexNavyColors.bgInset, const Color(0xFF081120));
      expect(GtexNavyColors.lineSubtle, const Color(0xFF22385A));
      expect(GtexNavyColors.lineStrong, const Color(0xFF2F4C75));
      expect(GtexNavyColors.textPrimary, const Color(0xFFF2F4F8));
      expect(GtexNavyColors.textSecondary, const Color(0xFF9AA7BD));
      expect(GtexNavyColors.textTertiary, const Color(0xFF6B7A93));
      expect(GtexNavyColors.gold500, const Color(0xFFD4AF37));
      expect(GtexNavyColors.gold300, const Color(0xFFE8C766));
      expect(GtexNavyColors.gold700, const Color(0xFFA8862A));
      expect(GtexNavyColors.info, const Color(0xFF5B8DEF));
      expect(GtexNavyColors.success, const Color(0xFF3DBE8B));
      expect(GtexNavyColors.warning, const Color(0xFFF0A93B));
      expect(GtexNavyColors.danger, const Color(0xFFE5534B));
      expect(GtexNavyColors.live, const Color(0xFFFF5B3A));

      expect(GtexColors.navy.bgBase, GtexNavyColors.bgBase);
      expect(GtexColors.navy.bgRaised, GtexNavyColors.bgRaised);
      expect(GtexColors.navy.bgOverlay, GtexNavyColors.bgOverlay);
      expect(GtexColors.navy.bgInset, GtexNavyColors.bgInset);
      expect(GtexColors.navy.lineSubtle, GtexNavyColors.lineSubtle);
      expect(GtexColors.navy.lineStrong, GtexNavyColors.lineStrong);
      expect(GtexColors.navy.gold500, GtexNavyColors.gold500);
      expect(GtexColors.navy.coinGtc, GtexNavyColors.info);
      expect(GtexColors.navy.coinFnc, GtexNavyColors.gold300);
    });

    test('GteThemeRegistry.gtexNavy satisfies WCAG 2.x AA contrast thresholds', () {
      const GteThemeDefinition navy = GteThemeRegistry.gtexNavy;

      expect(
        _contrast(navy.tokens.textPrimary, navy.tokens.background),
        greaterThanOrEqualTo(14.0),
      );
      expect(
        _contrast(navy.tokens.textPrimary, navy.tokens.panel),
        greaterThanOrEqualTo(11.0),
      );
      expect(
        _contrast(navy.tokens.textMuted, navy.tokens.background),
        greaterThanOrEqualTo(6.5),
      );
      expect(
        _contrast(navy.tokens.textMuted, navy.tokens.panel),
        greaterThanOrEqualTo(5.5),
      );
      expect(
        _contrast(navy.onPrimaryColor, navy.primaryColor),
        greaterThanOrEqualTo(7.5),
      );
      expect(
        _contrast(navy.onSecondaryColor, navy.secondaryColor),
        greaterThanOrEqualTo(9.0),
      );
      expect(
        _contrast(navy.onAccentColor, navy.accentColor),
        greaterThanOrEqualTo(7.0),
      );
    });

    test('GteThemeController reversibly toggles between GTEX Navy and Founders Black fallback', () async {
      final GteThemeController controller = GteThemeController();

      expect(controller.useGtexNavyShell, isFalse);
      expect(controller.activeTheme.metadata.label, 'Founders Black');

      controller.setUseGtexNavyShell(true);
      expect(controller.useGtexNavyShell, isTrue);
      expect(controller.activeTheme.metadata.label, 'GTEX Navy');
      expect(controller.activeTheme.tokens.background, GtexNavyColors.bgBase);
      expect(controller.activeTheme.tokens.accent, GtexNavyColors.gold500);

      // Reversible rollback to Founders Black.
      controller.setUseGtexNavyShell(false);
      expect(controller.useGtexNavyShell, isFalse);
      expect(
        controller.activeTheme,
        same(GteThemeRegistry.pitchBlackStadiumFallback),
      );

      // Selecting a legacy theme also resets the override cleanly.
      controller.setUseGtexNavyShell(true);
      await controller.selectTheme(GteThemeId.sandHillGold);
      expect(controller.useGtexNavyShell, isFalse);
      expect(controller.activeThemeId, GteThemeId.sandHillGold);
    });

    testWidgets('GteShellTheme.build(GteThemeRegistry.gtexNavy) renders and resolves GtexColors.of(context)', (
      WidgetTester tester,
    ) async {
      late GtexColorTokens resolvedColors;
      late Duration resolvedMotion;

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(GteThemeRegistry.gtexNavy),
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: Builder(
              builder: (BuildContext context) {
                resolvedColors = GtexColors.of(context);
                resolvedMotion = GtexMotion.effectiveDuration(
                  context,
                  GtexMotion.enterExitDuration,
                );
                return const Scaffold(body: Text('GTEX Navy Shell'));
              },
            ),
          ),
        ),
      );

      expect(find.text('GTEX Navy Shell'), findsOneWidget);
      expect(resolvedColors.bgBase, GtexNavyColors.bgBase);
      expect(resolvedColors.gold500, GtexNavyColors.gold500);
      expect(resolvedMotion, Duration.zero);
    });

    test('Document F4 & F5 typography, spacing, radius, and grid tokens are defined', () {
      expect(GtexText.displayL.fontSize, 40);
      expect(GtexText.displayM.fontSize, 28);
      expect(GtexText.titleL.fontSize, 22);
      expect(GtexText.titleM.fontSize, 17);
      expect(GtexText.titleS.fontSize, 15);
      expect(GtexText.body.fontSize, 14);
      expect(GtexText.bodyS.fontSize, 13);
      expect(GtexText.label.fontSize, 12);
      expect(GtexText.numericL.fontSize, 20);
      expect(GtexText.numericM.fontSize, 15);
      expect(GtexText.numericS.fontSize, 12);

      expect(GtexRadius.chip, 6);
      expect(GtexRadius.card, 10);
      expect(GtexRadius.sheet, 16);
      expect(GtexRadius.pill, 999);

      expect(GtexSpacing.minTouchTarget, 48);
      expect(GtexSpacing.listRowMinHeight, 56);
      expect(GtexSpacing.screenMarginForWidth(390), 16);
      expect(GtexSpacing.screenMarginForWidth(768), 24);
      expect(GtexSpacing.screenMarginForWidth(1280), 32);

      expect(GtexGrid.columnsForWidth(390), 4);
      expect(GtexGrid.columnsForWidth(768), 8);
      expect(GtexGrid.columnsForWidth(1280), 12);
    });

    test('CI guard: new Phase A2/A3 shell modules contain no hardcoded Color(0x...) outside ui_gtex/theme', () {
      final List<String> guardedPaths = <String>[
        'lib/ui_gtex/theme/gtex_motion.dart',
        'lib/features/navigation/model/gtex_route_alias_table.dart',
        'lib/features/navigation/model/gtex_shell_navigation_model.dart',
        'lib/features/navigation/model/gtex_deep_link_resolver.dart',
      ];
      final RegExp hexColorPattern = RegExp(r'Color\(\s*0x[0-9A-Fa-f]+');

      for (final String relativePath in guardedPaths) {
        final String source = File(relativePath).readAsStringSync();
        expect(
          hexColorPattern.hasMatch(source),
          isFalse,
          reason: '$relativePath must not contain raw Color(0x...) literals',
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
