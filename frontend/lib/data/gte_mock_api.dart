import 'dart:async';
import 'dart:math' as math;

import 'gte_api_repository.dart';
import 'gte_models.dart';

class GteMockApi implements GteApiRepository {
  GteMockApi({
    this.latency = const Duration(milliseconds: 250),
  })  : _catalog = _seedCatalog.map(_cloneSnapshot).toList(growable: false),
        _profiles = _seedProfiles.map(
          (String key, PlayerProfile value) => MapEntry<String, PlayerProfile>(
            key,
            _cloneProfile(value),
          ),
        ),
        _baseTickers = Map<String, GteMarketTicker>.from(_seedTickers),
        _candles = _seedCandles.map(
          (String key, GteMarketCandles value) =>
              MapEntry<String, GteMarketCandles>(
            key,
            _cloneCandles(value),
          ),
        ),
        _baseOrderBooks = _seedOrderBooks.map(
          (String key, GteOrderBook value) => MapEntry<String, GteOrderBook>(
            key,
            _cloneOrderBook(value),
          ),
        ),
        _walletSummary = _seedWalletSummary,
        _walletLedger =
            List<GteWalletLedgerEntry>.of(_seedWalletLedger, growable: true),
        _portfolio = GtePortfolioView(
          holdings: List<GtePortfolioHolding>.of(_seedPortfolioHoldings,
              growable: false),
        ),
        _orders = List<GteOrderRecord>.of(_seedOrders, growable: true),
        _portfolioSummary = _seedPortfolioSummary;

  final Duration latency;
  final List<PlayerSnapshot> _catalog;
  final Map<String, PlayerProfile> _profiles;
  final Map<String, GteMarketTicker> _baseTickers;
  final Map<String, GteMarketCandles> _candles;
  final Map<String, GteOrderBook> _baseOrderBooks;

  GteWalletSummary _walletSummary;
  final List<GteWalletLedgerEntry> _walletLedger;
  final GtePortfolioView _portfolio;
  GtePortfolioSummary _portfolioSummary;
  final List<GteOrderRecord> _orders;
  final Set<String> _sessionOrderIds = <String>{};

  int _orderSequence = _seedOrders.length;
  int _ledgerSequence = _seedWalletLedger.length;
  DateTime _clock = DateTime.utc(2026, 3, 11, 12, 0);

  @override
  Future<GteAuthSession> login(GteAuthLoginRequest request) async {
    await _delay();
    return _fixtureSession;
  }

  @override
  Future<GteAuthSession> register(GteAuthRegisterRequest request) async {
    await _delay();
    return GteAuthSession(
      accessToken: 'fixture-${request.username}-token',
      tokenType: 'bearer',
      expiresIn: 3600,
      user: GteCurrentUser(
        id: 'fixture-${request.username}',
        email: request.email,
        username: request.username,
        displayName: request.displayName,
        role: 'user',
      ),
    );
  }

  @override
  Future<GteCurrentUser> fetchCurrentUser() async {
    await _delay();
    return _fixtureSession.user;
  }

  @override
  Future<void> logout() async {}

