import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('GtexMasterDetailScaffold renders desktop panels', (
    WidgetTester tester,
  ) async {
    // The scaffold sizes itself from the box it is handed, not from a
    // MediaQuery that may describe a much larger window, so the harness has
    // to hand it a real desktop-width box.
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: Size(1440, 900)),
          child: Directionality(
            textDirection: TextDirection.ltr,
            child: GtexMasterDetailScaffold(
              title: 'Player Market',
              subtitle: 'Country -> League -> Division -> Club',
              leftPanel: Text('Left list'),
              detail: Text('Main detail'),
              rightPanel: Text('Basket'),
            ),
          ),
        ),
      ),
    );

    expect(find.text('Player Market'), findsOneWidget);
    expect(find.text('Left list'), findsOneWidget);
    expect(find.text('Main detail'), findsOneWidget);
    expect(find.text('Basket'), findsOneWidget);
  });

  testWidgets('GtexShortlistBasket shows total cost and wallet context', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexShortlistBasket(
            totalLabel: '2,500 GTC',
            balanceLabel: '4,000 GTC',
            remainingLabel: '1,500 GTC',
            items: const <GtexBasketLineItem>[
              GtexBasketLineItem(
                id: '1',
                title: 'Bukayo Saka',
                subtitle: 'Arsenal - RW',
                priceLabel: '2,500 GTC',
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Shortlist Basket'), findsOneWidget);
    expect(find.text('2,500 GTC'), findsWidgets);
    expect(
      find.text('Wallet GTC only - KoraPay/manual top-up if balance is short'),
      findsOneWidget,
    );
    expect(find.text('4,000 GTC'), findsOneWidget);
    expect(find.text('1,500 GTC'), findsOneWidget);
    expect(find.text('Bukayo Saka'), findsOneWidget);
  });

  testWidgets('GtexShortlistBasket blocks checkout when GTC balance is short', (
    WidgetTester tester,
  ) async {
    bool checkedOut = false;
    bool openedTopUp = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexShortlistBasket(
            totalLabel: '120 GTC',
            balanceLabel: '80 GTC',
            remainingLabel: '-40 GTC',
            insufficientLabel: 'You need 40 more GTC before checkout.',
            onTopUpWallet: () {
              openedTopUp = true;
            },
            onCheckout: () {
              checkedOut = true;
            },
            items: const <GtexBasketLineItem>[
              GtexBasketLineItem(
                id: '1',
                title: 'Liam Carver',
                subtitle: 'Regen DNA - CAM',
                priceLabel: '120 GTC',
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('You need 40 more GTC before checkout.'), findsOneWidget);

    await tester.tap(find.text('Continue to payment'));
    await tester.pump();
    expect(checkedOut, isFalse);

    await tester.tap(find.text('Top up'));
    await tester.pump();
    expect(openedTopUp, isTrue);
  });
}
