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

enum GtePaymentMode {
  manual,
  automatic,
}

enum GteRateDirection {
  fiatPerCoin,
  coinPerFiat,
}

enum GteDepositStatus {
  awaitingPayment,
  paymentSubmitted,
  underReview,
  confirmed,
  rejected,
  expired,
  disputed,
}

enum GteWithdrawalStatus {
  draft,
  pendingKyc,
  pendingReview,
  approved,
  rejected,
  processing,
  paid,
  disputed,
  cancelled,
}

enum GteKycStatus {
  unverified,
  pending,
  partialVerifiedNoId,
  fullyVerified,
  rejected,
}

enum GteDisputeStatus {
  open,
  awaitingUser,
  awaitingAdmin,
  resolved,
  closed,
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
    required this.fullName,
    required this.phoneNumber,
    required this.isOver18,
    this.username,
    required this.password,
  });

  final String email;
  final String fullName;
  final String phoneNumber;
  final bool isOver18;
  final String? username;
  final String password;

  Map<String, Object?> toJson() => <String, Object?>{
        'email': email,
        'full_name': fullName,
        'phone_number': phoneNumber,
        'is_over_18': isOver18,
        if (username != null) 'username': username,
        'password': password,
      };
}

class GteCurrentUser {
  const GteCurrentUser({
    required this.id,
    required this.email,
    required this.username,
    required this.fullName,
    required this.phoneNumber,
    required this.displayName,
    required this.role,
    this.kycStatus,
    this.isActive = true,
    this.ageConfirmedAt,
  });

  final String id;
  final String email;
  final String username;
  final String? fullName;
  final String? phoneNumber;
  final String? displayName;
  final String role;
  final String? kycStatus;
  final bool isActive;
  final DateTime? ageConfirmedAt;

  factory GteCurrentUser.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'current user');
    return GteCurrentUser(
      id: GteJson.string(json, <String>['id']),
      email: GteJson.string(json, <String>['email']),
      username: GteJson.string(json, <String>['username']),
      fullName: GteJson.stringOrNull(json, <String>['full_name', 'fullName']),
      phoneNumber:
          GteJson.stringOrNull(json, <String>['phone_number', 'phoneNumber']),
      displayName:
          GteJson.stringOrNull(json, <String>['display_name', 'displayName']),
      role: GteJson.string(json, <String>['role'], fallback: 'user'),
      kycStatus:
          GteJson.stringOrNull(json, <String>['kyc_status', 'kycStatus']),
      isActive: GteJson.boolean(json, <String>['is_active', 'isActive'],
          fallback: true),
      ageConfirmedAt: GteJson.dateTimeOrNull(
          json, <String>['age_confirmed_at', 'ageConfirmedAt']),
    );
  }
}

class GteAuthSession {
  const GteAuthSession({
    required this.accessToken,
    required this.tokenType,
    required this.expiresIn,
    required this.user,
    this.permissions = const <String>[],
    this.landingRoute,
  });

  final String accessToken;
  final String tokenType;
  final int expiresIn;
  final GteCurrentUser user;
  final List<String> permissions;
  final String? landingRoute;

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
      permissions: GteJson.typedList<String>(json, <String>['permissions'], (Object? value) => value.toString()),
      landingRoute: GteJson.stringOrNull(json, <String>['landing_route', 'landingRoute']),
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

class GteWalletOverview {
  const GteWalletOverview({
    required this.availableBalance,
    required this.pendingDeposits,
    required this.pendingWithdrawals,
    required this.totalInflow,
    required this.totalOutflow,
    required this.withdrawableNow,
    required this.currency,
    this.countryCode,
    this.requiredPolicyAcceptancesMissing = 0,
    this.policyBlocked = false,
    this.policyBlockReason,
  });

  final double availableBalance;
  final double pendingDeposits;
  final double pendingWithdrawals;
  final double totalInflow;
  final double totalOutflow;
  final double withdrawableNow;
  final GteLedgerUnit currency;
  final String? countryCode;
  final int requiredPolicyAcceptancesMissing;
  final bool policyBlocked;
  final String? policyBlockReason;

  factory GteWalletOverview.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'wallet overview');
    return GteWalletOverview(
      availableBalance:
          GteJson.number(json, <String>['available_balance', 'availableBalance']),
      pendingDeposits:
          GteJson.number(json, <String>['pending_deposits', 'pendingDeposits']),
      pendingWithdrawals: GteJson.number(
          json, <String>['pending_withdrawals', 'pendingWithdrawals']),
      totalInflow:
          GteJson.number(json, <String>['total_inflow', 'totalInflow']),
      totalOutflow:
          GteJson.number(json, <String>['total_outflow', 'totalOutflow']),
      withdrawableNow:
          GteJson.number(json, <String>['withdrawable_now', 'withdrawableNow']),
      currency: _ledgerUnitFromString(
          GteJson.string(json, <String>['currency'], fallback: 'coin')),
      countryCode: GteJson.stringOrNull(json, <String>['country_code', 'countryCode']),
      requiredPolicyAcceptancesMissing: GteJson.integer(
        json,
        <String>['required_policy_acceptances_missing', 'requiredPolicyAcceptancesMissing'],
      ),
      policyBlocked:
          GteJson.boolean(json, <String>['policy_blocked', 'policyBlocked']),
      policyBlockReason: GteJson.stringOrNull(
          json, <String>['policy_block_reason', 'policyBlockReason']),
    );
  }
}

class GteWithdrawalEligibility {
  const GteWithdrawalEligibility({
    required this.availableBalance,
    required this.withdrawableNow,
    required this.remainingAllowance,
    required this.nextEligibleAt,
    required this.kycStatus,
    required this.requiresKyc,
    required this.requiresBankAccount,
    required this.pendingWithdrawals,
    this.countryCode,
    this.countryWithdrawalsEnabled = true,
    this.missingRequiredPolicies = const <String>[],
    this.policyBlocked = false,
    this.policyBlockReason,
  });

  final double availableBalance;
  final double withdrawableNow;
  final double remainingAllowance;
  final DateTime? nextEligibleAt;
  final GteKycStatus kycStatus;
  final bool requiresKyc;
  final bool requiresBankAccount;
  final double pendingWithdrawals;
  final String? countryCode;
  final bool countryWithdrawalsEnabled;
  final List<String> missingRequiredPolicies;
  final bool policyBlocked;
  final String? policyBlockReason;

  factory GteWithdrawalEligibility.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'withdrawal eligibility');
    return GteWithdrawalEligibility(
      availableBalance:
          GteJson.number(json, <String>['available_balance', 'availableBalance']),
      withdrawableNow:
          GteJson.number(json, <String>['withdrawable_now', 'withdrawableNow']),
      remainingAllowance: GteJson.number(
          json, <String>['remaining_allowance', 'remainingAllowance']),
      nextEligibleAt: GteJson.dateTimeOrNull(
          json, <String>['next_eligible_at', 'nextEligibleAt']),
      kycStatus: _kycStatusFromString(GteJson.string(
          json, <String>['kyc_status', 'kycStatus'], fallback: 'unverified')),
      requiresKyc:
          GteJson.boolean(json, <String>['requires_kyc', 'requiresKyc']),
      requiresBankAccount: GteJson.boolean(
          json, <String>['requires_bank_account', 'requiresBankAccount']),
      pendingWithdrawals: GteJson.number(
          json, <String>['pending_withdrawals', 'pendingWithdrawals']),
      countryCode: GteJson.stringOrNull(json, <String>['country_code', 'countryCode']),
      countryWithdrawalsEnabled: GteJson.boolean(
        json,
        <String>['country_withdrawals_enabled', 'countryWithdrawalsEnabled'],
        fallback: true,
      ),
      missingRequiredPolicies: GteJson.typedList(
        json,
        <String>['missing_required_policies', 'missingRequiredPolicies'],
        (Object? value) => value?.toString() ?? '',
      ).where((String value) => value.trim().isNotEmpty).toList(growable: false),
      policyBlocked:
          GteJson.boolean(json, <String>['policy_blocked', 'policyBlocked']),
      policyBlockReason: GteJson.stringOrNull(
          json, <String>['policy_block_reason', 'policyBlockReason']),
    );
  }
}

