import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';

import 'honors_timeline_dto.dart';
import 'season_honors_dto.dart';
import 'trophy_cabinet_dto.dart';
import 'trophy_cabinet_repository.dart';
import 'trophy_leaderboard_entry_dto.dart';

class TrophyCabinetApiRepository implements TrophyCabinetRepository {
  TrophyCabinetApiRepository({
    required this.config,
    required this.transport,
    TrophyCabinetRepository? fixtures,
  }) : fixtures = fixtures ?? StubTrophyCabinetRepository();

  factory TrophyCabinetApiRepository.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return TrophyCabinetApiRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
      transport: GteHttpTransport(),
    );
  }

  final GteRepositoryConfig config;
  final GteTransport transport;
  final TrophyCabinetRepository fixtures;

  @override
  Future<TrophyCabinetDto> fetchTrophyCabinet({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<TrophyCabinetDto>(
      () async => TrophyCabinetDto.fromJson(
        _asMap(
          await _request(
            '/api/clubs/$clubId/trophy-cabinet',
            query: <String, Object?>{'team_scope': teamScope},
          ),
        ),
      ),
      () => fixtures.fetchTrophyCabinet(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<HonorsTimelineDto> fetchHonorsTimeline({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<HonorsTimelineDto>(
      () async => HonorsTimelineDto.fromJson(
        _asMap(
          await _request(
            '/api/clubs/$clubId/honors-timeline',
            query: <String, Object?>{'team_scope': teamScope},
          ),
        ),
      ),
      () => fixtures.fetchHonorsTimeline(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<SeasonHonorsArchiveDto> fetchSeasonHonors({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<SeasonHonorsArchiveDto>(
      () async => SeasonHonorsArchiveDto.fromJson(
        _asMap(
          await _request(
            '/api/clubs/$clubId/season-honors',
            query: <String, Object?>{'team_scope': teamScope},
          ),
        ),
      ),
      () => fixtures.fetchSeasonHonors(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<TrophyLeaderboardDto> fetchTrophyLeaderboard({String? teamScope}) {
    return _withFallback<TrophyLeaderboardDto>(
      () async => TrophyLeaderboardDto.fromJson(
        _asMap(
          await _request(
            '/api/leaderboards/trophies',
            query: <String, Object?>{'team_scope': teamScope},
          ),
        ),
      ),
      () => fixtures.fetchTrophyLeaderboard(teamScope: teamScope),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (config.mode == GteBackendMode.liveThenFixture &&
          (error.supportsFixtureFallback ||
              error.type == GteApiErrorType.notFound ||
              error.type == GteApiErrorType.unknown)) {
        return fixtureCall();
      }
      rethrow;
    } on GteParsingException {
      if (config.mode == GteBackendMode.liveThenFixture) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: 'GET',
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorType(response.statusCode),
          message: gteApiErrorMessage(
            response.body,
            fallback: 'Unable to load trophy cabinet data.',
          ),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return gteApiSuccessPayload(response.body);
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to load trophy cabinet data.',
        cause: error,
      );
    }
  }
}

Map<String, Object?> _asMap(Object? value) {
  return GteJson.map(value, label: 'trophy cabinet payload');
}

GteApiErrorType _errorType(int statusCode) {
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
