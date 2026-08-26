import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/runtime/gtex_realtime_client.dart';
import 'package:gte_frontend/core/runtime/gtex_runtime_graph.dart';
import 'package:gte_frontend/core/runtime/gtex_runtime_models.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_repository.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('strict-live runtime graph accepts live adapters only', () {
    expect(
      () => validateGtexRuntimeAdapterGraph(
        _runtime(),
        allowFlutterTestBypass: false,
      ),
      returnsNormally,
    );
  });

  test('strict-live runtime graph rejects fixture endpoints', () {
    expect(
      () => validateGtexRuntimeAdapterGraph(
        _runtime(apiBaseUrl: 'https://fixture.invalid'),
        allowFlutterTestBypass: false,
      ),
      throwsA(
        isA<StateError>().having(
          (StateError error) => error.message,
          'message',
          contains('non_live_api_base_url'),
        ),
      ),
    );
  });

  test('strict-live runtime graph rejects unavailable match repositories', () {
    expect(
      () => validateGtexRuntimeAdapterGraph(
        _runtime(matches: const GtexUnavailableMatchRepository()),
        allowFlutterTestBypass: false,
      ),
      throwsA(
        isA<StateError>().having(
          (StateError error) => error.message,
          'message',
          contains('synthetic_match_repository_registered'),
        ),
      ),
    );
  });

  test('strict-live runtime graph rejects registered fixture repositories', () {
    expect(
      () => validateGtexRuntimeAdapterGraph(
        _runtime(
          clubs: ClubApi.fixture(),
          nationalTeams: NationalTeamApi.fixture(),
          exchangeApi: GteExchangeApiClient.fixture(),
        ),
        allowFlutterTestBypass: false,
      ),
      throwsA(
        isA<StateError>().having(
          (StateError error) => error.message,
          'message',
          allOf(
            contains('synthetic_club_repository_registered'),
            contains('synthetic_exchange_repository_registered'),
            contains('synthetic_national_repository_registered'),
          ),
        ),
      ),
    );
  });
}

GtexRuntime _runtime({
  String apiBaseUrl = 'https://api.gtex.test',
  GtexMatchRepository? matches,
  ClubApi? clubs,
  NationalTeamApi? nationalTeams,
  GteExchangeApiClient? exchangeApi,
}) {
  final GteExchangeApiClient resolvedExchangeApi =
      exchangeApi ?? GteExchangeApiClient.standard(baseUrl: apiBaseUrl);
  return GtexRuntime(
    env: GtexRuntimeEnv.production,
    apiBaseUrl: apiBaseUrl,
    accessToken: 'token',
    websocket: GtexRealtimeClient(
      apiBaseUrl: apiBaseUrl,
      accessTokenProvider: () => 'token',
    ),
    repositories: GtexRuntimeRepositories(
      matches: matches ?? const _LiveMatchRepositoryStub(),
      clubs: clubs ?? ClubApi.standard(baseUrl: apiBaseUrl),
      competitions: CompetitionApi.standard(baseUrl: apiBaseUrl),
      nationalTeams:
          nationalTeams ??
          NationalTeamApi.standard(baseUrl: apiBaseUrl, accessToken: 'token'),
    ),
    controllers: GtexRuntimeControllers(
      exchange: GteExchangeController(api: resolvedExchangeApi),
      admin: null,
    ),
    capabilities: const GtexRuntimeCapabilities(
      korapay: true,
      manualPayment: true,
      paystack: true,
      fixtureMode: false,
    ),
    readiness: const GtexRuntimeReadiness(
      strictLive: true,
      blockedReasons: <String>[],
    ),
    observability: const GtexRuntimeObservability(
      liveEndpointProvenance: <String, String>{},
      websocketSourceTrace: <String, String>{},
      sourceOfTruthTag: 'persisted_backend_authority',
      stalePayloadThreshold: Duration(seconds: 45),
      healthOverlayEnabled: false,
    ),
    session: null,
  );
}

class _LiveMatchRepositoryStub implements GtexMatchRepository {
  const _LiveMatchRepositoryStub();

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) {
    return Future<GtexLiveMatchState>.error(UnimplementedError());
  }

  @override
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  ) {
    return Future<void>.error(UnimplementedError());
  }

  @override
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId) {
    return Stream<GtexLiveMatchState>.empty();
  }
}
