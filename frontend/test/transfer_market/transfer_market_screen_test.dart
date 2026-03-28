import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/transfer_market/transfer_market_screen.dart';

void main() {
  testWidgets('shows wallet flows and buys player shares', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: TransferMarketScreen()),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 600));

    expect(find.text('Transfer Market'), findsOneWidget);
    expect(find.text('Wallet Dashboard'), findsOneWidget);
    expect(find.byKey(const Key('wallet-action-deposit')), findsOneWidget);
    expect(find.byKey(const Key('trading-card-market-mbappe')), findsOneWidget);

    await tester.tap(find.byKey(const Key('trading-filter-defenders')));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.byKey(const Key('trading-card-market-saliba')), findsOneWidget);
    expect(find.byKey(const Key('trading-card-market-mbappe')), findsNothing);

    await tester.tap(find.byKey(const Key('trading-filter-all')));
    await tester.pump(const Duration(milliseconds: 400));

    await tester.tap(find.byKey(const Key('wallet-action-deposit')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byKey(const Key('deposit-flow-sheet')), findsOneWidget);
    expect(find.text('Choose method'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('sheet-close')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.byKey(const Key('sheet-close')));
    await tester.pump(const Duration(milliseconds: 500));

    await tester.ensureVisible(
      find.byKey(const Key('trading-card-market-palmer')),
    );
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.byKey(const Key('trading-card-market-palmer')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byKey(const Key('player-trade-sheet')), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('trade-submit-buy')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.byKey(const Key('trade-submit-buy')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('Bought 1 share of Cole Palmer.'), findsOneWidget);
  });
}
