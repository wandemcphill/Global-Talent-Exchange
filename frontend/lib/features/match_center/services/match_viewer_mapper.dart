import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

class MatchViewerMapper {
  MatchViewerMapper._();

  static final GteAppConfig _config = GteAppConfig.fromRuntimeEnvironment();
  static final GteExchangeApiClient _api = GteExchangeApiClient.standard(
    baseUrl: _config.apiBaseUrl,
    mode: _config.activeShellBackendMode,
  );

  static Future<MatchViewState> load({
    required CompetitionSummary competition,
    required String matchKey,
    GteAppConfig? config,
    GteExchangeApiClient? api,
  }) async {
    final GteAppConfig resolvedConfig = config ?? _config;
    final GteBackendMode effectiveMode = resolvedConfig.activeShellBackendMode;
    if (effectiveMode == GteBackendMode.fixture) {
      throw StateError(
        'Match viewer requires backend-authored timeline frames; local fixture '
        'fallbacks are disabled.',
      );
    }

    final GteExchangeApiClient resolvedApi = _resolveApiClient(
      resolvedConfig,
      api,
    );
    final Map<String, Object?> payload = await resolvedApi.fetchMatchViewer(
      matchKey,
    );
    _requireBackendAuthoredFrames(payload);
    return MatchViewState.fromJson(payload);
  }

  static void _requireBackendAuthoredFrames(Map<String, Object?> payload) {
    final Object? frames = payload['frames'];
    if (frames is List && frames.isNotEmpty) {
      return;
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'Live match viewer payload is missing backend-authored timeline frames.',
    );
  }

  static GteExchangeApiClient _resolveApiClient(
    GteAppConfig config,
    GteExchangeApiClient? api,
  ) {
    if (api != null) {
      return api;
    }
    if (identical(config, _config)) {
      return _api;
    }
    return GteExchangeApiClient.standard(
      baseUrl: config.apiBaseUrl,
      mode: config.activeShellBackendMode,
    );
  }
}
