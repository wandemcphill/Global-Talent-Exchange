import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';

abstract class ITraderRepository {
  Future<TraderOverview> getMarketplace();
  Future<TraderProfile> getProfile();
  Future<TraderDashboard> getDashboard();
  Future<TraderBalance> getBalance();
  Future<List<TraderMarket>> listMarkets();
  Future<TraderOrderBook> getOrderBook(String marketId);
  Future<List<TraderOrder>> getOrders({String? status});
  Future<TraderOrder> getOrderDetail(String orderId);
  Future<TraderQuote> requestQuote(TraderQuoteRequest request);
  Future<TraderOrder> placeOrder(TraderOrderCreate request);
  Future<void> cancelOrder(String orderId);
  Future<List<TraderDispute>> getDisputes();
  Future<TraderDispute> getDisputeDetail(String disputeId);
  Future<TraderDispute> fileDispute(FileDisputeRequest request);
  Future<List<TraderSettlement>> getSettlements();
  Future<TraderSettlement> getSettlementDetail(String settlementId);
  Future<TraderDepositResult> initiateDeposit(TraderDepositRequest request);
  Future<TraderWithdrawalResult> requestWithdrawal(
    TraderWithdrawalRequest request,
  );
}

class TraderContractGapException implements Exception {
  const TraderContractGapException(this.message);

  final String message;

  @override
  String toString() => message;
}

TraderApi createCapitalTraderApi({
  required String baseUrl,
  required String? accessToken,
  required GteBackendMode backendMode,
  GteTransport? transport,
}) {
  if (backendMode == GteBackendMode.fixture) {
    return TraderApi.fixture();
  }
  return TraderApi.standard(
    baseUrl: baseUrl,
    accessToken: accessToken,
    mode: backendMode,
    transport: transport,
  );
}

class TraderApi implements ITraderRepository {
  TraderApi({
    required this.client,
    required this.fixtures,
    this.enableFixtureFallback = false,
  });

  final GteAuthedApi client;
  final _TraderFixtures fixtures;
  final bool enableFixtureFallback;

  factory TraderApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return TraderApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: transport ?? GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: _TraderFixtures.seed(),
    );
  }

  factory TraderApi.fixture() {
    return TraderApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _TraderFixtures.seed(),
      enableFixtureFallback: true,
    );
  }

  @override
  Future<TraderOverview> getMarketplace() => overview();

  Future<TraderOverview> overview() {
    return _withOptionalFixture<TraderOverview>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/trader/overview',
      );
      return TraderOverview.fromJson(payload);
    }, fixtures.overview);
  }

  @override
  Future<TraderProfile> getProfile() async => (await overview()).profile;

  @override
  Future<TraderDashboard> getDashboard() async {
    return TraderDashboard.fromOverview(await overview());
  }

  @override
  Future<TraderBalance> getBalance() async {
    return TraderBalance.fromOverview(await overview());
  }

  @override
  Future<List<TraderMarket>> listMarkets() {
    return _withOptionalFixture<List<TraderMarket>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/v2/trader/markets',
      );
      return payload.map(TraderMarket.fromJson).toList(growable: false);
    }, fixtures.markets);
  }

  @override
  Future<TraderOrderBook> getOrderBook(String marketId) async {
    final List<TraderMarket> markets = await listMarkets();
    for (final TraderMarket market in markets) {
      if (market.id == marketId) {
        final TraderOrderBook? book = market.orderBook;
        if (book != null) {
          return book;
        }
        throw TraderContractGapException(
          'Order book payload is missing for trader market $marketId.',
        );
      }
    }
    throw TraderContractGapException(
      'GET /api/v2/trader/order-book/$marketId is not mounted by the backend yet.',
    );
  }

  @override
  Future<List<TraderOrder>> getOrders({String? status}) {
    return Future<List<TraderOrder>>.error(
      const TraderContractGapException(
        'GET /api/v2/trader/orders is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderOrder> getOrderDetail(String orderId) {
    return Future<TraderOrder>.error(
      TraderContractGapException(
        'GET /api/v2/trader/orders/$orderId is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderQuote> requestQuote(TraderQuoteRequest request) {
    return Future<TraderQuote>.error(
      const TraderContractGapException(
        'POST /api/v2/trader/quote is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderOrder> placeOrder(TraderOrderCreate request) {
    return _withOptionalFixture<TraderOrder>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/orders',
        request.toJson(),
      );
      return TraderOrder.fromJson(payload);
    }, () => fixtures.order(request));
  }

  @override
  Future<void> cancelOrder(String orderId) {
    return Future<void>.error(
      TraderContractGapException(
        'POST /api/v2/trader/orders/$orderId/cancel is not mounted by the backend yet.',
      ),
    );
  }

  Future<TraderP2POffer> createP2POffer(TraderP2POfferCreate request) {
    return _withOptionalFixture<TraderP2POffer>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/p2p',
        request.toJson(),
      );
      return TraderP2POffer.fromJson(payload);
    }, () => fixtures.p2pOffer(request));
  }

  Future<TraderProcurementQuote> quoteProcurement(
    TraderProcurementQuoteRequest request,
  ) {
    return _withOptionalFixture<TraderProcurementQuote>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/procurements/quote',
        request.toJson(),
      );
      return TraderProcurementQuote.fromJson(payload);
    }, () => fixtures.procurementQuote(request));
  }

  Future<TraderProcurement> createProcurement(
    TraderProcurementCreateRequest request,
  ) {
    return _withOptionalFixture<TraderProcurement>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/procurements',
        request.toJson(),
      );
      return TraderProcurement.fromJson(payload);
    }, () => fixtures.procurement(request));
  }

  @override
  Future<List<TraderDispute>> getDisputes() {
    return Future<List<TraderDispute>>.error(
      const TraderContractGapException(
        'GET /api/v2/trader/disputes is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderDispute> getDisputeDetail(String disputeId) {
    return Future<TraderDispute>.error(
      TraderContractGapException(
        'GET /api/v2/trader/disputes/$disputeId is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderDispute> fileDispute(FileDisputeRequest request) {
    return Future<TraderDispute>.error(
      const TraderContractGapException(
        'POST /api/v2/trader/disputes is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<List<TraderSettlement>> getSettlements() {
    return Future<List<TraderSettlement>>.error(
      const TraderContractGapException(
        'GET /api/v2/trader/settlements is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderSettlement> getSettlementDetail(String settlementId) {
    return Future<TraderSettlement>.error(
      TraderContractGapException(
        'GET /api/v2/trader/settlements/$settlementId is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderDepositResult> initiateDeposit(TraderDepositRequest request) {
    return Future<TraderDepositResult>.error(
      const TraderContractGapException(
        'POST /api/v2/trader/deposit is not mounted by the backend yet.',
      ),
    );
  }

  @override
  Future<TraderWithdrawalResult> requestWithdrawal(
    TraderWithdrawalRequest request,
  ) {
    return Future<TraderWithdrawalResult>.error(
      const TraderContractGapException(
        'POST /api/v2/trader/withdraw is not mounted by the backend yet.',
      ),
    );
  }

  Future<List<TraderWatchlistItem>> listWatchlist() {
    return _withOptionalFixture<List<TraderWatchlistItem>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/v2/trader/watchlist',
      );
      return payload.map(TraderWatchlistItem.fromJson).toList(growable: false);
    }, fixtures.watchlist);
  }

  Future<TraderWatchlistItem> addWatchlist(String marketId) {
    return _withOptionalFixture<TraderWatchlistItem>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/watchlist',
        <String, Object?>{'market_id': marketId},
      );
      return TraderWatchlistItem.fromJson(payload);
    }, () => fixtures.addWatchlist(marketId));
  }

  Future<TraderTotpSetup> setupTotp() {
    return _withOptionalFixture<TraderTotpSetup>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/security/totp/setup',
        const <String, Object?>{},
      );
      return TraderTotpSetup.fromJson(payload);
    }, fixtures.totpSetup);
  }

  Future<Map<String, dynamic>> _postMap(String path, Object? body) async {
    final Object? payload = await client.post(path, body: body);
    if (payload is Map) {
      return Map<String, dynamic>.from(payload);
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected response shape.',
    );
  }

  Future<T> _withOptionalFixture<T>(
    FutureOr<T> Function() liveCall,
    FutureOr<T> Function() fixtureCall,
  ) {
    if (!enableFixtureFallback) {
      return Future<T>.sync(liveCall);
    }
    return client.withFallback<T>(liveCall, fixtureCall);
  }
}

