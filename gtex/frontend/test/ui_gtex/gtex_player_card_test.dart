import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

Future<void> _pumpTallCard(WidgetTester tester, Widget card) async {
  tester.view.physicalSize = const Size(900, 1400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: SizedBox(width: 430, child: card),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('player card renders an identity plate and live indicators', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
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
    );

    expect(find.byIcon(Icons.hub_rounded), findsWidgets);
    expect(find.text('84'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('REGEN DNA'), findsWidgets);
    expect(find.text('National Seed'), findsOneWidget);
    expect(find.text('POOL EXCLUSIVE'), findsOneWidget);
    // No photograph, so the shared portrait plate stands in - never a drawn
    // face. It carries the position and the country the silhouette used to
    // be overlaid with.
    expect(find.byKey(const Key('gtex-player-portrait-plate')), findsOneWidget);
    expect(find.text('ST / NG'), findsOneWidget);
    expect(
      find.byType(CustomPaint).evaluate().where((Element element) {
        final CustomPaint paint = element.widget as CustomPaint;
        return paint.painter.runtimeType.toString().toLowerCase().contains(
          'silhouette',
        );
      }),
      isEmpty,
      reason: 'GTEX shows a real face or no face - never a drawn one',
    );
  });

  testWidgets('standard player card has real-player market identity', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
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
    );

    expect(find.text('REAL PLAYER'), findsWidgets);
    expect(find.text('SCOUTING PROFILE'), findsOneWidget);
    expect(find.text('For Sale'), findsOneWidget);
    expect(find.byIcon(Icons.badge_rounded), findsOneWidget);
  });

  testWidgets('ownershipLabel surfaces the user stake on full and compact cards', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Victor Osimhen',
        position: 'ST',
        clubName: 'Napoli',
        nationality: 'Nigeria',
        countryCode: 'NG',
        priceLabel: 'GTC 90',
        imageUrl: null,
        ownershipLabel: 'You own 2.5 shares',
      ),
    );
    expect(find.text('You own 2.5 shares'), findsOneWidget);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 430,
            height: 84,
            child: GtexPlayerCard(
              name: 'Victor Osimhen',
              position: 'ST',
              clubName: 'Napoli',
              nationality: 'Nigeria',
              priceLabel: 'GTC 90',
              imageUrl: null,
              scale: GtexPlayerCardScale.compact,
              ownershipLabel: 'You own 2.5 shares',
            ),
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    expect(find.text('YOU OWN 2.5 SHARES'), findsOneWidget);
  });

  testWidgets('card without ownershipLabel shows no ownership text', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Victor Osimhen',
        position: 'ST',
        clubName: 'Napoli',
        nationality: 'Nigeria',
        priceLabel: 'GTC 90',
        imageUrl: null,
      ),
    );
    expect(find.textContaining('You own'), findsNothing);
  });

  testWidgets('bio rail always shows height and foot slots', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Victor Osimhen',
        position: 'ST',
        clubName: 'Napoli',
        nationality: 'Nigeria',
        priceLabel: 'GTC 90',
        heightLabel: '185 cm',
        footLabel: 'Either',
        secondaryPositions: <String>['CF', 'LW'],
        // Real-player cards must ignore wage even if a caller passes it.
        salaryLabel: 'EUR 12.0M / yr',
        contractLabel: '3 yrs left',
      ),
    );

    expect(find.text('HEIGHT '), findsOneWidget);
    expect(find.text('185 cm'), findsOneWidget);
    expect(find.text('FOOT '), findsOneWidget);
    expect(find.text('Either'), findsOneWidget);
    expect(find.text('CF'), findsOneWidget);
    expect(find.text('LW'), findsOneWidget);
    expect(find.text('EUR 12.0M / yr'), findsNothing);
    expect(find.text('3 yrs left'), findsNothing);
  });

  testWidgets('regen cards surface salary and contract clocks', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Ayo Dynasty',
        position: 'CAM',
        clubName: 'GTEX Academy',
        nationality: 'Nigeria',
        priceLabel: 'GTC 1',
        cardVariant: GtexPlayerCardVariant.legendary,
        salaryLabel: 'FC 240K / yr',
        contractLabel: '2 yrs left',
      ),
    );

    expect(find.text('FC 240K / yr'), findsOneWidget);
    expect(find.text('2 yrs left'), findsOneWidget);
  });

  testWidgets('full card face shows OVR, GSI and PAC-PHY abilities', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Victor Osimhen',
        position: 'ST',
        clubName: 'Napoli',
        nationality: 'Nigeria',
        countryCode: 'NG',
        priceLabel: 'GTC 90',
        gsiLabel: 'GSI 91',
        overallLabel: '90',
        abilities: <String, int>{
          'PAC': 92,
          'SHO': 88,
          'PAS': 71,
          'DRI': 84,
          'DEF': 42,
          'PHY': 86,
        },
      ),
    );

    expect(find.text('OVR'), findsOneWidget);
    expect(find.text('90'), findsWidgets);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('91'), findsOneWidget);
    expect(find.byKey(const Key('gtex-player-ability-plate')), findsOneWidget);
    expect(find.text('PAC'), findsOneWidget);
    expect(find.text('SHO'), findsOneWidget);
    expect(find.text('PHY'), findsOneWidget);
    expect(find.text('92'), findsOneWidget);
    expect(find.byKey(const Key('gtex-player-portrait-plate')), findsOneWidget);
  });

  testWidgets('legendary regen card shows 1 OF 1 premium frame badge', (
    WidgetTester tester,
  ) async {
    await _pumpTallCard(
      tester,
      const GtexPlayerCard(
        name: 'Ayo Dynasty',
        position: 'CAM',
        clubName: 'GTEX Academy',
        nationality: 'Nigeria',
        priceLabel: 'GTC 1',
        cardVariant: GtexPlayerCardVariant.legendary,
        rarityLabel: 'Dynasty',
      ),
    );

    expect(find.text('REGEN DNA'), findsWidgets);
    expect(find.text('1 OF 1'), findsOneWidget);
    expect(find.text('Dynasty'), findsOneWidget);
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
