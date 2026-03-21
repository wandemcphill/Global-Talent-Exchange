import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('match viewer renders fallback replay and controls',
      (WidgetTester tester) async {
    final CompetitionSummary competition = CompetitionSummary(
      id: 'match-viewer-test',
      name: 'GTEX Replay Test',
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
      rulesSummary: 'Replay validation fixture',
      joinEligibility: const CompetitionJoinEligibility(eligible: true),
      beginnerFriendly: true,
      createdAt: DateTime.utc(2026, 1, 1),
      updatedAt: DateTime.utc(2026, 1, 2),
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 48));

    expect(find.text('2D Match Viewer'), findsOneWidget);
    expect(find.text('Replay lane'), findsOneWidget);
    expect(find.text('Restart'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
    expect(
      find.text(snapshot.homeTeam.substring(0, 3).toUpperCase()),
      findsOneWidget,
    );
    expect(
      find.text(snapshot.awayTeam.substring(0, 3).toUpperCase()),
      findsOneWidget,
    );
  });
}
