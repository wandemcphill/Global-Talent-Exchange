import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('coin chips keep GTEX Coin and Fan Coin visually distinct', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(GteThemeRegistry.gtexDaylight),
        home: const Scaffold(
          body: Row(
            children: <Widget>[
              GtexCoinChip(amount: '1,240.00'),
              SizedBox(width: 12),
              FanCoinChip(amount: '3,400'),
            ],
          ),
        ),
      ),
    );

    expect(find.text('1,240.00 GTC'), findsOneWidget);
    expect(find.text('3,400 FNC'), findsOneWidget);
    expect(find.byType(GtexCoinIcon), findsNWidgets(2));
    expect(GtexColors.coinGtex, isNot(GtexColors.coinFan));
  });

  testWidgets(
    'skeleton, error banner, and blocked state render truthful states',
    (WidgetTester tester) async {
      int retries = 0;
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: Column(
              children: <Widget>[
                const GtexSkeleton(width: 140, height: 18),
                GtexErrorBanner(
                  message: 'Wallet authority returned 503.',
                  onRetry: () => retries += 1,
                ),
                const GtexBlockedState(
                  severity: GtexBlockedSeverity.locked,
                  reason: 'Create a club before entering this competition.',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('gtex-skeleton-box')), findsOneWidget);
      expect(find.text('Wallet authority returned 503.'), findsOneWidget);
      expect(
        find.text('Create a club before entering this competition.'),
        findsOneWidget,
      );

      await tester.tap(find.text('Try again'));
      expect(retries, 1);
    },
  );

  testWidgets('green pulse dot respects reduced motion', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: Scaffold(body: GreenPulseDot()),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.byType(GreenPulseDot), findsOneWidget);
  });
}
