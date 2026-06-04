import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_availability.dart';

const List<String> regenDnaStatCodes = <String>[
  'PAC',
  'SHO',
  'PAS',
  'DRI',
  'DEF',
  'PHY',
];

String? _generatedImageUrl(Map<String, Object?> json) {
  return GteJson.stringOrNull(json, <String>[
    'image_url',
    'portrait_url',
    'photo_url',
    'imageUrl',
    'portraitUrl',
  ]);
}

List<String> _stringList(
  Map<String, Object?> json,
  List<String> keys, {
  List<String> fallback = const <String>[],
}) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return fallback;
  }
  if (rawValue is Iterable) {
    return rawValue
        .map((Object? value) => value?.toString().trim() ?? '')
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);
  }
  if (rawValue is Map) {
    return rawValue.values
        .where(
          (Object? value) =>
              value != null &&
              value is! Iterable &&
              value is! Map &&
              value.toString().trim().isNotEmpty,
        )
        .map((Object? value) => value.toString().trim())
        .toList(growable: false);
  }
  final String parsed = rawValue.toString().trim();
  return parsed.isEmpty ? fallback : <String>[parsed];
}

List<String> _normalizedTraits(Iterable<String> traits) {
  final Set<String> seen = <String>{};
  final List<String> normalized = <String>[];
  for (final String trait in traits) {
    final String value = trait.trim();
    if (value.isEmpty || !seen.add(value.toLowerCase())) {
      continue;
    }
    normalized.add(value);
  }
  return normalized;
}

List<String> _lineageList(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue is! Map) {
    return _stringList(json, keys);
  }
  final Map<Object?, Object?> rawMap = rawValue;
  final List<String> values = <String>[];
  for (final String key in <String>[
    'narrative_text',
    'narrativeText',
    'lineage_label',
    'lineageLabel',
    'bloodline_label',
    'bloodlineLabel',
    'related_legend_name',
    'relatedLegendName',
    'parent_name',
    'parentName',
    'relationship_type',
    'relationshipType',
    'lineage_tier',
    'lineageTier',
    'lineage_country_code',
    'lineageCountryCode',
  ]) {
    final Object? value = rawMap[key];
    if (value is String && value.trim().isNotEmpty) {
      values.add(value.trim().replaceAll('_', ' '));
    }
  }
  final Object? generation =
      rawMap['generation'] ??
      rawMap['generation_number'] ??
      rawMap['generationNumber'];
  final int? generationNumber =
      generation is num ? generation.toInt() : int.tryParse('$generation');
  if (generationNumber != null && generationNumber > 0) {
    values.add('GEN-$generationNumber');
  }
  return _normalizedTraits(values);
}

List<String> _requiredStringList(
  Map<String, Object?> json,
  String key, {
  required String label,
}) {
  final Object? rawValue = json[key];
  final List<Object?> rawItems = GteJson.list(rawValue, label: label);
  return rawItems
      .map((Object? value) {
        if (value is! String) {
          throw GteParsingException('$label must contain strings.', rawValue);
        }
        final String trimmed = value.trim();
        if (trimmed.isEmpty) {
          throw GteParsingException(
            '$label cannot contain empty strings.',
            rawValue,
          );
        }
        return trimmed;
      })
      .toList(growable: false);
}

String? _canonicalRequestedPosition(String? value) {
  final String trimmed = (value ?? '').trim().toUpperCase();
  if (trimmed.isEmpty) {
    return null;
  }
  const Map<String, String> aliases = <String, String>{
    'CDM': 'DM',
    'CAM': 'AM',
    'LCB': 'CB',
    'RCB': 'CB',
    'LWB': 'LB',
    'RWB': 'RB',
    'LM': 'LW',
    'RM': 'RW',
    'CF': 'ST',
  };
  return aliases[trimmed] ?? trimmed;
}

String _requestSonPaymentMethod(String value) {
  final String trimmed = value.trim().toLowerCase();
  if (trimmed != 'wallet') {
    throw GteParsingException(
      'Request-son creation must use wallet payment.',
      value,
    );
  }
  return trimmed;
}

