import 'gte_api_repository.dart';
import 'gte_http_transport.dart';

/// A snapshot of a live (tick-based) match session.
class LiveMatchState {
  const LiveMatchState({
    required this.matchId,
    required this.minute,
    required this.phase,
    required this.homeName,
    required this.awayName,
    required this.homeScore,
    required this.awayScore,
    required this.homeFormation,
    required this.awayFormation,
    this.halftimeSecondsRemaining,
    this.halftimeReady = const <String>[],
    this.events = const <Map<String, dynamic>>[],
    this.yourSide,
  });

  final String matchId;
  final int minute;
  final String phase; // pre_match | first_half | half_time | second_half | full_time
  final String homeName;
  final String awayName;
  final int homeScore;
  final int awayScore;
  final String homeFormation;
  final String awayFormation;
  final int? halftimeSecondsRemaining;
  final List<String> halftimeReady;
  final List<Map<String, dynamic>> events;
  /// The side ("home"/"away") the requesting user controls, or null for spectators.
  final String? yourSide;

  bool get isHalftime => phase == 'half_time';
  bool get isFullTime => phase == 'full_time';

  factory LiveMatchState.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic> tactics(String key) {
      final Object? raw = json[key];
      return raw is Map ? Map<String, dynamic>.from(raw) : const <String, dynamic>{};
    }

    return LiveMatchState(
      matchId: (json['match_id'] ?? '').toString(),
      minute: (json['minute'] as num?)?.toInt() ?? 0,
      phase: (json['phase'] ?? 'pre_match').toString(),
      homeName: (json['home_name'] ?? 'Home').toString(),
      awayName: (json['away_name'] ?? 'Away').toString(),
      homeScore: (json['home_score'] as num?)?.toInt() ?? 0,
      awayScore: (json['away_score'] as num?)?.toInt() ?? 0,
      homeFormation: (tactics('home_tactics')['formation'] ?? '4-3-3').toString(),
      awayFormation: (tactics('away_tactics')['formation'] ?? '4-3-3').toString(),
      halftimeSecondsRemaining: (json['halftime_seconds_remaining'] as num?)?.toInt(),
      halftimeReady: (json['halftime_ready'] as List?)
              ?.map((dynamic e) => e.toString())
              .toList(growable: false) ??
          const <String>[],
      events: (json['events'] as List?)
              ?.whereType<Map>()
              .map((dynamic e) => Map<String, dynamic>.from(e as Map))
              .toList(growable: false) ??
          const <Map<String, dynamic>>[],
      yourSide: (json['your_side'] as Object?)?.toString(),
    );
  }
}

class LiveMatchRepository {
  LiveMatchRepository({
    required this.config,
    required this.transport,
    required this.accessToken,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String accessToken;

  factory LiveMatchRepository.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return LiveMatchRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
    );
  }

  Future<LiveMatchState> fetchState(String matchId) async {
    final Map<String, dynamic> json =
        await _request('GET', '/api/live-match/sessions/$matchId');
    return LiveMatchState.fromJson(json);
  }

  Future<LiveMatchState> setTactics(
    String matchId, {
    required String side,
    String? formation,
    String? mentality,
    int? pressing,
    int? tempo,
  }) async {
    final Map<String, dynamic> json = await _request(
      'POST',
      '/api/live-match/sessions/$matchId/tactics',
      body: <String, Object?>{
        'side': side,
        if (formation != null) 'formation': formation,
        if (mentality != null) 'mentality': mentality,
        if (pressing != null) 'pressing': pressing,
        if (tempo != null) 'tempo': tempo,
      },
    );
    return LiveMatchState.fromJson(json);
  }

  Future<LiveMatchState> markHalftimeReady(String matchId, {required String side}) async {
    final Map<String, dynamic> json = await _request(
      'POST',
      '/api/live-match/sessions/$matchId/halftime/ready',
      body: <String, Object?>{'side': side},
    );
    return LiveMatchState.fromJson(json);
  }

  /// Settle a finished head-to-head live match for the initiator (idempotent).
  /// Returns the settlement result (win/loss/draw + entitlement effects).
  Future<Map<String, dynamic>> settleMatch(String matchId) async {
    return _request(
      'POST',
      '/api/simulation-matchmaking/quick-game/$matchId/settle',
    );
  }

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
        type: response.statusCode == 404
            ? GteApiErrorType.notFound
            : response.statusCode == 401 || response.statusCode == 403
            ? GteApiErrorType.unauthorized
            : GteApiErrorType.unknown,
        message: gteApiErrorMessage(response.body, fallback: 'Live match request failed.'),
        statusCode: response.statusCode,
      );
    }
    final Object? payload = gteApiSuccessPayload(response.body);
    if (payload is Map) {
      return Map<String, dynamic>.from(payload);
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected live match response shape.',
    );
  }
}
