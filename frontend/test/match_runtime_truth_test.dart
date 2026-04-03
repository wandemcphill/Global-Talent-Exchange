import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';

void main() {
  const GteAppConfig liveThenFixtureConfig = GteAppConfig(
    apiBaseUrl: 'https://example.test',
    backendMode: GteBackendMode.liveThenFixture,
  );

  test(
    'live match snapshot loader surfaces backend failures outside explicit fixture mode',
    () async {
      final _ThrowingMatchApiClient api = _ThrowingMatchApiClient();

      expect(
        () => loadLiveMatchSnapshot(
          _buildCompetition(id: 'live-feed-truth'),
          config: liveThenFixtureConfig,
          api: api,
        ),
        throwsA(isA<StateError>()),
      );
      expect(api.liveFeedCalls, 1);
    },
  );

  test(
    'match viewer mapper surfaces backend failures outside explicit fixture mode',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'viewer-truth',
      );
      final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
        competition,
      );
      final _ThrowingMatchApiClient api = _ThrowingMatchApiClient();

      expect(
        () => MatchViewerMapper.load(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          config: liveThenFixtureConfig,
          api: api,
        ),
        throwsA(isA<StateError>()),
      );

      final MatchViewState fallback = await MatchViewerMapper.load(
        competition: competition,
        matchKey: competition.id,
        fallbackSnapshot: snapshot,
        preferFallback: true,
        config: liveThenFixtureConfig,
        api: api,
      );

      expect(fallback.source, 'fixture_fallback');
      expect(api.viewerCalls, 1);
    },
  );
}

class _ThrowingMatchApiClient extends GteExchangeApiClient {
  _ThrowingMatchApiClient._(GteExchangeApiClient delegate)
    : super(
        config: delegate.config,
        transport: delegate.transport,
        repository: delegate.repository,
      );

  factory _ThrowingMatchApiClient() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _ThrowingMatchApiClient._(delegate);
  }

  int liveFeedCalls = 0;
  int viewerCalls = 0;

  @override
  Future<Map<String, Object?>> fetchMatchLiveFeed(String matchKey) {
    liveFeedCalls += 1;
    throw StateError('live-feed-offline:$matchKey');
  }

  @override
  Future<Map<String, Object?>> fetchMatchViewer(
    String matchKey, {
    MatchMode mode = MatchMode.standard,
  }) {
    viewerCalls += 1;
    throw StateError('viewer-offline:$matchKey:${mode.name}');
  }
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'Runtime truth test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.completed,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 8,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Runtime truth coverage',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
