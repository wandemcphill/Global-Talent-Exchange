import 'dart:collection';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

String? _imageUrlFromPayload(
  Map<String, Object?> json, {
  Map<String, Object?> metadata = const <String, Object?>{},
}) {
  return GteJson.stringOrNull(json, <String>[
        'image_url',
        'portrait_url',
        'photo_url',
        'imageUrl',
        'portraitUrl',
      ]) ??
      GteJson.stringOrNull(metadata, <String>[
        'image_url',
        'portrait_url',
        'photo_url',
        'imageUrl',
        'portraitUrl',
      ]);
}

String? _firstString(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final Map<String, Object?> source in sources) {
    final String? value = GteJson.stringOrNull(source, keys);
    if (value != null) {
      return value;
    }
  }
  return null;
}

int? _firstInteger(Iterable<Map<String, Object?>> sources, List<String> keys) {
  for (final Map<String, Object?> source in sources) {
    final int? value = GteJson.integerOrNull(source, keys);
    if (value != null) {
      return value;
    }
  }
  return null;
}

double? _firstNumber(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final Map<String, Object?> source in sources) {
    if (_hasAnyValue(source, keys)) {
      return GteJson.requiredNumber(source, keys);
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

int _requiredInteger(
  Map<String, Object?> json,
  List<String> keys, {
  required String label,
}) {
  if (!_hasAnyValue(json, keys)) {
    throw GteParsingException(
      'Missing required regen universe integer field: $label.',
      json,
    );
  }
  return GteJson.requiredInteger(json, keys, label: label);
}

double _requiredNumber(
  Map<String, Object?> json,
  List<String> keys, {
  required String label,
}) {
  if (!_hasAnyValue(json, keys)) {
    throw GteParsingException(
      'Missing required regen universe numeric field: $label.',
      json,
    );
  }
  return GteJson.requiredNumber(json, keys, label: label);
}

double _requiredNumberFromSources(
  Iterable<Map<String, Object?>> sources,
  List<String> keys, {
  required String label,
}) {
  final double? value = _firstNumber(sources, keys);
  if (value == null) {
    throw GteParsingException(
      'Missing required regen universe numeric field: $label.',
      sources.toList(growable: false),
    );
  }
  return value;
}

Map<String, Object?> _mapFrom(Map<String, Object?> json, List<String> keys) {
  return GteJson.map(json, keys: keys, fallback: const <String, Object?>{});
}

List<String> _stringListFromValue(Object? value) {
  if (value is List) {
    return value
        .map((Object? item) => item?.toString().trim() ?? '')
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }
  if (value is String && value.trim().isNotEmpty) {
    return <String>[value.trim()];
  }
  return const <String>[];
}

List<String> _stringListFromSources(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  final LinkedHashSet<String> values = LinkedHashSet<String>();
  for (final Map<String, Object?> source in sources) {
    for (final String key in keys) {
      values.addAll(_stringListFromValue(source[key]));
    }
  }
  return values.toList(growable: false);
}

Map<String, double> _numberMapFromValue(Object? value) {
  if (value is! Map) {
    return const <String, double>{};
  }
  final Map<String, double> parsed = <String, double>{};
  for (final MapEntry<Object?, Object?> entry in value.entries) {
    final String key = entry.key?.toString().trim() ?? '';
    if (key.isEmpty) {
      continue;
    }
    final Object? rawValue = entry.value;
    if (rawValue is num) {
      parsed[key] = rawValue.toDouble();
      continue;
    }
    if (rawValue is String) {
      final double? numeric = double.tryParse(rawValue);
      if (numeric != null) {
        parsed[key] = numeric;
      }
      continue;
    }
    if (rawValue is Map) {
      final Map<String, Object?> nested = rawValue.map(
        (Object? nestedKey, Object? nestedValue) =>
            MapEntry(nestedKey?.toString() ?? '', nestedValue),
      );
      final double score = GteJson.number(nested, <String>[
        'value',
        'score',
        'rating',
      ], fallback: double.nan);
      if (!score.isNaN) {
        parsed[key] = score;
      }
    }
  }
  return Map<String, double>.unmodifiable(parsed);
}

Map<String, double> _numberMapFromSources(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final Map<String, Object?> source in sources) {
    for (final String key in keys) {
      final Map<String, double> values = _numberMapFromValue(source[key]);
      if (values.isNotEmpty) {
        return values;
      }
    }
  }
  return const <String, double>{};
}

String _labelizeToken(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s-]+'))
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return value;
  }
  return parts
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

class RegenWorldDetails {
  const RegenWorldDetails({
    required this.key,
    required this.name,
    required this.nationality,
    required this.nationalityCode,
    required this.position,
    required this.age,
    required this.currentRating,
    required this.potentialRating,
    this.imageUrl,
    this.generationLabel,
    this.originStory,
    this.originLabel,
    this.projectedValueCoin,
    this.rarityLabel,
    this.lineage = const <String>[],
    this.traits = const <String>[],
    this.dna = const <String, double>{},
  });

