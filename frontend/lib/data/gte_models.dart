import 'dart:convert';

enum NotificationIntensity {
  light,
  standard,
  scoutMode,
}

enum GteOrderSide {
  buy,
  sell,
}

enum GteOrderStatus {
  open,
  partiallyFilled,
  filled,
  cancelled,
  rejected,
  unknown,
}

enum GteLedgerUnit {
  credit,
  coin,
  unknown,
}

class GteParsingException implements FormatException {
  const GteParsingException(this.messageText, [this.sourceText]);

  final String messageText;
  final Object? sourceText;

  @override
  String get message => messageText;

  @override
  int? get offset => null;

  @override
  Object? get source => sourceText;

  @override
  String toString() => 'GteParsingException: $messageText';
}

class GteJson {
  const GteJson._();

  static Map<String, Object?> map(Object? value, {String label = 'payload'}) {
    if (value is Map<String, Object?>) {
      return value;
    }
    if (value is Map) {
      return value.map(
        (Object? key, Object? entryValue) => MapEntry<String, Object?>(
          key.toString(),
          entryValue,
        ),
      );
    }
    throw GteParsingException('Expected $label to be a JSON object.', value);
  }

  static List<Object?> list(Object? value, {String label = 'payload'}) {
    if (value is List<Object?>) {
      return value;
    }
    if (value is List) {
      return value.cast<Object?>();
    }
    throw GteParsingException('Expected $label to be a JSON list.', value);
  }

  static Object? value(Map<String, Object?> json, List<String> keys) {
    for (final String key in keys) {
      if (json.containsKey(key)) {
        return json[key];
      }
    }
    return null;
  }

  static String string(
    Map<String, Object?> json,
    List<String> keys, {
    String? fallback,
  }) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      if (fallback != null) {
        return fallback;
      }
      throw GteParsingException(
          'Missing required string field: ${keys.join(' / ')}.', json);
    }
    final String parsed = rawValue.toString().trim();
    if (parsed.isEmpty) {
      if (fallback != null) {
        return fallback;
      }
      throw GteParsingException(
          'Empty string field: ${keys.join(' / ')}.', json);
    }
    return parsed;
  }

  static String? stringOrNull(Map<String, Object?> json, List<String> keys) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return null;
    }
    final String parsed = rawValue.toString().trim();
    return parsed.isEmpty ? null : parsed;
  }

  static int integer(
    Map<String, Object?> json,
    List<String> keys, {
    int fallback = 0,
  }) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return fallback;
    }
    if (rawValue is int) {
      return rawValue;
    }
    if (rawValue is num) {
      return rawValue.toInt();
    }
    return int.tryParse(rawValue.toString()) ?? fallback;
  }

  static double number(
    Map<String, Object?> json,
    List<String> keys, {
    double fallback = 0,
  }) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return fallback;
    }
    if (rawValue is num) {
      return rawValue.toDouble();
    }
    return double.tryParse(rawValue.toString()) ?? fallback;
  }

  static bool boolean(
    Map<String, Object?> json,
    List<String> keys, {
    bool fallback = false,
  }) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return fallback;
    }
    if (rawValue is bool) {
      return rawValue;
    }
    final String normalized = rawValue.toString().trim().toLowerCase();
    if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
      return true;
    }
    if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
      return false;
    }
    return fallback;
  }

  static DateTime? dateTimeOrNull(
      Map<String, Object?> json, List<String> keys) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return null;
    }
    if (rawValue is DateTime) {
      return rawValue;
    }
    return DateTime.tryParse(rawValue.toString())?.toUtc();
  }

  static List<T> typedList<T>(
    Map<String, Object?> json,
    List<String> keys,
    T Function(Object? value) parser,
  ) {
    final Object? rawValue = value(json, keys);
    if (rawValue == null) {
      return <T>[];
    }
    return list(rawValue, label: keys.join(' / '))
        .map(parser)
        .toList(growable: false);
  }

  static Map<String, Object?> decodeObject(String body) {
    return map(jsonDecode(body));
  }
}

class TrendPoint {
  const TrendPoint({
    required this.label,
    required this.value,
  });

  final String label;
  final double value;

  factory TrendPoint.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'trend point');
    return TrendPoint(
      label: GteJson.string(json, <String>['label', 'timestamp']),
      value: GteJson.number(
          json, <String>['value', 'close', 'current_value_credits']),
    );
  }
}