class TraderProfile {
  const TraderProfile({
    required this.id,
    required this.userId,
    required this.tradingAlias,
    required this.preferredCurrency,
    required this.tradingExperience,
    required this.interests,
    required this.walletLabel,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.isOnline,
    this.lastSeenAt,
    this.trustScore,
    this.trustTier,
    this.ratingAverage,
    this.ratingCount,
    this.disputeHistory = const <TraderDisputeRecord>[],
    this.hasDisputeHistory = false,
    this.liquiditySnapshot = const <String, Object?>{},
    this.completionRate,
    this.averageReleaseSeconds,
    this.ratingScore,
    this.metricsUpdatedAt,
  });

  final String id;
  final String userId;
  final String tradingAlias;
  final String preferredCurrency;
  final String tradingExperience;
  final List<String> interests;
  final String walletLabel;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final bool? isOnline;
  final DateTime? lastSeenAt;
  final int? trustScore;
  final String? trustTier;
  final double? ratingAverage;
  final int? ratingCount;
  final List<TraderDisputeRecord> disputeHistory;
  final bool hasDisputeHistory;
  final Map<String, Object?> liquiditySnapshot;
  final double? completionRate;
  final double? averageReleaseSeconds;
  final double? ratingScore;
  final DateTime? metricsUpdatedAt;

  factory TraderProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader profile',
    );
    final Object? disputePayload = GteJson.value(json, <String>[
      'dispute_history',
      'disputeHistory',
      'disputes',
    ]);
    return TraderProfile(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      tradingAlias: GteJson.string(json, <String>[
        'trading_alias',
        'tradingAlias',
      ]),
      preferredCurrency: GteJson.string(json, <String>[
        'preferred_currency',
        'preferredCurrency',
      ], fallback: 'USD'),
      tradingExperience: GteJson.string(json, <String>[
        'trading_experience',
        'tradingExperience',
      ], fallback: 'beginner'),
      interests: GteJson.typedList<String>(json, <String>[
        'interests_json',
        'interests',
      ], (Object? entry) => entry.toString()),
      walletLabel: GteJson.string(json, <String>[
        'wallet_label',
        'walletLabel',
      ], fallback: 'GTEX Wallet'),
      status: GteJson.string(json, <String>['status'], fallback: 'PENDING'),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      isOnline: _boolOrNull(json, <String>['is_online', 'isOnline', 'online']),
      lastSeenAt: GteJson.dateTimeOrNull(json, <String>[
        'last_seen_at',
        'lastSeenAt',
      ]),
      trustScore: GteJson.integerOrNull(json, <String>[
        'trust_score',
        'trustScore',
      ]),
      trustTier: GteJson.stringOrNull(json, <String>[
        'trust_tier',
        'trustTier',
      ]),
      ratingAverage: _numberOrNull(json, <String>[
        'rating_average',
        'ratingAverage',
        'average_rating',
        'averageRating',
        'rating_score',
        'ratingScore',
      ]),
      ratingCount: GteJson.integerOrNull(json, <String>[
        'rating_count',
        'ratingCount',
        'reviews_count',
        'reviewsCount',
      ]),
      disputeHistory: _disputeList(disputePayload),
      hasDisputeHistory: disputePayload != null,
      liquiditySnapshot: _jsonMapOrEmpty(
        GteJson.value(json, <String>[
          'liquidity_snapshot_json',
          'liquiditySnapshot',
        ]),
      ),
      completionRate: _numberOrNull(json, <String>[
        'completion_rate',
        'completionRate',
      ]),
      averageReleaseSeconds: _numberOrNull(json, <String>[
        'average_release_seconds',
        'averageReleaseSeconds',
      ]),
      ratingScore: _numberOrNull(json, <String>['rating_score', 'ratingScore']),
      metricsUpdatedAt: GteJson.dateTimeOrNull(json, <String>[
        'metrics_updated_at',
        'metricsUpdatedAt',
      ]),
    );
  }
}

class TraderDisputeRecord {
  const TraderDisputeRecord({
    this.id,
    this.status,
    this.summary,
    this.openedAt,
    this.resolvedAt,
  });

  final String? id;
  final String? status;
  final String? summary;
  final DateTime? openedAt;
  final DateTime? resolvedAt;

  factory TraderDisputeRecord.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader dispute record',
    );
    return TraderDisputeRecord(
      id: GteJson.stringOrNull(json, <String>['id']),
      status: GteJson.stringOrNull(json, <String>['status']),
      summary: GteJson.stringOrNull(json, <String>[
        'summary',
        'reason',
        'outcome',
      ]),
      openedAt: GteJson.dateTimeOrNull(json, <String>[
        'opened_at',
        'openedAt',
        'created_at',
        'createdAt',
      ]),
      resolvedAt: GteJson.dateTimeOrNull(json, <String>[
        'resolved_at',
        'resolvedAt',
        'closed_at',
        'closedAt',
      ]),
    );
  }
}

