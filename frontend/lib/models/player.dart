import 'package:gte_frontend/data/gte_models.dart';

class Player {
  const Player({
    required this.id,
    required this.name,
    required this.position,
    required this.age,
    required this.country,
    required this.imageUrl,
    this.club,
  });

  final String id;
  final String name;
  final String position;
  final int age;
  final String country;
  final String? club;
  final String imageUrl;

  factory Player.fromJson(Object? value) => Player.fromBackend(value);

  factory Player.fromBackend(Object? value) {
    return _PlayerBackendMapper.map(value);
  }
}

class _PlayerBackendMapper {
  const _PlayerBackendMapper._();

  static Player map(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'player');
    final Map<String, Object?> summaryJson = GteJson.map(
      json,
      keys: <String>['summary_json', 'summaryJson'],
      fallback: const <String, Object?>{},
    );
    final Map<String, Object?> metadataJson = GteJson.map(
      json,
      keys: <String>['metadata_json', 'metadataJson'],
      fallback: const <String, Object?>{},
    );

    return Player(
      id: GteJson.string(json, <String>['id', 'player_id', 'playerId']),
      name: GteJson.string(
        json,
        <String>[
          'name',
          'player_name',
          'playerName',
          'canonical_display_name',
          'canonicalDisplayName',
        ],
      ),
      position: GteJson.string(
        json,
        <String>[
          'position',
          'primary_position',
          'primaryPosition',
          'normalized_position',
          'normalizedPosition',
        ],
        fallback: 'Unknown',
      ),
      age: GteJson.integer(json, <String>['age']),
      country: GteJson.string(
        json,
        <String>['country', 'nationality'],
        fallback: 'Unknown',
      ),
      club: GteJson.stringOrNull(
        json,
        <String>['club', 'current_club_name', 'currentClubName'],
      ),
      imageUrl: _firstNonEmpty(<String?>[
            GteJson.stringOrNull(
              json,
              <String>[
                'image_url',
                'imageUrl',
                'portrait_url',
                'portraitUrl',
                'profile_image_url',
                'profileImageUrl',
              ],
            ),
            GteJson.stringOrNull(
              summaryJson,
              <String>[
                'image_url',
                'imageUrl',
                'portrait_url',
                'portraitUrl',
                'profile_image_url',
                'profileImageUrl',
              ],
            ),
            GteJson.stringOrNull(
              metadataJson,
              <String>[
                'image_url',
                'imageUrl',
                'portrait_url',
                'portraitUrl',
                'profile_image_url',
                'profileImageUrl',
              ],
            ),
          ]) ??
          '',
    );
  }
}

String? _firstNonEmpty(Iterable<String?> values) {
  for (final String? value in values) {
    if (value != null && value.trim().isNotEmpty) {
      return value;
    }
  }
  return null;
}