class PlayerSnapshot {
  const PlayerSnapshot({
    required this.id,
    required this.name,
    required this.club,
    required this.nation,
    required this.position,
    required this.age,
    required this.marketCredits,
    required this.gsi,
    required this.formRating,
    required this.valueDeltaPct,
    required this.valueTrend,
    required this.recentHighlights,
    this.isFollowed = false,
    this.isWatchlisted = false,
    this.isShortlisted = false,
    this.inTransferRoom = false,
    this.notificationIntensity = NotificationIntensity.standard,
  });

  final String id;
  final String name;
  final String club;
  final String nation;
  final String position;
  final int age;
  final int marketCredits;
  final int gsi;
  final double formRating;
  final double valueDeltaPct;
  final List<TrendPoint> valueTrend;
  final List<String> recentHighlights;
  final bool isFollowed;
  final bool isWatchlisted;
  final bool isShortlisted;
  final bool inTransferRoom;
  final NotificationIntensity notificationIntensity;

  PlayerSnapshot copyWith({
    String? id,
    String? name,
    String? club,
    String? nation,
    String? position,
    int? age,
    int? marketCredits,
    int? gsi,
    double? formRating,
    double? valueDeltaPct,
    List<TrendPoint>? valueTrend,
    List<String>? recentHighlights,
    bool? isFollowed,
    bool? isWatchlisted,
    bool? isShortlisted,
    bool? inTransferRoom,
    NotificationIntensity? notificationIntensity,
  }) {
    return PlayerSnapshot(
      id: id ?? this.id,
      name: name ?? this.name,
      club: club ?? this.club,
      nation: nation ?? this.nation,
      position: position ?? this.position,
      age: age ?? this.age,
      marketCredits: marketCredits ?? this.marketCredits,
      gsi: gsi ?? this.gsi,
      formRating: formRating ?? this.formRating,
      valueDeltaPct: valueDeltaPct ?? this.valueDeltaPct,
      valueTrend: valueTrend ?? this.valueTrend,
      recentHighlights: recentHighlights ?? this.recentHighlights,
      isFollowed: isFollowed ?? this.isFollowed,
      isWatchlisted: isWatchlisted ?? this.isWatchlisted,
      isShortlisted: isShortlisted ?? this.isShortlisted,
      inTransferRoom: inTransferRoom ?? this.inTransferRoom,
      notificationIntensity:
          notificationIntensity ?? this.notificationIntensity,
    );
  }
}

class PlayerProfile {
  const PlayerProfile({
    required this.snapshot,
    required this.gsiTrend,
    required this.awards,
    required this.statBlocks,
    required this.scoutingReport,
    required this.transferSignal,
    this.ticker,
    this.orderBook,
    this.candles,
  });

  final PlayerSnapshot snapshot;
  final List<TrendPoint> gsiTrend;
  final List<String> awards;
  final List<String> statBlocks;
  final String scoutingReport;
  final String transferSignal;
  final GteMarketTicker? ticker;
  final GteOrderBook? orderBook;
  final GteMarketCandles? candles;

  PlayerProfile copyWith({
    PlayerSnapshot? snapshot,
    List<TrendPoint>? gsiTrend,
    List<String>? awards,
    List<String>? statBlocks,
    String? scoutingReport,
    String? transferSignal,
    GteMarketTicker? ticker,
    GteOrderBook? orderBook,
    GteMarketCandles? candles,
  }) {
    return PlayerProfile(
      snapshot: snapshot ?? this.snapshot,
      gsiTrend: gsiTrend ?? this.gsiTrend,
      awards: awards ?? this.awards,
      statBlocks: statBlocks ?? this.statBlocks,
      scoutingReport: scoutingReport ?? this.scoutingReport,
      transferSignal: transferSignal ?? this.transferSignal,
      ticker: ticker ?? this.ticker,
      orderBook: orderBook ?? this.orderBook,
      candles: candles ?? this.candles,
    );
  }
}

class TransferRoomEntry {
  const TransferRoomEntry({
    required this.id,
    required this.headline,
    required this.lane,
    required this.marketCredits,
    required this.activity,
    required this.timestamp,
  });

  final String id;
  final String headline;
  final String lane;
  final int marketCredits;
  final String activity;
  final DateTime timestamp;
}

class MarketPulse {
  const MarketPulse({
    required this.marketMomentum,
    required this.dailyVolumeCredits,
    required this.activeWatchers,
    required this.liveDeals,
    required this.hottestLeague,
    required this.tickers,
    required this.transferRoom,
  });

