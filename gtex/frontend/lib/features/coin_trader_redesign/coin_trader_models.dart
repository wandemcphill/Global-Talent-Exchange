class GtexCoinTraderProfile {
  const GtexCoinTraderProfile({
    required this.id,
    required this.userId,
    required this.displayName,
    required this.status,
    required this.tier,
    this.bio,
    this.isOnline,
    this.lastSeenAt,
    this.tradingSince,
    this.completedTrades,
    this.responseTimeMinutes,
    this.verificationLevel = 'standard',
    required this.completionRate,
    required this.averageReleaseMinutes,
    required this.rating,
    this.completedVolumeFiat = 0,
    this.disputeScore = 0,
    required this.rates,
    this.countryCode,
    this.terms = const <String, Object?>{},
    this.paymentMethods = const <Map<String, Object?>>[],
    this.bankAccounts = const <Map<String, Object?>>[],
    this.liquiditySnapshot = const <String, Object?>{},
    this.metadata = const <String, Object?>{},
  });

  final String id;
  final String userId;
  final String displayName;
  final String? countryCode;
  final String status;
  final String tier;
  final String? bio;
  final bool? isOnline;
  final DateTime? lastSeenAt;
  final DateTime? tradingSince;
  final int? completedTrades;
  final double? responseTimeMinutes;
  final String verificationLevel;
  final double completionRate;
  final double averageReleaseMinutes;
  final double rating;
  final double completedVolumeFiat;
  final double disputeScore;
  final Map<String, Object?> terms;
  final List<Map<String, Object?>> paymentMethods;
  final List<Map<String, Object?>> bankAccounts;
  final Map<String, Object?> liquiditySnapshot;
  final List<GtexCoinTraderRate> rates;
  final Map<String, Object?> metadata;

  factory GtexCoinTraderProfile.fromJson(Object? raw) {
    final Map<String, Object?> json = _map(raw);
    final Map<String, Object?> metadata = _map(json['metadata_json']);
    return GtexCoinTraderProfile(
      id: _string(json['id']),
      userId: _string(json['user_id']),
      displayName: _string(json['display_name'], fallback: 'Coin trader'),
      countryCode: _stringOrNull(json['country_code']),
      status: _string(json['status'], fallback: 'applied'),
      tier: _string(json['tier'], fallback: 'bronze'),
      bio: _stringOrNull(json['bio']) ?? _stringOrNull(metadata['bio']),
      isOnline:
          _boolOrNull(json['is_online']) ??
          _boolOrNull(metadata['is_online']) ??
          _onlineStatus(metadata['online_status']),
      lastSeenAt:
          _dateTime(json['last_seen_at']) ??
          _dateTime(metadata['last_seen_at']) ??
          _dateTime(metadata['last_active_at']),
      tradingSince:
          _dateTime(json['trading_since']) ??
          _dateTime(json['created_at']) ??
          _dateTime(metadata['trading_since']) ??
          _dateTime(metadata['created_at']),
      completedTrades:
          _intOrNull(json['completed_trades']) ??
          _intOrNull(json['trade_count']) ??
          _intOrNull(metadata['completed_trades']) ??
          _intOrNull(metadata['trade_count']),
      responseTimeMinutes:
          _doubleOrNull(json['average_response_minutes']) ??
          _doubleOrNull(json['response_time_minutes']) ??
          _doubleOrNull(metadata['average_response_minutes']) ??
          _doubleOrNull(metadata['response_time_minutes']),
      verificationLevel: _string(
        json['verification_level'],
        fallback: 'standard',
      ),
      completionRate: _double(json['completion_rate']),
      averageReleaseMinutes: _double(json['average_release_minutes']),
      rating: _double(json['rating']),
      completedVolumeFiat: _double(json['completed_volume_fiat']),
      disputeScore: _double(json['dispute_score']),
      terms: _map(json['terms']),
      paymentMethods: _mapList(json['payment_methods']),
      bankAccounts: _mapList(json['bank_accounts']),
      liquiditySnapshot: _map(json['liquidity_snapshot']),
      rates: _list(
        json['rates'],
      ).map(GtexCoinTraderRate.fromJson).toList(growable: false),
      metadata: metadata,
    );
  }

  bool get isApproved => status.toLowerCase() == 'approved';

  double get totalLiquidity {
    return rates.fold<double>(
      0,
      (double total, GtexCoinTraderRate rate) =>
          total + rate.availableLiquidity,
    );
  }

  GtexCoinTraderRate? primaryRateFor(String coinUnit) {
    final String normalized = coinUnit.trim().toUpperCase();
    for (final GtexCoinTraderRate rate in rates) {
      if (rate.coinUnit == normalized && rate.isActive) {
        return rate;
      }
    }
    for (final GtexCoinTraderRate rate in rates) {
      if (rate.isActive) {
        return rate;
      }
    }
    return rates.isEmpty ? null : rates.first;
  }

  List<String> get activeCoinCodes {
    final Set<String> labels = <String>{};
    for (final GtexCoinTraderRate rate in rates) {
      if (rate.isActive) {
        labels.add(rate.coinCode);
      }
    }
    return labels.toList(growable: false);
  }

  String get onlineLabel {
    if (isOnline == true) {
      return 'Online now';
    }
    if (lastSeenAt != null) {
      return 'Last active ${_relativeTime(lastSeenAt!)}';
    }
    if (isOnline == false) {
      return 'Offline';
    }
    return 'Activity not published';
  }

  String get tradingSinceLabel {
    if (tradingSince == null) {
      return 'Trading since --';
    }
    return 'Since ${_monthYear(tradingSince!)}';
  }

  String get completedTradesLabel {
    if (completedTrades == null) {
      return 'Trades not published';
    }
    return '$completedTrades trades completed';
  }

  String get responseTimeLabel {
    if (responseTimeMinutes == null) {
      return 'Response not published';
    }
    return _minutesLabel(responseTimeMinutes!);
  }

  List<String> get paymentMethodLabels {
    return paymentMethods
        .map(
          (Map<String, Object?> item) =>
              _stringOrNull(item['label']) ??
              _stringOrNull(item['name']) ??
              _stringOrNull(item['type']) ??
              _stringOrNull(item['method']),
        )
        .whereType<String>()
        .toList(growable: false);
  }

  List<String> get bankAccountLabels {
    return bankAccounts
        .map(
          (Map<String, Object?> item) =>
              _stringOrNull(item['bank']) ??
              _stringOrNull(item['bank_name']) ??
              _stringOrNull(item['name']),
        )
        .whereType<String>()
        .toList(growable: false);
  }

  List<String> get termLabels {
    return terms.entries
        .where((MapEntry<String, Object?> entry) {
          final Object? value = entry.value;
          if (value == null) {
            return false;
          }
          if (value is bool) {
            return value;
          }
          if (value is String) {
            return value.trim().isNotEmpty;
          }
          return true;
        })
        .map((MapEntry<String, Object?> entry) {
          final String key = _titleCase(entry.key.replaceAll('_', ' '));
          final Object? value = entry.value;
          if (value is bool) {
            return key;
          }
          return '$key: $value';
        })
        .toList(growable: false);
  }
}