int? _generationNumberFromLabel(String? label) {
  if (label == null) {
    return null;
  }
  final RegExpMatch? match = RegExp(
    r'GEN-?(\d+)',
  ).firstMatch(label.toUpperCase());
  return match == null ? null : int.tryParse(match.group(1) ?? '');
}

Object? _firstValue(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    if (json.containsKey(key)) {
      return json[key];
    }
  }
  return null;
}

bool _hasAnyValue(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value == null) {
      continue;
    }
    if (value is String && value.trim().isEmpty) {
      continue;
    }
    return true;
  }
  return false;
}

bool _hasDnaCode(Map<String, Object?> json, String code) {
  return _hasAnyValue(json, <String>[
    code,
    code.toLowerCase(),
    code.toUpperCase(),
  ]);
}

RegenDnaProfile? _optionalCanonicalDnaProfile(Object? value) {
  if (value == null) {
    return null;
  }
  final Map<String, Object?> json = GteJson.map(
    value,
    label: 'optional regen DNA profile',
  );
  for (final String code in regenDnaStatCodes) {
    if (!_hasDnaCode(json, code)) {
      return null;
    }
  }
  return RegenDnaProfile.fromJson(json);
}

List<String> _missingKeys(
  Map<String, Object?> json,
  Map<String, List<String>> requiredGroups,
) {
  return <String>[
    for (final MapEntry<String, List<String>> group in requiredGroups.entries)
      if (!_hasAnyValue(json, group.value)) group.key,
  ];
}

class RegenDnaProfile {
  const RegenDnaProfile({required this.ratings});

  final Map<String, int> ratings;

  int valueFor(String code) => ratings[code.toUpperCase()] ?? 0;

  Map<String, Object?> toJson() => <String, Object?>{
    for (final String code in regenDnaStatCodes) code: valueFor(code),
  };

  factory RegenDnaProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen DNA profile',
    );
    return RegenDnaProfile(
      ratings: <String, int>{
        for (final String code in regenDnaStatCodes)
          code: GteJson.requiredInteger(json, <String>[
            code,
            code.toLowerCase(),
            code.toUpperCase(),
          ], label: 'regen DNA $code'),
      },
    );
  }
}

class RegenCreationWalletAvailability extends CapitalWalletAvailability {
  const RegenCreationWalletAvailability({
    required super.isAvailable,
    required super.availableBalanceCoin,
    required super.reservedBalanceCoin,
    required super.lockedBalanceCoin,
    required super.pendingWithdrawalBalanceCoin,
    super.totalBalanceCoin,
    super.currency,
    super.blockedReason,
    super.lockReasons,
  });

  factory RegenCreationWalletAvailability.fromJson(Object? value) {
    final CapitalWalletAvailability parsed = CapitalWalletAvailability.fromJson(
      value,
    );
    return RegenCreationWalletAvailability(
      isAvailable: parsed.isAvailable,
      availableBalanceCoin: parsed.availableBalanceCoin,
      reservedBalanceCoin: parsed.reservedBalanceCoin,
      lockedBalanceCoin: parsed.lockedBalanceCoin,
      pendingWithdrawalBalanceCoin: parsed.pendingWithdrawalBalanceCoin,
      totalBalanceCoin: parsed.totalBalanceCoin,
      currency: parsed.currency,
      blockedReason: parsed.blockedReason,
      lockReasons: parsed.lockReasons,
    );
  }
}

class RequestSonPreviewDraft {
  const RequestSonPreviewDraft({
    required this.parentPlayerId,
    required this.selectedTraits,
    this.requestedName,
    this.requestedCountryCode,
    this.requestedPosition,
    this.paymentMethod = 'wallet',
  });

  final String parentPlayerId;
  final List<String> selectedTraits;
  final String? requestedName;
  final String? requestedCountryCode;
  final String? requestedPosition;
  final String paymentMethod;

  bool get hasExactlyThreeTraits =>
      _normalizedTraits(selectedTraits).length == 3;

