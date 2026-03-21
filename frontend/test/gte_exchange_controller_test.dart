import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('controller bootstrap loads the market directory', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.bootstrap();

    expect(controller.players, isNotEmpty);
    expect(controller.marketPage?.total, greaterThan(0));
  });

  test('controller signs in and loads protected portfolio routes', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123',
    );

    expect(controller.isAuthenticated, isTrue);
    expect(controller.walletSummary?.availableBalance, greaterThan(0));
    expect(controller.portfolioSummary?.totalEquity, greaterThan(0));
    expect(controller.recentOrders, isNotEmpty);
    expect(controller.recentOrderTotal, greaterThan(0));
    expect(controller.openOrders, isNotEmpty);
    expect(controller.openOrderTotal, greaterThan(0));
  });

  test(
      'controller keeps wallet and order views in sync across submit and cancel',
      () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123',
    );
    await controller.openPlayer('lamine-yamal');
    final double startingAvailable = controller.walletSummary!.availableBalance;
    final double startingReserved = controller.walletSummary!.reservedBalance;
    final int startingOpenOrders = controller.openOrders.length;
    final GteOrderRecord? order = await controller.placeOrder(
      playerId: 'lamine-yamal',
      side: GteOrderSide.buy,
      quantity: 1,
      maxPrice: 1188,
    );
    expect(order, isNotNull);
    final GteOrderRecord placedOrder = order!;

    expect(
        controller.orderForPlayer('lamine-yamal')?.status, GteOrderStatus.open);
    expect(
      controller.recentOrders
          .any((GteOrderRecord item) => item.id == placedOrder.id),
      isTrue,
    );
    expect(controller.openOrders.length, greaterThan(startingOpenOrders));
    expect(controller.walletSummary!.availableBalance,
        lessThan(startingAvailable));
    expect(controller.walletSummary!.reservedBalance,
        greaterThan(startingReserved));

    final GteOrderRecord? cancelled =
        await controller.cancelOrder(placedOrder.id);

    expect(cancelled?.status, GteOrderStatus.cancelled);
    expect(
      controller.openOrders
          .any((GteOrderRecord item) => item.id == placedOrder.id),
      isFalse,
    );
    expect(controller.walletSummary!.availableBalance,
        closeTo(startingAvailable, 0.001));
    expect(controller.walletSummary!.reservedBalance,
        closeTo(startingReserved, 0.001));
  });
}