  @override
  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20}) async {
    await _delay();
    return _catalog.take(limit).map(_cloneSnapshot).toList(growable: false);
  }

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) async {
    await _delay();
    final PlayerProfile? profile = _profiles[playerId];
    if (profile == null) {
      throw StateError('Unknown player id: $playerId');
    }
    return _cloneProfile(profile);
  }

  @override
  Future<MarketPulse> fetchMarketPulse() async {
    await _delay();
    return _marketPulse.copyWith(
      tickers: List<String>.from(_marketPulse.tickers),
      transferRoom: List<TransferRoomEntry>.from(_marketPulse.transferRoom),
    );
  }

  @override
  Future<GteMarketTicker> fetchTicker(String playerId) async {
    await _delay();
    final GteMarketTicker? ticker = _baseTickers[playerId];
    if (ticker == null) {
      throw StateError('Unknown ticker player id: $playerId');
    }
    final Iterable<GteOrderRecord> openOrders = _orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          _sessionOrderIds.contains(order.id),
    );
    double? bestBid = ticker.bestBid;
    double? bestAsk = ticker.bestAsk;
    for (final GteOrderRecord order in openOrders) {
      final double? price = _priceForOrder(order);
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
    final double? midPrice = bestBid != null && bestAsk != null
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

  @override
  Future<GteMarketCandles> fetchCandles(
    String playerId, {
    String interval = '1h',
    int limit = 30,
  }) async {
    await _delay();
    final GteMarketCandles? candles = _candles[playerId];
    if (candles == null) {
      throw StateError('Unknown candle player id: $playerId');
    }
    final List<GteMarketCandle> trimmed =
        candles.candles.take(limit).toList(growable: false);
    return GteMarketCandles(
      playerId: playerId,
      interval: interval,
      candles: trimmed,
    );
  }

  @override
  Future<GteOrderBook> fetchOrderBook(String playerId) async {
    await _delay();
    final GteOrderBook? base = _baseOrderBooks[playerId];
    if (base == null) {
      throw StateError('Unknown order book player id: $playerId');
    }

    final Iterable<GteOrderRecord> openOrders = _orders.where(
      (GteOrderRecord order) =>
          order.playerId == playerId &&
          order.canCancel &&
          _sessionOrderIds.contains(order.id),
    );
    final List<GteOrderBookLevel> bids = _mergeOrderBookSide(
      base.bids,
      openOrders
          .where((GteOrderRecord order) => order.side == GteOrderSide.buy),
      descending: true,
    );
    final List<GteOrderBookLevel> asks = _mergeOrderBookSide(
      base.asks,
      openOrders
          .where((GteOrderRecord order) => order.side == GteOrderSide.sell),
      descending: false,
    );
    return GteOrderBook(
      playerId: playerId,
      bids: bids,
      asks: asks,
      generatedAt: _clock,
    );
  }

  @override
  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) async {
    await _delay();
    Iterable<GteOrderRecord> filtered = _orders;
    if (statuses != null && statuses.isNotEmpty) {
      final Set<GteOrderStatus> allowed = statuses.toSet();
      filtered = filtered
          .where((GteOrderRecord order) => allowed.contains(order.status));
    }
    final List<GteOrderRecord> ordered = filtered.toList(growable: false);
    final List<GteOrderRecord> items =
        ordered.skip(offset).take(limit).toList(growable: false);
    return GteOrderListView(
      items: items,
      limit: limit,
      offset: offset,
      total: ordered.length,
    );
  }

  @override
  Future<GteOrderRecord> fetchOrder(String orderId) async {
    await _delay();
    return _orders.firstWhere(
      (GteOrderRecord order) => order.id == orderId,
      orElse: () => throw StateError('Unknown order id: $orderId'),
    );
  }

  @override
  Future<GteOrderRecord> placeOrder(GteOrderCreateRequest request) async {
    await _delay();
    final double? referencePrice =
        _referencePriceFor(request.playerId, request.side);
    final double requestedReserve =
        request.side == GteOrderSide.buy && request.maxPrice != null
            ? request.quantity * request.maxPrice!
            : 0.0;
    final double reservedAmount =
        math.min(requestedReserve, _walletSummary.availableBalance);
    final DateTime timestamp = _nextTimestamp();

    final GteOrderRecord order = GteOrderRecord(
      id: 'ord-${++_orderSequence}',
      userId: _fixtureSession.user.id,
      playerId: request.playerId,
      side: request.side,
      status: GteOrderStatus.open,
      quantity: request.quantity,
      filledQuantity: 0.0,
      remainingQuantity: request.quantity,
      maxPrice: request.maxPrice ?? referencePrice,
      reservedAmount: reservedAmount,
      currency: GteLedgerUnit.credit,
      holdTransactionId: request.side == GteOrderSide.buy && reservedAmount > 0
          ? 'ledger-${_ledgerSequence + 1}'
          : null,
      createdAt: timestamp,
      updatedAt: timestamp,
      executionSummary: const GteOrderExecutionSummary(
        executionCount: 0,
        totalNotional: 0.0,
        averagePrice: null,
      ),
    );
    _orders.insert(0, order);
    _sessionOrderIds.add(order.id);

    if (request.side == GteOrderSide.buy && reservedAmount > 0) {
      _walletSummary = GteWalletSummary(
        availableBalance: _walletSummary.availableBalance - reservedAmount,
        reservedBalance: _walletSummary.reservedBalance + reservedAmount,
        totalBalance: _walletSummary.totalBalance,
        currency: _walletSummary.currency,
      );
      _walletLedger.insert(
        0,
        GteWalletLedgerEntry(
          id: 'ledger-${++_ledgerSequence}',
          amount: -reservedAmount,
          reason: 'order_funds_reserved',
          description: 'Reserved credits for ${request.playerId} buy order',
          createdAt: timestamp,
        ),
      );
      _rebuildPortfolioSummary();
    }

    return order;
  }

  @override
  Future<GteOrderRecord> cancelOrder(String orderId) async {
    await _delay();
    final int index =
        _orders.indexWhere((GteOrderRecord order) => order.id == orderId);
    if (index == -1) {
      throw StateError('Unknown order id: $orderId');
    }
    final GteOrderRecord existing = _orders[index];
    if (!existing.canCancel) {
      return existing;
    }

    final DateTime timestamp = _nextTimestamp();
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
    _orders[index] = cancelled;

    if (existing.side == GteOrderSide.buy && existing.reservedAmount > 0) {
      _walletSummary = GteWalletSummary(
        availableBalance:
            _walletSummary.availableBalance + existing.reservedAmount,
        reservedBalance: math.max(
          0.0,
          _walletSummary.reservedBalance - existing.reservedAmount,
        ),
        totalBalance: _walletSummary.totalBalance,
        currency: _walletSummary.currency,
      );
      _walletLedger.insert(
        0,
        GteWalletLedgerEntry(
          id: 'ledger-${++_ledgerSequence}',
          amount: existing.reservedAmount,
          reason: 'order_cancel_release',
          description: 'Released credits from cancelled order ${existing.id}',
          createdAt: timestamp,
        ),
      );
      _rebuildPortfolioSummary();
    }

    return cancelled;
  }

  @override
  Future<GteWalletSummary> fetchWalletSummary() async {
    await _delay();
    return _walletSummary;
  }

  @override
  Future<GteWalletLedgerPage> fetchWalletLedger(
      {int page = 1, int pageSize = 20}) async {
    await _delay();
    final int offset = (page - 1) * pageSize;
    final List<GteWalletLedgerEntry> items =
        _walletLedger.skip(offset).take(pageSize).toList(growable: false);
    return GteWalletLedgerPage(
      page: page,
      pageSize: pageSize,
      total: _walletLedger.length,
      items: items,
    );
  }

  @override
  Future<GtePortfolioView> fetchPortfolio() async {
    await _delay();
    return GtePortfolioView(
      holdings:
          List<GtePortfolioHolding>.of(_portfolio.holdings, growable: false),
    );
  }

  @override
  Future<GtePortfolioSummary> fetchPortfolioSummary() async {
    await _delay();
    return _portfolioSummary;
  }

  Future<void> _delay() async {
    await Future<void>.delayed(latency);
  }

  DateTime _nextTimestamp() {
    _clock = _clock.add(const Duration(seconds: 1));
    return _clock;
  }

  double? _referencePriceFor(String playerId, GteOrderSide side) {
    final GteMarketTicker? ticker = _baseTickers[playerId];
    if (ticker == null) {
      return null;
    }
    return side == GteOrderSide.buy
        ? ticker.bestAsk ?? ticker.referencePrice ?? ticker.lastPrice
        : ticker.bestBid ?? ticker.referencePrice ?? ticker.lastPrice;
  }

  double? _priceForOrder(GteOrderRecord order) {
    return order.maxPrice ?? _referencePriceFor(order.playerId, order.side);
  }

  List<GteOrderBookLevel> _mergeOrderBookSide(
    List<GteOrderBookLevel> seeded,
    Iterable<GteOrderRecord> liveOrders, {
    required bool descending,
  }) {
    final Map<String, _MutableBookLevel> byPrice =
        <String, _MutableBookLevel>{};

    void mergeLevel({
      required double price,
      required double quantity,
      required int orderCount,
    }) {
      if (price <= 0 || quantity <= 0 || orderCount <= 0) {
        return;
      }
      final String key = price.toStringAsFixed(4);
      final _MutableBookLevel existing = byPrice[key] ??
          _MutableBookLevel(
            price: price,
            quantity: 0.0,
            orderCount: 0,
          );
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
      final double? price = _priceForOrder(order);
      if (price == null) {
        continue;
      }
      mergeLevel(
        price: price,
        quantity: order.remainingQuantity,
        orderCount: 1,
      );
    }

    final List<_MutableBookLevel> merged =
        byPrice.values.toList(growable: false)
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

  void _rebuildPortfolioSummary() {
    final double totalMarketValue = _portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.marketValue,
    );
    final double unrealizedPlTotal = _portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.unrealizedPl,
    );
    _portfolioSummary = GtePortfolioSummary(
      totalMarketValue: totalMarketValue,
      cashBalance: _walletSummary.availableBalance,
      totalEquity: totalMarketValue + _walletSummary.availableBalance,
      unrealizedPlTotal: unrealizedPlTotal,
      realizedPlTotal: _seedPortfolioSummary.realizedPlTotal,
    );
  }
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

