import '../../shared/data/gte_feature_support.dart';

class GiftEconomyBurnEventsQuery {
  const GiftEconomyBurnEventsQuery({
    this.userId,
    this.sourceType,
    this.limit = 100,
  });

  final String? userId;
  final String? sourceType;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
    'user_id': userId,
    'source_type': sourceType,
    'limit': limit,
  });
}

class GiftEconomyRuleListQuery {
  const GiftEconomyRuleListQuery({this.activeOnly = true});

  final bool activeOnly;

  Map<String, Object?> toQuery() => <String, Object?>{
    'active_only': activeOnly,
  };
}

class GiftCatalogItemUpsertRequest {
  const GiftCatalogItemUpsertRequest({
    required this.key,
    required this.displayName,
    this.fallbackDisplayName,
    this.tier = 'standard',
    this.rarity = 'common',
    this.currency = 'credit',
    this.fancoinPrice = 0,
    this.animationKey,
    this.soundKey,
    this.description,
    this.durationMs = 2500,
    this.legalStatus = 'safe',
    this.sortOrder = 0,
    this.isAwardPack = false,
    this.active = true,
  });

  final String key;
  final String displayName;
  final String? fallbackDisplayName;
  final String tier;
  final String rarity;
  final String currency;
  final double fancoinPrice;
  final String? animationKey;
  final String? soundKey;
  final String? description;
  final int durationMs;
  final String legalStatus;
  final int sortOrder;
  final bool isAwardPack;
  final bool active;

  JsonMap toJson() => <String, Object?>{
    'code': key,
    'key': key,
    'display_name': displayName,
    if (fallbackDisplayName != null)
      'fallback_display_name': fallbackDisplayName,
    'tier': tier,
    'rarity': rarity,
    'currency': currency,
    'cost_amount': fancoinPrice,
    'fancoin_price': fancoinPrice,
    if (animationKey != null) 'animation_key': animationKey,
    if (soundKey != null) 'sound_key': soundKey,
    if (description != null) 'description': description,
    'duration_ms': durationMs,
    'legal_status': legalStatus,
    'sort_order': sortOrder,
    'is_award_pack': isAwardPack,
    'is_active': active,
    'active': active,
  };
}

class RevenueShareRuleUpsertRequest {
  const RevenueShareRuleUpsertRequest({
    required this.ruleKey,
    required this.scope,
    required this.title,
    this.description,
    this.platformShareBps = 0,
    this.creatorShareBps = 0,
    this.recipientShareBps,
    this.burnBps = 0,
    this.priority = 10,
    this.active = true,
  });

  final String ruleKey;
  final String scope;
  final String title;
  final String? description;
  final int platformShareBps;
  final int creatorShareBps;
  final int? recipientShareBps;
  final int burnBps;
  final int priority;
  final bool active;

  JsonMap toJson() => <String, Object?>{
    'rule_key': ruleKey,
    'scope': scope,
    'title': title,
    if (description != null) 'description': description,
    'platform_share_bps': platformShareBps,
    'creator_share_bps': creatorShareBps,
    if (recipientShareBps != null) 'recipient_share_bps': recipientShareBps,
    'burn_bps': burnBps,
    'priority': priority,
    'active': active,
  };
}

class GiftComboRuleUpsertRequest {
  const GiftComboRuleUpsertRequest({
    required this.ruleKey,
    required this.title,
    this.description,
    this.minComboCount = 2,
    this.windowSeconds = 120,
    this.bonusBps = 0,
    this.priority = 10,
    this.active = true,
  });

  final String ruleKey;
  final String title;
  final String? description;
  final int minComboCount;
  final int windowSeconds;
  final int bonusBps;
  final int priority;
  final bool active;

  JsonMap toJson() => <String, Object?>{
    'rule_key': ruleKey,
    'title': title,
    if (description != null) 'description': description,
    'min_combo_count': minComboCount,
    'window_seconds': windowSeconds,
    'bonus_bps': bonusBps,
    'priority': priority,
    'active': active,
  };
}

class GiftCatalogItem {
  const GiftCatalogItem._(this.raw);

  final JsonMap raw;

  factory GiftCatalogItem.fromJson(Object? value) {
    return GiftCatalogItem._(jsonMap(value, label: 'gift catalog item'));
  }

