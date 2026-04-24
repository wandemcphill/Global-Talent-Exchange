import 'dart:collection';

import 'package:gte_frontend/data/gte_models.dart';

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
      ], fallback: true),
      shareMarketEligible: GteJson.boolean(json, <String>[
        'share_market_eligible',
        'shareMarketEligible',
      ], fallback: true),
      tradable: GteJson.boolean(json, <String>['tradable'], fallback: true),
      buyable: GteJson.boolean(json, <String>['buyable'], fallback: true),
      transferable: GteJson.boolean(json, <String>[
        'transferable',
      ], fallback: true),
      cardMintEligible: GteJson.boolean(json, <String>[
        'card_mint_eligible',
        'cardMintEligible',
      ], fallback: true),
      buyCtaAllowed: GteJson.boolean(json, <String>[
        'buy_cta_allowed',
        'buyCtaAllowed',
      ], fallback: true),
      isPreseededNationalRegen: GteJson.boolean(json, <String>[
        'is_preseeded_national_regen',
        'isPreseededNationalRegen',
      ]),
      nationalPoolOnly: GteJson.boolean(json, <String>[
        'national_pool_only',
        'nationalPoolOnly',
      ]),
    );
  }
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
    this.clubId,
    this.marketAccess = const RegenMarketAccess(),
  });

  final String id;
  final String name;
  final int age;
  final String nationality;
  final String? nationalityCode;
  final String position;
  final int potential;
  final int currentRating;
  final double growthCurve;
  final String sourceType;
  final String? clubId;
  final RegenMarketAccess marketAccess;

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
    return RegenUniversePlayer(
      id: GteJson.string(json, <String>['id']),
      name: GteJson.string(json, <String>['name']),
      age: GteJson.integer(json, <String>['age']),
      nationality: GteJson.string(json, <String>[
        'nationality',
        'birth_country_code',
        'country_code',
      ], fallback: 'Unknown'),
      nationalityCode: GteJson.stringOrNull(json, <String>[
        'nationality_code',
        'birth_country_code',
        'country_code',
      ]),
      position: GteJson.string(json, <String>[
        'position',
        'primary_position',
      ], fallback: 'CM'),
      potential: GteJson.integer(json, <String>['potential'], fallback: 70),
      currentRating: GteJson.integer(json, <String>[
        'current_rating',
        'current_gsi',
        'rating',
      ], fallback: 60),
      growthCurve: GteJson.number(json, <String>[
        'growth_curve',
        'growthCurve',
      ], fallback: 0.5),
      sourceType: GteJson.string(json, <String>[
        'source_type',
        'generation_source',
      ], fallback: 'regen'),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      marketAccess: RegenMarketAccess.fromJson(
        GteJson.value(json, <String>['market_access', 'marketAccess']) ?? json,
      ),
    );
  }
}

class RegenRisingStar {
  const RegenRisingStar({
    required this.playerId,
    required this.player,
    required this.momentumLabel,
    required this.storySnippet,
    required this.badges,
    required this.marketValueCoin,
  });

  final String playerId;
  final RegenUniversePlayer player;
  final String momentumLabel;
  final String? storySnippet;
  final List<String> badges;
  final int? marketValueCoin;

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
      marketValueCoin: GteJson.integerOrNull(json, <String>[
        'market_value_coin',
      ]),
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
    this.growthCurve = 0.5,
    this.status = 'active',
    this.preseedBatch,
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
  final String seedType;
  final String primaryPosition;
  final int currentRating;
  final int potentialRating;
  final double growthCurve;
  final String rarityTier;
  final String status;
  final String? preseedBatch;
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
      seedType: GteJson.string(json, <String>[
        'seed_type',
        'seedType',
      ], fallback: 'national_seed'),
      primaryPosition: GteJson.string(json, <String>[
        'primary_position',
        'primaryPosition',
      ], fallback: 'CM'),
      currentRating: GteJson.integer(json, <String>[
        'current_rating',
        'currentRating',
      ], fallback: 60),
      potentialRating: GteJson.integer(json, <String>[
        'potential_rating',
        'potentialRating',
      ], fallback: 75),
      growthCurve: GteJson.number(
        json,
        <String>['growth_curve', 'growthCurve'],
        fallback: GteJson.number(metadata, <String>[
          'growth_curve',
          'growthCurve',
        ], fallback: 0.65),
      ),
      rarityTier: GteJson.string(json, <String>[
        'rarity_tier',
        'rarityTier',
      ], fallback: 'standard'),
      status: GteJson.string(json, <String>['status'], fallback: 'active'),
      preseedBatch: GteJson.stringOrNull(json, <String>[
        'preseed_batch',
        'preseedBatch',
      ]),
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
      GteJson.string(metadata, <String>['source_type'], fallback: 'regen');