  final double marketMomentum;
  final int dailyVolumeCredits;
  final int activeWatchers;
  final int liveDeals;
  final String hottestLeague;
  final List<String> tickers;
  final List<TransferRoomEntry> transferRoom;

  MarketPulse copyWith({
    double? marketMomentum,
    int? dailyVolumeCredits,
    int? activeWatchers,
    int? liveDeals,
    String? hottestLeague,
    List<String>? tickers,
    List<TransferRoomEntry>? transferRoom,
  }) {
    return MarketPulse(
      marketMomentum: marketMomentum ?? this.marketMomentum,
      dailyVolumeCredits: dailyVolumeCredits ?? this.dailyVolumeCredits,
      activeWatchers: activeWatchers ?? this.activeWatchers,
      liveDeals: liveDeals ?? this.liveDeals,
      hottestLeague: hottestLeague ?? this.hottestLeague,
      tickers: tickers ?? this.tickers,
      transferRoom: transferRoom ?? this.transferRoom,
    );
  }
}

class GteAuthLoginRequest {
  const GteAuthLoginRequest({
    required this.email,
    required this.password,
  });

  final String email;
  final String password;

  Map<String, Object?> toJson() => <String, Object?>{
        'email': email,
        'password': password,
      };
}

class GteAuthRegisterRequest {
  const GteAuthRegisterRequest({
    required this.email,
    required this.username,
    required this.password,
    this.displayName,
  });

  final String email;
  final String username;
  final String password;
  final String? displayName;

  Map<String, Object?> toJson() => <String, Object?>{
        'email': email,
        'username': username,
        'password': password,
        if (displayName != null) 'display_name': displayName,
      };
}

class GteCurrentUser {
  const GteCurrentUser({
    required this.id,
    required this.email,
    required this.username,
    required this.displayName,
    required this.role,
    this.kycStatus,
    this.isActive = true,
  });

  final String id;
  final String email;
  final String username;
  final String? displayName;
  final String role;
  final String? kycStatus;
  final bool isActive;

  factory GteCurrentUser.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'current user');
    return GteCurrentUser(
      id: GteJson.string(json, <String>['id']),
      email: GteJson.string(json, <String>['email']),
      username: GteJson.string(json, <String>['username']),
      displayName:
          GteJson.stringOrNull(json, <String>['display_name', 'displayName']),
      role: GteJson.string(json, <String>['role'], fallback: 'user'),
      kycStatus:
          GteJson.stringOrNull(json, <String>['kyc_status', 'kycStatus']),
      isActive: GteJson.boolean(json, <String>['is_active', 'isActive'],
          fallback: true),
    );
  }
}

class GteAuthSession {
  const GteAuthSession({
    required this.accessToken,
    required this.tokenType,
    required this.expiresIn,
    required this.user,
  });

  final String accessToken;
  final String tokenType;
  final int expiresIn;
  final GteCurrentUser user;

  factory GteAuthSession.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'auth session');
    return GteAuthSession(
      accessToken:
          GteJson.string(json, <String>['access_token', 'accessToken']),
      tokenType: GteJson.string(json, <String>['token_type', 'tokenType'],
          fallback: 'bearer'),
      expiresIn: GteJson.integer(json, <String>['expires_in', 'expiresIn'],
          fallback: 0),
      user: GteCurrentUser.fromJson(GteJson.value(json, <String>['user'])),
    );
  }
}

class GteMarketTicker {
  const GteMarketTicker({
    required this.playerId,
    required this.symbol,
    required this.lastPrice,
    required this.bestBid,
    required this.bestAsk,
    required this.spread,
    required this.midPrice,
    required this.referencePrice,
    required this.dayChange,
    required this.dayChangePercent,
    required this.volume24h,
  });

  final String playerId;
  final String? symbol;
  final double? lastPrice;
  final double? bestBid;
  final double? bestAsk;
  final double? spread;
  final double? midPrice;
  final double? referencePrice;
  final double dayChange;
  final double dayChangePercent;
  final double volume24h;