  Map<String, Object?> toJson() => <String, Object?>{
    'parent_player_id': parentPlayerId,
    'payment_method': _requestSonPaymentMethod(paymentMethod),
    'selected_traits': _normalizedTraits(selectedTraits),
    if ((requestedName ?? '').trim().isNotEmpty)
      'requested_name': requestedName!.trim(),
    if ((requestedCountryCode ?? '').trim().isNotEmpty)
      'requested_country_code': requestedCountryCode!.trim().toUpperCase(),
    if (_canonicalRequestedPosition(requestedPosition) != null)
      'requested_position': _canonicalRequestedPosition(requestedPosition),
  };
}

class RequestSonOrderDraft {
  const RequestSonOrderDraft({
    required this.parentPlayerId,
    required this.paymentMethod,
    this.selectedTraits = const <String>[],
    this.requestedName,
    this.requestedCountryCode,
    this.requestedPosition,
  });

  final String parentPlayerId;
  final String paymentMethod;
  final List<String> selectedTraits;
  final String? requestedName;
  final String? requestedCountryCode;
  final String? requestedPosition;

  Map<String, Object?> toJson() => <String, Object?>{
    'parent_player_id': parentPlayerId,
    'payment_method': _requestSonPaymentMethod(paymentMethod),
    if (selectedTraits.isNotEmpty)
      'selected_traits': _normalizedTraits(selectedTraits),
    if ((requestedName ?? '').trim().isNotEmpty)
      'requested_name': requestedName!.trim(),
    if ((requestedCountryCode ?? '').trim().isNotEmpty)
      'requested_country_code': requestedCountryCode!.trim().toUpperCase(),
    if (_canonicalRequestedPosition(requestedPosition) != null)
      'requested_position': _canonicalRequestedPosition(requestedPosition),
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
      baseCostCoin: GteJson.requiredNumber(json, <String>[
        'base_cost_coin',
        'baseCostCoin',
      ]),
      nameCostCoin: GteJson.requiredNumber(json, <String>[
        'name_cost_coin',
        'nameCostCoin',
      ]),
      customizationCostCoin: GteJson.requiredNumber(json, <String>[
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
    this.overallRating,
    this.generationNumber,
    this.generationLabel,
    this.traits = const <String>[],
    this.lineage = const <String>[],
    this.dnaProfile,
  });

  final String playerId;
  final String fullName;
  final String? position;
  final String? countryCode;
  final String? countryName;
  final String? imageUrl;
  final String? clubId;
  final String? clubName;
  final int? overallRating;
  final int? generationNumber;
  final String? generationLabel;
  final List<String> traits;
  final List<String> lineage;
  final RegenDnaProfile? dnaProfile;

  factory RegenCreationParentPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation parent player',
    );
    final String? generationLabel = GteJson.stringOrNull(json, <String>[
      'generation_label',
      'generationLabel',
      'gen',
    ]);
    final int? generationNumber =
        GteJson.integerOrNull(json, <String>[
          'generation_number',
          'generationNumber',
          'generation',
        ]) ??
        _generationNumberFromLabel(generationLabel);
    final Object? dnaValue = _firstValue(json, <String>[
      'dna_profile',
      'dnaProfile',
      'dna',
      'stats',
    ]);
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
      overallRating: GteJson.integerOrNull(json, <String>[
        'overall_rating',
        'overallRating',
        'current_rating',
        'currentRating',
        'rating',
        'ovr',
        'overall',
      ]),
      generationNumber: generationNumber,
      generationLabel:
          generationLabel ??
          (generationNumber == null ? null : 'GEN-$generationNumber'),
      traits: _stringList(json, <String>[
        'traits',
        'trait_names',
        'traitNames',
      ]),
      lineage: _lineageList(json, <String>[
        'lineage',
        'bloodline',
        'bloodlineNames',
      ]),
      dnaProfile: _optionalCanonicalDnaProfile(dnaValue),
    );
  }
}

class RequestSonPreview {
  const RequestSonPreview({
    required this.parentPlayerId,
    required this.selectedTraits,
    required this.projectedDna,
    required this.projectedOverall,
    required this.projectedPotential,
    required this.parentGeneration,
    required this.generationNumber,
    required this.generationLabel,
    required this.totalCostCoin,
    required this.currency,
    required this.walletAvailability,
    this.blockedReason,
  });