  final String key;
  final String name;
  final String nationality;
  final String? nationalityCode;
  final String position;
  final int age;
  final int currentRating;
  final int potentialRating;
  final String? imageUrl;
  final String? generationLabel;
  final String? originStory;
  final String? originLabel;
  final int? projectedValueCoin;
  final String? rarityLabel;
  final List<String> lineage;
  final List<String> traits;
  final Map<String, double> dna;

  factory RegenWorldDetails.fromRisingStarPayload({
    required Map<String, Object?> json,
    required RegenUniversePlayer player,
    required int? marketValueCoin,
  }) {
    final Map<String, Object?> profile = _mapFrom(json, <String>['profile']);
    final Map<String, Object?> card = _mapFrom(json, <String>['card']);
    final Map<String, Object?> metadata = _mapFrom(profile, <String>[
      'metadata',
      'metadata_json',
      'metadataJson',
    ]);
    final Map<String, Object?> lineageMap = _mapFrom(profile, <String>[
      'lineage',
    ]);
    final Map<String, Object?> metadataLineage = _mapFrom(metadata, <String>[
      'lineage',
    ]);
    final Map<String, Object?> origin = _mapFrom(profile, <String>['origin']);
    final Map<String, Object?> storySeed = _mapFrom(profile, <String>[
      'story_seed',
      'storySeed',
    ]);
    final Map<String, Object?> latestValue = _mapFrom(json, <String>[
      'latest_value',
      'latestValue',
    ]);
    final int? generationNumber = _firstInteger(
      <Map<String, Object?>>[metadata, profile],
      <String>[
        'generation_index',
        'generationIndex',
        'generation_number',
        'generationNumber',
      ],
    );
    final List<String> traits = _stringListFromSources(
      <Map<String, Object?>>[
        card,
        metadata,
        _mapFrom(profile, <String>['personality']),
      ],
      <String>[
        'traits_icons',
        'traitsIcons',
        'personality_tags',
        'personalityTags',
        'selected_traits',
        'selectedTraits',
        'traits',
      ],
    ).map(_labelizeToken).toList(growable: false);
    final LinkedHashSet<String> lineage = LinkedHashSet<String>();
    final String? lineageNarrative = _firstString(
      <Map<String, Object?>>[lineageMap, metadataLineage],
      <String>['narrative_text', 'narrativeText'],
    );
    if (lineageNarrative != null) {
      lineage.add(lineageNarrative);
    }
    lineage.addAll(
      _stringListFromSources(
        <Map<String, Object?>>[lineageMap, metadataLineage, metadata],
        <String>['tags', 'lineage', 'bloodline', 'bloodlineNames'],
      ).map(_labelizeToken),
    );
    final String? lineageTier = _firstString(
      <Map<String, Object?>>[lineageMap, metadataLineage],
      <String>['lineage_tier', 'lineageTier'],
    );
    final String? originLabel = _originLabel(origin);
    return RegenWorldDetails(
      key: player.id,
      name: player.name,
      nationality: player.nationality,
      nationalityCode: player.nationalityCode,
      position: player.position,
      age: player.age,
      currentRating: player.currentRating,
      potentialRating: player.potential,
      imageUrl: player.imageUrl ?? _imageUrlFromPayload(card),
      generationLabel:
          _firstString(
            <Map<String, Object?>>[metadata, profile],
            <String>['generation_label', 'generationLabel', 'gen'],
          ) ??
          (generationNumber == null ? null : 'GEN-$generationNumber'),
      originStory: _firstString(
        <Map<String, Object?>>[card, storySeed, metadata],
        <String>[
          'story_snippet',
          'storySnippet',
          'snippet',
          'origin_story',
          'originStory',
        ],
      ),
      originLabel: originLabel,
      projectedValueCoin:
          marketValueCoin ??
          _firstInteger(
            <Map<String, Object?>>[latestValue, metadata],
            <String>[
              'current_value_coin',
              'currentValueCoin',
              'projected_value_coin',
              'projectedValueCoin',
              'market_value_coin',
              'marketValueCoin',
            ],
          ),
      rarityLabel:
          _firstString(
            <Map<String, Object?>>[metadata, card],
            <String>[
              'rarity_tier',
              'rarityTier',
              'uniqueness_badge',
              'uniquenessBadge',
            ],
          ) ??
          lineageTier,
      lineage: lineage.toList(growable: false),
      traits: traits,
      dna: _numberMapFromSources(
        <Map<String, Object?>>[metadata, profile],
        <String>[
          'dna_profile',
          'dnaProfile',
          'projected_dna',
          'projectedDna',
          'dna',
        ],
      ),
    );
  }

