import 'gte_api_repository.dart';
import 'gte_http_transport.dart';

/// A squad member option for the lineup editor.
class LineupSquadPlayer {
  const LineupSquadPlayer({
    required this.playerId,
    required this.name,
    this.position,
  });

  final String playerId;
  final String name;
  final String? position;
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
          );
        })
        .where((LineupSquadPlayer p) => p.playerId.isNotEmpty)
        .toList(growable: false);
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
