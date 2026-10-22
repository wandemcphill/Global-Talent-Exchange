import 'gte_api_repository.dart';
import 'gte_authed_api.dart';

class MatchGiftCatalogItem {
  const MatchGiftCatalogItem({
    required this.key,
    required this.label,
    required this.description,
    required this.fanCoinAmount,
    this.currencyLabel = 'Fan Coin',
    this.rarity = 'common',
    this.tier = 'standard',
    this.animationKey,
    this.soundKey,
    this.durationMs = 1800,
    this.isAwardPack = false,
    this.legalStatus = 'safe',
  });

  factory MatchGiftCatalogItem.fromJson(Map<String, dynamic> json) {
    final Object? amount = json['cost_amount'] ?? json['fancoin_price'] ?? json['price'];
    return MatchGiftCatalogItem(
      key: _stringOrNullValue(json['code'] ?? json['key'] ?? json['gift_key']) ?? '',
      label: _stringOrNullValue(json['display_name'] ?? json['label']) ?? 'Gift',
      description: _stringOrNullValue(json['description']) ?? 'A gift for a memorable football moment.',
      fanCoinAmount: amount is num ? amount.toDouble() : double.tryParse('${amount ?? ''}') ?? 0,
      currencyLabel: _stringOrNullValue(json['currency_label']) ??
          (_stringOrNullValue(json['currency']) == 'coin' ? 'GTEX Coin' : 'Fan Coin'),
      rarity: _stringOrNullValue(json['rarity']) ?? _stringOrNullValue(json['tier']) ?? 'common',
      tier: _stringOrNullValue(json['tier']) ?? _stringOrNullValue(json['rarity']) ?? 'standard',
      animationKey: _stringOrNullValue(json['animation_key']),
      soundKey: _stringOrNullValue(json['sound_key']),
      durationMs: _toInt(json['duration_ms'], fallback: 1800),
      isAwardPack: json['is_award_pack'] == true,
      legalStatus: _stringOrNullValue(json['legal_status']) ?? 'safe',
    );
  }

  final String key;
  final String label;
  final String description;
  final double fanCoinAmount;
  final String currencyLabel;
  final String rarity;
  final String tier;
  final String? animationKey;
  final String? soundKey;
  final int durationMs;
  final bool isAwardPack;
  final String legalStatus;

  bool get requiresReview => legalStatus.trim().toLowerCase() == 'requires_review';

  String get priceLabel {
    final String amount = fanCoinAmount == fanCoinAmount.roundToDouble()
        ? fanCoinAmount.toStringAsFixed(0)
        : fanCoinAmount.toStringAsFixed(2);
    return '$amount $currencyLabel';
  }
}

/// Local graceful fallback mirrors canonical keys in backend/app/gift_engine/catalog.py.
/// Live sessions load the server's active catalogue via [MatchGiftCatalogProvider].
const List<MatchGiftCatalogItem> kMatchGiftCatalog = <MatchGiftCatalogItem>[
  MatchGiftCatalogItem(
    key: 'whistle_blow',
    label: 'Whistle Blow',
    description: 'A sharp referee whistle to mark a big moment.',
    fanCoinAmount: 1,
    rarity: 'common',
    animationKey: 'common_whistle',
    soundKey: 'whistle_pop',
    durationMs: 1200,
  ),
  MatchGiftCatalogItem(
    key: 'fan_chant',
    label: 'Fan Chant',
    description: 'Bring the terraces to life with a wall of sound.',
    fanCoinAmount: 2,
    rarity: 'common',
    animationKey: 'fan_chant',
    soundKey: 'crowd_chant',
    durationMs: 1600,
  ),
  MatchGiftCatalogItem(
    key: 'goal_celebration',
    label: 'Goal Celebration',
    description: 'A crowd-roaring celebration for a decisive play.',
    fanCoinAmount: 10,
    rarity: 'rare',
    animationKey: 'goal_celebration',
    soundKey: 'goal_roar',
    durationMs: 2200,
  ),
  MatchGiftCatalogItem(
    key: 'legend_card_reveal',
    label: 'Legend Card Reveal',
    description: 'A premium football-card reveal for a standout moment.',
    fanCoinAmount: 150,
    rarity: 'epic',
    animationKey: 'legend_card_reveal',
    soundKey: 'card_reveal_riser',
    durationMs: 3600,
  ),
  MatchGiftCatalogItem(
    key: 'tactical_masterclass',
    label: 'Tactical Masterclass',
    description: 'A glowing tactics board for the football purist.',
    fanCoinAmount: 180,
    rarity: 'epic',
    animationKey: 'tactical_masterclass',
    soundKey: 'tactics_board_ping',
    durationMs: 3600,
  ),
  MatchGiftCatalogItem(
    key: 'player_of_the_match',
    label: 'Player of the Match',
    description: 'Put the spotlight on a game-changing performance.',
    fanCoinAmount: 500,
    rarity: 'epic',
    animationKey: 'player_of_the_match',
    soundKey: 'mvp_card_hit',
    durationMs: 4000,
    isAwardPack: true,
  ),
  MatchGiftCatalogItem(
    key: 'king_of_tactics',
    label: 'King of Tactics',
    description: 'An elite tactical crown reveal for a football mind.',
    fanCoinAmount: 1100,
    rarity: 'legendary',
    animationKey: 'king_of_tactics',
    soundKey: 'tactics_crown_hit',
    durationMs: 5000,
    isAwardPack: true,
  ),
  MatchGiftCatalogItem(
    key: 'ballon_dor',
    label: 'Ballon d’Or',
    description: 'A full stadium ceremony for the ultimate football gift.',
    fanCoinAmount: 10000,
    rarity: 'mythic',
    animationKey: 'ballon_dor',
    soundKey: 'stadium_ceremony_roar',
    durationMs: 8000,
    isAwardPack: true,
    legalStatus: 'requires_review',
  ),
];

