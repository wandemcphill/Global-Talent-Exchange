import 'dart:math' as math;

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

class CapitalTraderFixtureStore {
  CapitalTraderFixtureStore.seeded({
    required this.wallet,
    required this.onWalletMutation,
  }) : tickers = Map<String, GteMarketTicker>.from(seedTickers),
       orderBooks = seedOrderBooks.map(
         (String key, GteOrderBook value) =>
             MapEntry<String, GteOrderBook>(key, _cloneOrderBook(value)),
       ),
       orders = List<GteOrderRecord>.of(seedOrders, growable: true),
       orderSequence = seedOrders.length;

  final CapitalWalletFixtureStore wallet;
  final void Function() onWalletMutation;
  final Map<String, GteMarketTicker> tickers;
  final Map<String, GteOrderBook> orderBooks;
  final List<GteOrderRecord> orders;
  final Set<String> sessionOrderIds = <String>{};
  int orderSequence;

  GteMarketTicker fetchTicker(String playerId) {
    final GteMarketTicker? ticker = tickers[playerId];
    if (ticker == null) {
      throw StateError('Unknown ticker player id: $playerId');
    }
    final Iterable<GteOrderRecord> openOrders = orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          sessionOrderIds.contains(order.id),
    );
    double? bestBid = ticker.bestBid;
    double? bestAsk = ticker.bestAsk;
    for (final GteOrderRecord order in openOrders) {
      final double? price = priceForOrder(order);
      if (price == null || price <= 0) {
        continue;
      }
      if (order.side == GteOrderSide.buy) {
        bestBid = bestBid == null ? price : math.max(bestBid, price);
      } else {
        bestAsk = bestAsk == null ? price : math.min(bestAsk, price);
      }
    }