  factory RegenWorldDetails.fromNationalSeed(NationalRegenSeed seed) {
    final Map<String, Object?> storySeed = _mapFrom(
      seed.personalitySeed,
      <String>['story_seed', 'storySeed'],
    );
    return RegenWorldDetails(
      key: seed.id,
      name: seed.displayName,
      nationality: seed.countryName,
      nationalityCode: seed.countryCode,
      position: seed.primaryPosition,
      age: seed.age ?? 0,
      currentRating: seed.currentRating,
      potentialRating: seed.potentialRating,
      imageUrl: seed.imageUrl,
      generationLabel:
          seed.generationIndex > 0 ? 'GEN-${seed.generationIndex}' : null,
      originStory: _firstString(
        <Map<String, Object?>>[storySeed, seed.metadata],
        <String>['snippet', 'origin_story', 'originStory'],
      ),
      originLabel: seed.countryName,
      projectedValueCoin: _firstInteger(
        <Map<String, Object?>>[seed.metadata],
        <String>[
          'projected_value_coin',
          'projectedValueCoin',
          'market_value_coin',
          'marketValueCoin',
        ],
      ),
      rarityLabel: seed.rarityTier,
      traits: _stringListFromSources(
        <Map<String, Object?>>[seed.personalitySeed, seed.metadata],
        <String>['traits', 'trait_names', 'traitNames'],
      ).map(_labelizeToken).toList(growable: false),
      lineage: _stringListFromSources(
        <Map<String, Object?>>[seed.personalitySeed, seed.metadata],
        <String>['lineage', 'bloodline', 'bloodlineNames'],
      ).map(_labelizeToken).toList(growable: false),
      dna: _numberMapFromSources(
        <Map<String, Object?>>[seed.metadata],
        <String>['dna_profile', 'dnaProfile', 'dna'],
      ),
    );
  }
}

String? _originLabel(Map<String, Object?> origin) {
  final String? city = GteJson.stringOrNull(origin, <String>[
    'city_name',
    'cityName',
  ]);
  final String? region = GteJson.stringOrNull(origin, <String>[
    'region_name',
    'regionName',
  ]);
  final String? country = GteJson.stringOrNull(origin, <String>[
    'country_code',
    'countryCode',
  ]);
  final List<String> parts = <String>[
    if (city != null) city,
    if (region != null) region,
    if (country != null) country,
  ];
  return parts.isEmpty ? null : parts.join(', ');
}

class RegenMarketAccess {
  const RegenMarketAccess({
    this.marketEligible = true,
    this.shareMarketEligible = true,
    this.tradable = true,
    this.buyable = true,
    this.transferable = true,
    this.cardMintEligible = true,
    this.buyCtaAllowed = true,
    this.isPreseededNationalRegen = false,
    this.nationalPoolOnly = false,
    this.backendProvided = false,
  });

  final bool marketEligible;
  final bool shareMarketEligible;
  final bool tradable;
  final bool buyable;
  final bool transferable;
  final bool cardMintEligible;
  final bool buyCtaAllowed;
  final bool isPreseededNationalRegen;
  final bool nationalPoolOnly;
  final bool backendProvided;

  factory RegenMarketAccess.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen market access',
      fallback: const <String, Object?>{},
    );
    return RegenMarketAccess(
      marketEligible: GteJson.boolean(json, <String>[
        'market_eligible',
        'marketEligible',
      ]),
      shareMarketEligible: GteJson.boolean(json, <String>[
        'share_market_eligible',
        'shareMarketEligible',
      ]),
      tradable: GteJson.boolean(json, <String>['tradable']),
      buyable: GteJson.boolean(json, <String>['buyable']),
      transferable: GteJson.boolean(json, <String>['transferable']),
      cardMintEligible: GteJson.boolean(json, <String>[
        'card_mint_eligible',
        'cardMintEligible',
      ]),
      buyCtaAllowed: GteJson.boolean(json, <String>[
        'buy_cta_allowed',
        'buyCtaAllowed',
      ]),
      isPreseededNationalRegen: GteJson.boolean(json, <String>[
        'is_preseeded_national_regen',
        'isPreseededNationalRegen',
      ]),
      nationalPoolOnly: GteJson.boolean(json, <String>[
        'national_pool_only',
        'nationalPoolOnly',
      ]),
      backendProvided: _hasAnyMarketAccessField(json),
    );
  }
}

bool _hasAnyMarketAccessField(Map<String, Object?> json) {
  return <String>[
    'market_eligible',
    'marketEligible',
    'share_market_eligible',
    'shareMarketEligible',
    'tradable',
    'buyable',
    'transferable',
    'card_mint_eligible',
    'cardMintEligible',
    'buy_cta_allowed',
    'buyCtaAllowed',
    'is_preseeded_national_regen',
    'isPreseededNationalRegen',
    'national_pool_only',
    'nationalPoolOnly',
  ].any(json.containsKey);
}

class RegenUniversePlayer {
  const RegenUniversePlayer({
    required this.id,
    required this.name,
    required this.age,
    required this.nationality,
    required this.position,
    required this.potential,
    required this.currentRating,
    required this.growthCurve,
    required this.sourceType,
    this.nationalityCode,
    this.imageUrl,
    this.clubId,
    this.marketAccess = const RegenMarketAccess(),
    this.generationNumber,
    this.generationLabel,
    this.rarityTier,
    this.originStory,
    this.projectedValueCoin,
    this.traits = const <String>[],
    this.lineage = const <String>[],
    this.dnaProfile,
  });

