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

    expect(find.byIcon(Icons.hub_rounded), findsWidgets);
    expect(find.text('84'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('REGEN DNA'), findsWidgets);
    expect(find.text('National Seed'), findsOneWidget);
    expect(find.text('POOL EXCLUSIVE'), findsOneWidget);
    expect(find.text('NG'), findsOneWidget);
  });

  testWidgets('standard player card has real-player market identity', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 430,
            child: GtexPlayerCard(
              name: 'Victor Osimhen',
              position: 'ST',
              clubName: 'Napoli',
              nationality: 'Nigeria',
              countryCode: 'NG',
              priceLabel: 'GTC 90,000,000',
              imageUrl: null,
              gsiLabel: 'GSI 91',
              ratingLabel: '86',
              marketHeatLabel: 'For Sale',
              valueState: GtexValueState.live,
            ),
          ),
        ),
      ),
    );

    expect(find.text('REAL PLAYER'), findsWidgets);
    expect(find.text('SCOUTING PROFILE'), findsOneWidget);
    expect(find.text('For Sale'), findsOneWidget);
    expect(find.byIcon(Icons.badge_rounded), findsOneWidget);
  });

  testWidgets('player card uses micro layout in tight tiles', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 110,
            height: 60,
            child: GtexPlayerCard(
              name: 'Ayo Okafor',
              position: 'ST',
              clubName: 'National rental pool',
              nationality: 'Nigeria',
              priceLabel: 'GTEX 50',
              imageUrl: null,
              gsiLabel: 'GSI 84',
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('Ayo Okafor'), findsOneWidget);
  });
}