PlayerSnapshot _cloneSnapshot(PlayerSnapshot player) {
  return player.copyWith(
    valueTrend: List<TrendPoint>.from(player.valueTrend),
    recentHighlights: List<String>.from(player.recentHighlights),
  );
}

PlayerProfile _cloneProfile(PlayerProfile profile) {
  return profile.copyWith(
    snapshot: _cloneSnapshot(profile.snapshot),
    gsiTrend: List<TrendPoint>.from(profile.gsiTrend),
    awards: List<String>.from(profile.awards),
    statBlocks: List<String>.from(profile.statBlocks),
  );
}

GteMarketCandles _cloneCandles(GteMarketCandles candles) {
  return GteMarketCandles(
    playerId: candles.playerId,
    interval: candles.interval,
    candles: List<GteMarketCandle>.from(candles.candles),
  );
}

GteOrderBook _cloneOrderBook(GteOrderBook orderBook) {
  return GteOrderBook(
    playerId: orderBook.playerId,
    bids: List<GteOrderBookLevel>.from(orderBook.bids),
    asks: List<GteOrderBookLevel>.from(orderBook.asks),
    generatedAt: orderBook.generatedAt,
  );
}

const GteAuthSession _fixtureSession = GteAuthSession(
  accessToken: 'fixture-demo-token',
  tokenType: 'bearer',
  expiresIn: 3600,
  user: GteCurrentUser(
    id: 'demo-user',
    email: 'fan@demo.gte.local',
    username: 'demo_fan',
    displayName: 'Demo Fan',
    role: 'user',
    kycStatus: 'pending',
    isActive: true,
  ),
);