  final String id;
  final String name;
  final int age;
  final String nationality;
  final String? nationalityCode;
  final String? imageUrl;
  final String position;
  final int potential;
  final int currentRating;
  final double growthCurve;
  final String sourceType;
  final String? clubId;
  final RegenMarketAccess marketAccess;
  final int? generationNumber;
  final String? generationLabel;
  final String? rarityTier;
  final String? originStory;
  final int? projectedValueCoin;
  final List<String> traits;
  final List<String> lineage;
  final RegenDnaProfile? dnaProfile;

  bool get isNationalPoolOnly => marketAccess.nationalPoolOnly;
  bool get isPreseededNationalRegen => marketAccess.isPreseededNationalRegen;

  bool get isRequestedSon => _normalizedSourceType == 'requested_son';

  bool get isBloodlineRegen {
    return _normalizedSourceType.contains('bloodline') ||
        _normalizedSourceType.contains('legend');
  }

  bool get isClubRegen {
    if (isPreseededNationalRegen) {
      return false;
    }
    if (<String>{
      'generated',
      'academy',
      'club_progression',
      'club_regen',
    }.contains(_normalizedSourceType)) {
      return true;
    }
    return (clubId?.trim().isNotEmpty ?? false) && !isRequestedSon;
  }

  List<String> badgeLabels({Iterable<String> additional = const <String>[]}) {
    final LinkedHashSet<String> badges = LinkedHashSet<String>();
    for (final String badge in additional) {
      final String normalized = badge.trim();
      if (normalized.isNotEmpty) {
        badges.add(normalized);
      }
    }
    if (isPreseededNationalRegen || isNationalPoolOnly) {
      badges.add('National Pool');
    }
    if (isNationalPoolOnly) {
      badges.add('Rental Only');
    }
    if (!marketAccess.tradable) {
      badges.add('Not Tradable');
    }
    if (isRequestedSon) {
      badges.add('Requested Son');
    } else if (isBloodlineRegen) {
      badges.add('Bloodline Regen');
    } else if (isClubRegen) {
      badges.add('Club Regen');
    }
    return badges.toList(growable: false);
  }

  String get _normalizedSourceType => sourceType.trim().toLowerCase();

  factory RegenUniversePlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen universe player',
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
    return RegenUniversePlayer(
      id: GteJson.string(json, <String>['id']),
      name: GteJson.string(json, <String>['name']),
      age: _requiredInteger(json, <String>['age'], label: 'age'),
      nationality: GteJson.string(json, <String>[
        'nationality',
        'birth_country_code',
        'country_code',
      ]),
      nationalityCode: GteJson.stringOrNull(json, <String>[
        'nationality_code',
        'birth_country_code',
        'country_code',
      ]),
      position: GteJson.string(json, <String>['position', 'primary_position']),
      potential: _requiredInteger(json, <String>[
        'potential',
        'potential_rating',
        'potentialRating',
      ], label: 'potential'),
      currentRating: _requiredInteger(json, <String>[
        'current_rating',
        'currentRating',
        'current_gsi',
        'rating',
      ], label: 'current_rating'),
      growthCurve: _requiredNumber(json, <String>[
        'growth_curve',
        'growthCurve',
      ], label: 'growth_curve'),
      sourceType: GteJson.string(json, <String>[
        'source_type',
        'generation_source',
      ]),
      imageUrl: _imageUrlFromPayload(json),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      marketAccess: RegenMarketAccess.fromJson(
        GteJson.value(json, <String>['market_access', 'marketAccess']) ?? json,
      ),
      generationNumber: generationNumber,
      generationLabel:
          generationLabel ??
          (generationNumber == null ? null : 'GEN-$generationNumber'),
      rarityTier:
          GteJson.stringOrNull(json, <String>['rarity_tier', 'rarityTier']) ??
          GteJson.stringOrNull(metadata, <String>['rarity_tier', 'rarityTier']),
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
      traits: _normalizedStringList(<String>[
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
    );
  }
}

Object? _firstValue(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    if (json.containsKey(key)) {
      return json[key];
    }
  }
  return null;
}

List<String> _stringList(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return const <String>[];
  }
  if (rawValue is Iterable) {
    return rawValue
        .map((Object? value) => value?.toString().trim() ?? '')
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);
  }
  final String parsed = rawValue.toString().trim();
  return parsed.isEmpty ? const <String>[] : <String>[parsed];
}

