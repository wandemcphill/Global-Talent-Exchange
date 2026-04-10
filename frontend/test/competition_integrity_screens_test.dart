import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/screens/competitions/gte_halftime_analytics_screen.dart';
import 'package:gte_frontend/screens/competitions/gte_match_highlights_screen.dart';

void main() {
  testWidgets('match highlights screen renders honest unavailable state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: GteMatchHighlightsScreen(
          competition: _buildCompetition(),
          isAuthenticated: true,
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Match highlights'), findsOneWidget);
    expect(find.text('Match highlights unavailable'), findsOneWidget);
  });

  testWidgets('halftime analytics screen renders honest unavailable state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: GteHalftimeAnalyticsScreen(competition: _buildCompetition()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Halftime analytics'), findsOneWidget);
    expect(find.text('Halftime analytics unavailable'), findsOneWidget);
  });
}

CompetitionSummary _buildCompetition() {
  return CompetitionSummary(
    id: 'competition-1',
    name: 'GTEX Verification Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
    creatorId: 'gtex',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 16,
    currency: 'coin',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 100,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Verification-only competition fixture.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}