  String get id => stringValue(raw['id']);
  String get key => stringValue(raw['key'] ?? raw['code']);
  String get displayName => stringValue(raw['display_name']);
  String? get fallbackDisplayName =>
      stringOrNullValue(raw['fallback_display_name']);
  String get tier => stringValue(raw['tier']);
  String get rarity => stringValue(raw['rarity'], fallback: tier);
  String get currency => stringValue(raw['currency'], fallback: 'credit');
  String get currencyLabel =>
      stringValue(raw['currency_label'], fallback: 'Fan Coin');
  double get fancoinPrice =>
      numberValue(raw['fancoin_price'] ?? raw['cost_amount']);
  String? get animationKey => stringOrNullValue(raw['animation_key']);
  String? get soundKey => stringOrNullValue(raw['sound_key']);
  String? get description => stringOrNullValue(raw['description']);
  int get durationMs => intValue(raw['duration_ms'], fallback: 2500);
  bool get isAwardPack => boolValue(raw['is_award_pack']);
  String get legalStatus => stringValue(raw['legal_status'], fallback: 'safe');
  int get sortOrder => intValue(raw['sort_order']);
  bool get active => boolValue(raw['active'] ?? raw['is_active']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class GiftEvent {
  const GiftEvent._(this.raw);

  final JsonMap raw;

  factory GiftEvent.fromJson(Object? value) {
    return GiftEvent._(jsonMap(value, label: 'gift event'));
  }

  String get id => stringValue(raw['id']);
  String get senderUserId => stringValue(raw['sender_user_id']);
  String get recipientUserId => stringValue(raw['recipient_user_id']);
  String get giftKey => stringValue(raw['gift_key']);
  String get giftDisplayName => stringValue(raw['gift_display_name']);
  String get rarity => stringValue(raw['rarity'], fallback: 'common');
  double get grossAmount => numberValue(raw['gross_amount']);
  double get platformRakeAmount => numberValue(raw['platform_rake_amount']);
  double get recipientNetAmount => numberValue(raw['recipient_net_amount']);
  String get currencyLabel =>
      stringValue(raw['currency_label'], fallback: 'Fan Coin');
  String get status => stringValue(raw['status'], fallback: 'settled');
  String get abuseStatus => stringValue(raw['abuse_status'], fallback: 'clean');
  String? get chatThreadId => stringOrNullValue(raw['chat_thread_id']);
  String? get discussionThreadId =>
      stringOrNullValue(raw['discussion_thread_id']);
  String? get animationKey => stringOrNullValue(raw['animation_key']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class GiftAbuseFlag {
  const GiftAbuseFlag._(this.raw);

  final JsonMap raw;

  factory GiftAbuseFlag.fromJson(Object? value) {
    return GiftAbuseFlag._(jsonMap(value, label: 'gift abuse flag'));
  }

  String get id => stringValue(raw['id']);
  String get flagKey => stringValue(raw['flag_key']);
  String get senderUserId => stringValue(raw['sender_user_id']);
  String get recipientType => stringValue(raw['recipient_type']);
  String get recipientId => stringValue(raw['recipient_id']);
  String? get giftTransactionId =>
      stringOrNullValue(raw['gift_transaction_id']);
  String get flagType => stringValue(raw['flag_type']);
  String get severity => stringValue(raw['severity'], fallback: 'medium');
  String get description => stringValue(raw['description']);
  String get status => stringValue(raw['status'], fallback: 'open');
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class RevenueShareRule {
  const RevenueShareRule._(this.raw);

  final JsonMap raw;

  factory RevenueShareRule.fromJson(Object? value) {
    return RevenueShareRule._(jsonMap(value, label: 'revenue share rule'));
  }

  String get id => stringValue(raw['id']);
  String get ruleKey => stringValue(raw['rule_key']);
  String get scope => stringValue(raw['scope']);
  String get title => stringValue(raw['title']);
  String? get description => stringOrNullValue(raw['description']);
  int get platformShareBps => intValue(raw['platform_share_bps']);
  int get creatorShareBps => intValue(raw['creator_share_bps']);
  int? get recipientShareBps =>
      raw['recipient_share_bps'] == null
          ? null
          : intValue(raw['recipient_share_bps']);
  int get burnBps => intValue(raw['burn_bps']);
  int get priority => intValue(raw['priority']);
  bool get active => boolValue(raw['active']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class GiftComboRule {
  const GiftComboRule._(this.raw);

  final JsonMap raw;

  factory GiftComboRule.fromJson(Object? value) {
    return GiftComboRule._(jsonMap(value, label: 'gift combo rule'));
  }

  String get id => stringValue(raw['id']);
  String get ruleKey => stringValue(raw['rule_key']);
  String get title => stringValue(raw['title']);
  String? get description => stringOrNullValue(raw['description']);
  int get minComboCount => intValue(raw['min_combo_count']);
  int get windowSeconds => intValue(raw['window_seconds']);
  int get bonusBps => intValue(raw['bonus_bps']);
  int get priority => intValue(raw['priority']);
  bool get active => boolValue(raw['active']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class EconomyBurnEvent {
  const EconomyBurnEvent._(this.raw);

  final JsonMap raw;

  factory EconomyBurnEvent.fromJson(Object? value) {
    return EconomyBurnEvent._(jsonMap(value, label: 'economy burn event'));
  }

  String get id => stringValue(raw['id']);
  String? get userId => stringOrNullValue(raw['user_id']);
  String get sourceType => stringValue(raw['source_type']);
  String? get sourceId => stringOrNullValue(raw['source_id']);
  double get amount => numberValue(raw['amount']);
  String get unit => stringValue(raw['unit']);
  String get reason => stringValue(raw['reason']);
  String? get ledgerTransactionId =>
      stringOrNullValue(raw['ledger_transaction_id']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}