class TraderMarket {
  const TraderMarket({
    required this.id,
    required this.symbol,
    required this.displayName,
    required this.assetType,
    required this.price,
    required this.dailyChangePercent,
    required this.marketCap,
    required this.volume24h,
    required this.liquidityScore,
    required this.updatedAt,
    this.buyPrice,
    this.sellPrice,
    this.orderBook,
    this.priceCandles = const <TraderPriceCandle>[],
    this.settlementEtaMinutes,
    this.settlementEtaLabel,
    this.settlementRails = const <String>[],
    this.hasSettlementRails = false,
  });

  final String id;
  final String symbol;
  final String displayName;
  final String assetType;
  final double? price;
  final double? dailyChangePercent;
  final double? marketCap;
  final double? volume24h;
  final int? liquidityScore;
  final DateTime updatedAt;
  final double? buyPrice;
  final double? sellPrice;
  final TraderOrderBook? orderBook;
  final List<TraderPriceCandle> priceCandles;
  final int? settlementEtaMinutes;
  final String? settlementEtaLabel;
  final List<String> settlementRails;
  final bool hasSettlementRails;

  double? get liveBestBid => sellPrice ?? orderBook?.bestBid;
  double? get liveBestAsk => buyPrice ?? orderBook?.bestAsk;

  double? get liveSpread {
    final double? bid = liveBestBid;
    final double? ask = liveBestAsk;
    if (bid == null || ask == null || ask < bid) {
      return null;
    }
    return ask - bid;
  }

  double? get liveSpreadPercent {
    final double? spread = liveSpread;
    final double? bid = liveBestBid;
    if (spread == null || bid == null || bid <= 0) {
      return null;
    }
    return (spread / bid) * 100;
  }

  bool get hasCanonicalSettlementRail => settlementRails.isNotEmpty;

  factory TraderMarket.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader market',
    );
    final Object? orderBookPayload =
        GteJson.value(json, <String>['order_book', 'orderBook']) ?? json;
    final Object? settlementRailPayload = GteJson.value(json, <String>[
      'settlement_rails',
      'settlementRails',
      'payment_rails',
      'paymentRails',
    ]);
    return TraderMarket(
      id: GteJson.string(json, <String>['id']),
      symbol: GteJson.string(json, <String>['symbol']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      assetType: GteJson.string(json, <String>[
        'asset_type',
        'assetType',
      ], fallback: 'fan_coin'),
      price: _numberOrNull(json, <String>['price']),
      dailyChangePercent: _numberOrNull(json, <String>[
        'daily_change_percent',
        'dailyChangePercent',
      ]),
      marketCap: _numberOrNull(json, <String>['market_cap', 'marketCap']),
      volume24h: _numberOrNull(json, <String>['volume_24h', 'volume24h']),
      liquidityScore: GteJson.integerOrNull(json, <String>[
        'liquidity_score',
        'liquidityScore',
      ]),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      buyPrice: _numberOrNull(json, <String>[
        'buy_price',
        'buyPrice',
        'best_ask',
        'bestAsk',
        'ask',
      ]),
      sellPrice: _numberOrNull(json, <String>[
        'sell_price',
        'sellPrice',
        'best_bid',
        'bestBid',
        'bid',
      ]),
      orderBook: TraderOrderBook.fromJsonOrNull(orderBookPayload),
      priceCandles: _candleList(
        GteJson.value(json, <String>['candles', 'price_candles']),
      ),
      settlementEtaMinutes: GteJson.integerOrNull(json, <String>[
        'settlement_eta_minutes',
        'settlementEtaMinutes',
      ]),
      settlementEtaLabel: GteJson.stringOrNull(json, <String>[
        'settlement_eta',
        'settlementEta',
        'settlement_eta_label',
        'settlementEtaLabel',
      ]),
      settlementRails: _canonicalSettlementRails(settlementRailPayload),
      hasSettlementRails: settlementRailPayload != null,
    );
  }
}

class TraderOrderBook {
  const TraderOrderBook({
    required this.bids,
    required this.asks,
    this.syncedAt,
    this.status,
  });

  final List<TraderOrderBookLevel> bids;
  final List<TraderOrderBookLevel> asks;
  final DateTime? syncedAt;
  final String? status;

  bool get hasLiveDepth => bids.isNotEmpty && asks.isNotEmpty;
  double? get bestBid => bids.isEmpty ? null : bids.first.price;
  double? get bestAsk => asks.isEmpty ? null : asks.first.price;

  double? get spread {
    final double? bid = bestBid;
    final double? ask = bestAsk;
    if (bid == null || ask == null || ask < bid) {
      return null;
    }
    return ask - bid;
  }

  double? get spreadPercent {
    final double? currentSpread = spread;
    final double? bid = bestBid;
    if (currentSpread == null || bid == null || bid <= 0) {
      return null;
    }
    return (currentSpread / bid) * 100;
  }

  double get maxDepth {
    final Iterable<double> quantities = <TraderOrderBookLevel>[
      ...bids,
      ...asks,
    ].map((TraderOrderBookLevel level) => level.quantity);
    if (quantities.isEmpty) {
      return 0;
    }
    return quantities.reduce((double left, double right) {
      return left > right ? left : right;
    });
  }

  static TraderOrderBook? fromJsonOrNull(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?>? json = _mapOrNull(value);
    if (json == null) {
      return null;
    }
    final List<TraderOrderBookLevel> bids = _orderBookLevels(
      GteJson.value(json, <String>['bids', 'buy', 'buys']),
      descending: true,
    );
    final List<TraderOrderBookLevel> asks = _orderBookLevels(
      GteJson.value(json, <String>['asks', 'sell', 'sells']),
      descending: false,
    );
    if (bids.isEmpty && asks.isEmpty) {
      return null;
    }
    return TraderOrderBook(
      bids: bids,
      asks: asks,
      syncedAt: GteJson.dateTimeOrNull(json, <String>[
        'synced_at',
        'syncedAt',
        'updated_at',
        'updatedAt',
      ]),
      status: GteJson.stringOrNull(json, <String>['status', 'state']),
    );
  }
}

class TraderOrderBookLevel {
  const TraderOrderBookLevel({required this.price, required this.quantity});

  final double price;
  final double quantity;