const List<PlayerSnapshot> _seedCatalog = <PlayerSnapshot>[
  PlayerSnapshot(
    id: 'lamine-yamal',
    name: 'Lamine Yamal',
    club: 'Barcelona',
    nation: 'Spain',
    position: 'RW',
    age: 18,
    marketCredits: 1180,
    gsi: 96,
    formRating: 9.2,
    valueDeltaPct: 7.8,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 67),
      TrendPoint(label: 'W2', value: 71),
      TrendPoint(label: 'W3', value: 76),
      TrendPoint(label: 'W4', value: 82),
      TrendPoint(label: 'W5', value: 88),
    ],
    recentHighlights: <String>[
      '2 goals in the last 3 matches',
      'Final-third chance creation up 18%',
      'Transfer room activity accelerated this week',
    ],
    isFollowed: true,
    isWatchlisted: true,
  ),
  PlayerSnapshot(
    id: 'jude-bellingham',
    name: 'Jude Bellingham',
    club: 'Real Madrid',
    nation: 'England',
    position: 'CM',
    age: 22,
    marketCredits: 1260,
    gsi: 94,
    formRating: 8.9,
    valueDeltaPct: 4.6,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 70),
      TrendPoint(label: 'W2', value: 73),
      TrendPoint(label: 'W3', value: 79),
      TrendPoint(label: 'W4', value: 84),
      TrendPoint(label: 'W5', value: 87),
    ],
    recentHighlights: <String>[
      'Tournament influence tier: elite',
      'Shortlist demand remains stable',
      'Midfield duel win rate above 64%',
    ],
    isShortlisted: true,
  ),
  PlayerSnapshot(
    id: 'jamal-musiala',
    name: 'Jamal Musiala',
    club: 'Bayern Munich',
    nation: 'Germany',
    position: 'AM',
    age: 23,
    marketCredits: 1095,
    gsi: 91,
    formRating: 8.7,
    valueDeltaPct: 3.9,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 61),
      TrendPoint(label: 'W2', value: 65),
      TrendPoint(label: 'W3', value: 69),
      TrendPoint(label: 'W4', value: 74),
      TrendPoint(label: 'W5', value: 79),
    ],
    recentHighlights: <String>[
      'Line-breaking carries trending upward',
      'Scout Mode alerts active across 14 clubs',
      'Ball progression profile improved',
    ],
    isFollowed: true,
    notificationIntensity: NotificationIntensity.scoutMode,
  ),
  PlayerSnapshot(
    id: 'victor-osimhen',
    name: 'Victor Osimhen',
    club: 'Galatasaray',
    nation: 'Nigeria',
    position: 'ST',
    age: 27,
    marketCredits: 920,
    gsi: 88,
    formRating: 8.4,
    valueDeltaPct: 6.1,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 55),
      TrendPoint(label: 'W2', value: 58),
      TrendPoint(label: 'W3', value: 62),
      TrendPoint(label: 'W4', value: 69),
      TrendPoint(label: 'W5', value: 75),
    ],
    recentHighlights: <String>[
      'Transfer signal upgraded to active',
      'Shot volume back above 4.2 per 90',
      'Platform market demand rose after last matchday',
    ],
    inTransferRoom: true,
  ),
];