  final String parentPlayerId;
  final List<String> selectedTraits;
  final RegenDnaProfile projectedDna;
  final int projectedOverall;
  final int projectedPotential;
  final int parentGeneration;
  final int generationNumber;
  final String generationLabel;
  final double totalCostCoin;
  final String currency;
  final CapitalWalletAvailability walletAvailability;
  final String? blockedReason;

  bool get canConfirm =>
      walletAvailability.isAvailable && (blockedReason ?? '').trim().isEmpty;

  factory RequestSonPreview.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'request son preview',
    );
    final List<String> missingProjectionFields = _missingKeys(
      json,
      <String, List<String>>{
        'selected_traits': <String>['selected_traits'],
        'projected_dna': <String>['projected_dna'],
        'projected_ovr': <String>['projected_ovr'],
        'projected_pot': <String>['projected_pot'],
        'parent_generation': <String>['parent_generation'],
        'projected_generation': <String>['projected_generation'],
        'generation_label': <String>['generation_label'],
        'total_cost_coin': <String>['total_cost_coin'],
        'wallet': <String>['wallet'],
      },
    );
    final Object? parentValue = GteJson.value(json, <String>['parent']);
    final Map<String, Object?> parentJson =
        parentValue == null
            ? const <String, Object?>{}
            : GteJson.map(parentValue, label: 'request son preview parent');
    final bool hasParentPlayerId = _hasAnyValue(parentJson, <String>[
      'player_id',
    ]);
    final Object? dnaValue = _firstValue(json, <String>['projected_dna']);
    final Map<String, Object?> dnaJson =
        dnaValue == null
            ? const <String, Object?>{}
            : GteJson.map(dnaValue, label: 'request son projected DNA');
    final List<String> missingDnaCodes = <String>[
      for (final String code in regenDnaStatCodes)
        if (!_hasDnaCode(dnaJson, code)) code,
    ];
    final Object? walletValue = _firstValue(json, <String>['wallet']);
    final Map<String, Object?> walletJson =
        walletValue == null
            ? const <String, Object?>{}
            : GteJson.map(
              walletValue,
              label: 'request son wallet availability',
            );
    final List<String> missingWalletFields = _missingKeys(
      walletJson,
      <String, List<String>>{
        'can_pay_with_wallet': <String>['can_pay_with_wallet'],
        'available_balance': <String>['available_balance'],
        'reserved_balance': <String>['reserved_balance'],
        'locked_balance': <String>['locked_balance'],
        'pending_withdrawal_balance': <String>['pending_withdrawal_balance'],
        'total_balance': <String>['total_balance'],
        'currency': <String>['currency'],
      },
    );
    final List<String> missingFields = <String>[
      if (!hasParentPlayerId) 'parent.player_id',
      ...missingProjectionFields,
      for (final String code in missingDnaCodes) 'projected_dna.$code',
      for (final String field in missingWalletFields) 'wallet.$field',
    ];
    if (missingFields.isNotEmpty) {
      final bool missingWalletAvailability = missingFields.any(
        (String field) => field == 'wallet' || field.startsWith('wallet.'),
      );
      throw GteParsingException(
        missingWalletAvailability
            ? 'Request-son preview missing backend wallet availability fields: ${missingFields.join(', ')}.'
            : 'Request-son preview missing backend projection fields: ${missingFields.join(', ')}.',
        value,
      );
    }
    final List<String> selectedTraits = _normalizedTraits(
      _requiredStringList(
        json,
        'selected_traits',
        label: 'request son selected_traits',
      ),
    );
    if (selectedTraits.length != 3) {
      throw GteParsingException(
        'Request-son preview selected_traits must contain exactly 3 backend traits.',
        value,
      );
    }
    final int parentGenerationValue = GteJson.requiredInteger(json, <String>[
      'parent_generation',
    ]);
    if (parentGenerationValue <= 0) {
      throw GteParsingException(
        'Request-son preview missing numeric backend parent generation.',
        value,
      );
    }
    final String generationLabelValue = GteJson.string(json, <String>[
      'generation_label',
    ]);
    final int generationNumberValue = GteJson.requiredInteger(json, <String>[
      'projected_generation',
    ]);
    if (generationNumberValue <= 0) {
      throw GteParsingException(
        'Request-son preview missing numeric backend generation.',
        value,
      );
    }
    if (generationNumberValue != parentGenerationValue + 1) {
      throw GteParsingException(
        'Request-son preview projected_generation must equal parent_generation + 1.',
        value,
      );
    }
    return RequestSonPreview(
      parentPlayerId: GteJson.string(parentJson, <String>['player_id']),
      selectedTraits: selectedTraits,
      projectedDna: RegenDnaProfile.fromJson(dnaValue),
      projectedOverall: GteJson.requiredInteger(json, <String>[
        'projected_ovr',
      ]),
      projectedPotential: GteJson.requiredInteger(json, <String>[
        'projected_pot',
      ]),
      parentGeneration: parentGenerationValue,
      generationNumber: generationNumberValue,
      generationLabel: generationLabelValue,
      totalCostCoin: GteJson.requiredNumber(json, <String>['total_cost_coin']),
      currency: GteJson.string(walletJson, <String>['currency']),
      walletAvailability: RegenCreationWalletAvailability.fromJson(walletJson),
      blockedReason: GteJson.stringOrNull(json, <String>['blocked_reason']),
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
    this.generationNumber,
    this.generationLabel,
    this.traits = const <String>[],
    this.lineage = const <String>[],
    this.dnaProfile,
    this.originStory,
    this.projectedValueCoin,
    this.rarityTier,
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
  final int? generationNumber;
  final String? generationLabel;
  final List<String> traits;
  final List<String> lineage;
  final RegenDnaProfile? dnaProfile;
  final String? originStory;
  final int? projectedValueCoin;
  final String? rarityTier;

  factory RegenCreationGeneratedPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation generated player',
    );
    final Map<String, Object?> metadata = GteJson.map(
      json,
      keys: <String>['metadata', 'metadata_json', 'metadataJson'],
      fallback: const <String, Object?>{},
    );
    final String? generationLabel =
        GteJson.stringOrNull(json, <String>[
          'generation_label',
          'generationLabel',
          'gen',
          'generation',
        ]) ??
        GteJson.stringOrNull(metadata, <String>[
          'generation_label',
          'generationLabel',
          'gen',
          'generation',
        ]);
    final int? generationNumber =
        GteJson.integerOrNull(json, <String>[
          'generation_number',
          'generationNumber',
        ]) ??
        GteJson.integerOrNull(metadata, <String>[
          'generation_number',
          'generationNumber',
        ]) ??
        _generationNumberFromLabel(generationLabel);
    final Object? dnaValue =
        _firstValue(json, <String>[
          'dna_profile',
          'dnaProfile',
          'dna',
          'stats',
        ]) ??
        _firstValue(metadata, <String>[
          'dna_profile',
          'dnaProfile',
          'dna',
          'stats',
        ]);
    return RegenCreationGeneratedPlayer(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      regenProfileId: GteJson.string(json, <String>[
        'regen_profile_id',
        'regenProfileId',
      ]),
      fullName: GteJson.string(json, <String>['full_name', 'fullName']),
      age: GteJson.requiredInteger(json, <String>['age']),
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
      currentRating: GteJson.requiredInteger(json, <String>[
        'current_rating',
        'currentRating',
      ]),
      potentialRating: GteJson.requiredInteger(json, <String>[
        'potential_rating',
        'potentialRating',
      ]),
      cardId: GteJson.stringOrNull(json, <String>['card_id', 'cardId']),
      generationNumber: generationNumber,
      generationLabel:
          generationLabel ??
          (generationNumber == null ? null : 'GEN-$generationNumber'),
      traits: _normalizedTraits(<String>[
        ..._stringList(json, <String>['traits', 'trait_names', 'traitNames']),
        ..._stringList(metadata, <String>[
          'traits',
          'trait_names',
          'traitNames',
        ]),
      ]),
      lineage: <String>{
        ..._stringList(json, <String>[
          'lineage',
          'bloodline',
          'bloodlineNames',
        ]),
        ..._stringList(metadata, <String>[
          'lineage',
          'bloodline',
          'bloodlineNames',
        ]),
      }.toList(growable: false),
      dnaProfile: dnaValue == null ? null : RegenDnaProfile.fromJson(dnaValue),
      originStory:
          GteJson.stringOrNull(json, <String>[
            'origin_story',
            'originStory',
            'origin',
          ]) ??
          GteJson.stringOrNull(metadata, <String>[
            'origin_story',
            'originStory',
            'origin',
          ]),
      projectedValueCoin:
          GteJson.integerOrNull(json, <String>[
            'projected_value_coin',
            'projectedValueCoin',
            'market_value_coin',
            'marketValueCoin',
          ]) ??
          GteJson.integerOrNull(metadata, <String>[
            'projected_value_coin',
            'projectedValueCoin',
            'market_value_coin',
            'marketValueCoin',
          ]),
      rarityTier:
          GteJson.stringOrNull(json, <String>['rarity_tier', 'rarityTier']) ??
          GteJson.stringOrNull(metadata, <String>['rarity_tier', 'rarityTier']),
    );
  }
}