  factory TraderOrderBookLevel.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader order book level',
    );
    return TraderOrderBookLevel(
      price: GteJson.number(json, <String>['price', 'limit_price']),
      quantity: GteJson.number(json, <String>[
        'quantity',
        'amount',
        'size',
        'depth',
      ]),
    );
  }
}

class TraderPriceCandle {
  const TraderPriceCandle({
    this.timestamp,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    this.volume,
  });

  final DateTime? timestamp;
  final double open;
  final double high;
  final double low;
  final double close;
  final double? volume;

  factory TraderPriceCandle.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader price candle',
    );
    final double open = GteJson.number(json, <String>['open', 'o']);
    final double close = GteJson.number(json, <String>['close', 'c']);
    return TraderPriceCandle(
      timestamp: GteJson.dateTimeOrNull(json, <String>[
        'timestamp',
        'time',
        't',
      ]),
      open: open,
      high: _numberOrNull(json, <String>['high', 'h']) ?? open,
      low: _numberOrNull(json, <String>['low', 'l']) ?? close,
      close: close,
      volume: _numberOrNull(json, <String>['volume', 'v']),
    );
  }
}

class TraderOverview {
  const TraderOverview({
    required this.profile,
    required this.portfolioValue,
    required this.gtexCoinPrice,
    required this.dailyPl,
    required this.walletBalance,
    required this.marketCap,
    required this.tradingVolume,
    required this.trending,
    required this.topGainers,
    required this.topLosers,
    required this.mostTradedFanCoins,
    required this.liquidityActivity,
  });

  final TraderProfile profile;
  final double? portfolioValue;
  final double? gtexCoinPrice;
  final double? dailyPl;
  final double? walletBalance;
  final double? marketCap;
  final double? tradingVolume;
  final List<TraderMarket> trending;
  final List<TraderMarket> topGainers;
  final List<TraderMarket> topLosers;
  final List<TraderMarket> mostTradedFanCoins;
  final List<TraderMarket> liquidityActivity;

  factory TraderOverview.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader overview',
    );
    return TraderOverview(
      profile: TraderProfile.fromJson(GteJson.value(json, <String>['profile'])),
      portfolioValue: _numberOrNull(json, <String>[
        'portfolio_value',
        'portfolioValue',
      ]),
      gtexCoinPrice: _numberOrNull(json, <String>[
        'gtex_coin_price',
        'gtexCoinPrice',
      ]),
      dailyPl: _numberOrNull(json, <String>['daily_pl', 'dailyPl']),
      walletBalance: _numberOrNull(json, <String>[
        'wallet_balance',
        'walletBalance',
      ]),
      marketCap: _numberOrNull(json, <String>['market_cap', 'marketCap']),
      tradingVolume: _numberOrNull(json, <String>[
        'trading_volume',
        'tradingVolume',
      ]),
      trending: _marketList(json, <String>['trending']),
      topGainers: _marketList(json, <String>['top_gainers', 'topGainers']),
      topLosers: _marketList(json, <String>['top_losers', 'topLosers']),
      mostTradedFanCoins: _marketList(json, <String>[
        'most_traded_fan_coins',
        'mostTradedFanCoins',
      ]),
      liquidityActivity: _marketList(json, <String>[
        'liquidity_activity',
        'liquidityActivity',
      ]),
    );
  }
}

class TraderBalance {
  const TraderBalance({
    required this.available,
    required this.reserved,
    required this.currency,
    this.total,
    this.lastSyncedAt,
  });

  final double? available;
  final double? reserved;
  final String currency;
  final double? total;
  final DateTime? lastSyncedAt;

  bool get isBlocked => available == null || currency.trim().isEmpty;

  factory TraderBalance.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader balance',
    );
    return TraderBalance(
      available: _numberOrNull(json, <String>[
        'available',
        'available_balance',
        'availableBalance',
        'wallet_balance',
        'walletBalance',
        'balance',
      ]),
      reserved: _numberOrNull(json, <String>[
        'reserved',
        'reserved_balance',
        'reservedBalance',
        'locked',
      ]),
      currency: GteJson.string(json, <String>['currency'], fallback: ''),
      total: _numberOrNull(json, <String>[
        'total',
        'total_balance',
        'totalBalance',
      ]),
      lastSyncedAt: GteJson.dateTimeOrNull(json, <String>[
        'last_synced_at',
        'lastSyncedAt',
        'metrics_updated_at',
        'metricsUpdatedAt',
      ]),
    );
  }

  factory TraderBalance.fromOverview(TraderOverview overview) {
    final Map<String, Object?> snapshot = overview.profile.liquiditySnapshot;
    return TraderBalance(
      available: overview.walletBalance,
      reserved: _numberOrNull(snapshot, <String>[
        'reserved_coin',
        'reserved',
        'reserved_balance',
      ]),
      total: _numberOrNull(snapshot, <String>[
        'total_coin',
        'total',
        'total_balance',
      ]),
      currency: overview.profile.preferredCurrency,
      lastSyncedAt: overview.profile.metricsUpdatedAt,
    );
  }
}

class TraderActivity {
  const TraderActivity({
    required this.id,
    required this.label,
    this.status,
    this.auditRef,
    this.createdAt,
  });

  final String id;
  final String label;
  final String? status;
  final String? auditRef;
  final DateTime? createdAt;

  factory TraderActivity.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader activity',
    );
    return TraderActivity(
      id: GteJson.string(json, <String>['id']),
      label: GteJson.string(json, <String>['label', 'title', 'event']),
      status: GteJson.stringOrNull(json, <String>['status', 'state']),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class TraderDashboard {
  const TraderDashboard({
    required this.balance,
    this.activeOrders,
    this.pendingSettlements,
    this.openDisputes,
    this.recentActivity = const <TraderActivity>[],
  });

  final TraderBalance balance;
  final int? activeOrders;
  final int? pendingSettlements;
  final int? openDisputes;
  final List<TraderActivity> recentActivity;

  factory TraderDashboard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader dashboard',
    );
    return TraderDashboard(
      balance: TraderBalance.fromJson(
        GteJson.value(json, <String>['balance']) ?? json,
      ),
      activeOrders: GteJson.integerOrNull(json, <String>[
        'active_orders',
        'activeOrders',
      ]),
      pendingSettlements: GteJson.integerOrNull(json, <String>[
        'pending_settlements',
        'pendingSettlements',
      ]),
      openDisputes: GteJson.integerOrNull(json, <String>[
        'open_disputes',
        'openDisputes',
      ]),
      recentActivity: GteJson.typedList<TraderActivity>(json, <String>[
        'recent_activity',
        'recentActivity',
      ], TraderActivity.fromJson),
    );
  }

  factory TraderDashboard.fromOverview(TraderOverview overview) {
    final Map<String, Object?> snapshot = overview.profile.liquiditySnapshot;
    final int? openDisputes =
        overview.profile.hasDisputeHistory
            ? overview.profile.disputeHistory.where((
              TraderDisputeRecord record,
            ) {
              final String status = (record.status ?? '').toLowerCase();
              return status == 'open' || status == 'pending';
            }).length
            : null;
    return TraderDashboard(
      balance: TraderBalance.fromOverview(overview),
      activeOrders: GteJson.integerOrNull(snapshot, <String>[
        'open_p2p_offers',
        'active_orders',
      ]),
      pendingSettlements: GteJson.integerOrNull(snapshot, <String>[
        'pending_procurements',
        'pending_settlements',
      ]),
      openDisputes: openDisputes,
    );
  }
}

