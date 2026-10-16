import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/competitions/presentation/gtex_live_competitions_command_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';

void main() {
  testWidgets('hub distinguishes loading from unavailable competition feeds', (
    WidgetTester tester,
  ) async {
    final Completer<CompetitionHubData> completer =
        Completer<CompetitionHubData>();
    await tester.pumpWidget(_host((Ref ref) => completer.future));
    expect(find.text('Loading competition command'), findsOneWidget);

    completer.completeError(StateError('offline'));
    await tester.pump();
    await tester.pumpAndSettle();
    expect(find.text('Competition feed unavailable'), findsOneWidget);
  });

  testWidgets('hub keeps the three competition families distinct', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _host(
        (Ref ref) async => CompetitionHubData(
          gtexCompetitions: <CompetitionSummary>[_competition('gtex-1')],
          hostedCompetitions: const <HostedCompetition>[],
          streamerTournaments: const [],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX competitions'), findsOneWidget);
    expect(find.text('Hosted competitions'), findsOneWidget);
    expect(find.text('Creator tournaments'), findsOneWidget);
    expect(find.text('GTEX Test Cup'), findsOneWidget);

    await tester.tap(find.text('Hosted competitions'));
    await tester.pumpAndSettle();
    expect(find.text('User Competitions are quiet'), findsOneWidget);
  });

  testWidgets(
    'GTEX detail keeps an unauthenticated participation decision locked',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final CompetitionSummary competition = _competition('gtex-1');
      await tester.pumpWidget(
        MaterialApp(
          home: ProviderScope(
            overrides: [
              competitionHubProvider.overrideWith(
                (Ref ref) async => CompetitionHubData(
                  gtexCompetitions: <CompetitionSummary>[competition],
                  hostedCompetitions: const <HostedCompetition>[],
                  streamerTournaments: const [],
                ),
              ),
              gtexCompetitionDetailProvider(
                'gtex-1',
              ).overrideWith((Ref ref) async => _detail(competition)),
            ],
            child: const Scaffold(
              body: GtexLiveCompetitionsCommandScreen(
                isAuthenticated: false,
                onOpenLogin: _noop,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('GTEX Test Cup'));
      await tester.pumpAndSettle();

      expect(find.text('Sign in to check participation'), findsOneWidget);
      expect(find.text('No fixtures reported'), findsOneWidget);
      expect(find.text('No standings reported'), findsOneWidget);
    },
  );
}

Widget _host(Future<CompetitionHubData> Function(Ref ref) load) => MaterialApp(
  home: ProviderScope(
    overrides: [competitionHubProvider.overrideWith((Ref ref) => load(ref))],
    child: const Scaffold(
      body: GtexLiveCompetitionsCommandScreen(
        isAuthenticated: false,
        onOpenLogin: _noop,
      ),
    ),
  ),
);

void _noop() {}

CompetitionSummary _competition(String id) => CompetitionSummary(
  id: id,
  name: 'GTEX Test Cup',
  format: CompetitionFormat.cup,
  visibility: CompetitionVisibility.public,
  status: CompetitionStatus.openForJoin,
  creatorId: 'gtex',
  creatorName: 'GTEX',
  participantCount: 2,
  capacity: 16,
  currency: 'GTEX',
  entryFee: 0,
  platformFeePct: 0,
  hostFeePct: 0,
  platformFeeAmount: 0,
  hostFeeAmount: 0,
  prizePool: 0,
  payoutStructure: const <CompetitionPayoutBreakdown>[],
  rulesSummary: 'Test rules',
  matchType: MatchType.gtexHosted,
  joinEligibility: const CompetitionJoinEligibility(eligible: true),
  beginnerFriendly: true,
  createdAt: DateTime.utc(2026),
  updatedAt: DateTime.utc(2026),
);

GtexCompetitionDetailBundle _detail(CompetitionSummary competition) =>
    GtexCompetitionDetailBundle(
      competition: competition,
      financials: CompetitionFinancialSummary(
        competitionId: competition.id,
        participantCount: competition.participantCount,
        entryFee: 0,
        grossPool: 0,
        platformFeeAmount: 0,
        hostFeeAmount: 0,
        prizePool: 0,
        payoutStructure: const <CompetitionPayoutBreakdown>[],
        currency: 'GTEX',
      ),
      standings: const [],
      fixtures: const [],
    );