class GteWithdrawalQuote {
  const GteWithdrawalQuote({
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.totalDebit,
    required this.sourceScope,
    required this.currencyCode,
    required this.rateValue,
    required this.rateDirection,
    required this.estimatedFiatPayout,
    required this.processorMode,
    required this.payoutChannel,
    required this.feeBps,
    required this.minimumFee,
    required this.eligibility,
    this.blockedReason,
  });

  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final double totalDebit;
  final String sourceScope;
  final String currencyCode;
  final double rateValue;
  final GteRateDirection rateDirection;
  final double estimatedFiatPayout;
  final String processorMode;
  final String payoutChannel;
  final int feeBps;
  final double minimumFee;
  final GteWithdrawalEligibility eligibility;
  final String? blockedReason;

  factory GteWithdrawalQuote.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'withdrawal quote');
    return GteWithdrawalQuote(
      grossAmount:
          GteJson.number(json, <String>['gross_amount', 'grossAmount']),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      totalDebit:
          GteJson.number(json, <String>['total_debit', 'totalDebit']),
      sourceScope: GteJson.string(
          json, <String>['source_scope', 'sourceScope'],
          fallback: 'trade'),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      rateValue:
          GteJson.number(json, <String>['rate_value', 'rateValue']),
      rateDirection: _rateDirectionFromString(GteJson.string(
          json, <String>['rate_direction', 'rateDirection'],
          fallback: 'fiat_per_coin')),
      estimatedFiatPayout: GteJson.number(
          json, <String>['estimated_fiat_payout', 'estimatedFiatPayout']),
      processorMode: GteJson.string(
          json, <String>['processor_mode', 'processorMode'],
          fallback: 'manual_bank_transfer'),
      payoutChannel: GteJson.string(
          json, <String>['payout_channel', 'payoutChannel'],
          fallback: 'bank_transfer'),
      feeBps: GteJson.integer(json, <String>['fee_bps', 'feeBps']),
      minimumFee:
          GteJson.number(json, <String>['minimum_fee', 'minimumFee']),
      eligibility: GteWithdrawalEligibility.fromJson(
        GteJson.value(json, <String>['eligibility']),
      ),
      blockedReason: GteJson.stringOrNull(
          json, <String>['blocked_reason', 'blockedReason']),
    );
  }
}

class GteWithdrawalQuoteRequest {
  const GteWithdrawalQuoteRequest({
    required this.amountCoin,
    this.sourceScope = 'trade',
  });

  final double amountCoin;
  final String sourceScope;

  Map<String, Object?> toJson() => <String, Object?>{
        'amount_coin': amountCoin,
        'source_scope': sourceScope,
      };
}

class GteWithdrawalReceipt {
  const GteWithdrawalReceipt({
    required this.withdrawal,
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.totalDebit,
    required this.sourceScope,
    required this.processorMode,
    required this.payoutChannel,
  });

  final GteTreasuryWithdrawalRequest withdrawal;
  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final double totalDebit;
  final String sourceScope;
  final String processorMode;
  final String payoutChannel;

  factory GteWithdrawalReceipt.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'withdrawal receipt');
    return GteWithdrawalReceipt(
      withdrawal: GteTreasuryWithdrawalRequest.fromJson(
        GteJson.value(json, <String>['withdrawal']),
      ),
      grossAmount:
          GteJson.number(json, <String>['gross_amount', 'grossAmount']),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      totalDebit:
          GteJson.number(json, <String>['total_debit', 'totalDebit']),
      sourceScope: GteJson.string(
          json, <String>['source_scope', 'sourceScope'],
          fallback: 'trade'),
      processorMode: GteJson.string(
          json, <String>['processor_mode', 'processorMode'],
          fallback: 'manual_bank_transfer'),
      payoutChannel: GteJson.string(
          json, <String>['payout_channel', 'payoutChannel'],
          fallback: 'bank_transfer'),
    );
  }
}



class GtePolicyDocumentVersionSummary {
  const GtePolicyDocumentVersionSummary({
    required this.id,
    required this.versionLabel,
    required this.effectiveAt,
    required this.publishedAt,
    this.changelog,
  });

  final String id;
  final String versionLabel;
  final DateTime? effectiveAt;
  final DateTime? publishedAt;
  final String? changelog;

  factory GtePolicyDocumentVersionSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'policy document version');
    return GtePolicyDocumentVersionSummary(
      id: GteJson.string(json, <String>['id']),
      versionLabel:
          GteJson.string(json, <String>['version_label', 'versionLabel']),
      effectiveAt: GteJson.dateTimeOrNull(
          json, <String>['effective_at', 'effectiveAt']),
      publishedAt: GteJson.dateTimeOrNull(
          json, <String>['published_at', 'publishedAt']),
      changelog: GteJson.stringOrNull(json, <String>['changelog']),
    );
  }
}

class GtePolicyDocumentSummary {
  const GtePolicyDocumentSummary({
    required this.id,
    required this.documentKey,
    required this.title,
    required this.isMandatory,
    required this.active,
    this.latestVersion,
  });

  final String id;
  final String documentKey;
  final String title;
  final bool isMandatory;
  final bool active;
  final GtePolicyDocumentVersionSummary? latestVersion;

  factory GtePolicyDocumentSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'policy document summary');
    final Object? latestVersionPayload =
        GteJson.value(json, <String>['latest_version', 'latestVersion']);
    return GtePolicyDocumentSummary(
      id: GteJson.string(json, <String>['id']),
      documentKey:
          GteJson.string(json, <String>['document_key', 'documentKey']),
      title: GteJson.string(json, <String>['title']),
      isMandatory:
          GteJson.boolean(json, <String>['is_mandatory', 'isMandatory']),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      latestVersion: latestVersionPayload == null
          ? null
          : GtePolicyDocumentVersionSummary.fromJson(latestVersionPayload),
    );
  }
}

class GtePolicyDocumentDetail extends GtePolicyDocumentSummary {
  const GtePolicyDocumentDetail({
    required super.id,
    required super.documentKey,
    required super.title,
    required super.isMandatory,
    required super.active,
    super.latestVersion,
    this.bodyMarkdown,
  });

  final String? bodyMarkdown;

  factory GtePolicyDocumentDetail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'policy document detail');
    final GtePolicyDocumentSummary summary =
        GtePolicyDocumentSummary.fromJson(json);
    return GtePolicyDocumentDetail(
      id: summary.id,
      documentKey: summary.documentKey,
      title: summary.title,
      isMandatory: summary.isMandatory,
      active: summary.active,
      latestVersion: summary.latestVersion,
      bodyMarkdown:
          GteJson.stringOrNull(json, <String>['body_markdown', 'bodyMarkdown']),
    );
  }
}

class GtePolicyAcceptanceSummary {
  const GtePolicyAcceptanceSummary({
    required this.documentKey,
    required this.title,
    required this.versionLabel,
    required this.acceptedAt,
  });

  final String documentKey;
  final String title;
  final String versionLabel;
  final DateTime? acceptedAt;

  factory GtePolicyAcceptanceSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'policy acceptance summary');
    return GtePolicyAcceptanceSummary(
      documentKey:
          GteJson.string(json, <String>['document_key', 'documentKey']),
      title: GteJson.string(json, <String>['title']),
      versionLabel:
          GteJson.string(json, <String>['version_label', 'versionLabel']),
      acceptedAt:
          GteJson.dateTimeOrNull(json, <String>['accepted_at', 'acceptedAt']),
    );
  }
}

class GtePolicyRequirementSummary {
  const GtePolicyRequirementSummary({
    required this.documentKey,
    required this.title,
    required this.versionLabel,
    required this.isMandatory,
    this.effectiveAt,
  });

  final String documentKey;
  final String title;
  final String versionLabel;
  final bool isMandatory;
  final DateTime? effectiveAt;