final Map<String, PlayerProfile> _seedProfiles = <String, PlayerProfile>{
  'lamine-yamal': PlayerProfile(
    snapshot: _seedCatalog[0],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 72),
      TrendPoint(label: 'M2', value: 77),
      TrendPoint(label: 'M3', value: 83),
      TrendPoint(label: 'M4', value: 89),
      TrendPoint(label: 'M5', value: 96),
    ],
    awards: const <String>[
      'Golden Boy shortlist',
      'Matchday MVP x3',
      'Continental semifinal decisive contribution',
    ],
    statBlocks: const <String>[
      'xA 0.42',
      'Dribbles won 5.7',
      'Progressive carries 7.3',
      'Final-third receptions 13.8',
    ],
    scoutingReport:
        'Explosive right-sided creator with elite manipulation of space and accelerating end product. Breakout profile still carries upside headroom.',
    transferSignal:
        'Untouchable unless a record-setting move materializes. Watchlist and shortlist activity remains the strongest in the catalog.',
  ),
  'jude-bellingham': PlayerProfile(
    snapshot: _seedCatalog[1],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 70),
      TrendPoint(label: 'M2', value: 75),
      TrendPoint(label: 'M3', value: 81),
      TrendPoint(label: 'M4', value: 87),
      TrendPoint(label: 'M5', value: 94),
    ],
    awards: const <String>[
      'Player of the season finalist',
      'Continental final-winning moment',
      'Best XI selection',
    ],
    statBlocks: const <String>[
      'Press resistance 95th pct',
      'Box arrivals 6.1',
      'Shot-creating actions 5.0',
      'Duel win rate 63%',
    ],
    scoutingReport:
        'Complete midfield controller with premium ball-carrying, duel dominance, and high-leverage scoring output. Low-risk elite asset.',
    transferSignal:
        'Market remains premium and supply-constrained. Acquisition scenario is improbable, but his card drives benchmark pricing.',
  ),
  'jamal-musiala': PlayerProfile(
    snapshot: _seedCatalog[2],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 66),
      TrendPoint(label: 'M2', value: 71),
      TrendPoint(label: 'M3', value: 76),
      TrendPoint(label: 'M4', value: 84),
      TrendPoint(label: 'M5', value: 91),
    ],
    awards: const <String>[
      'Young player of the month',
      'Tournament breakout watch',
      'Domestic title race accelerator',
    ],
    statBlocks: const <String>[
      'Carries into box 3.8',
      'Touches in zone 14: 11.2',
      'Turn resistance 92nd pct',
      'Progressive passes received 14.6',
    ],
    scoutingReport:
        'Hybrid creator-finisher with elite change of direction and close-control gravity. Best deployed with freedom between lines.',
    transferSignal:
        'Scout Mode traffic is heavy. Price is climbing steadily without the volatility seen in pure hype-driven movers.',
  ),
  'victor-osimhen': PlayerProfile(
    snapshot: _seedCatalog[3],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 61),
      TrendPoint(label: 'M2', value: 66),
      TrendPoint(label: 'M3', value: 69),
      TrendPoint(label: 'M4', value: 82),
      TrendPoint(label: 'M5', value: 88),
    ],
    awards: const <String>[
      'League golden boot race contender',
      'Transfer room headline striker',
      'Match-winning brace spotlight',
    ],
    statBlocks: const <String>[
      'Shots 4.4',
      'Aerial wins 3.2',
      'Penalty-box touches 8.9',
      'Goals per shot 0.23',
    ],
    scoutingReport:
        'Vertical striker with premium penalty-box occupation, elite separation bursts, and immediate transfer-market gravity.',
    transferSignal:
        'Transfer room remains live. Featured on both platform deal boards and user market chatter after the latest valuation jump.',
  ),
};

