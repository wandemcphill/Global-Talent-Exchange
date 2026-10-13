import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';

class GtexLiveWorldPulse {
  const GtexLiveWorldPulse({
    required this.clubsOnGtex,
    required this.usersOnline,
    required this.playersOnline,
    required this.usersOnlineWindowSeconds,
    required this.generatedAt,
    required this.labels,
  });

  final int clubsOnGtex;
  final int usersOnline;
  final int playersOnline;
  final int usersOnlineWindowSeconds;
  final DateTime generatedAt;
  final Map<String, String> labels;

  factory GtexLiveWorldPulse.fromJson(Object? raw) {
    final Map<String, Object?> json = GteJson.map(raw, label: 'live world pulse');
    return GtexLiveWorldPulse(
      clubsOnGtex: GteJson.integer(json, <String>['clubs_on_gtex', 'clubsOnGtex']),
      usersOnline: GteJson.integer(json, <String>['users_online', 'usersOnline']),
      playersOnline: GteJson.integer(json, <String>[
        'players_online',
        'playersOnline',
      ]),
      usersOnlineWindowSeconds: GteJson.integer(
        json,
        <String>['users_online_window_seconds', 'usersOnlineWindowSeconds'],
        fallback: 300,
      ),
      generatedAt: GteJson.dateTime(
        json,
        <String>['generated_at', 'generatedAt'],
      ),
      labels: GteJson.map(
        json,
        keys: <String>['labels'],
        fallback: const <String, Object?>{},
      ).map((String key, Object? value) => MapEntry(key, value?.toString() ?? '')),
    );
  }

  String get clubsLabel => _compact(clubsOnGtex);
  String get usersOnlineLabel => _compact(usersOnline);
  String get playersOnlineLabel => _compact(playersOnline);

  static String _compact(int value) {
    if (value >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}m';
    }
    if (value >= 1000) {
      return '${(value / 1000).toStringAsFixed(value >= 10000 ? 0 : 1)}k';
    }
    return '$value';
  }
}

class PublicPulseApi {
  PublicPulseApi({required this.client});

  final GteAuthedApi client;

  factory PublicPulseApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    return PublicPulseApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: transport ?? GteHttpTransport(),
        accessToken: null,
        mode: mode,
      ),
    );
  }

  Future<GtexLiveWorldPulse> fetchLiveStats() {
    return client.withFallback<GtexLiveWorldPulse>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/public/live-stats',
        auth: false,
      );
      return GtexLiveWorldPulse.fromJson(payload);
    }, () => throw StateError('Live world pulse requires the public API.'));
  }
}
