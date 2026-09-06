import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_order_ticket_sheet.dart';

/// PHASE5-A / PR-2B: the trade ticket runs on the canonical System A market.
///
/// It buys and sells through POST /api/market/buy|sell, prices from
/// PlayerShareMarket.share_price_coin rather than any valuation, and reuses one
/// idempotency key across retries of the same user action.

/// Builds the controller with real async.
///
/// The fixture repository awaits `Future.delayed`, which never completes under
/// the fake async clock `testWidgets` installs, so setup has to run outside it.
Future<GteExchangeController> _controller(
  WidgetTester tester, {
  bool signedIn = true,
}) async {
  late GteExchangeController controller;
  await tester.runAsync(() async {
    controller = GteExchangeController(api: GteExchangeApiClient.fixture());
    if (signedIn) {
      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
    }
    await controller.openPlayer('lamine-yamal');
  });
  return controller;
}

/// Drains work without pumpAndSettle: the ticket shows an indeterminate
/// progress indicator while settling, which schedules frames forever and would
/// make pumpAndSettle hang rather than return.
Future<void> _settle(WidgetTester tester) async {
  for (int i = 0; i < 20; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

Future<void> _pumpTicket(
  WidgetTester tester,
  GteExchangeController controller,
) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: GteOrderTicketSheet(
          controller: controller,
          snapshot: controller.selectedPlayer!,
        ),
      ),
    ),
  );
  await _settle(tester);
}

void main() {
  testWidgets('ticket prices from the tradable share price, not a valuation',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    final GtePlayerMarketSnapshot snapshot = controller.selectedPlayer!;
    final double? sharePrice = snapshot.detail.marketProfile.sharePriceCoin;
    final double? valuationCredits = snapshot.detail.value.currentValueCredits;

    await _pumpTicket(tester, controller);

    expect(sharePrice, isNotNull);
    // The two must not be silently interchangeable - that was the P0-3 defect.
    expect(sharePrice, isNot(equals(valuationCredits)));
    expect(find.text('SHARE PRICE'), findsOneWidget);
    // The order-book vocabulary is gone: no limit price, no bid/ask.
    expect(find.textContaining('Max price'), findsNothing);
    expect(find.textContaining('Bid '), findsNothing);
  });

  testWidgets('quantity is whole shares only', (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpTicket(tester, controller);

    await tester.enterText(find.byType(TextField), '2.5');
    await tester.pump();

    // System A trades whole shares; the field refuses anything else.
    expect(find.text('2.5'), findsNothing);
  });

  testWidgets('rejects a zero quantity before calling the server',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpTicket(tester, controller);

    await tester.enterText(find.byType(TextField), '0');
    await tester.pump();
    await tester.tap(find.text('Buy shares'));
    await _settle(tester);

    expect(
      find.text('Enter a whole number of shares above zero.'),
      findsOneWidget,
    );
    expect(controller.orderError, isNull);
  });

  testWidgets('retrying a failed trade reuses the same idempotency key',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpTicket(tester, controller);

    // Far beyond the fixture wallet, so the trade fails and the sheet stays open.
    await tester.enterText(find.byType(TextField), '100000');
    await tester.pump();
    await tester.ensureVisible(find.text('Buy shares'));
    await tester.pump();
    await tester.tap(find.text('Buy shares'));
    await _settle(tester);

    expect(controller.orderError, isNotNull);
    // The button now offers a retry, and says so: the key is being held.
    expect(find.text('Retry buy'), findsOneWidget);
    expect(
      find.textContaining('will not place a second trade'),
      findsOneWidget,
    );
  });

  testWidgets('changing the quantity starts a genuinely new trade',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpTicket(tester, controller);
    await tester.enterText(find.byType(TextField), '100000');
    await tester.pump();
    await tester.ensureVisible(find.text('Buy shares'));
    await tester.pump();
    await tester.tap(find.text('Buy shares'));
    await _settle(tester);
    expect(find.text('Retry buy'), findsOneWidget);

    // A different quantity is a different economic intent, so the held key is
    // dropped rather than reused - reusing it would be rejected by the server.
    await tester.enterText(find.byType(TextField), '3');
    await tester.pump();

    expect(find.text('Buy shares'), findsOneWidget);
    expect(find.text('Retry buy'), findsNothing);
  });

  testWidgets('ownership is reported as unavailable, never fabricated as zero',
      (WidgetTester tester) async {
    final GteExchangeController controller =
        await _controller(tester, signedIn: false);

    await _pumpTicket(tester, controller);

    // Signed out: ownership is unknown, which is not the same as owning none.
    expect(find.text('SHARES OWNED'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('0'), findsNothing);
  });
}
