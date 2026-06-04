import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../support/live_match_test_fixtures.dart';
import 'package:gte_frontend/features/match_center/data/match/match_simulation_engine.dart';
import 'package:gte_frontend/features/match_center/data/match/match_simulation_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_simulation_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('simulation screen is quarantined behind backend realtime', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _competition();
    final LiveMatchSnapshot snapshot = LiveMatchTestFixtures.buildSnapshot(
      competition,
    );
    final MatchSimulationRequest request =
        MatchSimulationRequestFactory.fromLiveSnapshot(
          snapshot,
          matchId: competition.id,
          importance: MatchSimulationImportance.tournament,
        );
    final MatchSimulationResult result = const MatchSimulationEngine().simulate(
      request,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchSimulationScreen(
          result: result,
          competitionLabel: competition.name,
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.text('Simulation blocked'), findsWidgets);
    expect(
      find.textContaining('Local match simulation playback is quarantined'),
      findsWidgets,
    );
    expect(find.text('Live commentary'), findsNothing);
    expect(find.text('Timeline'), findsNothing);
  });
}

CompetitionSummary _competition() {
  return CompetitionSummary(
    id: 'simulation-screen-test',
    name: 'GTEX Arena Night',
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
    rulesSummary: 'Simulation screen fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
