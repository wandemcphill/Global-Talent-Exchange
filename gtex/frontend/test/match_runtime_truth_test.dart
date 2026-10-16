import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';

void main() {
  test(
    'live match snapshot loader returns fixture data in explicit fixture mode',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'live-feed-truth',
      );

      final LiveMatchSnapshot snapshot = await loadLiveMatchSnapshot(
        competition,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
      );

      expect(snapshot.matchId, competition.id);
      expect(snapshot.homeTeam, isNotEmpty);
      expect(snapshot.awayTeam, isNotEmpty);
      expect(snapshot.commentary, isNotEmpty);
      expect(snapshot.highlights, isNotEmpty);
    },
  );

  test(
    'match viewer mapper returns fixture fallback state in fixture mode',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'viewer-truth',
      );
      final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
        competition,
      );

      final MatchViewState state = await MatchViewerMapper.load(
        competition: competition,
        matchKey: competition.id,
        fallbackSnapshot: snapshot,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
      );

      expect(state.matchId, competition.id);
      expect(state.source, 'fixture_fallback');
      expect(state.events, isNotEmpty);
      expect(state.frames, isNotEmpty);
    },
  );
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