class TraderOrderCreate {
  const TraderOrderCreate({
    required this.marketId,
    required this.side,
    required this.quantity,
    this.limitPrice,
    this.quoteId,
  });

  final String marketId;
  final String side;
  final double quantity;
  final double? limitPrice;
  final String? quoteId;

  Map<String, Object?> toJson() => <String, Object?>{
    'market_id': marketId,
    'side': side,
    'quantity': quantity,
    if (limitPrice != null) 'limit_price': limitPrice,
    if (quoteId != null) 'quote_id': quoteId,
  };
}

class TraderOrder {
  const TraderOrder({
    required this.id,
    required this.marketId,
    required this.side,
    required this.status,
    required this.quantity,
    this.limitPrice,
    this.currency,
    this.createdAt,
    this.updatedAt,
    this.expiresAt,
    this.filledAt,
    this.quoteId,
    this.quoteExpiresAt,
    this.quoteLocked,
    this.auditRef,
  });

  final String id;
  final String marketId;
  final String side;
  final String? status;
  final double quantity;
  final double? limitPrice;
  final String? currency;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final DateTime? expiresAt;
  final DateTime? filledAt;
  final String? quoteId;
  final DateTime? quoteExpiresAt;
  final bool? quoteLocked;
  final String? auditRef;

  factory TraderOrder.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'trader order');
    return TraderOrder(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      side: GteJson.string(json, <String>['side']),
      status: GteJson.stringOrNull(json, <String>['status']),
      quantity: GteJson.number(json, <String>['quantity']),
      limitPrice:
          GteJson.value(json, <String>['limit_price', 'limitPrice']) == null
              ? null
              : GteJson.number(json, <String>['limit_price', 'limitPrice']),
      currency: GteJson.stringOrNull(json, <String>['currency']),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
      expiresAt: GteJson.dateTimeOrNull(json, <String>[
        'expires_at',
        'expiresAt',
      ]),
      filledAt: GteJson.dateTimeOrNull(json, <String>['filled_at', 'filledAt']),
      quoteId: GteJson.stringOrNull(json, <String>['quote_id', 'quoteId']),
      quoteExpiresAt: GteJson.dateTimeOrNull(json, <String>[
        'quote_expires_at',
        'quoteExpiresAt',
      ]),
      quoteLocked: _boolOrNull(json, <String>['quote_locked', 'quoteLocked']),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

enum TraderPaymentMethod { koraPay, manual }

extension TraderPaymentMethodWire on TraderPaymentMethod {
  String get wireValue {
    return switch (this) {
      TraderPaymentMethod.koraPay => 'korapay',
      TraderPaymentMethod.manual => 'manual',
    };
  }

  String get label {
    return switch (this) {
      TraderPaymentMethod.koraPay => 'KoraPay',
      TraderPaymentMethod.manual => 'Manual bank transfer',
    };
  }
}

TraderPaymentMethod? traderPaymentMethodFromBackend(Object? value) {
  if (value == null) {
    return null;
  }
  final String normalized = value.toString().trim().toLowerCase().replaceAll(
    RegExp(r'[\s_-]+'),
    '',
  );
  if (normalized == 'korapay') {
    return TraderPaymentMethod.koraPay;
  }
  if (normalized == 'manual' ||
      normalized == 'manualpayment' ||
      normalized == 'banktransfer' ||
      normalized == 'manualbanktransfer') {
    return TraderPaymentMethod.manual;
  }
  return null;
}

class TraderQuoteRequest {
  const TraderQuoteRequest({
    required this.marketId,
    required this.side,
    required this.amount,
    required this.currency,
  });

  final String marketId;
  final String side;
  final double amount;
  final String currency;

  Map<String, Object?> toJson() => <String, Object?>{
    'market_id': marketId,
    'side': side,
    'amount': amount,
    'currency': currency,
  };
}

class TraderQuote {
  const TraderQuote({
    required this.id,
    required this.price,
    required this.amount,
    required this.currency,
    this.validUntil,
    this.lockedUntil,
    this.lockSecondsRemaining,
    this.auditRef,
  });

  final String id;
  final double price;
  final double amount;
  final String currency;
  final DateTime? validUntil;
  final DateTime? lockedUntil;
  final int? lockSecondsRemaining;
  final String? auditRef;

  bool get hasBackendLock =>
      lockedUntil != null || lockSecondsRemaining != null;

  int? secondsRemaining({DateTime? now}) {
    final int? backendSeconds = lockSecondsRemaining;
    if (backendSeconds != null) {
      return backendSeconds;
    }
    final DateTime? backendLockedUntil = lockedUntil;
    if (backendLockedUntil == null) {
      return null;
    }
    final DateTime comparisonTime = (now ?? DateTime.now()).toUtc();
    return backendLockedUntil.toUtc().difference(comparisonTime).inSeconds;
  }

  bool isExpired({DateTime? now}) {
    final int? remaining = secondsRemaining(now: now);
    if (remaining != null) {
      return remaining <= 0;
    }
    return true;
  }

  factory TraderQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'trader quote');
    return TraderQuote(
      id: GteJson.string(json, <String>['id', 'quote_id', 'quoteId']),
      price: GteJson.number(json, <String>['price']),
      amount: GteJson.number(json, <String>['amount', 'quantity']),
      currency: GteJson.string(json, <String>['currency'], fallback: ''),
      validUntil: GteJson.dateTimeOrNull(json, <String>[
        'valid_until',
        'validUntil',
        'expires_at',
        'expiresAt',
      ]),
      lockedUntil: GteJson.dateTimeOrNull(json, <String>[
        'locked_until',
        'lockedUntil',
      ]),
      lockSecondsRemaining: GteJson.integerOrNull(json, <String>[
        'lock_seconds_remaining',
        'lockSecondsRemaining',
        'seconds_remaining',
        'secondsRemaining',
      ]),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class TraderDisputeEvent {
  const TraderDisputeEvent({
    required this.id,
    required this.event,
    this.actorId,
    this.auditRef,
    this.createdAt,
  });

  final String id;
  final String event;
  final String? actorId;
  final String? auditRef;
  final DateTime? createdAt;

  factory TraderDisputeEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader dispute event',
    );
    return TraderDisputeEvent(
      id: GteJson.string(json, <String>['id']),
      event: GteJson.string(json, <String>['event', 'type', 'message']),
      actorId: GteJson.stringOrNull(json, <String>['actor_id', 'actorId']),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class TraderDispute {
  const TraderDispute({
    required this.id,
    required this.orderId,
    required this.reason,
    required this.status,
    this.filedAt,
    this.resolvedAt,
    this.resolution,
    this.auditTrail = const <TraderDisputeEvent>[],
    this.auditRef,
  });

  final String id;
  final String orderId;
  final String reason;
  final String status;
  final DateTime? filedAt;
  final DateTime? resolvedAt;
  final String? resolution;
  final List<TraderDisputeEvent> auditTrail;
  final String? auditRef;

  factory TraderDispute.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader dispute',
    );
    return TraderDispute(
      id: GteJson.string(json, <String>['id']),
      orderId: GteJson.string(json, <String>['order_id', 'orderId']),
      reason: GteJson.string(json, <String>['reason']),
      status: GteJson.string(json, <String>['status']),
      filedAt: GteJson.dateTimeOrNull(json, <String>[
        'filed_at',
        'filedAt',
        'created_at',
        'createdAt',
      ]),
      resolvedAt: GteJson.dateTimeOrNull(json, <String>[
        'resolved_at',
        'resolvedAt',
      ]),
      resolution: GteJson.stringOrNull(json, <String>['resolution']),
      auditTrail: GteJson.typedList<TraderDisputeEvent>(json, <String>[
        'audit_trail',
        'auditTrail',
        'events',
      ], TraderDisputeEvent.fromJson),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class FileDisputeRequest {
  const FileDisputeRequest({required this.orderId, required this.reason});

  final String orderId;
  final String reason;

  Map<String, Object?> toJson() => <String, Object?>{
    'order_id': orderId,
    'reason': reason,
  };
}

class TraderSettlement {
  const TraderSettlement({
    required this.id,
    required this.orderId,
    required this.amount,
    required this.currency,
    required this.status,
    this.method,
    this.initiatedAt,
    this.confirmedAt,
    this.eta,
    this.receiptRef,
    this.proofUrl,
    this.auditRef,
  });

  final String id;
  final String orderId;
  final double amount;
  final String currency;
  final String status;
  final TraderPaymentMethod? method;
  final DateTime? initiatedAt;
  final DateTime? confirmedAt;
  final String? eta;
  final String? receiptRef;
  final String? proofUrl;
  final String? auditRef;

  String get etaLabel => eta ?? 'ETA pending.';

  factory TraderSettlement.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader settlement',
    );
    return TraderSettlement(
      id: GteJson.string(json, <String>['id']),
      orderId: GteJson.string(json, <String>['order_id', 'orderId']),
      amount: GteJson.number(json, <String>['amount']),
      currency: GteJson.string(json, <String>['currency'], fallback: ''),
      method: traderPaymentMethodFromBackend(
        GteJson.value(json, <String>['method', 'payment_method']),
      ),
      status: GteJson.string(json, <String>['status']),
      initiatedAt: GteJson.dateTimeOrNull(json, <String>[
        'initiated_at',
        'initiatedAt',
      ]),
      confirmedAt: GteJson.dateTimeOrNull(json, <String>[
        'confirmed_at',
        'confirmedAt',
      ]),
      eta: GteJson.stringOrNull(json, <String>['eta']),
      receiptRef: GteJson.stringOrNull(json, <String>[
        'receipt_ref',
        'receiptRef',
      ]),
      proofUrl: GteJson.stringOrNull(json, <String>['proof_url', 'proofUrl']),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class TraderDepositRequest {
  const TraderDepositRequest({
    required this.amount,
    required this.currency,
    required this.method,
    this.proofAttachmentId,
  });

  final double amount;
  final String currency;
  final TraderPaymentMethod method;
  final String? proofAttachmentId;

  Map<String, Object?> toJson() => <String, Object?>{
    'amount': amount,
    'currency': currency,
    'method': method.wireValue,
    if (proofAttachmentId != null) 'proof_attachment_id': proofAttachmentId,
  };
}

class TraderDepositResult {
  const TraderDepositResult({
    required this.id,
    required this.status,
    this.checkoutUrl,
    this.auditRef,
  });

  final String id;
  final String status;
  final String? checkoutUrl;
  final String? auditRef;

  factory TraderDepositResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader deposit result',
    );
    return TraderDepositResult(
      id: GteJson.string(json, <String>['id']),
      status: GteJson.string(json, <String>['status']),
      checkoutUrl: GteJson.stringOrNull(json, <String>[
        'checkout_url',
        'checkoutUrl',
      ]),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class TraderWithdrawalRequest {
  const TraderWithdrawalRequest({
    required this.amount,
    required this.currency,
    required this.method,
    required this.destinationRef,
  });

  final double amount;
  final String currency;
  final TraderPaymentMethod method;
  final String destinationRef;

  Map<String, Object?> toJson() => <String, Object?>{
    'amount': amount,
    'currency': currency,
    'method': method.wireValue,
    'destination_ref': destinationRef,
  };
}

class TraderWithdrawalResult {
  const TraderWithdrawalResult({
    required this.id,
    required this.status,
    this.auditRef,
  });

  final String id;
  final String status;
  final String? auditRef;

  factory TraderWithdrawalResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader withdrawal result',
    );
    return TraderWithdrawalResult(
      id: GteJson.string(json, <String>['id']),
      status: GteJson.string(json, <String>['status']),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class TraderProcurementQuoteRequest {
  const TraderProcurementQuoteRequest({
    required this.amount,
    this.feeBps = 0,
    this.unit = 'coin',
  });

  final double amount;
  final int feeBps;
  final String unit;

  Map<String, Object?> toJson() => <String, Object?>{
    'amount': amount,
    'fee_bps': feeBps,
    'unit': unit,
  };
}

class TraderProcurementQuote {
  const TraderProcurementQuote({
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.unit,
    required this.sourceScope,
  });

  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final String unit;
  final String sourceScope;

  factory TraderProcurementQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader procurement quote',
    );
    return TraderProcurementQuote(
      grossAmount: GteJson.number(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      unit: GteJson.string(json, <String>['unit']),
      sourceScope: GteJson.string(json, <String>[
        'source_scope',
        'sourceScope',
      ], fallback: 'liquidity'),
    );
  }
}

class TraderProcurementCreateRequest extends TraderProcurementQuoteRequest {
  const TraderProcurementCreateRequest({
    required super.amount,
    super.feeBps,
    super.unit,
    this.notes,
  });

  final String? notes;

  @override
  Map<String, Object?> toJson() => <String, Object?>{
    ...super.toJson(),
    if (notes != null) 'notes': notes,
  };
}

class TraderProcurement {
  const TraderProcurement({
    required this.id,
    required this.reference,
    required this.status,
    required this.unit,
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.sourceScope,
    this.auditRef,
  });

  final String id;
  final String reference;
  final String status;
  final String unit;
  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final String sourceScope;
  final String? auditRef;

  factory TraderProcurement.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader procurement',
    );
    return TraderProcurement(
      id: GteJson.string(json, <String>['id']),
      reference: GteJson.string(json, <String>['reference']),
      status: GteJson.string(json, <String>['status']),
      unit: GteJson.string(json, <String>['unit']),
      grossAmount: GteJson.number(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      sourceScope: GteJson.string(json, <String>[
        'source_scope',
        'sourceScope',
      ], fallback: 'liquidity'),
      auditRef: GteJson.stringOrNull(json, <String>[
        'audit_ref',
        'auditRef',
        'audit_reference',
        'auditReference',
      ]),
    );
  }
}

class TraderP2POfferCreate {
  const TraderP2POfferCreate({
    required this.marketId,
    required this.side,
    required this.quantity,
    required this.unitPrice,
    required this.preferredCurrency,
  });

  final String marketId;
  final String side;
  final double quantity;
  final double unitPrice;
  final String preferredCurrency;

  Map<String, Object?> toJson() => <String, Object?>{
    'market_id': marketId,
    'side': side,
    'quantity': quantity,
    'unit_price': unitPrice,
    'preferred_currency': preferredCurrency,
  };
}

class TraderP2POffer {
  const TraderP2POffer({
    required this.id,
    required this.marketId,
    required this.side,
    required this.status,
    required this.quantity,
    required this.unitPrice,
    required this.preferredCurrency,
  });

  final String id;
  final String marketId;
  final String side;
  final String? status;
  final double quantity;
  final double unitPrice;
  final String preferredCurrency;

  factory TraderP2POffer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader p2p offer',
    );
    return TraderP2POffer(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      side: GteJson.string(json, <String>['side']),
      status: GteJson.stringOrNull(json, <String>['status']),
      quantity: GteJson.number(json, <String>['quantity']),
      unitPrice: GteJson.number(json, <String>['unit_price', 'unitPrice']),
      preferredCurrency: GteJson.string(json, <String>[
        'preferred_currency',
        'preferredCurrency',
      ], fallback: 'USD'),
    );
  }
}

class TraderWatchlistItem {
  const TraderWatchlistItem({required this.id, required this.market});

  final String id;
  final TraderMarket market;

  factory TraderWatchlistItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader watchlist item',
    );
    return TraderWatchlistItem(
      id: GteJson.string(json, <String>['id']),
      market: TraderMarket.fromJson(GteJson.value(json, <String>['market'])),
    );
  }
}

class TraderTotpSetup {
  const TraderTotpSetup({
    required this.secret,
    required this.issuer,
    required this.accountLabel,
  });

  final String secret;
  final String issuer;
  final String accountLabel;

  factory TraderTotpSetup.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader totp setup',
    );
    return TraderTotpSetup(
      secret: GteJson.string(json, <String>['secret']),
      issuer: GteJson.string(json, <String>['issuer'], fallback: 'GTEX'),
      accountLabel: GteJson.string(json, <String>[
        'account_label',
        'accountLabel',
      ], fallback: 'GTEX Trader'),
    );
  }
}

