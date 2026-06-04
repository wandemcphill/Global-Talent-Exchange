import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/capital/trader/presentation/trader_balance_guard.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test('null backend balance becomes blocked state', () {
    final ProviderContainer container = ProviderContainer();
    addTearDown(container.dispose);

    final GtexSurfaceState<TraderBalanceSnapshot> state = container.read(
      traderBalanceSurfaceProvider(
        const TraderBalancePayload(available: null, currency: 'USD'),
      ),
    );

    expect(state, isA<GtexBlocked<TraderBalanceSnapshot>>());
    expect(
      (state as GtexBlocked<TraderBalanceSnapshot>).reason,
      traderBalanceUnavailableReason,
    );
  });

  test('null backend balance is never converted into zero data', () {
    final GtexSurfaceState<TraderBalanceSnapshot> state =
        traderBalanceSurfaceFromBackend(
          const TraderBalancePayload(available: null, currency: 'USD'),
        );

    expect(state, isNot(isA<GtexData<TraderBalanceSnapshot>>()));
  });
}
