import 'package:gte_frontend/data/gte_models.dart';

String? _generatedImageUrl(Map<String, Object?> json) {
  return GteJson.stringOrNull(json, <String>[
    'image_url',
    'portrait_url',
    'photo_url',
    'imageUrl',
    'portraitUrl',
  ]);
}

class RequestSonOrderDraft {
  const RequestSonOrderDraft({
    required this.parentPlayerId,
    required this.paymentMethod,
    this.requestedName,
    this.requestedCountryCode,
    this.requestedPosition,
  });

  final String parentPlayerId;
  final String paymentMethod;
  final String? requestedName;
  final String? requestedCountryCode;
  final String? requestedPosition;

  Map<String, Object?> toJson() => <String, Object?>{
    'parent_player_id': parentPlayerId,
    'payment_method': paymentMethod,
    if ((requestedName ?? '').trim().isNotEmpty)
      'requested_name': requestedName!.trim(),
    if ((requestedCountryCode ?? '').trim().isNotEmpty)
      'requested_country_code': requestedCountryCode!.trim().toUpperCase(),
    if ((requestedPosition ?? '').trim().isNotEmpty)
      'requested_position': requestedPosition!.trim().toUpperCase(),
  };
}

class RegenCreationPricing {
  const RegenCreationPricing({
    required this.baseCostCoin,
    required this.nameCostCoin,
    required this.customizationCostCoin,
  });

  final double baseCostCoin;
  final double nameCostCoin;
  final double customizationCostCoin;

  factory RegenCreationPricing.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation pricing',
    );
    return RegenCreationPricing(
      baseCostCoin: GteJson.number(json, <String>[
        'base_cost_coin',
        'baseCostCoin',
      ]),
      nameCostCoin: GteJson.number(json, <String>[
        'name_cost_coin',
        'nameCostCoin',
      ]),
      customizationCostCoin: GteJson.number(json, <String>[
        'customization_cost_coin',
        'customizationCostCoin',
      ]),
    );
  }
}

class RegenCreationParentPlayer {
  const RegenCreationParentPlayer({
    required this.playerId,
    required this.fullName,
    this.position,
    this.countryCode,
    this.countryName,
    this.imageUrl,
    this.clubId,
    this.clubName,
  });

  final String playerId;
  final String fullName;
  final String? position;
  final String? countryCode;
  final String? countryName;
  final String? imageUrl;
  final String? clubId;
  final String? clubName;

  factory RegenCreationParentPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation parent player',
    );
    return RegenCreationParentPlayer(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      fullName: GteJson.string(json, <String>['full_name', 'fullName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      countryName: GteJson.stringOrNull(json, <String>[
        'country_name',
        'countryName',
      ]),
      imageUrl: _generatedImageUrl(json),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      clubName: GteJson.stringOrNull(json, <String>['club_name', 'clubName']),
    );
  }
}

class RegenCreationGeneratedPlayer {
  const RegenCreationGeneratedPlayer({
    required this.playerId,
    required this.regenProfileId,
    required this.fullName,
    required this.age,
    required this.position,
    required this.currentRating,
    required this.potentialRating,
    this.countryCode,
    this.countryName,
    this.clubId,
    this.clubName,
    this.imageUrl,
    this.cardId,
  });

  final String playerId;
  final String regenProfileId;
  final String fullName;
  final int age;
  final String position;
  final String? countryCode;
  final String? countryName;
  final String? clubId;
  final String? clubName;
  final String? imageUrl;
  final int currentRating;
  final int potentialRating;
  final String? cardId;

  factory RegenCreationGeneratedPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation generated player',
    );
    return RegenCreationGeneratedPlayer(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      regenProfileId: GteJson.string(json, <String>[
        'regen_profile_id',
        'regenProfileId',
      ]),
      fullName: GteJson.string(json, <String>['full_name', 'fullName']),
      age: GteJson.integer(json, <String>['age']),
      position: GteJson.string(json, <String>['position']),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      countryName: GteJson.stringOrNull(json, <String>[
        'country_name',
        'countryName',
      ]),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      clubName: GteJson.stringOrNull(json, <String>['club_name', 'clubName']),
      imageUrl: _generatedImageUrl(json),
      currentRating: GteJson.integer(json, <String>[
        'current_rating',
        'currentRating',
      ]),
      potentialRating: GteJson.integer(json, <String>[
        'potential_rating',
        'potentialRating',
      ]),
      cardId: GteJson.stringOrNull(json, <String>['card_id', 'cardId']),
    );
  }
}

class RegenCreationOrder {
  const RegenCreationOrder({
    required this.id,
    required this.userId,
    required this.requestType,
    required this.amountCoin,
    required this.currency,
    required this.paymentMethod,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.clubId,
    this.parentPlayerId,
    this.requestedName,
    this.requestedCountryCode,
    this.requestedPosition,
    this.amountMinor,
    this.paymentProvider,
    this.paymentReference,
    this.generatedPlayerId,
    this.generatedRegenProfileId,
    this.paymentLink,
    this.mockPayment = false,
    this.paidAt,
    this.generatedAt,
    this.generatedPlayer,
  });