List<TraderMarket> _marketList(Map<String, Object?> json, List<String> keys) {
  return GteJson.typedList<TraderMarket>(json, keys, TraderMarket.fromJson);
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return null;
  }
  if (rawValue is num) {
    return rawValue.toDouble();
  }
  return double.tryParse(rawValue.toString().replaceAll(',', '').trim());
}

bool? _boolOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return null;
  }
  if (rawValue is bool) {
    return rawValue;
  }
  if (rawValue is num) {
    return rawValue != 0;
  }
  final String normalized = rawValue.toString().trim().toLowerCase();
  if (normalized == 'true' ||
      normalized == '1' ||
      normalized == 'yes' ||
      normalized == 'online') {
    return true;
  }
  if (normalized == 'false' ||
      normalized == '0' ||
      normalized == 'no' ||
      normalized == 'offline') {
    return false;
  }
  return null;
}

Map<String, Object?>? _mapOrNull(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return Map<String, Object?>.from(value);
  }
  return null;
}

Map<String, Object?> _jsonMapOrEmpty(Object? value) {
  final Map<String, Object?>? parsed = _mapOrNull(value);
  if (parsed == null) {
    return const <String, Object?>{};
  }
  return Map<String, Object?>.unmodifiable(parsed);
}

List<Object?> _objectList(Object? value) {
  if (value == null) {
    return const <Object?>[];
  }
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return <Object?>[value];
}

