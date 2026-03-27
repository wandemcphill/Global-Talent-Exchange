import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/gte_live_match_center_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('live match center exposes broadcast and replay entry points',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _buildCompetition();
    final LiveMatchSnapshot base = LiveMatchFixtures.buildSnapshot(competition);
    final LiveMatchSnapshot snapshot = LiveMatchSnapshot(
      matchId: base.matchId,
      halftimeAnalyticsAvailable: base.halftimeAnalyticsAvailable,
      highlightsAvailable: true,
      keyMomentsAvailable: true,
      homeTeam: base.homeTeam,
      awayTeam: base.awayTeam,
      homeScore: base.homeScore,
      awayScore: base.awayScore,
      minute: base.minute,
      phase: base.phase,
      momentum: base.momentum,
      commentary: base.commentary,
      homeLineup: base.homeLineup,
      awayLineup: base.awayLineup,
      substitutions: base.substitutions,
      cards: base.cards,
      tacticalSuggestions: base.tacticalSuggestions,
      keyMoments: base.keyMoments,
      highlights: base.highlights,
      standardHighlightExpiresAt: base.standardHighlightExpiresAt,
      premiumHighlightExpiresAt: base.premiumHighlightExpiresAt,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLiveMatchCenterScreen(
          competition: competition,
          snapshotLoader: (_) async => snapshot,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('Live broadcast layer'), findsOneWidget);
    expect(find.text('Watch broadcast'), findsOneWidget);
    expect(find.text('2D replay viewer'), findsOneWidget);
    expect(find.text('Open replay'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Tactical match simulation'),
      250,
    );
    expect(find.text('Tactical match simulation'), findsOneWidget);
    expect(find.text('Run simulation'), findsOneWidget);
  });
}

CompetitionSummary _buildCompetition() {
  return CompetitionSummary(
    id: 'live-match-center-test',
    name: 'GTEX Live',
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
    rulesSummary: 'Live center fixture',
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