final MarketPulse _marketPulse = MarketPulse(
  marketMomentum: 8.4,
  dailyVolumeCredits: 18340,
  activeWatchers: 642,
  liveDeals: 21,
  hottestLeague: 'UEFA Club Championship',
  tickers: const <String>[
    'Yamal +7.8%',
    'Osimhen +6.1%',
    'Musiala Scout Mode spike',
    'Transfer room volume +14%',
  ],
  transferRoom: <TransferRoomEntry>[
    TransferRoomEntry(
      id: 'tr-1',
      headline: 'Platform Deal: Victor Osimhen demand surge',
      lane: 'Platform Deals',
      marketCredits: 920,
      activity: '22 shortlist moves in 24h',
      timestamp: DateTime.utc(2026, 3, 11, 10, 30),
    ),
    TransferRoomEntry(
      id: 'tr-2',
      headline: 'User Market Deal: Musiala premium listing filled',
      lane: 'User Market Deals',
      marketCredits: 1110,
      activity: 'Cleared in 6 minutes',
      timestamp: DateTime.utc(2026, 3, 11, 9, 50),
    ),
    TransferRoomEntry(
      id: 'tr-3',
      headline: 'Announcement: Jude benchmark pricing reset',
      lane: 'Announcements',
      marketCredits: 1260,
      activity: 'Market cap ceiling updated',
      timestamp: DateTime.utc(2026, 3, 11, 8, 45),
    ),
  ],
);

final Map<String, GteMarketTicker> _seedTickers = <String, GteMarketTicker>{
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

final Map<String, GteMarketCandles> _seedCandles = <String, GteMarketCandles>{
  'lamine-yamal': GteMarketCandles(
    playerId: 'lamine-yamal',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1148,
        high: 1159,
        low: 1141,
        close: 1152,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1152,
        high: 1168,
        low: 1149,
        close: 1161,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1161,
        high: 1175,
        low: 1158,
        close: 1168,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1168,
        high: 1182,
        low: 1164,
        close: 1176,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1176,
        high: 1193,
        low: 1170,
        close: 1180,
        volume: 7,
      ),
    ],
  ),
  'jude-bellingham': GteMarketCandles(
    playerId: 'jude-bellingham',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1210,
        high: 1222,
        low: 1204,
        close: 1216,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1216,
        high: 1230,
        low: 1213,
        close: 1224,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1224,
        high: 1241,
        low: 1218,
        close: 1233,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1233,
        high: 1254,
        low: 1228,
        close: 1246,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1246,
        high: 1268,
        low: 1240,
        close: 1260,
        volume: 7,
      ),
    ],
  ),
  'jamal-musiala': GteMarketCandles(
    playerId: 'jamal-musiala',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 8),
        open: 1061,
        high: 1074,
        low: 1055,
        close: 1068,
        volume: 3,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 9),
        open: 1068,
        high: 1082,
        low: 1061,
        close: 1075,
        volume: 4,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 10),
        open: 1075,
        high: 1089,
        low: 1069,
        close: 1081,
        volume: 5,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 11),
        open: 1081,
        high: 1100,
        low: 1078,
        close: 1090,
        volume: 6,
      ),
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 1090,
        high: 1107,
        low: 1084,
        close: 1095,
        volume: 7,
      ),
    ],
  ),
  'victor-osimhen': GteMarketCandles(
    playerId: 'victor-osimhen',
    interval: '1h',
    candles: <GteMarketCandle>[
      GteMarketCandle(
        timestamp: DateTime.utc(2026, 3, 11, 12),
        open: 920,
        high: 924,
        low: 915,
        close: 920,
        volume: 1,
      ),
    ],
  ),
};