List<TraderDisputeRecord> _disputeList(Object? value) {
  final List<TraderDisputeRecord> records = <TraderDisputeRecord>[];
  for (final Object? entry in _objectList(value)) {
    try {
      records.add(TraderDisputeRecord.fromJson(entry));
    } catch (_) {
      continue;
    }
  }
  return List<TraderDisputeRecord>.unmodifiable(records);
}

List<TraderPriceCandle> _candleList(Object? value) {
  final List<TraderPriceCandle> candles = <TraderPriceCandle>[];
  for (final Object? entry in _objectList(value)) {
    try {
      final TraderPriceCandle candle = TraderPriceCandle.fromJson(entry);
      if (candle.high >= candle.low) {
        candles.add(candle);
      }
    } catch (_) {
      continue;
    }
  }
  return List<TraderPriceCandle>.unmodifiable(candles);
}

List<TraderOrderBookLevel> _orderBookLevels(
  Object? value, {
  required bool descending,
}) {
  final List<TraderOrderBookLevel> levels = <TraderOrderBookLevel>[];
  for (final Object? entry in _objectList(value)) {
    try {
      final TraderOrderBookLevel level = TraderOrderBookLevel.fromJson(entry);
      if (level.price > 0 && level.quantity > 0) {
        levels.add(level);
      }
    } catch (_) {
      continue;
    }
  }
  levels.sort((TraderOrderBookLevel left, TraderOrderBookLevel right) {
    return descending
        ? right.price.compareTo(left.price)
        : left.price.compareTo(right.price);
  });
  return List<TraderOrderBookLevel>.unmodifiable(levels);
}

