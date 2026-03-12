import '../../../../data/gte_api_repository.dart';
import '../../../../data/gte_http_transport.dart';
import '../../../../data/gte_models.dart';
import 'dynasty_era_dto.dart';
import 'dynasty_fixture_repository.dart';
import 'dynasty_leaderboard_entry_dto.dart';
import 'dynasty_profile_dto.dart';
import 'dynasty_response_mapper.dart';
import 'dynasty_repository.dart';

class DynastyApiRepository implements DynastyRepository {
  DynastyApiRepository({
    required this.config,
    required this.transport,
    required this.fixtures,
    DynastyResponseMapper? mapper,
  }) : mapper = mapper ?? dynastyResponseMapper;

  final GteRepositoryConfig config;
  final GteTransport transport;
  final DynastyRepository fixtures;
  final DynastyResponseMapper mapper;

  factory DynastyApiRepository.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
    Duration latency = const Duration(milliseconds: 220),
  }) {
    final GteRepositoryConfig config =
        GteRepositoryConfig(baseUrl: baseUrl, mode: mode);
    return DynastyApiRepository(
      config: config,
      transport: GteHttpTransport(),
      fixtures: DynastyFixtureRepository(latency: latency),
    );
  }

  @override
  Future<DynastyProfileDto> fetchDynastyProfile(String clubId) {
    return _withFallback<DynastyProfileDto>(
      () => _fetchLiveProfile(clubId),
      () => fixtures.fetchDynastyProfile(clubId),
    );
  }

  @override
  Future<DynastyHistoryDto> fetchDynastyHistory(String clubId) {
    return _withFallback<DynastyHistoryDto>(
      () async => mapper.mapHistory(
          await _request('GET', '/api/clubs/$clubId/dynasty/history')),
      () => fixtures.fetchDynastyHistory(clubId),
    );
  }

  @override
  Future<List<DynastyEraDto>> fetchEras(String clubId) {
    if (config.mode == GteBackendMode.fixture) {
      return fixtures.fetchEras(clubId);
    }
    return _fetchLiveEras(clubId);
  }

  @override
  Future<List<DynastyLeaderboardEntryDto>> fetchDynastyLeaderboard({
    int limit = 25,
  }) {
    return _withFallback<List<DynastyLeaderboardEntryDto>>(
      () async => mapper.mapLeaderboard(
        await _request(
          'GET',
          '/api/leaderboards/dynasties',
          query: <String, Object?>{'limit': limit},
        ),
      ),
      () => fixtures.fetchDynastyLeaderboard(limit: limit),
    );
  }

  Future<DynastyProfileDto> _fetchLiveProfile(String clubId) async {
    final Object? payload = await _request('GET', '/api/clubs/$clubId/dynasty');
    if (!_isLegacyProfilePayload(payload)) {
      return mapper.mapProfile(payload);
    }

    final DynastyHistoryDto? history = await _tryFetchHistory(clubId);
    final List<DynastyEraDto> explicitEras =
        history == null ? const <DynastyEraDto>[] : await _tryFetchEras(clubId);
    return mapper.mapProfile(
      payload,
      history: history,
      explicitEras: explicitEras,
    );
  }

  Future<DynastyHistoryDto?> _tryFetchHistory(String clubId) async {
    try {
      return mapper.mapHistory(
        await _request('GET', '/api/clubs/$clubId/dynasty/history'),
      );
    } catch (_) {
      return null;
    }
  }

  Future<List<DynastyEraDto>> _fetchLiveEras(String clubId) async {
    return mapper.mapEras(await _request('GET', '/api/clubs/$clubId/eras'));
  }

  Future<List<DynastyEraDto>> _tryFetchEras(String clubId) async {
    try {
      return await _fetchLiveEras(clubId);
    } catch (_) {
      return const <DynastyEraDto>[];
    }
  }

  bool _isLegacyProfilePayload(Object? payload) {
    if (payload is! Map) {
      return false;
    }
    final Map<String, Object?> json =
        GteJson.map(payload, label: 'dynasty profile');
    return json.containsKey('progress');
  }

  Future<T> _withFallback<T>(
    Future<T> Function() loadLive,
    Future<T> Function() loadFixture,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return loadFixture();
    }

    try {
      return await loadLive();
    } catch (error) {
      if (_shouldFallback(error)) {
        return loadFixture();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatus(response.statusCode),
          message: _errorMessage(
            response.body,
            fallback: 'Dynasty request failed.',
          ),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to load dynasty data right now.',
        cause: error,
      );
    }
  }

  bool _shouldFallback(Object error) {
    if (config.mode != GteBackendMode.liveThenFixture) {
      return false;
    }
    return (error is GteApiException && error.supportsFixtureFallback) ||
        error is GteParsingException;
  }

  GteApiErrorType _errorTypeFromStatus(int statusCode) {
    if (statusCode == 401 || statusCode == 403) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode == 422) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  String _errorMessage(
    Object? payload, {
    required String fallback,
  }) {
    if (payload is String && payload.trim().isNotEmpty) {
      return payload;
    }
    if (payload is Map) {
      final Map<String, Object?> json = GteJson.map(payload);
      final String? detail = GteJson.stringOrNull(
        json,
        const <String>['detail', 'message', 'error'],
      );
      if (detail != null && detail.isNotEmpty) {
        return detail;
      }
    }
    return fallback;
  }
}
