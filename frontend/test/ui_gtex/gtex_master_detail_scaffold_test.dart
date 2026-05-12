import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('GtexMasterDetailScaffold renders desktop panels', (WidgetTester tester) async {
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

  testWidgets('GtexShortlistBasket shows total cost', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexShortlistBasket(
            totalLabel: '₦2,500 GTEX',
            items: const <GtexBasketLineItem>[
              GtexBasketLineItem(
                id: '1',
                title: 'Bukayo Saka',
                subtitle: 'Arsenal • RW',
                priceLabel: '₦2,500',
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Shortlist Basket'), findsOneWidget);
    expect(find.text('₦2,500 GTEX'), findsOneWidget);
    expect(find.text('Bukayo Saka'), findsOneWidget);
  });
}