abstract interface class MatchGiftClient {
  Future<MatchGiftReceipt> sendGift({
    required MatchGiftTarget target,
    required MatchGiftCatalogItem gift,
  });
}

abstract interface class MatchGiftCatalogProvider {
  Future<List<MatchGiftCatalogItem>> fetchCatalog();
}

class MatchGiftTarget {
  const MatchGiftTarget({
    required this.recipientUserId,
    required this.recipientLabel,
    required this.sourceScope,
  });

  final String recipientUserId;
  final String recipientLabel;
  final String sourceScope;

  static MatchGiftTarget? fromMetadata(Map<String, Object?>? metadata) {
    if (metadata == null || metadata.isEmpty) {
      return null;
    }
    final String recipientUserId = _stringValue(metadata['gift_recipient_user_id']);
    if (recipientUserId.isEmpty) {
      return null;
    }
    final String recipientLabel =
        _stringOrNullValue(metadata['gift_recipient_label']) ?? 'Match host';
    final String sourceScope =
        _stringOrNullValue(metadata['gift_source_scope']) ?? 'user_hosted';
    return MatchGiftTarget(
      recipientUserId: recipientUserId,
      recipientLabel: recipientLabel,
      sourceScope: sourceScope,
    );
  }
}

class MatchGiftReceipt {
  const MatchGiftReceipt({
    required this.giftKey,
    required this.giftDisplayName,
    required this.grossAmount,
    required this.ledgerUnit,
    required this.recipientLabel,
    this.rarity = 'common',
    this.animationKey,
    this.soundKey,
    this.durationMs = 1800,
  });

  final String giftKey;
  final String giftDisplayName;
  final String grossAmount;
  final String ledgerUnit;
  final String recipientLabel;
  final String rarity;
  final String? animationKey;
  final String? soundKey;
  final int durationMs;

  String get currencyLabel => _unitLabelForLedger(ledgerUnit);

  String get confirmationMessage =>
      '$giftDisplayName sent to $recipientLabel for $grossAmount $currencyLabel.';

  factory MatchGiftReceipt.fromResponse(
    Object? payload, {
    required MatchGiftTarget target,
  }) {
    if (payload is! Map) {
      throw const GteApiException(
        type: GteApiErrorType.parsing,
        message: 'Unexpected gift response shape.',
      );
    }
    final Map<String, Object?> map = Map<String, Object?>.from(payload);
    final Map<String, dynamic> animation = map['animation_payload'] is Map
        ? Map<String, dynamic>.from(map['animation_payload'] as Map)
        : <String, dynamic>{};
    return MatchGiftReceipt(
      giftKey: _stringValue(map['gift_key'] ?? animation['gift_code']),
      giftDisplayName: _stringOrNullValue(map['gift_display_name'] ?? animation['gift_name']) ?? 'Gift',
      grossAmount: _stringOrNullValue(map['gross_amount'] ?? animation['amount']) ?? '0.0000',
      ledgerUnit: _stringOrNullValue(map['ledger_unit']) ??
          _ledgerUnitForScope(target.sourceScope),
      recipientLabel: target.recipientLabel,
      rarity: _stringOrNullValue(map['rarity'] ?? animation['rarity']) ?? 'common',
      animationKey: _stringOrNullValue(map['animation_key'] ?? animation['animation_key']),
      soundKey: _stringOrNullValue(map['sound_key'] ?? animation['sound_key']),
      durationMs: _toInt(map['duration_ms'] ?? animation['duration_ms'], fallback: 1800),
    );
  }
}

class MatchGiftApi implements MatchGiftClient, MatchGiftCatalogProvider {
  const MatchGiftApi({required this.client});

  final GteAuthedApi client;

  @override
  Future<List<MatchGiftCatalogItem>> fetchCatalog() async {
    final List<dynamic> payload = await client.getList('/gifts/catalog');
    final items = payload
        .whereType<Map<dynamic, dynamic>>()
        .map((Map<dynamic, dynamic> row) => MatchGiftCatalogItem.fromJson(
              Map<String, dynamic>.from(row),
            ))
        .where((MatchGiftCatalogItem item) => item.key.isNotEmpty)
        .toList(growable: false);
    return items.isEmpty ? kMatchGiftCatalog : items;
  }

  @override
  Future<MatchGiftReceipt> sendGift({
    required MatchGiftTarget target,
    required MatchGiftCatalogItem gift,
  }) async {
    final Object? payload = await client.post(
      '/api/gift-engine/send',
      body: <String, Object?>{
        'recipient_user_id': target.recipientUserId,
        'gift_key': gift.key,
        'quantity': '1.0000',
        'source_scope': target.sourceScope,
      },
    );
    return MatchGiftReceipt.fromResponse(payload, target: target);
  }
}

String _stringValue(Object? value) {
  final String text = value?.toString().trim() ?? '';
  return text;
}

String? _stringOrNullValue(Object? value) {
  final String text = _stringValue(value);
  return text.isEmpty ? null : text;
}

int _toInt(Object? value, {required int fallback}) {
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse('${value ?? ''}') ?? fallback;
}

String _ledgerUnitForScope(String sourceScope) {
  final String normalized = sourceScope.trim().toLowerCase();
  if (normalized == 'gtex' ||
      normalized == 'gtex_platform' ||
      normalized == 'gtex_competition') {
    return 'coin';
  }
  return 'credit';
}

String _unitLabelForLedger(String ledgerUnit) {
  return ledgerUnit.trim().toLowerCase() == 'coin' ? 'GTEX Coin' : 'Fan Coin';
}