    final double? spread =
        bestBid != null && bestAsk != null ? bestAsk - bestBid : ticker.spread;
    final double? midPrice =
        bestBid != null && bestAsk != null
            ? (bestBid + bestAsk) / 2
            : ticker.midPrice;
    return GteMarketTicker(
      playerId: ticker.playerId,
      symbol: ticker.symbol,
      lastPrice: ticker.lastPrice,
      bestBid: bestBid,
      bestAsk: bestAsk,
      spread: spread,
      midPrice: midPrice,
      referencePrice: ticker.referencePrice,
      dayChange: ticker.dayChange,
      dayChangePercent: ticker.dayChangePercent,
      volume24h: ticker.volume24h,
    );
  }

  GteOrderBook fetchOrderBook(
    String playerId, {
    required DateTime generatedAt,
  }) {
    final GteOrderBook? base = orderBooks[playerId];
    if (base == null) {
      throw StateError('Unknown order book player id: $playerId');
    }

    final Iterable<GteOrderRecord> openOrders = orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          sessionOrderIds.contains(order.id),
    );
    final List<GteOrderBookLevel> bids = _mergeOrderBookSide(
      base.bids,
      openOrders.where(
        (GteOrderRecord order) => order.side == GteOrderSide.buy,
      ),
      descending: true,
      priceForOrder: priceForOrder,
    );
    final List<GteOrderBookLevel> asks = _mergeOrderBookSide(
      base.asks,
      openOrders.where(
        (GteOrderRecord order) => order.side == GteOrderSide.sell,
      ),
      descending: false,
      priceForOrder: priceForOrder,
    );
    return GteOrderBook(
      playerId: playerId,
      bids: bids,
      asks: asks,
      generatedAt: generatedAt,
    );
  }

  GteOrderListView listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) {
    Iterable<GteOrderRecord> filtered = orders;
    if (statuses != null && statuses.isNotEmpty) {
      final Set<GteOrderStatus> allowed = statuses.toSet();
      filtered = filtered.where(
        (GteOrderRecord order) => allowed.contains(order.status),
      );
    }
    final List<GteOrderRecord> ordered = filtered.toList(growable: false);
    final List<GteOrderRecord> items = ordered
        .skip(offset)
        .take(limit)
        .toList(growable: false);
    return GteOrderListView(
      items: items,
      limit: limit,
      offset: offset,
      total: ordered.length,
    );
  }

  GteOrderRecord fetchOrder(String orderId) {
    return orders.firstWhere(
      (GteOrderRecord order) => order.id == orderId,
      orElse: () => throw StateError('Unknown order id: $orderId'),
    );
  }

  GteOrderRecord placeOrder({
    required GteOrderCreateRequest request,
    required String userId,
    required DateTime timestamp,
  }) {
    final double? referencePrice = referencePriceFor(
      request.playerId,
      request.side,
    );
    final double requestedReserve =
        request.side == GteOrderSide.buy && request.maxPrice != null
            ? request.quantity * request.maxPrice!
            : 0.0;
    final double reservedAmount = math.min(
      requestedReserve,
      wallet.coinSummary.availableBalance,
    );

    final GteOrderRecord order = GteOrderRecord(
      id: 'ord-${++orderSequence}',
      userId: userId,
      playerId: request.playerId,
      side: request.side,
      status: GteOrderStatus.open,
      quantity: request.quantity,
      filledQuantity: 0.0,
      remainingQuantity: request.quantity,
      maxPrice: request.maxPrice ?? referencePrice,
      reservedAmount: reservedAmount,
      currency: GteLedgerUnit.coin,
      holdTransactionId:
          request.side == GteOrderSide.buy && reservedAmount > 0
              ? wallet.nextLedgerId
              : null,
      createdAt: timestamp,
      updatedAt: timestamp,
      executionSummary: const GteOrderExecutionSummary(
        executionCount: 0,
        totalNotional: 0.0,
        averagePrice: null,
      ),
    );
    orders.insert(0, order);
    sessionOrderIds.add(order.id);

    if (request.side == GteOrderSide.buy && reservedAmount > 0) {
      wallet.reserveOrderFunds(
        amount: reservedAmount,
        playerId: request.playerId,
        createdAt: timestamp,
      );
      onWalletMutation();
    }

    return order;
  }

  GteOrderRecord cancelOrder({
    required String orderId,
    required DateTime timestamp,
  }) {
    final int index = orders.indexWhere(
      (GteOrderRecord order) => order.id == orderId,
    );
    if (index == -1) {
      throw StateError('Unknown order id: $orderId');
    }
    final GteOrderRecord existing = orders[index];
    if (!existing.canCancel) {
      return existing;
    }

    final GteOrderRecord cancelled = GteOrderRecord(
      id: existing.id,
      userId: existing.userId,
      playerId: existing.playerId,
      side: existing.side,
      status: GteOrderStatus.cancelled,
      quantity: existing.quantity,
      filledQuantity: existing.filledQuantity,
      remainingQuantity: existing.remainingQuantity,
      maxPrice: existing.maxPrice,
      reservedAmount: 0.0,
      currency: existing.currency,
      holdTransactionId: existing.holdTransactionId,
      createdAt: existing.createdAt,
      updatedAt: timestamp,
      executionSummary: existing.executionSummary,
    );
    orders[index] = cancelled;

    if (existing.side == GteOrderSide.buy && existing.reservedAmount > 0) {
      wallet.releaseOrderFunds(
        amount: existing.reservedAmount,
        orderId: existing.id,
        createdAt: timestamp,
      );
      onWalletMutation();
    }

    return cancelled;
  }

  GteOrderRecord updateOrder(
    String orderId,
    GteOrderRecord Function(GteOrderRecord existing) update,
  ) {
    final int index = orders.indexWhere(
      (GteOrderRecord order) => order.id == orderId,
    );
    if (index == -1) {
      throw StateError('Unknown order id: $orderId');
    }
    final GteOrderRecord updated = update(orders[index]);
    orders[index] = updated;
    return updated;
  }

  double? referencePriceFor(String playerId, GteOrderSide side) {
    final GteMarketTicker? ticker = tickers[playerId];
    if (ticker == null) {
      return null;
    }
    return side == GteOrderSide.buy
        ? ticker.bestAsk ?? ticker.referencePrice ?? ticker.lastPrice
        : ticker.bestBid ?? ticker.referencePrice ?? ticker.lastPrice;
  }

  double? priceForOrder(GteOrderRecord order) {
    return order.maxPrice ?? referencePriceFor(order.playerId, order.side);
  }

  static final Map<String, GteMarketTicker> seedTickers =
      <String, GteMarketTicker>{
        'lamine-yamal': const GteMarketTicker(
          playerId: 'lamine-yamal',
          symbol: 'L. Yamal',
          lastPrice: 1180,
          bestBid: 1172,
          bestAsk: 1188,
          spread: 16,
          midPrice: 1180,
          referencePrice: 1095,
          dayChange: 85,
          dayChangePercent: 7.8,
          volume24h: 34,
        ),
        'jude-bellingham': const GteMarketTicker(
          playerId: 'jude-bellingham',
          symbol: 'J. Bellingham',
          lastPrice: 1260,
          bestBid: 1254,
          bestAsk: 1266,
          spread: 12,
          midPrice: 1260,
          referencePrice: 1205,
          dayChange: 55,
          dayChangePercent: 4.6,
          volume24h: 28,
        ),
        'jamal-musiala': const GteMarketTicker(
          playerId: 'jamal-musiala',
          symbol: 'J. Musiala',
          lastPrice: 1095,
          bestBid: 1087,
          bestAsk: 1104,
          spread: 17,
          midPrice: 1095.5,
          referencePrice: 1054,
          dayChange: 41,
          dayChangePercent: 3.9,
          volume24h: 19,
        ),
        'victor-osimhen': const GteMarketTicker(
          playerId: 'victor-osimhen',
          symbol: 'V. Osimhen',
          lastPrice: 920,
          bestBid: 914,
          bestAsk: 929,
          spread: 15,
          midPrice: 921.5,
          referencePrice: 867,
          dayChange: 53,
          dayChangePercent: 6.1,
          volume24h: 24,
        ),
      };

  static final Map<String, GteOrderBook> seedOrderBooks =
      <String, GteOrderBook>{
        'lamine-yamal': GteOrderBook(
          playerId: 'lamine-yamal',
          generatedAt: DateTime.utc(2026, 3, 11, 12),
          bids: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1172, quantity: 3, orderCount: 2),
            GteOrderBookLevel(price: 1166, quantity: 6, orderCount: 3),
          ],
          asks: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1188, quantity: 2, orderCount: 1),
            GteOrderBookLevel(price: 1196, quantity: 5, orderCount: 2),
          ],
        ),
        'jude-bellingham': GteOrderBook(
          playerId: 'jude-bellingham',
          generatedAt: DateTime.utc(2026, 3, 11, 12),
          bids: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1254, quantity: 2, orderCount: 1),
            GteOrderBookLevel(price: 1248, quantity: 5, orderCount: 3),
          ],
          asks: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1266, quantity: 2, orderCount: 1),
            GteOrderBookLevel(price: 1274, quantity: 4, orderCount: 2),
          ],
        ),
        'jamal-musiala': GteOrderBook(
          playerId: 'jamal-musiala',
          generatedAt: DateTime.utc(2026, 3, 11, 12),
          bids: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1087, quantity: 1.5, orderCount: 1),
            GteOrderBookLevel(price: 1081, quantity: 4.0, orderCount: 2),
          ],
          asks: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 1104, quantity: 1.0, orderCount: 1),
            GteOrderBookLevel(price: 1112, quantity: 3.0, orderCount: 2),
          ],
        ),
        'victor-osimhen': GteOrderBook(
          playerId: 'victor-osimhen',
          generatedAt: DateTime.utc(2026, 3, 11, 12),
          bids: const <GteOrderBookLevel>[],
          asks: const <GteOrderBookLevel>[
            GteOrderBookLevel(price: 929, quantity: 1.0, orderCount: 1),
          ],
        ),
      };

  static final List<GteOrderRecord> seedOrders = <GteOrderRecord>[
    GteOrderRecord(
      id: 'ord-1',
      userId: 'fixture-user',
      playerId: 'lamine-yamal',
      side: GteOrderSide.buy,
      status: GteOrderStatus.open,
      quantity: 0.5,
      filledQuantity: 0,
      remainingQuantity: 0.5,
      maxPrice: 125,
      reservedAmount: 62.5,
      currency: GteLedgerUnit.coin,
      holdTransactionId: 'ledger-1',
      createdAt: DateTime.utc(2026, 3, 11, 11, 30),
      updatedAt: DateTime.utc(2026, 3, 11, 11, 30),
      executionSummary: GteOrderExecutionSummary(
        executionCount: 0,
        totalNotional: 0.0,
        averagePrice: null,
      ),
    ),
    GteOrderRecord(
      id: 'ord-2',
      userId: 'fixture-user',
      playerId: 'victor-osimhen',
      side: GteOrderSide.buy,
      status: GteOrderStatus.filled,
      quantity: 1,
      filledQuantity: 1,
      remainingQuantity: 0.0,
      maxPrice: 920,
      reservedAmount: 0.0,
      currency: GteLedgerUnit.coin,
      holdTransactionId: 'ledger-3',
      createdAt: DateTime.utc(2026, 3, 10, 18, 15),
      updatedAt: DateTime.utc(2026, 3, 10, 18, 16),
      executionSummary: GteOrderExecutionSummary(
        executionCount: 1,
        totalNotional: 920,
        averagePrice: 920,
        lastExecutedAt: DateTime.utc(2026, 3, 10, 18, 16),
        executions: <GteOrderExecution>[
          GteOrderExecution(
            payload: <String, Object?>{'price': 920, 'quantity': 1},
          ),
        ],
      ),
    ),
  ];
}

