import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_quote_lock.dart';

void main() {
  testWidgets('expired quote disables order action', (
    WidgetTester tester,
  ) async {
    var placedOrders = 0;
    final TraderQuoteLockState expired = TraderQuoteLockState.fromBackend(
      TraderQuoteLock(
        id: 'quote-expired',
        price: 1.42,
        amount: 25,
        currency: 'USD',
        lockedUntil: DateTime.utc(2026, 6, 2, 12),
      ),
      now: DateTime.utc(2026, 6, 2, 12, 0, 1),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: <Widget>[
              QuoteLockCard(state: expired),
              ConfirmOrderBar(
                quoteLock: expired,
                balanceAvailable: true,
                onConfirm: () => placedOrders += 1,
              ),
            ],
          ),
        ),
      ),
    );

    final Finder confirmButton = find.byKey(
      const ValueKey<String>('trader-confirm-order'),
    );
    final FilledButton button = tester.widget<FilledButton>(confirmButton);

    expect(expired.canConfirm, isFalse);
    expect(button.onPressed, isNull);
    expect(find.text('Quote expired'), findsOneWidget);
    expect(find.text('Quote expired - refresh'), findsOneWidget);

    await tester.tap(confirmButton);
    await tester.pump();

    expect(placedOrders, 0);
  });

  test(
    'quote lock accepts backend remaining seconds without local duration',
    () {
      final TraderQuoteLockState locked = TraderQuoteLockState.fromBackend(
        const TraderQuoteLock(
          id: 'quote-live',
          price: 1.42,
          amount: 25,
          currency: 'USD',
          lockSecondsRemaining: 30,
        ),
      );

      expect(locked.canConfirm, isTrue);
      expect(locked.secondsRemaining, 30);
    },
  );

  testWidgets('quote lock surfaces backend audit reference', (
    WidgetTester tester,
  ) async {
    final TraderQuoteLockState locked = TraderQuoteLockState.fromBackend(
      const TraderQuoteLock(
        id: 'quote-audited',
        price: 1.42,
        amount: 25,
        currency: 'USD',
        lockSecondsRemaining: 30,
        auditRef: 'audit-quote-123',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: QuoteLockCard(state: locked))),
    );

    expect(find.text('Audit reference: audit-quote-123'), findsOneWidget);
  });
}