  factory GteMarketTicker.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market ticker');
    return GteMarketTicker(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      symbol: GteJson.stringOrNull(json, <String>['symbol', 'player_name']),
      lastPrice:
          GteJson.value(json, <String>['last_price', 'lastPrice']) == null
              ? null
              : GteJson.number(json, <String>['last_price', 'lastPrice']),
      bestBid: GteJson.value(json, <String>['best_bid', 'bestBid']) == null
          ? null
          : GteJson.number(json, <String>['best_bid', 'bestBid']),
      bestAsk: GteJson.value(json, <String>['best_ask', 'bestAsk']) == null
          ? null
          : GteJson.number(json, <String>['best_ask', 'bestAsk']),
      spread: GteJson.value(json, <String>['spread']) == null
          ? null
          : GteJson.number(json, <String>['spread']),
      midPrice: GteJson.value(json, <String>['mid_price', 'midPrice']) == null
          ? null
          : GteJson.number(json, <String>['mid_price', 'midPrice']),
      referencePrice: GteJson.value(
                  json, <String>['reference_price', 'referencePrice']) ==
              null
          ? null
          : GteJson.number(json, <String>['reference_price', 'referencePrice']),
      dayChange: GteJson.number(json, <String>['day_change', 'dayChange']),
      dayChangePercent: GteJson.number(
          json, <String>['day_change_percent', 'dayChangePercent']),
      volume24h: GteJson.number(json, <String>['volume_24h', 'volume24h']),
    );
  }
}

class GteMarketCandle {
  const GteMarketCandle({
    required this.timestamp,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });

  final DateTime timestamp;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;

  factory GteMarketCandle.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market candle');
    return GteMarketCandle(
      timestamp: GteJson.dateTimeOrNull(json, <String>['timestamp']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      open: GteJson.number(json, <String>['open']),
      high: GteJson.number(json, <String>['high']),
      low: GteJson.number(json, <String>['low']),
      close: GteJson.number(json, <String>['close']),
      volume: GteJson.number(json, <String>['volume']),
    );
  }
}

class GteMarketCandles {
  const GteMarketCandles({
    required this.playerId,
    required this.interval,
    required this.candles,
  });

  final String playerId;
  final String interval;
  final List<GteMarketCandle> candles;

  factory GteMarketCandles.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market candles');
    return GteMarketCandles(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      interval: GteJson.string(json, <String>['interval'], fallback: '1h'),
      candles: GteJson.typedList(
          json, <String>['candles'], GteMarketCandle.fromJson),
    );
  }
}

class GteOrderBookLevel {
  const GteOrderBookLevel({
    required this.price,
    required this.quantity,
    required this.orderCount,
  });

  final double price;
  final double quantity;
  final int orderCount;

  factory GteOrderBookLevel.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'order book level');
    return GteOrderBookLevel(
      price: GteJson.number(json, <String>['price']),
      quantity: GteJson.number(json, <String>['quantity']),
      orderCount: GteJson.integer(json, <String>['order_count', 'orderCount'],
          fallback: 1),
    );
  }
}

class GteOrderBook {
  const GteOrderBook({
    required this.playerId,
    required this.bids,
    required this.asks,
    required this.generatedAt,
  });

  final String playerId;
  final List<GteOrderBookLevel> bids;
  final List<GteOrderBookLevel> asks;
  final DateTime? generatedAt;

  factory GteOrderBook.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'order book');
    return GteOrderBook(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      bids:
          GteJson.typedList(json, <String>['bids'], GteOrderBookLevel.fromJson),
      asks:
          GteJson.typedList(json, <String>['asks'], GteOrderBookLevel.fromJson),
      generatedAt:
          GteJson.dateTimeOrNull(json, <String>['generated_at', 'generatedAt']),
    );
  }
}

class GteWalletSummary {
  const GteWalletSummary({
    required this.availableBalance,
    required this.reservedBalance,
    required this.totalBalance,
    required this.currency,
  });

  final double availableBalance;
  final double reservedBalance;
  final double totalBalance;
  final GteLedgerUnit currency;

  factory GteWalletSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'wallet summary');
    return GteWalletSummary(
      availableBalance: GteJson.number(
          json, <String>['available_balance', 'availableBalance']),
      reservedBalance:
          GteJson.number(json, <String>['reserved_balance', 'reservedBalance']),
      totalBalance:
          GteJson.number(json, <String>['total_balance', 'totalBalance']),
      currency: _ledgerUnitFromString(
          GteJson.string(json, <String>['currency'], fallback: 'unknown')),
    );
  }
}

class GteWalletLedgerEntry {
  const GteWalletLedgerEntry({
    required this.id,
    required this.amount,
    required this.reason,
    required this.description,
    required this.createdAt,
  });

  final String id;
  final double amount;
  final String reason;
  final String? description;
  final DateTime? createdAt;

