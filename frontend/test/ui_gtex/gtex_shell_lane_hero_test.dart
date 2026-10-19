import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('shell lane hero paints floodlit ownership masthead', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: GtexShellLaneHero(
                eyebrow: 'Club ownership',
                identity: 'Lagos Lions',
                title: 'Lagos Lions',
                summary: 'Decisions and capital.',
                statusLabel: 'OWNER',
                status: GtexCommandStatus.active,
                metrics: <GtexCommandMetric>[
                  GtexCommandMetric(
                    label: 'Capital',
                    value: '50 GTX',
                    detail: 'Wallet',
                    accent: GtexFloodlit.gold,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('gtex-shell-lane-hero')), findsOneWidget);
    expect(find.text('Lagos Lions'), findsWidgets);
    expect(find.textContaining('CLUB OWNERSHIP'), findsOneWidget);
  });

  testWidgets('compact strip keeps a thin ownership banner', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexShellLaneHero.compactStrip(
            eyebrow: 'Capital',
            title: 'Your football capital',
            summary: 'Balances and payouts.',
          ),
        ),
      ),
    );

    expect(
      find.byKey(const Key('gtex-shell-lane-hero-compact')),
      findsOneWidget,
    );
    expect(find.text('Your football capital'), findsOneWidget);
  });
}
