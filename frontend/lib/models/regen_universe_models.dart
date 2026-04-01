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