  factory GteWalletLedgerEntry.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'wallet ledger entry');
    return GteWalletLedgerEntry(
      id: GteJson.string(json, <String>['id']),
      amount: GteJson.number(json, <String>['amount']),
      reason: GteJson.string(json, <String>['reason']),
      description: GteJson.stringOrNull(json, <String>['description']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
    );
  }
}

class GteWalletLedgerPage {
  const GteWalletLedgerPage({
    required this.page,
    required this.pageSize,
    required this.total,
    required this.items,
  });

  final int page;
  final int pageSize;
  final int total;
  final List<GteWalletLedgerEntry> items;

  factory GteWalletLedgerPage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'wallet ledger page');
    return GteWalletLedgerPage(
      page: GteJson.integer(json, <String>['page'], fallback: 1),
      pageSize: GteJson.integer(json, <String>['page_size', 'pageSize'],
          fallback: 20),
      total: GteJson.integer(json, <String>['total']),
      items: GteJson.typedList(
          json, <String>['items'], GteWalletLedgerEntry.fromJson),
    );
  }
}

class GtePortfolioHolding {
  const GtePortfolioHolding({
    required this.playerId,
    required this.quantity,
    required this.averageCost,
    required this.currentPrice,
    required this.marketValue,
    required this.unrealizedPl,
    required this.unrealizedPlPercent,
  });

  final String playerId;
  final double quantity;
  final double averageCost;
  final double currentPrice;
  final double marketValue;
  final double unrealizedPl;
  final double unrealizedPlPercent;

  factory GtePortfolioHolding.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'portfolio holding');
    return GtePortfolioHolding(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      quantity: GteJson.number(json, <String>['quantity']),
      averageCost:
          GteJson.number(json, <String>['average_cost', 'averageCost']),
      currentPrice:
          GteJson.number(json, <String>['current_price', 'currentPrice']),
      marketValue:
          GteJson.number(json, <String>['market_value', 'marketValue']),
      unrealizedPl:
          GteJson.number(json, <String>['unrealized_pl', 'unrealizedPl']),
      unrealizedPlPercent: GteJson.number(
          json, <String>['unrealized_pl_percent', 'unrealizedPlPercent']),
    );
  }
}

class GtePortfolioSummary {
  const GtePortfolioSummary({
    required this.totalMarketValue,
    required this.cashBalance,
    required this.totalEquity,
    required this.unrealizedPlTotal,
    required this.realizedPlTotal,
  });

  final double totalMarketValue;
  final double cashBalance;
  final double totalEquity;
  final double unrealizedPlTotal;
  final double realizedPlTotal;

  factory GtePortfolioSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'portfolio summary');
    return GtePortfolioSummary(
      totalMarketValue: GteJson.number(
          json, <String>['total_market_value', 'totalMarketValue']),
      cashBalance:
          GteJson.number(json, <String>['cash_balance', 'cashBalance']),
      totalEquity:
          GteJson.number(json, <String>['total_equity', 'totalEquity']),
      unrealizedPlTotal: GteJson.number(
          json, <String>['unrealized_pl_total', 'unrealizedPlTotal']),
      realizedPlTotal: GteJson.number(
          json, <String>['realized_pl_total', 'realizedPlTotal']),
    );
  }
}

class GtePortfolioView {
  const GtePortfolioView({
    required this.holdings,
  });

  final List<GtePortfolioHolding> holdings;

  factory GtePortfolioView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'portfolio');
    return GtePortfolioView(
      holdings: GteJson.typedList(
          json, <String>['holdings'], GtePortfolioHolding.fromJson),
    );
  }
}

class GteOrderCreateRequest {
  const GteOrderCreateRequest({
    required this.playerId,
    required this.side,
    required this.quantity,
    this.maxPrice,
  });

  final String playerId;
  final GteOrderSide side;
  final double quantity;
  final double? maxPrice;

  Map<String, Object?> toJson() => <String, Object?>{
        'player_id': playerId,
        'side': side.name,
        'quantity': quantity.toStringAsFixed(4),
        if (maxPrice != null) 'max_price': maxPrice!.toStringAsFixed(4),
      };
}

class GteOrderExecution {
  const GteOrderExecution({
    required this.payload,
  });

  final Map<String, Object?> payload;

  factory GteOrderExecution.fromJson(Object? value) {
    return GteOrderExecution(
      payload: GteJson.map(value, label: 'order execution'),
    );
  }
}

class GteOrderExecutionSummary {
  const GteOrderExecutionSummary({
    required this.executionCount,
    required this.totalNotional,
    required this.averagePrice,
    this.lastExecutedAt,
    this.executions = const <GteOrderExecution>[],
  });

