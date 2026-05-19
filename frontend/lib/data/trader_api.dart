import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';

class TraderApi {
  TraderApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final _TraderFixtures fixtures;

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
    );
  }

  Future<TraderOverview> overview() {
    return client.withFallback<TraderOverview>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/trader/overview',
      );
      return TraderOverview.fromJson(payload);
    }, fixtures.overview);
  }

  Future<List<TraderMarket>> listMarkets() {
    return client.withFallback<List<TraderMarket>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/v2/trader/markets',
      );
      return payload.map(TraderMarket.fromJson).toList(growable: false);
    }, fixtures.markets);
  }

  Future<TraderOrder> placeOrder(TraderOrderCreate request) {
    return client.withFallback<TraderOrder>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/orders',
        request.toJson(),
      );
      return TraderOrder.fromJson(payload);
    }, () => fixtures.order(request));
  }

  Future<TraderP2POffer> createP2POffer(TraderP2POfferCreate request) {
    return client.withFallback<TraderP2POffer>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/p2p',
        request.toJson(),
      );
      return TraderP2POffer.fromJson(payload);
    }, () => fixtures.p2pOffer(request));
  }

  Future<List<TraderWatchlistItem>> listWatchlist() {
    return client.withFallback<List<TraderWatchlistItem>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/v2/trader/watchlist',
      );
      return payload.map(TraderWatchlistItem.fromJson).toList(growable: false);
    }, fixtures.watchlist);
  }

  Future<TraderWatchlistItem> addWatchlist(String marketId) {
    return client.withFallback<TraderWatchlistItem>(() async {
      final Map<String, dynamic> payload = await _postMap(
        '/api/v2/trader/watchlist',
        <String, Object?>{'market_id': marketId},
      );
      return TraderWatchlistItem.fromJson(payload);
    }, () => fixtures.addWatchlist(marketId));
  }

  Future<TraderTotpSetup> setupTotp() {
    return client.withFallback<TraderTotpSetup>(() async {
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

  factory TraderProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader profile',
    );
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
  });

  final String id;
  final String symbol;
  final String displayName;
  final String assetType;
  final double price;
  final double dailyChangePercent;
  final double marketCap;
  final double volume24h;
  final int liquidityScore;
  final DateTime updatedAt;

  factory TraderMarket.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'trader market',
    );
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
      price: GteJson.number(json, <String>['price']),
      dailyChangePercent: GteJson.number(json, <String>[
        'daily_change_percent',
        'dailyChangePercent',
      ]),
      marketCap: GteJson.number(json, <String>['market_cap', 'marketCap']),
      volume24h: GteJson.number(json, <String>['volume_24h', 'volume24h']),
      liquidityScore: GteJson.integer(json, <String>[
        'liquidity_score',
        'liquidityScore',
      ]),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
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
  final double portfolioValue;
  final double gtexCoinPrice;
  final double dailyPl;
  final double walletBalance;
  final double marketCap;
  final double tradingVolume;
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
      portfolioValue: GteJson.number(json, <String>[
        'portfolio_value',
        'portfolioValue',
      ]),
      gtexCoinPrice: GteJson.number(json, <String>[
        'gtex_coin_price',
        'gtexCoinPrice',
      ]),
      dailyPl: GteJson.number(json, <String>['daily_pl', 'dailyPl']),
      walletBalance: GteJson.number(json, <String>[
        'wallet_balance',
        'walletBalance',
      ]),
      marketCap: GteJson.number(json, <String>['market_cap', 'marketCap']),
      tradingVolume: GteJson.number(json, <String>[
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

class TraderOrderCreate {
  const TraderOrderCreate({
    required this.marketId,
    required this.side,
    required this.quantity,
    this.limitPrice,
  });

  final String marketId;
  final String side;
  final double quantity;
  final double? limitPrice;

  Map<String, Object?> toJson() => <String, Object?>{
    'market_id': marketId,
    'side': side,
    'quantity': quantity,
    if (limitPrice != null) 'limit_price': limitPrice,
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
  });

  final String id;
  final String marketId;
  final String side;
  final String status;
  final double quantity;
  final double? limitPrice;

  factory TraderOrder.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'trader order');
    return TraderOrder(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      side: GteJson.string(json, <String>['side']),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      quantity: GteJson.number(json, <String>['quantity']),
      limitPrice:
          GteJson.value(json, <String>['limit_price', 'limitPrice']) == null
              ? null
              : GteJson.number(json, <String>['limit_price', 'limitPrice']),
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
  final String status;
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
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
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
          .where((TraderMarket market) => market.dailyChangePercent > 0)
          .toList(growable: false),
      topLosers: seedMarkets
          .where((TraderMarket market) => market.dailyChangePercent < 0)
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