List<String> _normalizedStringList(Iterable<String> values) {
  final LinkedHashSet<String> seen = LinkedHashSet<String>();
  for (final String value in values) {
    final String normalized = value.trim();
    if (normalized.isNotEmpty) {
      seen.add(normalized);
    }
  }
  return seen.toList(growable: false);
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

class RegenRisingStar {
  const RegenRisingStar({
    required this.playerId,
    required this.player,
    required this.momentumLabel,
    required this.storySnippet,
    required this.badges,
    required this.marketValueCoin,
    this.details,
  });

  final String playerId;
  final RegenUniversePlayer player;
  final String momentumLabel;
  final String? storySnippet;
  final List<String> badges;
  final int? marketValueCoin;
  final RegenWorldDetails? details;

  List<String> get displayBadges =>
      player.badgeLabels(additional: badges).toList(growable: false);

  factory RegenRisingStar.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen rising star',
    );
    final RegenUniversePlayer player = _playerFromEntry(json);
    final Map<String, Object?> card = GteJson.map(
      json,
      keys: <String>['card'],
      fallback: const <String, Object?>{},
    );
    final int? marketValueCoin = GteJson.integerOrNull(json, <String>[
      'market_value_coin',
    ]);
    return RegenRisingStar(
      playerId: GteJson.string(json, <String>[
        'player_id',
        'playerId',
      ], fallback: player.id),
      player: player,
      momentumLabel: GteJson.string(json, <String>[
        'momentum_label',
        'momentumLabel',
      ], fallback: 'High-upside prospect'),
      storySnippet: GteJson.stringOrNull(card, <String>[
        'story_snippet',
        'storySnippet',
      ]),
      badges: GteJson.list(card['badges'] ?? const <Object?>[])
          .map((Object? item) {
            if (item is Map<String, Object?>) {
              return GteJson.string(item, <String>[
                'label',
                'code',
              ], fallback: '');
            }
            return item?.toString().trim() ?? '';
          })
          .where((String item) => item.isNotEmpty)
          .toList(growable: false),
      marketValueCoin: marketValueCoin,
      details: RegenWorldDetails.fromRisingStarPayload(
        json: json,
        player: player,
        marketValueCoin: marketValueCoin,
      ),
    );
  }
}

class RegenScoutingFeedItem {
  const RegenScoutingFeedItem({
    required this.feedId,
    required this.feedType,
    required this.title,
    required this.summary,
    required this.occurredAt,
    required this.importance,
    required this.badges,
    this.player,
  });

  final String feedId;
  final String feedType;
  final String title;
  final String summary;
  final DateTime occurredAt;
  final double importance;
  final List<String> badges;
  final RegenUniversePlayer? player;

  List<String> get displayBadges {
    if (player == null) {
      return badges;
    }
    return player!.badgeLabels(additional: badges).toList(growable: false);
  }

  factory RegenScoutingFeedItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen scouting feed item',
    );
    return RegenScoutingFeedItem(
      feedId: GteJson.string(json, <String>['feed_id', 'feedId']),
      feedType: GteJson.string(json, <String>[
        'feed_type',
        'feedType',
      ], fallback: 'scouting_update'),
      title: GteJson.string(json, <String>['title']),
      summary: GteJson.string(json, <String>['summary'], fallback: ''),
      occurredAt: GteJson.dateTime(json, <String>['occurred_at', 'occurredAt']),
      importance: GteJson.number(json, <String>['importance'], fallback: 0.0),
      badges: GteJson.list(json['badges'] ?? const <Object?>[])
          .map((Object? item) => item?.toString().trim() ?? '')
          .where((String item) => item.isNotEmpty)
          .toList(growable: false),
      player:
          json.containsKey('player')
              ? RegenUniversePlayer.fromJson(json['player'])
              : null,
    );
  }
}

class NationalRegenSeed {
  const NationalRegenSeed({
    required this.id,
    required this.seedKey,
    required this.displayName,
    required this.countryCode,
    required this.countryName,
    required this.seedType,
    required this.primaryPosition,
    required this.currentRating,
    required this.potentialRating,
    required this.rarityTier,
    required this.metadata,
    this.age,
    this.ageBand = 'senior',
    this.confederationCode,
    this.secondaryPositions = const <String>[],
    this.generationIndex = 1,
    this.growthCurve = 0.5,
    this.personalitySeed = const <String, Object?>{},
    this.status = 'active',
    this.preseedBatch,
    this.imageUrl,
    this.marketEligible = false,
    this.shareMarketEligible = false,
    this.tradable = false,
    this.buyable = false,
    this.transferable = false,
    this.cardMintEligible = false,
    this.buyCtaAllowed = false,
    this.isPreseededNationalRegen = true,
    this.nationalPoolOnly = true,
  });

  final String id;
  final String seedKey;
  final String displayName;
  final int? age;
  final String ageBand;
  final String countryCode;
  final String countryName;
  final String? confederationCode;
  final String seedType;
  final String primaryPosition;
  final List<String> secondaryPositions;
  final int generationIndex;
  final int currentRating;
  final int potentialRating;
  final double growthCurve;
  final Map<String, Object?> personalitySeed;
  final String rarityTier;
  final String status;
  final String? preseedBatch;
  final String? imageUrl;
  final Map<String, Object?> metadata;
  final bool marketEligible;
  final bool shareMarketEligible;
  final bool tradable;
  final bool buyable;
  final bool transferable;
  final bool cardMintEligible;
  final bool buyCtaAllowed;
  final bool isPreseededNationalRegen;
  final bool nationalPoolOnly;

  RegenMarketAccess get marketAccess => RegenMarketAccess(
    marketEligible: marketEligible,
    shareMarketEligible: shareMarketEligible,
    tradable: tradable,
    buyable: buyable,
    transferable: transferable,
    cardMintEligible: cardMintEligible,
    buyCtaAllowed: buyCtaAllowed,
    isPreseededNationalRegen: isPreseededNationalRegen,
    nationalPoolOnly: nationalPoolOnly,
    backendProvided: true,
  );

  List<String> get badgeLabels => toPlayer().badgeLabels();