class GtexCoinTraderRate {
  const GtexCoinTraderRate({
    required this.id,
    required this.traderProfileId,
    required this.coinUnit,
    required this.fiatCurrency,
    required this.buyRateFiat,
    required this.sellRateFiat,
    required this.minCoinAmount,
    required this.maxCoinAmount,
    required this.availableLiquidity,
    required this.isActive,
    this.spreadFiat = 0,
    this.treasuryDepositRateFiat,
    this.treasuryWithdrawalRateFiat,
    this.minTraderBuyRateFiat,
    this.maxTraderBuyRateFiat,
    this.minTraderSellRateFiat,
    this.maxTraderSellRateFiat,
    this.maxTraderSpreadFiat,
    this.governanceStatus = 'compliant',
    this.governanceReasons = const <String>[],
    this.metadata = const <String, Object?>{},
  });

  final String id;
  final String traderProfileId;
  final String coinUnit;
  final String fiatCurrency;
  final double buyRateFiat;
  final double sellRateFiat;
  final double minCoinAmount;
  final double maxCoinAmount;
  final double availableLiquidity;
  final bool isActive;
  final double spreadFiat;
  final double? treasuryDepositRateFiat;
  final double? treasuryWithdrawalRateFiat;
  final double? minTraderBuyRateFiat;
  final double? maxTraderBuyRateFiat;
  final double? minTraderSellRateFiat;
  final double? maxTraderSellRateFiat;
  final double? maxTraderSpreadFiat;
  final String governanceStatus;
  final List<String> governanceReasons;
  final Map<String, Object?> metadata;