  bool get isNationalPoolWinner =>
      GteJson.boolean(metadata, <String>['national_pool_only']) ||
      sourceType.trim().toLowerCase() == 'national_seed';

  List<String> get badgeLabels {
    final RegenUniversePlayer player = RegenUniversePlayer(
      id: playerId,
      name: playerName,
      age: GteJson.integer(metadata, <String>['age'], fallback: 17),
      nationality: GteJson.string(metadata, <String>[
        'nationality',
        'country_name',
      ], fallback: 'Unknown'),
      nationalityCode: GteJson.stringOrNull(metadata, <String>[
        'nationality_code',
        'country_code',
      ]),
      position: GteJson.string(metadata, <String>[
        'position',
        'position_group',
      ], fallback: 'CM'),
      potential: GteJson.integer(metadata, <String>['potential'], fallback: 75),
      currentRating: GteJson.integer(metadata, <String>[
        'current_rating',
      ], fallback: 70),
      growthCurve: GteJson.number(metadata, <String>[
        'growth_curve',
      ], fallback: 0.6),
      sourceType: sourceType,
      clubId: GteJson.stringOrNull(metadata, <String>['club_id']),
      marketAccess: RegenMarketAccess(
        tradable: !isNationalPoolWinner,
        isPreseededNationalRegen: isNationalPoolWinner,
        nationalPoolOnly: isNationalPoolWinner,
      ),
    );
    return player.badgeLabels();
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
  return RegenUniversePlayer(
    id: GteJson.string(
      json,
      <String>['player_id', 'playerId'],
      fallback: GteJson.string(profile, <String>[
        'player_id',
        'playerId',
        'id',
      ], fallback: 'regen-player'),
    ),
    name: GteJson.string(profile, <String>[
      'display_name',
      'displayName',
    ], fallback: 'Unknown Prospect'),
    age: GteJson.integer(profile, <String>['age']),
    nationality: GteJson.string(profile, <String>[
      'birth_country_code',
      'birthCountryCode',
      'nationality',
    ], fallback: 'Unknown'),
    nationalityCode: GteJson.stringOrNull(profile, <String>[
      'birth_country_code',
      'birthCountryCode',
      'nationality_code',
    ]),
    position: GteJson.string(profile, <String>[
      'primary_position',
      'primaryPosition',
    ], fallback: 'CM'),
    potential: GteJson.integer(
      profile,
      <String>['potential'],
      fallback: GteJson.integer(profile, <String>[
        'current_rating',
      ], fallback: 70),
    ),
    currentRating: GteJson.integer(profile, <String>[
      'current_rating',
      'currentRating',
      'current_gsi',
    ], fallback: 60),
    growthCurve: GteJson.number(profile, <String>[
      'growth_curve',
      'growthCurve',
    ], fallback: 0.5),
    sourceType: GteJson.string(profile, <String>[
      'generation_source',
      'source_type',
    ], fallback: 'regen'),
    clubId: GteJson.stringOrNull(profile, <String>['club_id', 'clubId']),
    marketAccess: marketAccess,
  );
}
