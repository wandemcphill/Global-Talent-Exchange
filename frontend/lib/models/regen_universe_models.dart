import 'package:gte_frontend/data/gte_models.dart';

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
    this.preseedBatch,
  });

  final String id;
  final String seedKey;
  final String displayName;
  final int? age;
  final String countryCode;
  final String countryName;
  final String seedType;
  final String primaryPosition;
  final int currentRating;
  final int potentialRating;
  final String rarityTier;
  final String? preseedBatch;
  final Map<String, Object?> metadata;

  factory NationalRegenSeed.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national regen seed',
    );
    return NationalRegenSeed(
      id: GteJson.string(json, <String>['id']),
      seedKey: GteJson.string(json, <String>['seed_key', 'seedKey']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      age: GteJson.integerOrNull(json, <String>['age']),
      countryCode: GteJson.string(json, <String>[
        'country_code',
        'countryCode',
      ]),
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
      rarityTier: GteJson.string(json, <String>[
        'rarity_tier',
        'rarityTier',
      ], fallback: 'standard'),
      preseedBatch: GteJson.stringOrNull(json, <String>[
        'preseed_batch',
        'preseedBatch',
      ]),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata'],
        fallback: const <String, Object?>{},
      ),
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
      growthCurve: GteJson.number(metadata, <String>[
        'growth_curve',
        'growthCurve',
      ], fallback: 0.65),
      sourceType: seedType,
      clubId: null,
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
      peakRating: GteJson.integer(json, <String>[
        'peak_rating',
        'peakRating',
      ]),
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
      seedTypes: GteJson.typedList(
        json,
        <String>['seed_types', 'seedTypes'],
        RegenGenerationTrackingEntry.fromJson,
      ),
      rarityBreakdown: GteJson.typedList(
        json,
        <String>['rarity_breakdown', 'rarityBreakdown'],
        RegenGenerationTrackingEntry.fromJson,
      ),
      countryDistribution: GteJson.typedList(
        json,
        <String>['country_distribution', 'countryDistribution'],
        RegenGenerationTrackingEntry.fromJson,
      ),
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
    ], fallback: 'Unknown'),
    nationalityCode: GteJson.stringOrNull(profile, <String>[
      'birth_country_code',
      'birthCountryCode',
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
  );
}
