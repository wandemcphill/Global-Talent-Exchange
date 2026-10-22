import 'gte_api_repository.dart';
import 'gte_http_transport.dart';

/// A squad member option for the lineup editor.
class LineupSquadPlayer {
  const LineupSquadPlayer({
    required this.playerId,
    required this.name,
    this.position,
    this.shirtNumber,
    this.rating,
    this.potential,
    this.form,
    this.fitnessPct,
    this.morale,
    this.portraitUrl,
  });

  final String playerId;
  final String name;
  final String? position;
  final int? shirtNumber;
  final double? rating;
  final double? potential;
  final String? form;
  final double? fitnessPct;
  final double? morale;
  final String? portraitUrl;
}

/// A club's saved formation + starting XI.
class ClubLineupPlan {
  const ClubLineupPlan({
    required this.formation,
    required this.starterPlayerIds,
    required this.benchPlayerIds,
  });

  final String formation;
  final List<String> starterPlayerIds;
  final List<String> benchPlayerIds;
}

class ClubLineupRepository {
  ClubLineupRepository({
    required this.config,
    required this.transport,
    required this.accessToken,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String accessToken;

  factory ClubLineupRepository.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return ClubLineupRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
    );
  }

  Future<ClubLineupPlan> fetchLineup(String clubId) async {
    final Map<String, dynamic> json = await _getMap('/api/clubs/$clubId/lineup');
    return ClubLineupPlan(
      formation: (json['formation'] as String?)?.trim().isNotEmpty == true
          ? json['formation'] as String
          : '4-3-3',
      starterPlayerIds: _stringList(json['starter_player_ids']),
      benchPlayerIds: _stringList(json['bench_player_ids']),
    );
  }

  Future<ClubLineupPlan> saveLineup(
    String clubId, {
    required String formation,
    required List<String> starterPlayerIds,
    required List<String> benchPlayerIds,
  }) async {
    final Map<String, dynamic> json = await _request(
      'PUT',
      '/api/clubs/$clubId/lineup',
      body: <String, Object?>{
        'formation': formation,
        'starter_player_ids': starterPlayerIds,
        'bench_player_ids': benchPlayerIds,
      },
    );
    return ClubLineupPlan(
      formation: json['formation'] as String? ?? formation,
      starterPlayerIds: _stringList(json['starter_player_ids']),
      benchPlayerIds: _stringList(json['bench_player_ids']),
    );
  }

  Future<List<LineupSquadPlayer>> fetchSquad(String clubId) async {
    final Map<String, dynamic> json =
        await _getMap('/api/market/clubs/$clubId/players');
    final Object? items = json['items'];
    if (items is! List) {
      return const <LineupSquadPlayer>[];
    }
    return items
        .whereType<Map>()
        .map((dynamic raw) {
          final Map<String, dynamic> item = Map<String, dynamic>.from(raw as Map);
          return LineupSquadPlayer(
            playerId: (item['player_id'] ?? item['playerId'] ?? '').toString(),
            name: (item['player_name'] ?? item['playerName'] ?? 'Player').toString(),
            position: (item['position'] ?? item['normalized_position'])?.toString(),
            shirtNumber: _intField(item, const <String>[
              'shirt_number', 'shirtNumber', 'jersey_number', 'jerseyNumber',
            ]),
            rating: _doubleField(item, const <String>[
              'rating', 'overall', 'overall_rating', 'overallRating',
              'current_rating', 'currentRating',
            ]),
            potential: _doubleField(item, const <String>[
              'potential', 'potential_rating', 'potentialRating',
            ]),
            form: _formField(item),
            fitnessPct: _doubleField(item, const <String>[
              'fitness_pct', 'fitnessPct', 'fitness', 'stamina_pct', 'staminaPct',
            ]),
            morale: _doubleField(item, const <String>['morale', 'happiness']),
            portraitUrl: _stringField(item, const <String>[
              'portrait_url', 'portraitUrl', 'image_url', 'imageUrl',
              'avatar_url', 'avatarUrl',
            ]),
          );
        })
        .where((LineupSquadPlayer p) => p.playerId.isNotEmpty)
        .toList(growable: false);
  }

  static String? _stringField(
    Map<String, dynamic> item,
    List<String> keys,
  ) {
    for (final String key in keys) {
      final Object? value = item[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
    return null;
  }

  static int? _intField(Map<String, dynamic> item, List<String> keys) {
    for (final String key in keys) {
      final Object? value = item[key];
      if (value is int) return value;
      if (value is num) return value.round();
      if (value is String) {
        final int? parsed = int.tryParse(value.trim());
        if (parsed != null) return parsed;
      }
    }
    return null;
  }

  static double? _doubleField(
    Map<String, dynamic> item,
    List<String> keys,
  ) {
    for (final String key in keys) {
      final Object? value = item[key];
      if (value is num) return value.toDouble();
      if (value is String) {
        final double? parsed = double.tryParse(value.trim());
        if (parsed != null) return parsed;
      }
    }
    return null;
  }

  static String? _formField(Map<String, dynamic> item) {
    final Object? value = item['form'] ?? item['recent_form'] ?? item['recentForm'];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is List) {
      final String joined = value
          .map((dynamic item) => item?.toString() ?? '')
          .where((String item) => item.trim().isNotEmpty)
          .take(5)
          .join();
      return joined.isEmpty ? null : joined;
    }
    if (value is num) return value.toString();
    return null;
  }

  List<String> _stringList(Object? value) {
    if (value is! List) {
      return <String>[];
    }
    return value
        .map((dynamic e) => e?.toString() ?? '')
        .where((String e) => e.isNotEmpty)
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> _getMap(String path) => _request('GET', path);

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Object? body,
  }) async {
    final GteTransportResponse response = await transport.send(
      GteTransportRequest(
        method: method,
        uri: config.uriFor(path, const <String, Object?>{}),
        headers: <String, String>{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        },
        body: body,
      ),
    );
    if (response.statusCode >= 400) {
      throw GteApiException(
        type: response.statusCode == 401 || response.statusCode == 403
            ? GteApiErrorType.unauthorized
            : response.statusCode == 404
            ? GteApiErrorType.notFound
            : response.statusCode == 422
            ? GteApiErrorType.validation
            : response.statusCode >= 500
            ? GteApiErrorType.unavailable
            : GteApiErrorType.unknown,
        message: gteApiErrorMessage(response.body, fallback: 'Lineup request failed.'),
        statusCode: response.statusCode,
      );
    }
    final Object? payload = gteApiSuccessPayload(response.body);
    if (payload is Map<String, dynamic>) {
      return payload;
    }
    if (payload is Map) {
      return Map<String, dynamic>.from(payload);
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected lineup response shape.',
    );
  }
}