  factory NationalRegenSeed.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national regen seed',
    );
    final String id = GteJson.string(json, <String>['id']);
    final String countryCode = GteJson.string(json, <String>[
      'country_code',
      'countryCode',
    ]);
    final String displayName = GteJson.string(json, <String>[
      'display_name',
      'displayName',
    ]);
    final Map<String, Object?> metadata = GteJson.map(
      json,
      keys: <String>['metadata'],
      fallback: const <String, Object?>{},
    );
    return NationalRegenSeed(
      id: id,
      seedKey: GteJson.string(json, <String>[
        'seed_key',
        'seedKey',
      ], fallback: '$countryCode:$id'),
      displayName: displayName,
      age: GteJson.integerOrNull(json, <String>['age']),
      ageBand: GteJson.string(json, <String>[
        'age_band',
        'ageBand',
      ], fallback: 'senior'),
      countryCode: countryCode,
      countryName: GteJson.string(json, <String>[
        'country_name',
        'countryName',
      ]),
      confederationCode:
          GteJson.stringOrNull(json, <String>[
            'confederation_code',
            'confederationCode',
          ]) ??
          GteJson.stringOrNull(metadata, <String>[
            'confederation_code',
            'confederationCode',
          ]),
      seedType: GteJson.string(json, <String>[
        'seed_type',
        'seedType',
      ], fallback: 'national_seed'),
      primaryPosition: GteJson.string(json, <String>[
        'primary_position',
        'primaryPosition',
      ]),
      secondaryPositions: GteJson.typedList<String>(
        json,
        <String>['secondary_positions', 'secondaryPositions'],
        (Object? item) => item?.toString() ?? '',
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
      generationIndex: GteJson.requiredInteger(json, <String>[
        'generation_index',
        'generationIndex',
      ]),
      currentRating: _requiredInteger(json, <String>[
        'current_rating',
        'currentRating',
      ], label: 'current_rating'),
      potentialRating: _requiredInteger(json, <String>[
        'potential_rating',
        'potentialRating',
      ], label: 'potential_rating'),
      growthCurve: _requiredNumberFromSources(
        <Map<String, Object?>>[json, metadata],
        <String>['growth_curve', 'growthCurve'],
        label: 'growth_curve',
      ),
      personalitySeed: GteJson.map(
        json,
        keys: <String>['personality_seed', 'personalitySeed'],
        fallback: const <String, Object?>{},
      ),
      rarityTier: GteJson.string(json, <String>['rarity_tier', 'rarityTier']),
      status: GteJson.string(json, <String>['status'], fallback: 'active'),
      preseedBatch: GteJson.stringOrNull(json, <String>[
        'preseed_batch',
        'preseedBatch',
      ]),
      imageUrl: _imageUrlFromPayload(json, metadata: metadata),
      metadata: metadata,
      marketEligible: GteJson.boolean(json, <String>[
        'market_eligible',
        'marketEligible',
      ]),
      shareMarketEligible: GteJson.boolean(json, <String>[
        'share_market_eligible',
        'shareMarketEligible',
      ]),
      tradable: GteJson.boolean(json, <String>['tradable']),
      buyable: GteJson.boolean(json, <String>['buyable']),
      transferable: GteJson.boolean(json, <String>['transferable']),
      cardMintEligible: GteJson.boolean(json, <String>[
        'card_mint_eligible',
        'cardMintEligible',
      ]),
      buyCtaAllowed: GteJson.boolean(json, <String>[
        'buy_cta_allowed',
        'buyCtaAllowed',
      ]),
      isPreseededNationalRegen: GteJson.boolean(json, <String>[
        'is_preseeded_national_regen',
        'isPreseededNationalRegen',
      ], fallback: true),
      nationalPoolOnly: GteJson.boolean(json, <String>[
        'national_pool_only',
        'nationalPoolOnly',
      ], fallback: true),
    );
  }

  RegenUniversePlayer toPlayer() {
    return RegenUniversePlayer(
      id: id,
      name: displayName,
      age: age ?? 17,
      nationality: countryName,
      nationalityCode: countryCode,
      position: primaryPosition,
      potential: potentialRating,
      currentRating: currentRating,
      growthCurve: growthCurve,
      sourceType: seedType,
      imageUrl: imageUrl,
      clubId: null,
      marketAccess: marketAccess,
    );
  }
}

class RegenAwardDefinition {
  const RegenAwardDefinition({
    required this.id,
    required this.code,
    required this.name,
    required this.description,
    required this.category,
  });

  final String id;
  final String code;
  final String name;
  final String description;
  final String category;

  factory RegenAwardDefinition.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen award definition',
    );
    return RegenAwardDefinition(
      id: GteJson.string(json, <String>['id']),
      code: GteJson.string(json, <String>['code']),
      name: GteJson.string(json, <String>['name']),
      description: GteJson.string(json, <String>['description'], fallback: ''),
      category: GteJson.string(json, <String>['category'], fallback: 'season'),
    );
  }
}

class RegenAwardSeason {
  const RegenAwardSeason({
    required this.id,
    required this.seasonNumber,
    required this.startDate,
    required this.endDate,
  });

