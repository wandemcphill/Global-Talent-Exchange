import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';

import 'live_match_session.dart';

class LiveMatchSessionService {
  LiveMatchSessionService({GteAppConfig? config, GteExchangeApiClient? api})
    : _config = config ?? GteAppConfig.fromRuntimeEnvironment(),
      _api =
          api ??
          GteExchangeApiClient.standard(
            baseUrl:
                (config ?? GteAppConfig.fromRuntimeEnvironment()).apiBaseUrl,
            mode:
                (config ?? GteAppConfig.fromRuntimeEnvironment())
                    .activeShellBackendMode,
          );

  final GteAppConfig _config;
  final GteExchangeApiClient _api;

  Future<LiveMatchSpectateSession?> resolveSession(String matchId) async {
    if (_config.activeShellBackendMode == GteBackendMode.fixture) {
      return null;
    }
    try {
      final Map<String, Object?> payload = await _api.joinMatchSpectateSession(
        matchId,
      );
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
    final Uri? resolved = Uri.tryParse(trimmedPath);
    if (resolved == null || !_isCanonicalMatchWebSocketPath(resolved.path)) {
      return null;
    }
    if (resolved.hasScheme) {
      if (resolved.scheme != 'ws' && resolved.scheme != 'wss') {
        return null;
      }
      return resolved;
    }
    return base.replace(
      scheme: scheme,
      path: resolved.path,
      query: resolved.hasQuery ? resolved.query : null,
    );
  }

  bool _isCanonicalMatchWebSocketPath(String path) {
    final List<String> segments =
        Uri(path: path.trim().toLowerCase()).pathSegments;
    if (_matchesSegments(segments, const <String>[
      'api',
      'matches',
      '*',
      'stream',
    ])) {
      return true;
    }
    if (_matchesSegments(segments, const <String>[
      'api',
      'matches',
      '*',
      'commentary',
      'stream',
    ])) {
      return true;
    }
    if (_matchesSegments(segments, const <String>[
      'api',
      'matches',
      '*',
      'audio',
      'stems',
      'stream',
    ])) {
      return true;
    }
    if (_matchesSegments(segments, const <String>[
      'api',
      'v2',
      'matches',
      '*',
      'stream',
    ])) {
      return true;
    }
    if (_matchesSegments(segments, const <String>[
      'api',
      'v2',
      'matches',
      '*',
      'commentary',
      'stream',
    ])) {
      return true;
    }
    return _matchesSegments(segments, const <String>[
      'api',
      'v2',
      'matches',
      '*',
      'audio',
      'stems',
      'stream',
    ]);
  }

  bool _matchesSegments(List<String> segments, List<String> pattern) {
    if (segments.length != pattern.length) {
      return false;
    }
    for (var index = 0; index < pattern.length; index += 1) {
      final String expected = pattern[index];
      if (expected == '*') {
        if (segments[index].trim().isEmpty) {
          return false;
        }
        continue;
      }
      if (segments[index] != expected) {
        return false;
      }
    }
    return true;
  }
}
