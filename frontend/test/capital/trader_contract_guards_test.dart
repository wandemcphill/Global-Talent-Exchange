import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/capital/trader/data/trader_api.dart'
    as trader_data;
import 'package:gte_frontend/features/capital/trader/providers/exchange_hub_provider.dart'
    as capital_provider;
import 'package:gte_frontend/features/capital/trader/presentation/trader_balance_guard.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_quote_lock.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  group('TraderQuoteLockState', () {
    test('uses backend remaining seconds for active quote locks', () {
      const TraderQuoteLock quote = TraderQuoteLock(
        id: 'quote-1',
        price: 1.25,
        amount: 100,
        currency: 'USD',
        lockSecondsRemaining: 45,
      );

      final TraderQuoteLockState state = TraderQuoteLockState.fromBackend(
        quote,
      );

      expect(state.phase, TraderQuoteLockPhase.locked);
      expect(state.secondsRemaining, 45);
      expect(state.canConfirm, isTrue);
    });

    test('uses backend lockedUntil when remaining seconds are absent', () {
      final TraderQuoteLock quote = TraderQuoteLock(
        id: 'quote-2',
        price: 1.25,
        amount: 100,
        currency: 'USD',
        lockedUntil: DateTime.utc(2026, 6, 2, 12, 0, 30),
      );

      final TraderQuoteLockState state = TraderQuoteLockState.fromBackend(
        quote,
        now: DateTime.utc(2026, 6, 2, 12),
      );

      expect(state.phase, TraderQuoteLockPhase.locked);
      expect(state.secondsRemaining, 30);
      expect(state.canConfirm, isTrue);
    });

    test('expires quotes without backend lock truth', () {
      final TraderQuoteLock quote = TraderQuoteLock(
        id: 'quote-3',
        price: 1.25,
        amount: 100,
        currency: 'USD',
        validUntil: DateTime.utc(2026, 6, 2, 12, 5),
      );

      final TraderQuoteLockState state = TraderQuoteLockState.fromBackend(
        quote,
        now: DateTime.utc(2026, 6, 2, 12),
      );

      expect(state.phase, TraderQuoteLockPhase.expired);
      expect(state.canConfirm, isFalse);
      expect(state.message, contains('backend lock'));
    });

    test('validUntil alone never unlocks capital quote actions', () {
      final trader_data.TraderQuote quote = trader_data.TraderQuote(
        id: 'quote-valid-only',
        price: 1.25,
        amount: 100,
        currency: 'USD',
        validUntil: DateTime.utc(2026, 6, 2, 12, 5),
      );

      final capital_provider.CapitalQuoteLockState state = capital_provider
          .CapitalQuoteLockState.fromBackend(
        quote,
        now: DateTime.utc(2026, 6, 2, 12),
      );

      expect(quote.isExpired(now: DateTime.utc(2026, 6, 2, 12)), isTrue);
      expect(state.phase, capital_provider.CapitalQuoteLockPhase.expired);
      expect(state.canPlaceOrder, isFalse);
    });
  });

  testWidgets('expired quote disables order confirmation', (
    WidgetTester tester,
  ) async {
    bool confirmed = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ConfirmOrderBar(
            quoteLock: TraderQuoteLockState.expired(
              quote: const TraderQuoteLock(
                id: 'quote-expired',
                price: 1.25,
                amount: 100,
                currency: 'USD',
                lockSecondsRemaining: 0,
              ),
            ),
            balanceAvailable: true,
            onConfirm: () => confirmed = true,
          ),
        ),
      ),
    );

    await tester.tap(
      find.byKey(const ValueKey<String>('trader-confirm-order')),
    );
    await tester.pump();

    expect(confirmed, isFalse);
    expect(find.text('Quote expired - refresh'), findsOneWidget);
  });

  test('null trader balance renders blocked instead of zero fallback', () {
    final GtexSurfaceState<TraderBalanceSnapshot> state =
        traderBalanceSurfaceFromBackend(
          const TraderBalancePayload(available: null, currency: 'USD'),
        );

    expect(state, isA<GtexBlocked<TraderBalanceSnapshot>>());
    expect(traderBalanceAllowsActions(state), isFalse);
    expect(
      (state as GtexBlocked<TraderBalanceSnapshot>).reason,
      contains('sync'),
    );
  });

  test('zero trader balance stays backend data, not a null fallback', () {
    final GtexSurfaceState<TraderBalanceSnapshot> state =
        traderBalanceSurfaceFromBackend(
          const TraderBalancePayload(available: 0, currency: 'USD'),
        );

    expect(state, isA<GtexData<TraderBalanceSnapshot>>());
    expect((state as GtexData<TraderBalanceSnapshot>).data.available, 0);
  });
}