  factory GtexCoinTraderRate.fromJson(Object? raw) {
    final Map<String, Object?> json = _map(raw);
    return GtexCoinTraderRate(
      id: _string(json['id']),
      traderProfileId: _string(json['trader_profile_id']),
      coinUnit: _string(json['coin_unit'], fallback: 'COIN').toUpperCase(),
      fiatCurrency: _string(json['fiat_currency'], fallback: 'NGN'),
      buyRateFiat: _double(json['buy_rate_fiat']),
      sellRateFiat: _double(json['sell_rate_fiat']),
      minCoinAmount: _double(json['min_coin_amount']),
      maxCoinAmount: _double(json['max_coin_amount']),
      availableLiquidity: _double(json['available_liquidity']),
      isActive: _bool(json['is_active'], fallback: true),
      spreadFiat: _double(json['spread_fiat']),
      treasuryDepositRateFiat: _doubleOrNull(
        json['treasury_deposit_rate_fiat'],
      ),
      treasuryWithdrawalRateFiat: _doubleOrNull(
        json['treasury_withdrawal_rate_fiat'],
      ),
      minTraderBuyRateFiat: _doubleOrNull(json['min_trader_buy_rate_fiat']),
      maxTraderBuyRateFiat: _doubleOrNull(json['max_trader_buy_rate_fiat']),
      minTraderSellRateFiat: _doubleOrNull(json['min_trader_sell_rate_fiat']),
      maxTraderSellRateFiat: _doubleOrNull(json['max_trader_sell_rate_fiat']),
      maxTraderSpreadFiat: _doubleOrNull(json['max_trader_spread_fiat']),
      governanceStatus: _string(
        json['governance_status'],
        fallback: 'compliant',
      ),
      governanceReasons: _list(
        json['governance_reasons'],
      ).map((Object? value) => value.toString()).toList(growable: false),
      metadata: _map(json['metadata_json']),
    );
  }

  String get coinCode => coinUnit == 'CREDIT' ? 'FNC' : 'GTC';

  String get coinName => coinUnit == 'CREDIT' ? 'Fan Coin' : 'GTEX Coin';

  String get coinLabel => coinCode;

  bool get isGovernanceCompliant =>
      governanceStatus.toLowerCase() == 'compliant';

  bool get isRestricted => !isGovernanceCompliant;

  String get governanceLabel {
    switch (governanceStatus.toLowerCase()) {
      case 'arbitrage_risk':
        return 'Arbitrage risk';
      case 'out_of_bounds':
        return 'Out of bounds';
      default:
        return 'Compliant';
    }
  }
}

class GtexCoinTradeOrder {
  const GtexCoinTradeOrder({
    required this.id,
    required this.traderProfileId,
    required this.userId,
    required this.direction,
    required this.coinUnit,
    required this.coinAmount,
    required this.quotedRateFiat,
    required this.fiatTotal,
    required this.fiatCurrency,
    required this.status,
    this.escrowOwnerUserId,
    this.idempotencyKey,
    this.paymentMethod,
    this.paymentWindowExpiresAt,
    this.acceptedAt,
    this.proofSubmittedAt,
    this.releasedAt,
    this.cancelledAt,
    this.disputedAt,
    this.termsSnapshot = const <String, Object?>{},
    this.proof = const <String, Object?>{},
    this.ledgerRefs = const <String, Object?>{},
    this.metadata = const <String, Object?>{},
  });