List<String> _canonicalSettlementRails(Object? value) {
  final Set<String> rails = <String>{};
  for (final Object? entry in _objectList(value)) {
    for (final String token in entry.toString().split(RegExp(r'[,/|]+'))) {
      final String normalized = token.trim().toLowerCase().replaceAll(
        RegExp(r'[\s_-]+'),
        '',
      );
      if (normalized == 'korapay') {
        rails.add('KoraPay');
      } else if (normalized == 'manual' ||
          normalized == 'manualpayment' ||
          normalized == 'banktransfer' ||
          normalized == 'manualbanktransfer') {
        rails.add('manual');
      }
    }
  }
  return List<String>.unmodifiable(rails);
}

class _TraderFixtures {
  _TraderFixtures({required this.profile, required this.seedMarkets});

  final TraderProfile profile;
  final List<TraderMarket> seedMarkets;

  static _TraderFixtures seed() {
    final DateTime now = DateTime.parse('2026-05-18T12:00:00Z');
    return _TraderFixtures(
      profile: TraderProfile(
        id: 'trader-profile-fixture',
        userId: 'user-fixture',
        tradingAlias: 'Atlas Desk',
        preferredCurrency: 'USD',
        tradingExperience: 'professional',
        interests: const <String>['GTEX Coin', 'Fan Coins', 'P2P'],
        walletLabel: 'GTEX Prime Wallet',
        status: 'VERIFIED',
        createdAt: now,
        updatedAt: now,
      ),
      seedMarkets: <TraderMarket>[
        TraderMarket(
          id: 'market-gtex',
          symbol: 'GTEX',
          displayName: 'GTEX Coin',
          assetType: 'platform_coin',
          price: 1.42,
          dailyChangePercent: 1.4,
          marketCap: 412800000,
          volume24h: 18200000,
          liquidityScore: 92,
          updatedAt: now,
        ),
        TraderMarket(
          id: 'market-lagfc',
          symbol: 'LAGFC',
          displayName: 'Lagos FC Fan Coin',
          assetType: 'fan_coin',
          price: 0.84,
          dailyChangePercent: 8.7,
          marketCap: 24800000,
          volume24h: 2800000,
          liquidityScore: 84,
          updatedAt: now,
        ),
        TraderMarket(
          id: 'market-acra',
          symbol: 'ACCRA',
          displayName: 'Accra Royals Fan Coin',
          assetType: 'fan_coin',
          price: 0.62,
          dailyChangePercent: 5.1,
          marketCap: 18400000,
          volume24h: 1600000,
          liquidityScore: 76,
          updatedAt: now,
        ),
        TraderMarket(
          id: 'market-lonfc',
          symbol: 'LONFC',
          displayName: 'London United Fan Coin',
          assetType: 'fan_coin',
          price: 1.08,
          dailyChangePercent: -2.9,
          marketCap: 29700000,
          volume24h: 980000,
          liquidityScore: 68,
          updatedAt: now,
        ),
      ],
    );
  }

  Future<TraderOverview> overview() async {
    return TraderOverview(
      profile: profile,
      portfolioValue: 24820,
      gtexCoinPrice: seedMarkets.first.price,
      dailyPl: 312.4,
      walletBalance: 8410.5,
      marketCap: 412800000,
      tradingVolume: 18200000,
      trending: seedMarkets.take(3).toList(growable: false),
      topGainers: seedMarkets
          .where((TraderMarket market) => (market.dailyChangePercent ?? 0) > 0)
          .toList(growable: false),
      topLosers: seedMarkets
          .where((TraderMarket market) => (market.dailyChangePercent ?? 0) < 0)
          .toList(growable: false),
      mostTradedFanCoins: seedMarkets
          .where((TraderMarket market) => market.assetType == 'fan_coin')
          .toList(growable: false),
      liquidityActivity: seedMarkets,
    );
  }

  Future<List<TraderMarket>> markets() async =>
      List<TraderMarket>.of(seedMarkets, growable: false);

  Future<TraderOrder> order(TraderOrderCreate request) async {
    return TraderOrder(
      id: 'order-fixture',
      marketId: request.marketId,
      side: request.side,
      status: 'open',
      quantity: request.quantity,
      limitPrice: request.limitPrice,
    );
  }

  Future<TraderP2POffer> p2pOffer(TraderP2POfferCreate request) async {
    return TraderP2POffer(
      id: 'p2p-fixture',
      marketId: request.marketId,
      side: request.side,
      status: 'open',
      quantity: request.quantity,
      unitPrice: request.unitPrice,
      preferredCurrency: request.preferredCurrency,
    );
  }

  Future<TraderProcurementQuote> procurementQuote(
    TraderProcurementQuoteRequest request,
  ) async {
    final double fee = request.amount * request.feeBps / 10000;
    return TraderProcurementQuote(
      grossAmount: request.amount,
      feeAmount: fee,
      netAmount: request.amount - fee,
      unit: request.unit,
      sourceScope: 'liquidity',
    );
  }

  Future<TraderProcurement> procurement(
    TraderProcurementCreateRequest request,
  ) async {
    final double fee = request.amount * request.feeBps / 10000;
    return TraderProcurement(
      id: 'procurement-fixture',
      reference: 'PO-FIXTURE',
      status: 'requested',
      unit: request.unit,
      grossAmount: request.amount,
      feeAmount: fee,
      netAmount: request.amount - fee,
      sourceScope: 'liquidity',
      auditRef: 'audit-procurement-fixture',
    );
  }

  Future<List<TraderWatchlistItem>> watchlist() async {
    return <TraderWatchlistItem>[
      TraderWatchlistItem(id: 'watch-fixture', market: seedMarkets.first),
    ];
  }

  Future<TraderWatchlistItem> addWatchlist(String marketId) async {
    final TraderMarket market = seedMarkets.firstWhere(
      (TraderMarket entry) => entry.id == marketId,
      orElse: () => seedMarkets.first,
    );
    return TraderWatchlistItem(id: 'watch-fixture', market: market);
  }

  Future<TraderTotpSetup> totpSetup() async {
    return const TraderTotpSetup(
      secret: 'JBSWY3DPEHPK3PXP',
      issuer: 'GTEX',
      accountLabel: 'Atlas Desk',
    );
  }
}
