import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('player card renders football silhouette and live indicators', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 430,
            child: GtexPlayerCard(
              name: 'Ayo Okafor',
              position: 'ST',
              clubName: 'National rental pool',
              nationality: 'Nigeria',
              countryCode: 'NG',
              priceLabel: 'GTC 50',
              imageUrl: null,
              gsiLabel: 'GSI 84',
              gsiTierLabel: 'High-grade GSI',
              gsiTrendLabel: 'Up',
              rarityLabel: 'National Seed',
              marketHeatLabel: 'Hot demand',
              demandLabel: 'Pool exclusive',
              chemistryLinks: <String>['Pre-seeded regen', 'approved'],
              cardVariant: GtexPlayerCardVariant.nationalSeed,
              portraitMissingReason: 'asset pending',
            ),
          ),
        ),
      ),
    );

    expect(find.byIcon(Icons.person_rounded), findsOneWidget);
    expect(find.text('84'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('National Seed'), findsOneWidget);
    expect(find.text('Pool exclusive'), findsOneWidget);
    expect(find.text('NG'), findsOneWidget);
  });
}