  final String id;
  final String traderProfileId;
  final String userId;
  final String direction;
  final String coinUnit;
  final double coinAmount;
  final double quotedRateFiat;
  final double fiatTotal;
  final String fiatCurrency;
  final String status;
  final String? escrowOwnerUserId;
  final String? idempotencyKey;
  final String? paymentMethod;
  final DateTime? paymentWindowExpiresAt;
  final DateTime? acceptedAt;
  final DateTime? proofSubmittedAt;
  final DateTime? releasedAt;
  final DateTime? cancelledAt;
  final DateTime? disputedAt;
  final Map<String, Object?> termsSnapshot;
  final Map<String, Object?> proof;
  final Map<String, Object?> ledgerRefs;
  final Map<String, Object?> metadata;

  factory GtexCoinTradeOrder.fromJson(Object? raw) {
    final Map<String, Object?> json = _map(raw);
    return GtexCoinTradeOrder(
      id: _string(json['id']),
      traderProfileId: _string(json['trader_profile_id']),
      userId: _string(json['user_id']),
      direction: _string(json['direction'], fallback: 'user_buys'),
      coinUnit: _string(json['coin_unit'], fallback: 'COIN').toUpperCase(),
      coinAmount: _double(json['coin_amount']),
      quotedRateFiat: _double(json['quoted_rate_fiat']),
      fiatTotal: _double(json['fiat_total']),
      fiatCurrency: _string(json['fiat_currency'], fallback: 'NGN'),
      status: _string(json['status'], fallback: 'created'),
      escrowOwnerUserId: _stringOrNull(json['escrow_owner_user_id']),
      idempotencyKey: _stringOrNull(json['idempotency_key']),
      paymentMethod: _stringOrNull(json['payment_method']),
      paymentWindowExpiresAt: _dateTime(json['payment_window_expires_at']),
      acceptedAt: _dateTime(json['accepted_at']),
      proofSubmittedAt: _dateTime(json['proof_submitted_at']),
      releasedAt: _dateTime(json['released_at']),
      cancelledAt: _dateTime(json['cancelled_at']),
      disputedAt: _dateTime(json['disputed_at']),
      termsSnapshot: _map(json['terms_snapshot']),
      proof: _map(json['proof']),
      ledgerRefs: _map(json['ledger_refs']),
      metadata: _map(json['metadata_json']),
    );
  }

  bool get isUserBuys => direction == 'user_buys';

  bool get isUserSells => direction == 'user_sells';

  String get directionLabel => isUserSells ? 'User sells' : 'User buys';

  String get coinCode => coinUnit == 'CREDIT' ? 'FNC' : 'GTC';

  String get coinName => coinUnit == 'CREDIT' ? 'Fan Coin' : 'GTEX Coin';

  String get coinLabel => coinCode;

  String get statusLabel => _titleCase(status.replaceAll('_', ' '));

  bool get isActiveEscrow {
    final String normalized = status.toLowerCase();
    return normalized == 'payment_pending' || normalized == 'proof_submitted';
  }

  bool get canCancel {
    final String normalized = status.toLowerCase();
    return normalized == 'created' || isActiveEscrow;
  }

  bool get canAccept => status.toLowerCase() == 'created';

  bool get canSubmitProof => isActiveEscrow;

  bool get canConfirmRelease => status.toLowerCase() == 'proof_submitted';

  bool canSubmitProofFor({required bool isTrader}) {
    if (!canSubmitProof) {
      return false;
    }
    return isUserBuys ? !isTrader : isTrader;
  }

  bool canConfirmReleaseFor({required bool isTrader}) {
    if (!canConfirmRelease) {
      return false;
    }
    return isUserBuys ? isTrader : !isTrader;
  }

  bool get canDispute => isActiveEscrow;