final Map<String, GteOrderBook> _seedOrderBooks = <String, GteOrderBook>{
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

const GteWalletSummary _seedWalletSummary = GteWalletSummary(
  availableBalance: 1200,
  reservedBalance: 62.5,
  totalBalance: 1262.5,
  currency: GteLedgerUnit.credit,
);

const List<GtePortfolioHolding> _seedPortfolioHoldings = <GtePortfolioHolding>[
  GtePortfolioHolding(
    playerId: 'lamine-yamal',
    quantity: 1,
    averageCost: 1095,
    currentPrice: 1180,
    marketValue: 1180,
    unrealizedPl: 85,
    unrealizedPlPercent: 7.8,
  ),
  GtePortfolioHolding(
    playerId: 'victor-osimhen',
    quantity: 1.2,
    averageCost: 850,
    currentPrice: 920,
    marketValue: 1104,
    unrealizedPl: 84,
    unrealizedPlPercent: 8.2,
  ),
];

const GtePortfolioSummary _seedPortfolioSummary = GtePortfolioSummary(
  totalMarketValue: 2284,
  cashBalance: 1200,
  totalEquity: 3484,
  unrealizedPlTotal: 169,
  realizedPlTotal: 42,
);

final List<GteWalletLedgerEntry> _seedWalletLedger = <GteWalletLedgerEntry>[
  GteWalletLedgerEntry(
    id: 'ledger-1',
    amount: -62.5,
    reason: 'withdrawal_hold',
    description: 'Reserved credits for resting buy order',
    createdAt: DateTime.utc(2026, 3, 11, 11, 30),
  ),
  GteWalletLedgerEntry(
    id: 'ledger-2',
    amount: 1200,
    reason: 'adjustment',
    description: 'Demo wallet seed',
    createdAt: DateTime.utc(2026, 3, 11, 8),
  ),
  GteWalletLedgerEntry(
    id: 'ledger-3',
    amount: -1095,
    reason: 'trade_execution',
    description: 'Portfolio acquisition cash leg',
    createdAt: DateTime.utc(2026, 3, 10, 18, 15),
  ),
];

final List<GteOrderRecord> _seedOrders = <GteOrderRecord>[
  GteOrderRecord(
    id: 'ord-1',
    userId: 'demo-user',
    playerId: 'lamine-yamal',
    side: GteOrderSide.buy,
    status: GteOrderStatus.open,
    quantity: 0.5,
    filledQuantity: 0,
    remainingQuantity: 0.5,
    maxPrice: 125,
    reservedAmount: 62.5,
    currency: GteLedgerUnit.credit,
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
    userId: 'demo-user',
    playerId: 'victor-osimhen',
    side: GteOrderSide.buy,
    status: GteOrderStatus.filled,
    quantity: 1,
    filledQuantity: 1,
    remainingQuantity: 0.0,
    maxPrice: 920,
    reservedAmount: 0.0,
    currency: GteLedgerUnit.credit,
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
          payload: <String, Object?>{
            'price': 920,
            'quantity': 1,
          },
        ),
      ],
    ),
  ),
];