class RegenCreationWalletReservation {
  const RegenCreationWalletReservation({
    required this.kind,
    required this.key,
    required this.status,
    required this.amountCoin,
    required this.currency,
    this.reference,
    this.lockReason,
    this.updatedAt,
  });

  final String kind;
  final String key;
  final String status;
  final double amountCoin;
  final String currency;
  final String? reference;
  final String? lockReason;
  final DateTime? updatedAt;

  bool get isReserved => status.trim().toLowerCase() == 'reserved';
  bool get isSettled => status.trim().toLowerCase() == 'settled';
  bool get isReleased => status.trim().toLowerCase() == 'released';

  factory RegenCreationWalletReservation.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation wallet reservation',
    );
    return RegenCreationWalletReservation(
      kind: GteJson.string(json, <String>['kind']),
      key: GteJson.string(json, <String>['key', 'reservation_id']),
      status: GteJson.string(json, <String>['status']),
      amountCoin: GteJson.requiredNumber(json, <String>[
        'amount_coin',
        'amountCoin',
        'amount',
      ]),
      currency: GteJson.string(json, <String>['currency']),
      reference: GteJson.stringOrNull(json, <String>['reference']),
      lockReason: GteJson.stringOrNull(json, <String>[
        'lock_reason',
        'lockReason',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
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
    this.walletReservation,
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
  final RegenCreationWalletReservation? walletReservation;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? paidAt;
  final DateTime? generatedAt;
  final RegenCreationGeneratedPlayer? generatedPlayer;

  bool get isPendingPayment => status == 'pending_payment';
  bool get isPaid => status == 'paid';
  bool get isGenerating => status == 'generating';
  bool get isCancelled => status == 'cancelled';
  bool get isGenerated => status == 'generated' && generatedPlayer != null;
  bool get usesWallet => paymentMethod == 'wallet';
  bool get hasReservedWalletFunds =>
      walletReservation?.isReserved == true ||
      (usesWallet &&
          isPendingPayment &&
          (paymentReference ?? '').startsWith('regen-wallet-reserve:'));

  factory RegenCreationOrder.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen creation order',
    );
    final Object? generatedPlayerValue = GteJson.value(json, <String>[
      'generated_player',
      'generatedPlayer',
    ]);
    final Object? walletReservationValue = GteJson.value(json, <String>[
      'wallet_reservation',
      'walletReservation',
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
      amountCoin: GteJson.requiredNumber(json, <String>[
        'amount_coin',
        'amountCoin',
      ]),
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
      walletReservation:
          walletReservationValue == null
              ? null
              : RegenCreationWalletReservation.fromJson(walletReservationValue),
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

class RequestSonNationalityOption {
  const RequestSonNationalityOption({
    required this.code,
    required this.name,
    this.alpha2Code,
    this.alpha3Code,
    this.fifaCode,
    this.flagUrl,
    this.marketRegion,
    this.isDefault = false,
  });

  final String code;
  final String name;
  final String? alpha2Code;
  final String? alpha3Code;
  final String? fifaCode;
  final String? flagUrl;
  final String? marketRegion;
  final bool isDefault;

  String get displayLabel => '$code - $name';

  factory RequestSonNationalityOption.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'request son nationality option',
    );
    return RequestSonNationalityOption(
      code: GteJson.string(json, <String>['code']).toUpperCase(),
      name: GteJson.string(json, <String>['name']),
      alpha2Code:
          GteJson.stringOrNull(json, <String>[
            'alpha2_code',
            'alpha2Code',
          ])?.toUpperCase(),
      alpha3Code:
          GteJson.stringOrNull(json, <String>[
            'alpha3_code',
            'alpha3Code',
          ])?.toUpperCase(),
      fifaCode:
          GteJson.stringOrNull(json, <String>[
            'fifa_code',
            'fifaCode',
          ])?.toUpperCase(),
      flagUrl: GteJson.stringOrNull(json, <String>['flag_url', 'flagUrl']),
      marketRegion: GteJson.stringOrNull(json, <String>[
        'market_region',
        'marketRegion',
      ]),
      isDefault: GteJson.boolean(json, <String>['is_default', 'isDefault']),
    );
  }
}

class RequestSonPositionOption {
  const RequestSonPositionOption({
    required this.code,
    required this.label,
    this.aliases = const <String>[],
    this.group,
    this.isDefault = false,
  });

  final String code;
  final String label;
  final List<String> aliases;
  final String? group;
  final bool isDefault;

  String get displayLabel => label == code ? code : '$code - $label';

  factory RequestSonPositionOption.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'request son position option',
    );
    return RequestSonPositionOption(
      code: GteJson.string(json, <String>['code']).toUpperCase(),
      label: GteJson.string(json, <String>['label']),
      aliases: _stringList(json, <String>[
        'aliases',
      ]).map((String value) => value.toUpperCase()).toList(growable: false),
      group: GteJson.stringOrNull(json, <String>['group']),
      isDefault: GteJson.boolean(json, <String>['is_default', 'isDefault']),
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
    this.nationalityOptions = const <RequestSonNationalityOption>[],
    this.positionOptions = const <RequestSonPositionOption>[],
    this.defaultCountryCode,
    this.defaultPosition,
  });

  final String clubId;
  final String clubName;
  final String currency;
  final RegenCreationPricing pricing;
  final List<RegenCreationParentPlayer> eligibleParents;
  final List<RequestSonNationalityOption> nationalityOptions;
  final List<RequestSonPositionOption> positionOptions;
  final String? defaultCountryCode;
  final String? defaultPosition;

  factory RequestSonOptions.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'request son options',
    );
    final List<RequestSonNationalityOption> nationalityOptions =
        GteJson.typedList(json, <String>[
          'nationality_options',
          'nationalityOptions',
          'nationalities',
          'country_options',
          'countryOptions',
        ], RequestSonNationalityOption.fromJson);
    final List<RequestSonPositionOption> positionOptions = GteJson.typedList(
      json,
      <String>['position_options', 'positionOptions', 'positions'],
      RequestSonPositionOption.fromJson,
    );
    final List<String> missingSelectorFields = <String>[
      if (nationalityOptions.isEmpty) 'nationality_options',
      if (positionOptions.isEmpty) 'position_options',
    ];
    if (missingSelectorFields.isNotEmpty) {
      throw GteParsingException(
        'Request-son options missing backend selector fields: ${missingSelectorFields.join(', ')}.',
        value,
      );
    }
    return RequestSonOptions(
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, <String>['club_name', 'clubName']),
      currency: GteJson.string(json, <String>['currency']),
      pricing: RegenCreationPricing.fromJson(
        GteJson.value(json, <String>['pricing']),
      ),
      eligibleParents: GteJson.typedList(json, <String>[
        'eligible_parents',
        'eligibleParents',
      ], RegenCreationParentPlayer.fromJson),
      nationalityOptions: nationalityOptions,
      positionOptions: positionOptions,
      defaultCountryCode:
          GteJson.stringOrNull(json, <String>[
            'default_country_code',
            'defaultCountryCode',
          ])?.toUpperCase(),
      defaultPosition:
          GteJson.stringOrNull(json, <String>[
            'default_position',
            'defaultPosition',
          ])?.toUpperCase(),
    );
  }
}