  bool get canAdminResolve {
    final String normalized = status.toLowerCase();
    return isActiveEscrow || normalized == 'disputed';
  }

  List<String> get termsSnapshotLabels => _labelMap(termsSnapshot);

  List<String> get proofLabels => _labelMap(proof);

  List<String> get ledgerLabels => _labelMap(ledgerRefs);

  List<String> get metadataLabels => _labelMap(metadata);
}

Map<String, Object?> _map(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map<String, dynamic>) {
    return Map<String, Object?>.from(value);
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? entryValue) =>
          MapEntry<String, Object?>(key.toString(), entryValue),
    );
  }
  return const <String, Object?>{};
}

List<Object?> _list(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.toList(growable: false);
  }
  return const <Object?>[];
}

List<Map<String, Object?>> _mapList(Object? value) {
  return _list(value).map(_map).toList(growable: false);
}

String _string(Object? value, {String fallback = ''}) {
  return _stringOrNull(value) ?? fallback;
}

String? _stringOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  final String resolved = value.toString().trim();
  return resolved.isEmpty ? null : resolved;
}

double _double(Object? value, {double fallback = 0}) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? fallback;
}

double? _doubleOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

int? _intOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString());
}

bool _bool(Object? value, {bool fallback = false}) {
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
    return true;
  }
  if (normalized == 'false' || normalized == '0' || normalized == 'no') {
    return false;
  }
  return fallback;
}

bool? _boolOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is bool) {
    return value;
  }
  final String normalized = value.toString().trim().toLowerCase();
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

bool? _onlineStatus(Object? value) {
  final String? raw = _stringOrNull(value)?.toLowerCase();
  if (raw == null) {
    return null;
  }
  if (raw == 'online' || raw == 'available' || raw == 'live') {
    return true;
  }
  if (raw == 'offline' || raw == 'away' || raw == 'unavailable') {
    return false;
  }
  return null;
}

DateTime? _dateTime(Object? value) {
  final String? raw = _stringOrNull(value);
  if (raw == null) {
    return null;
  }
  return DateTime.tryParse(raw)?.toLocal();
}

String _relativeTime(DateTime value) {
  final Duration difference = DateTime.now().difference(value.toLocal());
  if (difference.inMinutes < 1) {
    return 'just now';
  }
  if (difference.inMinutes < 60) {
    return '${difference.inMinutes} min ago';
  }
  if (difference.inHours < 24) {
    return '${difference.inHours}h ago';
  }
  if (difference.inDays < 7) {
    return '${difference.inDays}d ago';
  }
  return _monthYear(value);
}

String _monthYear(DateTime value) {
  const List<String> months = <String>[
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final DateTime local = value.toLocal();
  return '${months[local.month - 1]} ${local.year}';
}

String _minutesLabel(double value) {
  if (value < 1) {
    return '<1 min';
  }
  if (value < 60) {
    final bool whole = value == value.roundToDouble();
    return '${value.toStringAsFixed(whole ? 0 : 1)} min';
  }
  final double hours = value / 60;
  return '${hours.toStringAsFixed(hours >= 10 ? 0 : 1)}h';
}

List<String> _labelMap(Map<String, Object?> values) {
  return values.entries
      .where((MapEntry<String, Object?> entry) => entry.value != null)
      .map((MapEntry<String, Object?> entry) {
        final String key = _titleCase(entry.key.replaceAll('_', ' '));
        final Object? value = entry.value;
        if (value is bool) {
          return value ? key : '$key: no';
        }
        if (value is Iterable) {
          return '$key: ${value.length}';
        }
        if (value is Map) {
          return '$key: ${value.length}';
        }
        return '$key: $value';
      })
      .toList(growable: false);
}

String _titleCase(String value) {
  return value
      .split(RegExp(r'\s+'))
      .where((String item) => item.isNotEmpty)
      .map(
        (String item) =>
            item.substring(0, 1).toUpperCase() +
            item.substring(1).toLowerCase(),
      )
      .join(' ');
}
