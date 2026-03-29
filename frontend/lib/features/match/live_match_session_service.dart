import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';

import 'live_match_session.dart';

class LiveMatchSessionService {
  LiveMatchSessionService({
    GteAppConfig? config,
    GteExchangeApiClient? api,
  }) : _config = config ?? GteAppConfig.fromEnvironment(),
       _api = api ??
           GteExchangeApiClient.standard(
             baseUrl: (config ?? GteAppConfig.fromEnvironment()).apiBaseUrl,
             mode: (config ?? GteAppConfig.fromEnvironment()).backendMode,
           );

  final GteAppConfig _config;
  final GteExchangeApiClient _api;

  Future<LiveMatchSpectateSession?> resolveSession(String matchId) async {
    if (_config.backendMode == GteBackendMode.fixture) {
      return null;
    }
    try {
      final Map<String, Object?> payload =
          await _api.joinMatchSpectateSession(matchId);
      return LiveMatchSpectateSession.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  Uri? resolveWebSocketUri(String? websocketPath) {
    final String? trimmedPath = websocketPath?.trim();
    if (trimmedPath == null || trimmedPath.isEmpty) {
      return null;
    }
    final Uri? base = Uri.tryParse(_config.apiBaseUrl);
    if (base == null || !base.hasScheme || base.host.trim().isEmpty) {
      return null;
    }
    final String scheme = switch (base.scheme) {
      'https' => 'wss',
      'http' => 'ws',
      'ws' || 'wss' => base.scheme,
      _ => 'wss',
    };
    final Uri resolved = Uri.parse(trimmedPath);
    if (resolved.hasScheme) {
      return resolved;
    }
    return base.replace(
      scheme: scheme,
      path: resolved.path,
      query: resolved.hasQuery ? resolved.query : null,
    );
  }
}