  final String id;
  final String userId;
  final String? clubId;
  final String requestType;
  final String? parentPlayerId;
  final String? requestedName;
  final String? requestedCountryCode;
  final String? requestedPosition;
  final double amountCoin;
  final int? amountMinor;
  final String currency;
  final String paymentMethod;
  final String? paymentProvider;
  final String? paymentReference;
  final String status;
  final String? generatedPlayerId;
  final String? generatedRegenProfileId;
  final String? paymentLink;
  final bool mockPayment;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? paidAt;
  final DateTime? generatedAt;
  final RegenCreationGeneratedPlayer? generatedPlayer;

  bool get isPendingPayment => status == 'pending_payment';
  bool get isGenerated => status == 'generated' && generatedPlayer != null;
  bool get usesWallet => paymentMethod == 'wallet';
  bool get usesKorapay => paymentMethod == 'korapay';

  factory RegenCreationOrder.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation order',
    );
    final Object? generatedPlayerValue = GteJson.value(json, <String>[
      'generated_player',
      'generatedPlayer',
    ]);
    return RegenCreationOrder(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      requestType: GteJson.string(json, <String>[
        'request_type',
        'requestType',
      ]),
      parentPlayerId: GteJson.stringOrNull(json, <String>[
        'parent_player_id',
        'parentPlayerId',
      ]),
      requestedName: GteJson.stringOrNull(json, <String>[
        'requested_name',
        'requestedName',
      ]),
      requestedCountryCode: GteJson.stringOrNull(json, <String>[
        'requested_country_code',
        'requestedCountryCode',
      ]),
      requestedPosition: GteJson.stringOrNull(json, <String>[
        'requested_position',
        'requestedPosition',
      ]),
      amountCoin: GteJson.number(json, <String>['amount_coin', 'amountCoin']),
      amountMinor: GteJson.integerOrNull(json, <String>[
        'amount_minor',
        'amountMinor',
      ]),
      currency: GteJson.string(json, <String>['currency']),
      paymentMethod: GteJson.string(json, <String>[
        'payment_method',
        'paymentMethod',
      ]),
      paymentProvider: GteJson.stringOrNull(json, <String>[
        'payment_provider',
        'paymentProvider',
      ]),
      paymentReference: GteJson.stringOrNull(json, <String>[
        'payment_reference',
        'paymentReference',
      ]),
      status: GteJson.string(json, <String>['status']),
      generatedPlayerId: GteJson.stringOrNull(json, <String>[
        'generated_player_id',
        'generatedPlayerId',
      ]),
      generatedRegenProfileId: GteJson.stringOrNull(json, <String>[
        'generated_regen_profile_id',
        'generatedRegenProfileId',
      ]),
      paymentLink: GteJson.stringOrNull(json, <String>[
        'payment_link',
        'paymentLink',
      ]),
      mockPayment: GteJson.boolean(json, <String>[
        'mock_payment',
        'mockPayment',
      ]),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
      paidAt: GteJson.dateTimeOrNull(json, <String>['paid_at', 'paidAt']),
      generatedAt: GteJson.dateTimeOrNull(json, <String>[
        'generated_at',
        'generatedAt',
      ]),
      generatedPlayer:
          generatedPlayerValue == null
              ? null
              : RegenCreationGeneratedPlayer.fromJson(generatedPlayerValue),
    );
  }
}

class RegenCreationOrderList {
  const RegenCreationOrderList({required this.items});

  final List<RegenCreationOrder> items;

  factory RegenCreationOrderList.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation order list',
    );
    return RegenCreationOrderList(
      items: GteJson.typedList(json, <String>[
        'items',
      ], RegenCreationOrder.fromJson),
    );
  }
}

class RequestSonOptions {
  const RequestSonOptions({
    required this.clubId,
    required this.clubName,
    required this.currency,
    required this.pricing,
    required this.eligibleParents,
  });

  final String clubId;
  final String clubName;
  final String currency;
  final RegenCreationPricing pricing;
  final List<RegenCreationParentPlayer> eligibleParents;

  factory RequestSonOptions.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'request son options',
    );
    return RequestSonOptions(
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, <String>['club_name', 'clubName']),
      currency: GteJson.string(json, <String>['currency'], fallback: 'COIN'),
      pricing: RegenCreationPricing.fromJson(
        GteJson.value(json, <String>['pricing']) ?? const <String, Object?>{},
      ),
      eligibleParents: GteJson.typedList(json, <String>[
        'eligible_parents',
        'eligibleParents',
      ], RegenCreationParentPlayer.fromJson),
    );
  }
}
