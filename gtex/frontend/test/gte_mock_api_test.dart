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
    expect(wallet.currency, GteLedgerUnit.coin);
    expect(portfolio.holdings, hasLength(2));
    expect(orders.items, hasLength(2));
  });

  test('mock api settles a player-share buy and moves the wallet', () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final GteWalletSummary startingWallet = await api.fetchWalletSummary();
    final GtePlayerShareTradeResult trade = await api.buyPlayerShares(
      playerId: 'jude-bellingham',
      shareCount: 2,
      idempotencyKey: 'fixture-buy-key-1',
    );
    final GteWalletSummary afterWallet = await api.fetchWalletSummary();
    final GtePortfolioView portfolio = await api.fetchPortfolio();

    // System A fills instantly: ownership exists straight away, no open order.
    expect(trade.holding.shareCount, 2);
    expect(trade.market.circulatingShares, 2);
    expect(trade.transactionId, isNotEmpty);
    expect(trade.netAmountCoin, greaterThan(trade.grossAmountCoin));
    expect(
      afterWallet.availableBalance,
      closeTo(startingWallet.availableBalance - trade.netAmountCoin, 0.001),
    );
    expect(
      portfolio.holdings
          .firstWhere(
            (GtePortfolioHolding holding) =>
                holding.playerId == 'jude-bellingham',
          )
          .quantity,
      2,
    );
  });

  test('mock api replays a repeated idempotency key instead of trading twice',
      () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final GteWalletSummary startingWallet = await api.fetchWalletSummary();
    final GtePlayerShareTradeResult first = await api.buyPlayerShares(
      playerId: 'jude-bellingham',
      shareCount: 2,
      idempotencyKey: 'fixture-retry-key',
    );
    final GtePlayerShareTradeResult second = await api.buyPlayerShares(
      playerId: 'jude-bellingham',
      shareCount: 2,
      idempotencyKey: 'fixture-retry-key',
    );
    final GteWalletSummary afterWallet = await api.fetchWalletSummary();

    expect(second.transactionId, first.transactionId);
    expect(second.holding.shareCount, 2);
    expect(
      afterWallet.availableBalance,
      closeTo(startingWallet.availableBalance - first.netAmountCoin, 0.001),
    );
  });

  test('mock api sells shares back and credits the wallet', () async {
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    await api.buyPlayerShares(playerId: 'jude-bellingham', shareCount: 4);
    final GteWalletSummary afterBuy = await api.fetchWalletSummary();
    final GtePlayerShareTradeResult sale = await api.sellPlayerShares(
      playerId: 'jude-bellingham',
      shareCount: 3,
    );
    final GteWalletSummary afterSell = await api.fetchWalletSummary();

    expect(sale.holding.shareCount, 1);
    expect(sale.netAmountCoin, lessThan(sale.grossAmountCoin));
    expect(
      afterSell.availableBalance,
      closeTo(afterBuy.availableBalance + sale.netAmountCoin, 0.001),
    );
  });

  test('mock api can still cancel a seeded historical order', () async {
    // Order creation is retired, but existing open orders must stay closable.
    final GteMockApi api = GteMockApi(latency: Duration.zero);

    final GteOrderListView open = await api.listOrders(
      statuses: const <GteOrderStatus>[
        GteOrderStatus.open,
        GteOrderStatus.partiallyFilled,
      ],
    );
    expect(open.items, isNotEmpty);

    final GteOrderRecord cancelled = await api.cancelOrder(open.items.first.id);

    expect(cancelled.status, GteOrderStatus.cancelled);
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
