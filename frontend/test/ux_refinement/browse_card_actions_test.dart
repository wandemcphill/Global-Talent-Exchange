import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The market browse grid renders the compact player card at every
/// breakpoint. Before this pass the compact variant dropped the buy and
/// shortlist callbacks entirely, so the market had no card-level actions on
/// any screen size.
void main() {
  Widget marketGrid(double width, {required bool withActions}) {
    final int cross = width >= 1100 ? 3 : (width >= 680 ? 2 : 1);
    return MaterialApp(
      home: Scaffold(
        body: GridView.builder(
          padding: const EdgeInsets.all(GtexSpacing.md),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cross,
            crossAxisSpacing: GtexSpacing.sm,
            mainAxisSpacing: GtexSpacing.sm,
            // Mirrors GtexMarketPlayerGrid.
            mainAxisExtent: 132,
          ),
          itemCount: 3,
          itemBuilder:
              (_, __) => GtexPlayerCard(
                name: 'Emmanuel Adebayo-Oluwaseun',
                position: 'ST',
                clubName: 'Real Sporting Clube de Portugal B',
                nationality: 'Nigeria',
                priceLabel: '1,240,000 GTC',
                ratingLabel: '84',
                formResults: const <String>['W', 'W', 'D', 'L', 'W'],
                onTap: () {},
                onAddToShortlist: withActions ? () {} : null,
                onBuyNow: withActions ? () {} : null,
                buyNowLabel: 'Negotiate',
              ),
        ),
      ),
    );
  }

  for (final double width in <double>[360, 414, 700, 900, 1200, 1440]) {
    testWidgets('browse grid exposes card actions at ${width}px', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final List<String> errors = <String>[];
      final void Function(FlutterErrorDetails)? previous = FlutterError.onError;
      FlutterError.onError =
          (FlutterErrorDetails details) =>
              errors.add(details.exceptionAsString());

      await tester.pumpWidget(marketGrid(width, withActions: true));
      await tester.pump();
      FlutterError.onError = previous;

      expect(
        find.text('Negotiate'),
        findsWidgets,
        reason: 'buy action must be reachable at ${width}px',
      );
      expect(
        find.text('Shortlist'),
        findsWidgets,
        reason: 'shortlist action must be reachable at ${width}px',
      );
      expect(
        errors.where((String e) => e.contains('overflow')),
        isEmpty,
        reason: 'browse card must not overflow at ${width}px',
      );
    });
  }

  testWidgets('card with no action callbacks draws no action bar', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(marketGrid(390, withActions: false));
    await tester.pump();

    expect(find.text('Negotiate'), findsNothing);
    expect(find.text('Shortlist'), findsNothing);
  });

  testWidgets('list usage stays a plain row without an action bar', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: <Widget>[
              GtexPlayerCard(
                name: 'Short Name',
                position: 'CM',
                clubName: 'Club',
                nationality: 'NG',
                priceLabel: '10 GTC',
                onAddToShortlist: () {},
                onBuyNow: () {},
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Buy now'), findsNothing);
    expect(find.text('Shortlist'), findsNothing);
  });
}