  final String id;
  final int seasonNumber;
  final DateTime startDate;
  final DateTime endDate;

  factory RegenAwardSeason.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen award season',
    );
    return RegenAwardSeason(
      id: GteJson.string(json, <String>['id']),
      seasonNumber: GteJson.integer(json, <String>[
        'season_number',
        'seasonNumber',
      ]),
      startDate: GteJson.dateTime(json, <String>['start_date', 'startDate']),
      endDate: GteJson.dateTime(json, <String>['end_date', 'endDate']),
    );
  }
}

class RegenAwardWinner {
  const RegenAwardWinner({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.rankingScore,
    required this.awardedAt,
    required this.metadata,
    this.rank,
  });

  final String id;
  final String playerId;
  final String playerName;
  final double rankingScore;
  final int? rank;
  final DateTime awardedAt;
  final Map<String, Object?> metadata;

  String get sourceType =>
      GteJson.stringOrNull(metadata, <String>['source_type']) ?? '';

  bool get isNationalPoolWinner =>
      GteJson.boolean(metadata, <String>['national_pool_only']) ||
      sourceType.trim().toLowerCase() == 'national_seed';

  List<String> get badgeLabels {
    final LinkedHashSet<String> badges = LinkedHashSet<String>();
    final String normalized = sourceType.trim().toLowerCase();
    if (isNationalPoolWinner) {
      badges
        ..add('National Pool')
        ..add('Rental Only')
        ..add('Not Tradable');
    } else if (normalized == 'requested_son') {
      badges.add('Requested Son');
    } else if (normalized.contains('bloodline') ||
        normalized.contains('legend')) {
      badges.add('Bloodline Regen');
    } else if (normalized.isNotEmpty) {
      badges.add('Club Regen');
    }
    return badges.toList(growable: false);
  }

  factory RegenAwardWinner.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen award winner',
    );
    return RegenAwardWinner(
      id: GteJson.string(json, <String>['id']),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      rankingScore: GteJson.number(json, <String>[
        'ranking_score',
        'rankingScore',
      ]),
      rank: GteJson.integerOrNull(json, <String>['rank']),
      awardedAt: GteJson.dateTime(json, <String>['awarded_at', 'awardedAt']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class RegenAwardResult {
  const RegenAwardResult({
    required this.award,
    required this.season,
    required this.winners,
  });

  final RegenAwardDefinition award;
  final RegenAwardSeason season;
  final List<RegenAwardWinner> winners;

  factory RegenAwardResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen award result',
    );
    return RegenAwardResult(
      award: RegenAwardDefinition.fromJson(json['award']),
      season: RegenAwardSeason.fromJson(json['season']),
      winners: GteJson.typedList(json, <String>[
        'winners',
      ], RegenAwardWinner.fromJson),
    );
  }
}

class RegenGenerationTrackingEntry {
  const RegenGenerationTrackingEntry({
    required this.bucket,
    required this.count,
    required this.peakRating,
    required this.achievements,
    required this.metadata,
  });

  final String bucket;
  final int count;
  final int peakRating;
  final List<String> achievements;
  final Map<String, Object?> metadata;

  factory RegenGenerationTrackingEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen tracking entry',
    );
    return RegenGenerationTrackingEntry(
      bucket: GteJson.string(json, <String>['bucket']),
      count: GteJson.integer(json, <String>['count']),
      peakRating: GteJson.integer(json, <String>['peak_rating', 'peakRating']),
      achievements: GteJson.typedList(
        json,
        <String>['achievements'],
        (Object? item) => item?.toString() ?? '',
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class RegenGenerationTracking {
  const RegenGenerationTracking({
    required this.totalSeededPlayers,
    required this.seedTypes,
    required this.rarityBreakdown,
    required this.countryDistribution,
    required this.globalPeakRating,
    required this.trackedAchievements,
  });

  final int totalSeededPlayers;
  final List<RegenGenerationTrackingEntry> seedTypes;
  final List<RegenGenerationTrackingEntry> rarityBreakdown;
  final List<RegenGenerationTrackingEntry> countryDistribution;
  final int globalPeakRating;
  final List<String> trackedAchievements;

  factory RegenGenerationTracking.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen tracking',
    );
    return RegenGenerationTracking(
      totalSeededPlayers: GteJson.integer(json, <String>[
        'total_seeded_players',
        'totalSeededPlayers',
      ]),
      seedTypes: GteJson.typedList(json, <String>[
        'seed_types',
        'seedTypes',
      ], RegenGenerationTrackingEntry.fromJson),
      rarityBreakdown: GteJson.typedList(json, <String>[
        'rarity_breakdown',
        'rarityBreakdown',
      ], RegenGenerationTrackingEntry.fromJson),
      countryDistribution: GteJson.typedList(json, <String>[
        'country_distribution',
        'countryDistribution',
      ], RegenGenerationTrackingEntry.fromJson),
      globalPeakRating: GteJson.integer(json, <String>[
        'global_peak_rating',
        'globalPeakRating',
      ]),
      trackedAchievements: GteJson.typedList(
        json,
        <String>['tracked_achievements', 'trackedAchievements'],
        (Object? item) => item?.toString() ?? '',
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
    );
  }
}

class RegenBloodlinePlayer {
  const RegenBloodlinePlayer({
    required this.playerId,
    required this.regenId,
    required this.displayName,
    required this.regenType,
    required this.generationIndex,
    required this.primaryPosition,
    required this.currentRating,
    required this.potential,
    required this.uniquenessScore,
    required this.legacyScore,
    this.storySnippet,
  });

  final String? playerId;
  final String regenId;
  final String displayName;
  final String regenType;
  final int generationIndex;
  final String primaryPosition;
  final int currentRating;
  final int potential;
  final double uniquenessScore;
  final double legacyScore;
  final String? storySnippet;

  factory RegenBloodlinePlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen bloodline player',
    );
    return RegenBloodlinePlayer(
      playerId: GteJson.stringOrNull(json, <String>['player_id', 'playerId']),
      regenId: GteJson.string(json, <String>['regen_id', 'regenId']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      regenType: GteJson.string(json, <String>['regen_type', 'regenType']),
      generationIndex: _requiredInteger(json, <String>[
        'generation_index',
        'generationIndex',
      ], label: 'generation_index'),
      primaryPosition: GteJson.string(json, <String>[
        'primary_position',
        'primaryPosition',
      ]),
      currentRating: _requiredInteger(json, <String>[
        'current_rating',
        'currentRating',
      ], label: 'current_rating'),
      potential: _requiredInteger(json, <String>[
        'potential',
      ], label: 'potential'),
      uniquenessScore: _requiredNumber(json, <String>[
        'uniqueness_score',
        'uniquenessScore',
      ], label: 'uniqueness_score'),
      legacyScore: _requiredNumber(json, <String>[
        'legacy_score',
        'legacyScore',
      ], label: 'legacy_score'),
      storySnippet: GteJson.stringOrNull(json, <String>[
        'story_snippet',
        'storySnippet',
      ]),
    );
  }
}