List<GteOrderBookLevel> _mergeOrderBookSide(
  List<GteOrderBookLevel> seeded,
  Iterable<GteOrderRecord> liveOrders, {
  required bool descending,
  required double? Function(GteOrderRecord order) priceForOrder,
}) {
  final Map<String, _MutableBookLevel> byPrice = <String, _MutableBookLevel>{};

  void mergeLevel({
    required double price,
    required double quantity,
    required int orderCount,
  }) {
    if (price <= 0 || quantity <= 0 || orderCount <= 0) {
      return;
    }
    final String key = price.toStringAsFixed(4);
    final _MutableBookLevel existing =
        byPrice[key] ??
        _MutableBookLevel(price: price, quantity: 0.0, orderCount: 0);
    existing.quantity += quantity;
    existing.orderCount += orderCount;
    byPrice[key] = existing;
  }

  for (final GteOrderBookLevel level in seeded) {
    mergeLevel(
      price: level.price,
      quantity: level.quantity,
      orderCount: level.orderCount,
    );
  }
  for (final GteOrderRecord order in liveOrders) {
    final double? price = priceForOrder(order);
    if (price == null) {
      continue;
    }
    mergeLevel(price: price, quantity: order.remainingQuantity, orderCount: 1);
  }

  final List<_MutableBookLevel> merged = byPrice.values.toList(growable: false)
    ..sort((_MutableBookLevel left, _MutableBookLevel right) {
      return descending
          ? right.price.compareTo(left.price)
          : left.price.compareTo(right.price);
    });
  return merged
      .map(
        (_MutableBookLevel level) => GteOrderBookLevel(
          price: level.price,
          quantity: level.quantity,
          orderCount: level.orderCount,
        ),
      )
      .toList(growable: false);
}

class _MutableBookLevel {
  _MutableBookLevel({
    required this.price,
    required this.quantity,
    required this.orderCount,
  });

  final double price;
  double quantity;
  int orderCount;
}

GteOrderBook _cloneOrderBook(GteOrderBook orderBook) {
  return GteOrderBook(
    playerId: orderBook.playerId,
    bids: List<GteOrderBookLevel>.from(orderBook.bids),
    asks: List<GteOrderBookLevel>.from(orderBook.asks),
    generatedAt: orderBook.generatedAt,
  );
}
