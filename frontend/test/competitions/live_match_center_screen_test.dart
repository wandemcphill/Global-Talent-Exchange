import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/screens/competitions/gte_live_match_center_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('live match center exposes replay and spectator entry points', (
    WidgetTester tester,
  ) async {
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

    expect(find.text('2D replay viewer'), findsOneWidget);
    expect(find.text('Open viewer'), findsOneWidget);
    expect(find.text('Spectator modes'), findsOneWidget);
    expect(find.text('2D commentary'), findsOneWidget);
    expect(find.text('Key-moment video'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Live momentum'), 250);
    expect(find.text('Live momentum'), findsOneWidget);
  });

  testWidgets('live match center switches into the key-moment access panel', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _buildCompetition();
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLiveMatchCenterScreen(
          competition: competition,
          snapshotLoader: (_) async => snapshot,
          onOpenLogin: () {},
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    await tester.scrollUntilVisible(find.text('Key-moment video').first, 250);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Key-moment video').first);
    await tester.pumpAndSettle();

    expect(find.text('Key-moment video locked'), findsOneWidget);
    expect(find.text('Unlock with Arena Pass'), findsOneWidget);
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
    matchType: MatchType.userHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}