class RegenBloodlineChain {
  const RegenBloodlineChain({
    required this.bloodlineKey,
    required this.originLabel,
    required this.originRefId,
    required this.originType,
    required this.driftScore,
    required this.entries,
  });

  final String bloodlineKey;
  final String originLabel;
  final String originRefId;
  final String originType;
  final double driftScore;
  final List<RegenBloodlinePlayer> entries;

  factory RegenBloodlineChain.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen bloodline chain',
    );
    return RegenBloodlineChain(
      bloodlineKey: GteJson.string(json, <String>[
        'bloodline_key',
        'bloodlineKey',
      ]),
      originLabel: GteJson.string(json, <String>[
        'origin_label',
        'originLabel',
      ]),
      originRefId: GteJson.string(json, <String>[
        'origin_ref_id',
        'originRefId',
      ]),
      originType: GteJson.string(json, <String>['origin_type', 'originType']),
      driftScore: _requiredNumber(json, <String>[
        'drift_score',
        'driftScore',
      ], label: 'drift_score'),
      entries: GteJson.typedList(json, <String>[
        'entries',
      ], RegenBloodlinePlayer.fromJson),
    );
  }
}

RegenUniversePlayer _playerFromEntry(Map<String, Object?> json) {
  if (json['player'] != null) {
    return RegenUniversePlayer.fromJson(json['player']);
  }
  final Map<String, Object?> profile = GteJson.map(
    json,
    keys: <String>['profile'],
    fallback: const <String, Object?>{},
  );
  final RegenMarketAccess marketAccess = RegenMarketAccess.fromJson(
    GteJson.value(json, <String>['market_access', 'marketAccess']) ??
        GteJson.value(profile, <String>['market_access', 'marketAccess']) ??
        json,
  );
  final String playerId =
      GteJson.stringOrNull(json, <String>['player_id', 'playerId']) ??
      GteJson.string(profile, <String>['player_id', 'playerId', 'id']);
  return RegenUniversePlayer(
    id: playerId,
    name: GteJson.string(profile, <String>['display_name', 'displayName']),
    age: _requiredInteger(profile, <String>['age'], label: 'age'),
    nationality: GteJson.string(profile, <String>[
      'birth_country_code',
      'birthCountryCode',
      'nationality',
    ]),
    nationalityCode: GteJson.stringOrNull(profile, <String>[
      'birth_country_code',
      'birthCountryCode',
      'nationality_code',
    ]),
    position: GteJson.string(profile, <String>[
      'primary_position',
      'primaryPosition',
    ]),
    potential: _requiredInteger(profile, <String>[
      'potential',
      'potential_rating',
      'potentialRating',
    ], label: 'potential'),
    currentRating: _requiredInteger(profile, <String>[
      'current_rating',
      'currentRating',
      'current_gsi',
    ], label: 'current_rating'),
    growthCurve: _requiredNumber(profile, <String>[
      'growth_curve',
      'growthCurve',
    ], label: 'growth_curve'),
    sourceType: GteJson.string(profile, <String>[
      'generation_source',
      'source_type',
    ]),
    clubId: GteJson.stringOrNull(profile, <String>['club_id', 'clubId']),
    marketAccess: marketAccess,
  );
}
