import 'gte_api_repository.dart';
import 'gte_authed_api.dart';

class MatchGiftCatalogItem {
  const MatchGiftCatalogItem({
    required this.key,
    required this.label,
    required this.fanCoinAmount,
  });

  final String key;
  final String label;
  final double fanCoinAmount;
}

const List<MatchGiftCatalogItem> kMatchGiftCatalog = <MatchGiftCatalogItem>[
  MatchGiftCatalogItem(key: 'fire', label: 'Fire', fanCoinAmount: 2),
  MatchGiftCatalogItem(key: 'applause', label: 'Applause', fanCoinAmount: 5),
  MatchGiftCatalogItem(key: 'crown', label: 'Crown', fanCoinAmount: 20),
];

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
    final String recipientUserId = _stringValue(
      metadata['gift_recipient_user_id'],
    );
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

abstract class MatchGiftClient {
  Future<MatchGiftReceipt> sendGift({
    required MatchGiftTarget target,
    required MatchGiftCatalogItem gift,
  });
}

class MatchGiftReceipt {
  const MatchGiftReceipt({
    required this.giftKey,
    required this.giftDisplayName,
    required this.grossAmount,
    required this.recipientLabel,
  });

  final String giftKey;
  final String giftDisplayName;
  final String grossAmount;
  final String recipientLabel;

  String get confirmationMessage =>
      '$giftDisplayName sent to $recipientLabel for $grossAmount Fan Coin.';

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
    return MatchGiftReceipt(
      giftKey: _stringValue(map['gift_key']),
      giftDisplayName: _stringOrNullValue(map['gift_display_name']) ?? 'Gift',
      grossAmount: _stringOrNullValue(map['gross_amount']) ?? '0.0000',
      recipientLabel: target.recipientLabel,
    );
  }
}

class MatchGiftApi implements MatchGiftClient {
  const MatchGiftApi({required this.client});

  final GteAuthedApi client;

  @override
  Future<MatchGiftReceipt> sendGift({
    required MatchGiftTarget target,
    required MatchGiftCatalogItem gift,
  }) async {
    final Object? payload = await client.post(
      '/gift-engine/send',
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