  final int executionCount;
  final double totalNotional;
  final double? averagePrice;
  final DateTime? lastExecutedAt;
  final List<GteOrderExecution> executions;

  factory GteOrderExecutionSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'order execution summary');
    return GteOrderExecutionSummary(
      executionCount:
          GteJson.integer(json, <String>['execution_count', 'executionCount']),
      totalNotional:
          GteJson.number(json, <String>['total_notional', 'totalNotional']),
      averagePrice:
          GteJson.value(json, <String>['average_price', 'averagePrice']) == null
              ? null
              : GteJson.number(json, <String>['average_price', 'averagePrice']),
      lastExecutedAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_executed_at', 'lastExecutedAt'],
      ),
      executions: GteJson.typedList(
        json,
        <String>['executions'],
        GteOrderExecution.fromJson,
      ),
    );
  }
}

class GteOrderRecord {
  const GteOrderRecord({
    required this.id,
    required this.playerId,
    required this.side,
    required this.status,
    required this.quantity,
    required this.remainingQuantity,
    required this.maxPrice,
    required this.reservedAmount,
    required this.executionSummary,
    this.userId,
    this.filledQuantity = 0,
    this.currency = GteLedgerUnit.credit,
    this.holdTransactionId,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String playerId;
  final GteOrderSide side;
  final GteOrderStatus status;
  final double quantity;
  final double filledQuantity;
  final double remainingQuantity;
  final double? maxPrice;
  final double reservedAmount;
  final GteOrderExecutionSummary executionSummary;
  final String? userId;
  final GteLedgerUnit currency;
  final String? holdTransactionId;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get canCancel =>
      status == GteOrderStatus.open || status == GteOrderStatus.partiallyFilled;

  factory GteOrderRecord.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'order');
    return GteOrderRecord(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.stringOrNull(json, <String>['user_id', 'userId']),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      side: _orderSideFromString(GteJson.string(json, <String>['side'])),
      status: _orderStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'unknown')),
      quantity: GteJson.number(json, <String>['quantity']),
      filledQuantity:
          GteJson.number(json, <String>['filled_quantity', 'filledQuantity']),
      remainingQuantity: GteJson.number(
          json, <String>['remaining_quantity', 'remainingQuantity']),
      maxPrice: GteJson.value(json, <String>['max_price', 'maxPrice']) == null
          ? null
          : GteJson.number(json, <String>['max_price', 'maxPrice']),
      currency: _ledgerUnitFromString(
        GteJson.string(json, <String>['currency'], fallback: 'credit'),
      ),
      reservedAmount:
          GteJson.number(json, <String>['reserved_amount', 'reservedAmount']),
      holdTransactionId: GteJson.stringOrNull(
        json,
        <String>['hold_transaction_id', 'holdTransactionId'],
      ),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
      executionSummary: GteOrderExecutionSummary.fromJson(
        GteJson.value(
                json, <String>['execution_summary', 'executionSummary']) ??
            const <String, Object?>{},
      ),
    );
  }
}

class GteOrderListView {
  const GteOrderListView({
    required this.items,
    required this.limit,
    required this.offset,
    required this.total,
  });

  final List<GteOrderRecord> items;
  final int limit;
  final int offset;
  final int total;

  factory GteOrderListView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'order list');
    return GteOrderListView(
      items:
          GteJson.typedList(json, <String>['items'], GteOrderRecord.fromJson),
      limit: GteJson.integer(json, <String>['limit'], fallback: 20),
      offset: GteJson.integer(json, <String>['offset']),
      total: GteJson.integer(json, <String>['total']),
    );
  }
}

GteOrderSide _orderSideFromString(String value) {
  return value.toLowerCase() == 'sell' ? GteOrderSide.sell : GteOrderSide.buy;
}

GteOrderStatus _orderStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'open':
      return GteOrderStatus.open;
    case 'partially_filled':
      return GteOrderStatus.partiallyFilled;
    case 'filled':
      return GteOrderStatus.filled;
    case 'cancelled':
      return GteOrderStatus.cancelled;
    case 'rejected':
      return GteOrderStatus.rejected;
    default:
      return GteOrderStatus.unknown;
  }
}

GteLedgerUnit _ledgerUnitFromString(String value) {
  switch (value.toLowerCase()) {
    case 'credit':
      return GteLedgerUnit.credit;
    case 'coin':
      return GteLedgerUnit.coin;
    default:
      return GteLedgerUnit.unknown;
  }
}
