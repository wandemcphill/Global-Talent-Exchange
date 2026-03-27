import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/match/match_simulation_engine.dart';
import 'package:gte_frontend/data/match/match_simulation_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/match/gtex_match_simulation_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('simulation screen renders commentary and analysis tabs',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _competition();
    final LiveMatchSnapshot snapshot =
        LiveMatchFixtures.buildSnapshot(competition);
    final MatchSimulationRequest request =
        MatchSimulationRequestFactory.fromLiveSnapshot(
      snapshot,
      matchId: competition.id,
      importance: MatchSimulationImportance.tournament,
    );
    final MatchSimulationResult result =
        const MatchSimulationEngine().simulate(request);

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

    await tester.drag(find.byType(ListView).first, const Offset(0, -500));
    await tester.pump();
    expect(find.text('Live commentary'), findsOneWidget);
    expect(find.text('Stats'), findsWidgets);
    expect(find.text('Timeline'), findsOneWidget);
    expect(find.text('Ratings'), findsOneWidget);
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
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
