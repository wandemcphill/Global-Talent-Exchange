import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test('mock api exposes seeded players and market pulse', () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final List<PlayerSnapshot> players = await api.fetchPlayers();
    final MarketPulse pulse = await api.fetchMarketPulse();
    final GteWalletSummary wallet = await api.fetchWalletSummary();
    final GtePortfolioView portfolio = await api.fetchPortfolio();
    final GteOrderListView orders = await api.listOrders();

    expect(players, hasLength(4));
    expect(players.first.name, 'Lamine Yamal');
    expect(players.last.inTransferRoom, isTrue);
    expect(pulse.transferRoom, hasLength(3));
    expect(pulse.hottestLeague, 'UEFA Club Championship');
    expect(wallet.currency, GteLedgerUnit.credit);
    expect(portfolio.holdings, hasLength(2));
    expect(orders.items, hasLength(2));
  });

  test(
      'mock api filters open orders and keeps balances in sync on submit and cancel',
      () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final GteWalletSummary startingWallet = await api.fetchWalletSummary();
    final GteOrderRecord order = await api.placeOrder(
      const GteOrderCreateRequest(
        playerId: 'jude-bellingham',
        side: GteOrderSide.buy,
        quantity: 1,
        maxPrice: 1266,
      ),
    );
    final GteOrderListView openOrders = await api.listOrders(
      statuses: const <GteOrderStatus>[
        GteOrderStatus.open,
        GteOrderStatus.partiallyFilled,
      ],
    );
    final GteWalletSummary reservedWallet = await api.fetchWalletSummary();
    final GteOrderBook bookAfterPlace =
        await api.fetchOrderBook('jude-bellingham');
    final GteOrderRecord cancelled = await api.cancelOrder(order.id);
    final GteWalletSummary restoredWallet = await api.fetchWalletSummary();

    expect(openOrders.items.any((GteOrderRecord item) => item.id == order.id),
        isTrue);
    expect(reservedWallet.availableBalance,
        lessThan(startingWallet.availableBalance));
    expect(reservedWallet.reservedBalance,
        greaterThan(startingWallet.reservedBalance));
    expect(
      bookAfterPlace.bids
          .any((GteOrderBookLevel level) => level.price == order.maxPrice),
      isTrue,
    );
    expect(cancelled.status, GteOrderStatus.cancelled);
    expect(restoredWallet.availableBalance,
        closeTo(startingWallet.availableBalance, 0.001));
    expect(restoredWallet.reservedBalance,
        closeTo(startingWallet.reservedBalance, 0.001));
  });

  test(
      'mock api exposes sparse candles and a one-sided book for an illiquid player',
      () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final GteMarketCandles candles = await api.fetchCandles('victor-osimhen');
    final GteOrderBook book = await api.fetchOrderBook('victor-osimhen');

    expect(candles.candles, hasLength(1));
    expect(book.bids, isEmpty);
    expect(book.asks, isNotEmpty);
  });

  test('mock api throws for unknown player ids', () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    expect(
      () => api.fetchPlayerProfile('unknown-player'),
      throwsA(isA<StateError>()),
    );
  });
}