  factory GtePolicyRequirementSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'policy requirement summary');
    return GtePolicyRequirementSummary(
      documentKey:
          GteJson.string(json, <String>['document_key', 'documentKey']),
      title: GteJson.string(json, <String>['title']),
      versionLabel:
          GteJson.string(json, <String>['version_label', 'versionLabel']),
      isMandatory:
          GteJson.boolean(json, <String>['is_mandatory', 'isMandatory']),
      effectiveAt: GteJson.dateTimeOrNull(
          json, <String>['effective_at', 'effectiveAt']),
    );
  }
}

class GteComplianceStatus {
  const GteComplianceStatus({
    required this.countryCode,
    required this.countryPolicyBucket,
    required this.depositsEnabled,
    required this.marketTradingEnabled,
    required this.platformRewardWithdrawalsEnabled,
    required this.requiredPolicyAcceptancesMissing,
    required this.missingPolicyAcceptances,
    required this.canDeposit,
    required this.canWithdrawPlatformRewards,
    required this.canTradeMarket,
  });

  final String countryCode;
  final String countryPolicyBucket;
  final bool depositsEnabled;
  final bool marketTradingEnabled;
  final bool platformRewardWithdrawalsEnabled;
  final int requiredPolicyAcceptancesMissing;
  final List<GtePolicyRequirementSummary> missingPolicyAcceptances;
  final bool canDeposit;
  final bool canWithdrawPlatformRewards;
  final bool canTradeMarket;

  bool get hasMissingRequiredPolicies => requiredPolicyAcceptancesMissing > 0;

  factory GteComplianceStatus.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'compliance status');
    return GteComplianceStatus(
      countryCode:
          GteJson.string(json, <String>['country_code', 'countryCode'], fallback: 'GLOBAL'),
      countryPolicyBucket: GteJson.string(
          json, <String>['country_policy_bucket', 'countryPolicyBucket'],
          fallback: 'default'),
      depositsEnabled:
          GteJson.boolean(json, <String>['deposits_enabled', 'depositsEnabled'], fallback: true),
      marketTradingEnabled: GteJson.boolean(
          json, <String>['market_trading_enabled', 'marketTradingEnabled'],
          fallback: true),
      platformRewardWithdrawalsEnabled: GteJson.boolean(
        json,
        <String>['platform_reward_withdrawals_enabled', 'platformRewardWithdrawalsEnabled'],
        fallback: true,
      ),
      requiredPolicyAcceptancesMissing: GteJson.integer(
        json,
        <String>['required_policy_acceptances_missing', 'requiredPolicyAcceptancesMissing'],
      ),
      missingPolicyAcceptances: GteJson.typedList(
        json,
        <String>['missing_policy_acceptances', 'missingPolicyAcceptances'],
        GtePolicyRequirementSummary.fromJson,
      ),
      canDeposit:
          GteJson.boolean(json, <String>['can_deposit', 'canDeposit'], fallback: true),
      canWithdrawPlatformRewards: GteJson.boolean(
        json,
        <String>['can_withdraw_platform_rewards', 'canWithdrawPlatformRewards'],
        fallback: true,
      ),
      canTradeMarket: GteJson.boolean(
          json, <String>['can_trade_market', 'canTradeMarket'], fallback: true),
    );
  }
}

class GteDepositRequest {
  const GteDepositRequest({
    required this.id,
    required this.reference,
    required this.status,
    required this.amountFiat,
    required this.amountCoin,
    required this.currencyCode,
    required this.rateValue,
    required this.rateDirection,
    required this.bankName,
    required this.bankAccountNumber,
    required this.bankAccountName,
    required this.bankCode,
    required this.payerName,
    required this.senderBank,
    required this.transferReference,
    required this.proofAttachmentId,
    required this.adminNotes,
    required this.createdAt,
    required this.submittedAt,
    required this.reviewedAt,
    required this.confirmedAt,
    required this.rejectedAt,
    required this.expiresAt,
  });

  final String id;
  final String reference;
  final GteDepositStatus status;
  final double amountFiat;
  final double amountCoin;
  final String currencyCode;
  final double rateValue;
  final GteRateDirection rateDirection;
  final String bankName;
  final String bankAccountNumber;
  final String bankAccountName;
  final String? bankCode;
  final String? payerName;
  final String? senderBank;
  final String? transferReference;
  final String? proofAttachmentId;
  final String? adminNotes;
  final DateTime? createdAt;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final DateTime? confirmedAt;
  final DateTime? rejectedAt;
  final DateTime? expiresAt;

  factory GteDepositRequest.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'deposit request');
    return GteDepositRequest(
      id: GteJson.string(json, <String>['id']),
      reference: GteJson.string(json, <String>['reference']),
      status: _depositStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'awaiting_payment')),
      amountFiat:
          GteJson.number(json, <String>['amount_fiat', 'amountFiat']),
      amountCoin:
          GteJson.number(json, <String>['amount_coin', 'amountCoin']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      rateValue: GteJson.number(json, <String>['rate_value', 'rateValue']),
      rateDirection: _rateDirectionFromString(
          GteJson.string(json, <String>['rate_direction', 'rateDirection'],
              fallback: 'fiat_per_coin')),
      bankName: GteJson.string(json, <String>['bank_name', 'bankName']),
      bankAccountNumber: GteJson.string(
          json, <String>['bank_account_number', 'bankAccountNumber']),
      bankAccountName: GteJson.string(
          json, <String>['bank_account_name', 'bankAccountName']),
      bankCode:
          GteJson.stringOrNull(json, <String>['bank_code', 'bankCode']),
      payerName:
          GteJson.stringOrNull(json, <String>['payer_name', 'payerName']),
      senderBank:
          GteJson.stringOrNull(json, <String>['sender_bank', 'senderBank']),
      transferReference: GteJson.stringOrNull(
          json, <String>['transfer_reference', 'transferReference']),
      proofAttachmentId: GteJson.stringOrNull(
          json, <String>['proof_attachment_id', 'proofAttachmentId']),
      adminNotes:
          GteJson.stringOrNull(json, <String>['admin_notes', 'adminNotes']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      submittedAt:
          GteJson.dateTimeOrNull(json, <String>['submitted_at', 'submittedAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      confirmedAt:
          GteJson.dateTimeOrNull(json, <String>['confirmed_at', 'confirmedAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      expiresAt:
          GteJson.dateTimeOrNull(json, <String>['expires_at', 'expiresAt']),
    );
  }
}

class GteDepositCreateRequest {
  const GteDepositCreateRequest({
    required this.amount,
    required this.inputUnit,
  });

  final double amount;
  final String inputUnit;

  Map<String, Object?> toJson() => <String, Object?>{
        'amount': amount,
        'input_unit': inputUnit,
      };
}

class GteDepositSubmitRequest {
  const GteDepositSubmitRequest({
    this.payerName,
    this.senderBank,
    this.transferReference,
    this.proofAttachmentId,
  });

  final String? payerName;
  final String? senderBank;
  final String? transferReference;
  final String? proofAttachmentId;

  Map<String, Object?> toJson() => <String, Object?>{
        if (payerName != null) 'payer_name': payerName,
        if (senderBank != null) 'sender_bank': senderBank,
        if (transferReference != null) 'transfer_reference': transferReference,
        if (proofAttachmentId != null)
          'proof_attachment_id': proofAttachmentId,
      };
}

class GteTreasuryWithdrawalRequest {
  const GteTreasuryWithdrawalRequest({
    required this.id,
    required this.payoutRequestId,
    required this.reference,
    required this.status,
    required this.unit,
    required this.amountCoin,
    required this.amountFiat,
    required this.currencyCode,
    required this.rateValue,
    required this.rateDirection,
    required this.bankName,
    required this.bankAccountNumber,
    required this.bankAccountName,
    required this.bankCode,
    required this.kycStatusSnapshot,
    required this.kycTierSnapshot,
    required this.feeAmount,
    required this.totalDebit,
    required this.notes,
    required this.createdAt,
    required this.reviewedAt,
    required this.approvedAt,
    required this.processedAt,
    required this.paidAt,
    required this.rejectedAt,
    required this.cancelledAt,
  });

  final String id;
  final String payoutRequestId;
  final String reference;
  final GteWithdrawalStatus status;
  final GteLedgerUnit unit;
  final double amountCoin;
  final double amountFiat;
  final String currencyCode;
  final double rateValue;
  final GteRateDirection rateDirection;
  final String bankName;
  final String bankAccountNumber;
  final String bankAccountName;
  final String? bankCode;
  final String kycStatusSnapshot;
  final String kycTierSnapshot;
  final double feeAmount;
  final double totalDebit;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? reviewedAt;
  final DateTime? approvedAt;
  final DateTime? processedAt;
  final DateTime? paidAt;
  final DateTime? rejectedAt;
  final DateTime? cancelledAt;

  factory GteTreasuryWithdrawalRequest.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'withdrawal request');
    return GteTreasuryWithdrawalRequest(
      id: GteJson.string(json, <String>['id']),
      payoutRequestId:
          GteJson.string(json, <String>['payout_request_id', 'payoutRequestId']),
      reference: GteJson.string(json, <String>['reference']),
      status: _withdrawalStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'pending_review')),
      unit: _ledgerUnitFromString(
          GteJson.string(json, <String>['unit'], fallback: 'coin')),
      amountCoin:
          GteJson.number(json, <String>['amount_coin', 'amountCoin']),
      amountFiat:
          GteJson.number(json, <String>['amount_fiat', 'amountFiat']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      rateValue: GteJson.number(json, <String>['rate_value', 'rateValue']),
      rateDirection: _rateDirectionFromString(
          GteJson.string(json, <String>['rate_direction', 'rateDirection'],
              fallback: 'fiat_per_coin')),
      bankName: GteJson.string(json, <String>['bank_name', 'bankName']),
      bankAccountNumber: GteJson.string(
          json, <String>['bank_account_number', 'bankAccountNumber']),
      bankAccountName: GteJson.string(
          json, <String>['bank_account_name', 'bankAccountName']),
      bankCode:
          GteJson.stringOrNull(json, <String>['bank_code', 'bankCode']),
      kycStatusSnapshot: GteJson.string(
          json, <String>['kyc_status_snapshot', 'kycStatusSnapshot'],
          fallback: 'unverified'),
      kycTierSnapshot: GteJson.string(
          json, <String>['kyc_tier_snapshot', 'kycTierSnapshot'],
          fallback: 'unverified'),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      totalDebit:
          GteJson.number(json, <String>['total_debit', 'totalDebit']),
      notes: GteJson.stringOrNull(json, <String>['notes']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      approvedAt:
          GteJson.dateTimeOrNull(json, <String>['approved_at', 'approvedAt']),
      processedAt:
          GteJson.dateTimeOrNull(json, <String>['processed_at', 'processedAt']),
      paidAt: GteJson.dateTimeOrNull(json, <String>['paid_at', 'paidAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      cancelledAt:
          GteJson.dateTimeOrNull(json, <String>['cancelled_at', 'cancelledAt']),
    );
  }
}

class GteWithdrawalCreateRequest {
  const GteWithdrawalCreateRequest({
    required this.amountCoin,
    this.bankAccountId,
    this.notes,
    this.sourceScope = 'trade',
  });

  final double amountCoin;
  final String? bankAccountId;
  final String? notes;
  final String sourceScope;

  Map<String, Object?> toJson() => <String, Object?>{
        'amount_coin': amountCoin,
        if (bankAccountId != null) 'bank_account_id': bankAccountId,
        if (notes != null) 'notes': notes,
        'source_scope': sourceScope,
      };
}

class GteUserBankAccount {
  const GteUserBankAccount({
    required this.id,
    required this.currencyCode,
    required this.bankName,
    required this.accountNumber,
    required this.accountName,
    required this.bankCode,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String currencyCode;
  final String bankName;
  final String accountNumber;
  final String accountName;
  final String? bankCode;
  final bool isActive;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  factory GteUserBankAccount.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'user bank account');
    return GteUserBankAccount(
      id: GteJson.string(json, <String>['id']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      bankName: GteJson.string(json, <String>['bank_name', 'bankName']),
      accountNumber: GteJson.string(
          json, <String>['account_number', 'accountNumber']),
      accountName:
          GteJson.string(json, <String>['account_name', 'accountName']),
      bankCode:
          GteJson.stringOrNull(json, <String>['bank_code', 'bankCode']),
      isActive:
          GteJson.boolean(json, <String>['is_active', 'isActive']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GteUserBankAccountCreate {
  const GteUserBankAccountCreate({
    required this.bankName,
    required this.accountNumber,
    required this.accountName,
    this.bankCode,
    this.currencyCode = 'NGN',
    this.setActive = true,
  });

  final String bankName;
  final String accountNumber;
  final String accountName;
  final String? bankCode;
  final String currencyCode;
  final bool setActive;

  Map<String, Object?> toJson() => <String, Object?>{
        'bank_name': bankName,
        'account_number': accountNumber,
        'account_name': accountName,
        if (bankCode != null) 'bank_code': bankCode,
        'currency_code': currencyCode,
        'set_active': setActive,
      };
}

class GteUserBankAccountUpdate {
  const GteUserBankAccountUpdate({
    this.bankName,
    this.accountNumber,
    this.accountName,
    this.bankCode,
    this.currencyCode,
    this.isActive,
  });

  final String? bankName;
  final String? accountNumber;
  final String? accountName;
  final String? bankCode;
  final String? currencyCode;
  final bool? isActive;

  Map<String, Object?> toJson() => <String, Object?>{
        if (bankName != null) 'bank_name': bankName,
        if (accountNumber != null) 'account_number': accountNumber,
        if (accountName != null) 'account_name': accountName,
        if (bankCode != null) 'bank_code': bankCode,
        if (currencyCode != null) 'currency_code': currencyCode,
        if (isActive != null) 'is_active': isActive,
      };
}

class GteKycProfile {
  const GteKycProfile({
    required this.id,
    required this.status,
    required this.nin,
    required this.bvn,
    required this.addressLine1,
    required this.addressLine2,
    required this.city,
    required this.state,
    required this.country,
    required this.idDocumentAttachmentId,
    required this.submittedAt,
    required this.reviewedAt,
    required this.rejectionReason,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final GteKycStatus status;
  final String? nin;
  final String? bvn;
  final String? addressLine1;
  final String? addressLine2;
  final String? city;
  final String? state;
  final String? country;
  final String? idDocumentAttachmentId;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final String? rejectionReason;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  factory GteKycProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'kyc profile');
    return GteKycProfile(
      id: GteJson.string(json, <String>['id']),
      status: _kycStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'unverified')),
      nin: GteJson.stringOrNull(json, <String>['nin']),
      bvn: GteJson.stringOrNull(json, <String>['bvn']),
      addressLine1:
          GteJson.stringOrNull(json, <String>['address_line1', 'addressLine1']),
      addressLine2:
          GteJson.stringOrNull(json, <String>['address_line2', 'addressLine2']),
      city: GteJson.stringOrNull(json, <String>['city']),
      state: GteJson.stringOrNull(json, <String>['state']),
      country: GteJson.stringOrNull(json, <String>['country']),
      idDocumentAttachmentId: GteJson.stringOrNull(
          json, <String>['id_document_attachment_id', 'idDocumentAttachmentId']),
      submittedAt:
          GteJson.dateTimeOrNull(json, <String>['submitted_at', 'submittedAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      rejectionReason: GteJson.stringOrNull(
          json, <String>['rejection_reason', 'rejectionReason']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GteKycSubmitRequest {
  const GteKycSubmitRequest({
    this.nin,
    this.bvn,
    required this.addressLine1,
    this.addressLine2,
    this.city,
    this.state,
    this.country = 'Nigeria',
    this.idDocumentAttachmentId,
  });

  final String? nin;
  final String? bvn;
  final String addressLine1;
  final String? addressLine2;
  final String? city;
  final String? state;
  final String? country;
  final String? idDocumentAttachmentId;

  Map<String, Object?> toJson() => <String, Object?>{
        if (nin != null) 'nin': nin,
        if (bvn != null) 'bvn': bvn,
        'address_line1': addressLine1,
        if (addressLine2 != null) 'address_line2': addressLine2,
        if (city != null) 'city': city,
        if (state != null) 'state': state,
        if (country != null) 'country': country,
        if (idDocumentAttachmentId != null)
          'id_document_attachment_id': idDocumentAttachmentId,
      };
}

class GteKycReviewRequest {
  const GteKycReviewRequest({
    required this.status,
    this.rejectionReason,
  });

  final GteKycStatus status;
  final String? rejectionReason;

  Map<String, Object?> toJson() => <String, Object?>{
        'status': _kycStatusToString(status),
        if (rejectionReason != null) 'rejection_reason': rejectionReason,
      };
}

class GteDisputeMessage {
  const GteDisputeMessage({
    required this.id,
    required this.senderUserId,
    required this.senderRole,
    required this.message,
    required this.attachmentId,
    required this.createdAt,
  });

  final String id;
  final String? senderUserId;
  final String senderRole;
  final String message;
  final String? attachmentId;
  final DateTime? createdAt;

  factory GteDisputeMessage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dispute message');
    return GteDisputeMessage(
      id: GteJson.string(json, <String>['id']),
      senderUserId: GteJson.stringOrNull(
          json, <String>['sender_user_id', 'senderUserId']),
      senderRole:
          GteJson.string(json, <String>['sender_role', 'senderRole'],
              fallback: 'user'),
      message: GteJson.string(json, <String>['message']),
      attachmentId:
          GteJson.stringOrNull(json, <String>['attachment_id', 'attachmentId']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
    );
  }
}

class GteDispute {
  const GteDispute({
    required this.id,
    required this.status,
    required this.reference,
    required this.resourceType,
    required this.resourceId,
    required this.subject,
    required this.createdAt,
    required this.updatedAt,
    required this.lastMessageAt,
    required this.userId,
    required this.userEmail,
    required this.userFullName,
    required this.userPhoneNumber,
    required this.messages,
  });

  final String id;
  final GteDisputeStatus status;
  final String reference;
  final String resourceType;
  final String resourceId;
  final String? subject;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final DateTime? lastMessageAt;
  final String userId;
  final String userEmail;
  final String? userFullName;
  final String? userPhoneNumber;
  final List<GteDisputeMessage> messages;

  factory GteDispute.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'dispute');
    return GteDispute(
      id: GteJson.string(json, <String>['id']),
      status: _disputeStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'open')),
      reference: GteJson.string(json, <String>['reference']),
      resourceType:
          GteJson.string(json, <String>['resource_type', 'resourceType']),
      resourceId:
          GteJson.string(json, <String>['resource_id', 'resourceId']),
      subject: GteJson.stringOrNull(json, <String>['subject']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
      lastMessageAt: GteJson.dateTimeOrNull(
          json, <String>['last_message_at', 'lastMessageAt']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      userEmail:
          GteJson.string(json, <String>['user_email', 'userEmail']),
      userFullName:
          GteJson.stringOrNull(json, <String>['user_full_name', 'userFullName']),
      userPhoneNumber: GteJson.stringOrNull(
          json, <String>['user_phone_number', 'userPhoneNumber']),
      messages: GteJson.typedList(
          json, <String>['messages'], GteDisputeMessage.fromJson),
    );
  }
}

class GteDisputeCreateRequest {
  const GteDisputeCreateRequest({
    required this.resourceType,
    required this.resourceId,
    required this.reference,
    this.subject,
    required this.message,
    this.attachmentId,
  });

  final String resourceType;
  final String resourceId;
  final String reference;
  final String? subject;
  final String message;
  final String? attachmentId;

  Map<String, Object?> toJson() => <String, Object?>{
        'resource_type': resourceType,
        'resource_id': resourceId,
        'reference': reference,
        if (subject != null) 'subject': subject,
        'message': message,
        if (attachmentId != null) 'attachment_id': attachmentId,
      };
}

class GteDisputeMessageRequest {
  const GteDisputeMessageRequest({
    required this.message,
    this.attachmentId,
  });

  final String message;
  final String? attachmentId;

  Map<String, Object?> toJson() => <String, Object?>{
        'message': message,
        if (attachmentId != null) 'attachment_id': attachmentId,
      };
}

class GteNotification {
  const GteNotification({
    required this.notificationId,
    required this.userId,
    required this.topic,
    required this.templateKey,
    required this.resourceId,
    required this.fixtureId,
    required this.competitionId,
    required this.message,
    required this.metadata,
    required this.createdAt,
    required this.readAt,
    required this.isRead,
  });

  final String notificationId;
  final String userId;
  final String? topic;
  final String? templateKey;
  final String? resourceId;
  final String? fixtureId;
  final String? competitionId;
  final String? message;
  final Map<String, Object?> metadata;
  final DateTime? createdAt;
  final DateTime? readAt;
  final bool isRead;

  factory GteNotification.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'notification');
    final Map<String, Object?> metadataJson = GteJson.map(
      GteJson.value(json, <String>['metadata']) ?? const <String, Object?>{},
      label: 'notification metadata',
    );
    return GteNotification(
      notificationId:
          GteJson.string(json, <String>['notification_id', 'notificationId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      topic: GteJson.stringOrNull(json, <String>['topic']),
      templateKey:
          GteJson.stringOrNull(json, <String>['template_key', 'templateKey']),
      resourceId:
          GteJson.stringOrNull(json, <String>['resource_id', 'resourceId']),
      fixtureId:
          GteJson.stringOrNull(json, <String>['fixture_id', 'fixtureId']),
      competitionId: GteJson.stringOrNull(
          json, <String>['competition_id', 'competitionId']),
      message: GteJson.stringOrNull(json, <String>['message']),
      metadata: metadataJson,
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      readAt: GteJson.dateTimeOrNull(json, <String>['read_at', 'readAt']),
      isRead: GteJson.boolean(json, <String>['is_read', 'isRead'],
          fallback: false),
    );
  }
}

class GteAttachment {
  const GteAttachment({
    required this.id,
    required this.filename,
    required this.contentType,
    required this.sizeBytes,
    required this.createdAt,
  });

  final String id;
  final String filename;
  final String contentType;
  final int sizeBytes;
  final DateTime? createdAt;

  factory GteAttachment.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'attachment');
    return GteAttachment(
      id: GteJson.string(json, <String>['id']),
      filename: GteJson.string(json, <String>['filename']),
      contentType:
          GteJson.string(json, <String>['content_type', 'contentType']),
      sizeBytes:
          GteJson.integer(json, <String>['size_bytes', 'sizeBytes']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
    );
  }
}

class GteTreasuryBankAccount {
  const GteTreasuryBankAccount({
    required this.id,
    required this.currencyCode,
    required this.bankName,
    required this.accountNumber,
    required this.accountName,
    required this.bankCode,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String currencyCode;
  final String bankName;
  final String accountNumber;
  final String accountName;
  final String? bankCode;
  final bool isActive;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  factory GteTreasuryBankAccount.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'treasury bank account');
    return GteTreasuryBankAccount(
      id: GteJson.string(json, <String>['id']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      bankName: GteJson.string(json, <String>['bank_name', 'bankName']),
      accountNumber: GteJson.string(
          json, <String>['account_number', 'accountNumber']),
      accountName:
          GteJson.string(json, <String>['account_name', 'accountName']),
      bankCode:
          GteJson.stringOrNull(json, <String>['bank_code', 'bankCode']),
      isActive:
          GteJson.boolean(json, <String>['is_active', 'isActive']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GteTreasurySettings {
  const GteTreasurySettings({
    required this.id,
    required this.settingsKey,
    required this.currencyCode,
    required this.depositRateValue,
    required this.depositRateDirection,
    required this.withdrawalRateValue,
    required this.withdrawalRateDirection,
    required this.minDeposit,
    required this.maxDeposit,
    required this.minWithdrawal,
    required this.maxWithdrawal,
    required this.depositMode,
    required this.withdrawalMode,
    required this.maintenanceMessage,
    required this.whatsappNumber,
    required this.activeBankAccount,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String settingsKey;
  final String currencyCode;
  final double depositRateValue;
  final GteRateDirection depositRateDirection;
  final double withdrawalRateValue;
  final GteRateDirection withdrawalRateDirection;
  final double minDeposit;
  final double maxDeposit;
  final double minWithdrawal;
  final double maxWithdrawal;
  final GtePaymentMode depositMode;
  final GtePaymentMode withdrawalMode;
  final String? maintenanceMessage;
  final String? whatsappNumber;
  final GteTreasuryBankAccount? activeBankAccount;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  factory GteTreasurySettings.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'treasury settings');
    return GteTreasurySettings(
      id: GteJson.string(json, <String>['id']),
      settingsKey:
          GteJson.string(json, <String>['settings_key', 'settingsKey']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      depositRateValue: GteJson.number(
          json, <String>['deposit_rate_value', 'depositRateValue']),
      depositRateDirection: _rateDirectionFromString(GteJson.string(
          json, <String>['deposit_rate_direction', 'depositRateDirection'],
          fallback: 'fiat_per_coin')),
      withdrawalRateValue: GteJson.number(
          json, <String>['withdrawal_rate_value', 'withdrawalRateValue']),
      withdrawalRateDirection: _rateDirectionFromString(GteJson.string(
          json,
          <String>['withdrawal_rate_direction', 'withdrawalRateDirection'],
          fallback: 'fiat_per_coin')),
      minDeposit:
          GteJson.number(json, <String>['min_deposit', 'minDeposit']),
      maxDeposit:
          GteJson.number(json, <String>['max_deposit', 'maxDeposit']),
      minWithdrawal:
          GteJson.number(json, <String>['min_withdrawal', 'minWithdrawal']),
      maxWithdrawal:
          GteJson.number(json, <String>['max_withdrawal', 'maxWithdrawal']),
      depositMode: _paymentModeFromString(
          GteJson.string(json, <String>['deposit_mode', 'depositMode'],
              fallback: 'manual')),
      withdrawalMode: _paymentModeFromString(
          GteJson.string(json, <String>['withdrawal_mode', 'withdrawalMode'],
              fallback: 'manual')),
      maintenanceMessage: GteJson.stringOrNull(
          json, <String>['maintenance_message', 'maintenanceMessage']),
      whatsappNumber:
          GteJson.stringOrNull(json, <String>['whatsapp_number', 'whatsappNumber']),
      activeBankAccount: GteJson.value(json, <String>['active_bank_account']) == null
          ? null
          : GteTreasuryBankAccount.fromJson(
              GteJson.value(json, <String>['active_bank_account'])),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GteTreasurySettingsUpdate {
  const GteTreasurySettingsUpdate({
    this.currencyCode,
    this.depositRateValue,
    this.depositRateDirection,
    this.withdrawalRateValue,
    this.withdrawalRateDirection,
    this.minDeposit,
    this.maxDeposit,
    this.minWithdrawal,
    this.maxWithdrawal,
    this.depositMode,
    this.withdrawalMode,
    this.maintenanceMessage,
    this.whatsappNumber,
    this.activeBankAccountId,
  });

  final String? currencyCode;
  final double? depositRateValue;
  final GteRateDirection? depositRateDirection;
  final double? withdrawalRateValue;
  final GteRateDirection? withdrawalRateDirection;
  final double? minDeposit;
  final double? maxDeposit;
  final double? minWithdrawal;
  final double? maxWithdrawal;
  final GtePaymentMode? depositMode;
  final GtePaymentMode? withdrawalMode;
  final String? maintenanceMessage;
  final String? whatsappNumber;
  final String? activeBankAccountId;

  Map<String, Object?> toJson() => <String, Object?>{
        if (currencyCode != null) 'currency_code': currencyCode,
        if (depositRateValue != null) 'deposit_rate_value': depositRateValue,
        if (depositRateDirection != null)
          'deposit_rate_direction': _rateDirectionToString(depositRateDirection!),
        if (withdrawalRateValue != null)
          'withdrawal_rate_value': withdrawalRateValue,
        if (withdrawalRateDirection != null)
          'withdrawal_rate_direction':
              _rateDirectionToString(withdrawalRateDirection!),
        if (minDeposit != null) 'min_deposit': minDeposit,
        if (maxDeposit != null) 'max_deposit': maxDeposit,
        if (minWithdrawal != null) 'min_withdrawal': minWithdrawal,
        if (maxWithdrawal != null) 'max_withdrawal': maxWithdrawal,
        if (depositMode != null) 'deposit_mode': depositMode!.name,
        if (withdrawalMode != null) 'withdrawal_mode': withdrawalMode!.name,
        if (maintenanceMessage != null)
          'maintenance_message': maintenanceMessage,
        if (whatsappNumber != null) 'whatsapp_number': whatsappNumber,
        if (activeBankAccountId != null)
          'active_bank_account_id': activeBankAccountId,
      };
}

class GteTreasuryBankAccountCreate {
  const GteTreasuryBankAccountCreate({
    required this.bankName,
    required this.accountNumber,
    required this.accountName,
    this.bankCode,
    this.currencyCode = 'NGN',
    this.isActive = true,
  });

  final String bankName;
  final String accountNumber;
  final String accountName;
  final String? bankCode;
  final String currencyCode;
  final bool isActive;

  Map<String, Object?> toJson() => <String, Object?>{
        'bank_name': bankName,
        'account_number': accountNumber,
        'account_name': accountName,
        if (bankCode != null) 'bank_code': bankCode,
        'currency_code': currencyCode,
        'is_active': isActive,
      };
}

class GteTreasuryBankAccountUpdate {
  const GteTreasuryBankAccountUpdate({
    this.bankName,
    this.accountNumber,
    this.accountName,
    this.bankCode,
    this.currencyCode,
    this.isActive,
  });

  final String? bankName;
  final String? accountNumber;
  final String? accountName;
  final String? bankCode;
  final String? currencyCode;
  final bool? isActive;

  Map<String, Object?> toJson() => <String, Object?>{
        if (bankName != null) 'bank_name': bankName,
        if (accountNumber != null) 'account_number': accountNumber,
        if (accountName != null) 'account_name': accountName,
        if (bankCode != null) 'bank_code': bankCode,
        if (currencyCode != null) 'currency_code': currencyCode,
        if (isActive != null) 'is_active': isActive,
      };
}

class GteTreasuryDashboard {
  const GteTreasuryDashboard({
    required this.totalUsers,
    required this.activeUsers,
    required this.pendingDeposits,
    required this.pendingWithdrawals,
    required this.pendingKyc,
    required this.openDisputes,
    required this.depositsConfirmedToday,
    required this.withdrawalsPaidToday,
    required this.walletLiability,
    required this.pendingTreasuryExposure,
  });

  final int totalUsers;
  final int activeUsers;
  final int pendingDeposits;
  final int pendingWithdrawals;
  final int pendingKyc;
  final int openDisputes;
  final int depositsConfirmedToday;
  final int withdrawalsPaidToday;
  final double walletLiability;
  final double pendingTreasuryExposure;

  factory GteTreasuryDashboard.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'treasury dashboard');
    return GteTreasuryDashboard(
      totalUsers:
          GteJson.integer(json, <String>['total_users', 'totalUsers']),
      activeUsers:
          GteJson.integer(json, <String>['active_users', 'activeUsers']),
      pendingDeposits:
          GteJson.integer(json, <String>['pending_deposits', 'pendingDeposits']),
      pendingWithdrawals: GteJson.integer(
          json, <String>['pending_withdrawals', 'pendingWithdrawals']),
      pendingKyc:
          GteJson.integer(json, <String>['pending_kyc', 'pendingKyc']),
      openDisputes:
          GteJson.integer(json, <String>['open_disputes', 'openDisputes']),
      depositsConfirmedToday: GteJson.integer(
          json, <String>['deposits_confirmed_today', 'depositsConfirmedToday']),
      withdrawalsPaidToday: GteJson.integer(
          json, <String>['withdrawals_paid_today', 'withdrawalsPaidToday']),
      walletLiability:
          GteJson.number(json, <String>['wallet_liability', 'walletLiability']),
      pendingTreasuryExposure: GteJson.number(json,
          <String>['pending_treasury_exposure', 'pendingTreasuryExposure']),
    );
  }
}

class GteAdminDeposit {
  const GteAdminDeposit({
    required this.id,
    required this.reference,
    required this.status,
    required this.amountFiat,
    required this.amountCoin,
    required this.currencyCode,
    required this.payerName,
    required this.senderBank,
    required this.transferReference,
    required this.createdAt,
    required this.submittedAt,
    required this.reviewedAt,
    required this.confirmedAt,
    required this.rejectedAt,
    required this.adminNotes,
    required this.userId,
    required this.userEmail,
    required this.userFullName,
    required this.userPhoneNumber,
  });

  final String id;
  final String reference;
  final GteDepositStatus status;
  final double amountFiat;
  final double amountCoin;
  final String currencyCode;
  final String? payerName;
  final String? senderBank;
  final String? transferReference;
  final DateTime? createdAt;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final DateTime? confirmedAt;
  final DateTime? rejectedAt;
  final String? adminNotes;
  final String userId;
  final String userEmail;
  final String? userFullName;
  final String? userPhoneNumber;

  factory GteAdminDeposit.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'admin deposit');
    return GteAdminDeposit(
      id: GteJson.string(json, <String>['id']),
      reference: GteJson.string(json, <String>['reference']),
      status: _depositStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'awaiting_payment')),
      amountFiat:
          GteJson.number(json, <String>['amount_fiat', 'amountFiat']),
      amountCoin:
          GteJson.number(json, <String>['amount_coin', 'amountCoin']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      payerName:
          GteJson.stringOrNull(json, <String>['payer_name', 'payerName']),
      senderBank:
          GteJson.stringOrNull(json, <String>['sender_bank', 'senderBank']),
      transferReference: GteJson.stringOrNull(
          json, <String>['transfer_reference', 'transferReference']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      submittedAt:
          GteJson.dateTimeOrNull(json, <String>['submitted_at', 'submittedAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      confirmedAt:
          GteJson.dateTimeOrNull(json, <String>['confirmed_at', 'confirmedAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      adminNotes:
          GteJson.stringOrNull(json, <String>['admin_notes', 'adminNotes']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      userEmail:
          GteJson.string(json, <String>['user_email', 'userEmail']),
      userFullName: GteJson.stringOrNull(
          json, <String>['user_full_name', 'userFullName']),
      userPhoneNumber: GteJson.stringOrNull(
          json, <String>['user_phone_number', 'userPhoneNumber']),
    );
  }
}

class GteAdminWithdrawal {
  const GteAdminWithdrawal({
    required this.id,
    required this.reference,
    required this.status,
    required this.amountCoin,
    required this.amountFiat,
    required this.currencyCode,
    required this.bankName,
    required this.bankAccountNumber,
    required this.bankAccountName,
    required this.createdAt,
    required this.reviewedAt,
    required this.approvedAt,
    required this.processedAt,
    required this.paidAt,
    required this.rejectedAt,
    required this.cancelledAt,
    required this.userId,
    required this.userEmail,
    required this.userFullName,
    required this.userPhoneNumber,
  });

  final String id;
  final String reference;
  final GteWithdrawalStatus status;
  final double amountCoin;
  final double amountFiat;
  final String currencyCode;
  final String bankName;
  final String bankAccountNumber;
  final String bankAccountName;
  final DateTime? createdAt;
  final DateTime? reviewedAt;
  final DateTime? approvedAt;
  final DateTime? processedAt;
  final DateTime? paidAt;
  final DateTime? rejectedAt;
  final DateTime? cancelledAt;
  final String userId;
  final String userEmail;
  final String? userFullName;
  final String? userPhoneNumber;

  factory GteAdminWithdrawal.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'admin withdrawal');
    return GteAdminWithdrawal(
      id: GteJson.string(json, <String>['id']),
      reference: GteJson.string(json, <String>['reference']),
      status: _withdrawalStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'pending_review')),
      amountCoin:
          GteJson.number(json, <String>['amount_coin', 'amountCoin']),
      amountFiat:
          GteJson.number(json, <String>['amount_fiat', 'amountFiat']),
      currencyCode:
          GteJson.string(json, <String>['currency_code', 'currencyCode']),
      bankName: GteJson.string(json, <String>['bank_name', 'bankName']),
      bankAccountNumber: GteJson.string(
          json, <String>['bank_account_number', 'bankAccountNumber']),
      bankAccountName: GteJson.string(
          json, <String>['bank_account_name', 'bankAccountName']),
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      approvedAt:
          GteJson.dateTimeOrNull(json, <String>['approved_at', 'approvedAt']),
      processedAt:
          GteJson.dateTimeOrNull(json, <String>['processed_at', 'processedAt']),
      paidAt: GteJson.dateTimeOrNull(json, <String>['paid_at', 'paidAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      cancelledAt:
          GteJson.dateTimeOrNull(json, <String>['cancelled_at', 'cancelledAt']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      userEmail:
          GteJson.string(json, <String>['user_email', 'userEmail']),
      userFullName: GteJson.stringOrNull(
          json, <String>['user_full_name', 'userFullName']),
      userPhoneNumber: GteJson.stringOrNull(
          json, <String>['user_phone_number', 'userPhoneNumber']),
    );
  }
}

class GteAdminKyc {
  const GteAdminKyc({
    required this.id,
    required this.userId,
    required this.status,
    required this.nin,
    required this.bvn,
    required this.addressLine1,
    required this.city,
    required this.state,
    required this.country,
    required this.submittedAt,
    required this.reviewedAt,
    required this.rejectionReason,
    required this.userEmail,
    required this.userFullName,
    required this.userPhoneNumber,
  });

  final String id;
  final String userId;
  final GteKycStatus status;
  final String? nin;
  final String? bvn;
  final String? addressLine1;
  final String? city;
  final String? state;
  final String? country;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final String? rejectionReason;
  final String userEmail;
  final String? userFullName;
  final String? userPhoneNumber;

  factory GteAdminKyc.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'admin kyc');
    return GteAdminKyc(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      status: _kycStatusFromString(
          GteJson.string(json, <String>['status'], fallback: 'unverified')),
      nin: GteJson.stringOrNull(json, <String>['nin']),
      bvn: GteJson.stringOrNull(json, <String>['bvn']),
      addressLine1:
          GteJson.stringOrNull(json, <String>['address_line1', 'addressLine1']),
      city: GteJson.stringOrNull(json, <String>['city']),
      state: GteJson.stringOrNull(json, <String>['state']),
      country: GteJson.stringOrNull(json, <String>['country']),
      submittedAt:
          GteJson.dateTimeOrNull(json, <String>['submitted_at', 'submittedAt']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      rejectionReason: GteJson.stringOrNull(
          json, <String>['rejection_reason', 'rejectionReason']),
      userEmail:
          GteJson.string(json, <String>['user_email', 'userEmail']),
      userFullName: GteJson.stringOrNull(
          json, <String>['user_full_name', 'userFullName']),
      userPhoneNumber: GteJson.stringOrNull(
          json, <String>['user_phone_number', 'userPhoneNumber']),
    );
  }
}

class GteAdminQueuePage<T> {
  const GteAdminQueuePage({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  final List<T> items;
  final int total;
  final int limit;
  final int offset;

  factory GteAdminQueuePage.fromJson(
    Object? value,
    T Function(Object? value) parser,
  ) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'admin queue');
    return GteAdminQueuePage<T>(
      items: GteJson.typedList(json, <String>['items'], parser),
      total: GteJson.integer(json, <String>['total']),
      limit: GteJson.integer(json, <String>['limit'], fallback: 50),
      offset: GteJson.integer(json, <String>['offset'], fallback: 0),
    );
  }
}

class GteAnalyticsEvent {
  const GteAnalyticsEvent({
    required this.id,
    required this.name,
    required this.userId,
    required this.metadata,
    required this.createdAt,
  });

  final String id;
  final String name;
  final String? userId;
  final Map<String, Object?> metadata;
  final DateTime? createdAt;

  factory GteAnalyticsEvent.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'analytics event');
    final Map<String, Object?> metadataJson = GteJson.map(
      GteJson.value(json, <String>['metadata_json', 'metadata']) ??
          const <String, Object?>{},
      label: 'analytics metadata',
    );
    return GteAnalyticsEvent(
      id: GteJson.string(json, <String>['id']),
      name: GteJson.string(json, <String>['name']),
      userId: GteJson.stringOrNull(json, <String>['user_id', 'userId']),
      metadata: metadataJson,
      createdAt:
          GteJson.dateTimeOrNull(json, <String>['created_at', 'createdAt']),
    );
  }
}

class GteAnalyticsSummaryItem {
  const GteAnalyticsSummaryItem({
    required this.name,
    required this.count,
  });

  final String name;
  final int count;

  factory GteAnalyticsSummaryItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'analytics summary item');
    return GteAnalyticsSummaryItem(
      name: GteJson.string(json, <String>['name']),
      count: GteJson.integer(json, <String>['count']),
    );
  }
}

class GteAnalyticsSummary {
  const GteAnalyticsSummary({
    required this.since,
    required this.totals,
  });

  final DateTime? since;
  final List<GteAnalyticsSummaryItem> totals;

  factory GteAnalyticsSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'analytics summary');
    return GteAnalyticsSummary(
      since: GteJson.dateTimeOrNull(json, <String>['since']),
      totals: GteJson.typedList(
          json, <String>['totals'], GteAnalyticsSummaryItem.fromJson),
    );
  }
}

class GteAnalyticsFunnelStep {
  const GteAnalyticsFunnelStep({
    required this.name,
    required this.users,
  });

  final String name;
  final int users;

  factory GteAnalyticsFunnelStep.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'analytics funnel step');
    return GteAnalyticsFunnelStep(
      name: GteJson.string(json, <String>['name']),
      users: GteJson.integer(json, <String>['users']),
    );
  }
}

class GteAnalyticsFunnel {
  const GteAnalyticsFunnel({
    required this.since,
    required this.steps,
  });

  final DateTime? since;
  final List<GteAnalyticsFunnelStep> steps;

  factory GteAnalyticsFunnel.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'analytics funnel');
    return GteAnalyticsFunnel(
      since: GteJson.dateTimeOrNull(json, <String>['since']),
      steps: GteJson.typedList(
          json, <String>['steps'], GteAnalyticsFunnelStep.fromJson),
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

GtePaymentMode _paymentModeFromString(String value) {
  return value.toLowerCase() == 'automatic'
      ? GtePaymentMode.automatic
      : GtePaymentMode.manual;
}

GteRateDirection _rateDirectionFromString(String value) {
  switch (value.toLowerCase()) {
    case 'coin_per_fiat':
      return GteRateDirection.coinPerFiat;
    case 'fiat_per_coin':
    default:
      return GteRateDirection.fiatPerCoin;
  }
}

String _rateDirectionToString(GteRateDirection direction) {
  switch (direction) {
    case GteRateDirection.coinPerFiat:
      return 'coin_per_fiat';
    case GteRateDirection.fiatPerCoin:
      return 'fiat_per_coin';
  }
}

GteDepositStatus _depositStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'payment_submitted':
      return GteDepositStatus.paymentSubmitted;
    case 'under_review':
      return GteDepositStatus.underReview;
    case 'confirmed':
      return GteDepositStatus.confirmed;
    case 'rejected':
      return GteDepositStatus.rejected;
    case 'expired':
      return GteDepositStatus.expired;
    case 'disputed':
      return GteDepositStatus.disputed;
    case 'awaiting_payment':
    default:
      return GteDepositStatus.awaitingPayment;
  }
}

String _depositStatusToString(GteDepositStatus status) {
  switch (status) {
    case GteDepositStatus.awaitingPayment:
      return 'awaiting_payment';
    case GteDepositStatus.paymentSubmitted:
      return 'payment_submitted';
    case GteDepositStatus.underReview:
      return 'under_review';
    case GteDepositStatus.confirmed:
      return 'confirmed';
    case GteDepositStatus.rejected:
      return 'rejected';
    case GteDepositStatus.expired:
      return 'expired';
    case GteDepositStatus.disputed:
      return 'disputed';
  }
}

GteWithdrawalStatus _withdrawalStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'draft':
      return GteWithdrawalStatus.draft;
    case 'pending_kyc':
      return GteWithdrawalStatus.pendingKyc;
    case 'approved':
      return GteWithdrawalStatus.approved;
    case 'rejected':
      return GteWithdrawalStatus.rejected;
    case 'processing':
      return GteWithdrawalStatus.processing;
    case 'paid':
      return GteWithdrawalStatus.paid;
    case 'disputed':
      return GteWithdrawalStatus.disputed;
    case 'cancelled':
      return GteWithdrawalStatus.cancelled;
    case 'pending_review':
    default:
      return GteWithdrawalStatus.pendingReview;
  }
}

String _withdrawalStatusToString(GteWithdrawalStatus status) {
  switch (status) {
    case GteWithdrawalStatus.draft:
      return 'draft';
    case GteWithdrawalStatus.pendingKyc:
      return 'pending_kyc';
    case GteWithdrawalStatus.pendingReview:
      return 'pending_review';
    case GteWithdrawalStatus.approved:
      return 'approved';
    case GteWithdrawalStatus.rejected:
      return 'rejected';
    case GteWithdrawalStatus.processing:
      return 'processing';
    case GteWithdrawalStatus.paid:
      return 'paid';
    case GteWithdrawalStatus.disputed:
      return 'disputed';
    case GteWithdrawalStatus.cancelled:
      return 'cancelled';
  }
}

GteKycStatus _kycStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'pending':
      return GteKycStatus.pending;
    case 'partial_verified_no_id':
      return GteKycStatus.partialVerifiedNoId;
    case 'fully_verified':
      return GteKycStatus.fullyVerified;
    case 'rejected':
      return GteKycStatus.rejected;
    case 'unverified':
    default:
      return GteKycStatus.unverified;
  }
}

String _kycStatusToString(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'unverified';
    case GteKycStatus.pending:
      return 'pending';
    case GteKycStatus.partialVerifiedNoId:
      return 'partial_verified_no_id';
    case GteKycStatus.fullyVerified:
      return 'fully_verified';
    case GteKycStatus.rejected:
      return 'rejected';
  }
}

GteDisputeStatus _disputeStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'awaiting_user':
      return GteDisputeStatus.awaitingUser;
    case 'awaiting_admin':
      return GteDisputeStatus.awaitingAdmin;
    case 'resolved':
      return GteDisputeStatus.resolved;
    case 'closed':
      return GteDisputeStatus.closed;
    case 'open':
    default:
      return GteDisputeStatus.open;
  }
}

String _disputeStatusToString(GteDisputeStatus status) {
  switch (status) {
    case GteDisputeStatus.open:
      return 'open';
    case GteDisputeStatus.awaitingUser:
      return 'awaiting_user';
    case GteDisputeStatus.awaitingAdmin:
      return 'awaiting_admin';
    case GteDisputeStatus.resolved:
      return 'resolved';
    case GteDisputeStatus.closed:
      return 'closed';
  }
}
