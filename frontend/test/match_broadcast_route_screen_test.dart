import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/features/match/match_broadcast_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('broadcast route mounts the package lane on a live payload', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildWidget(
        repository: _FakeViewerRepository(
          viewState: buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Broadcast Package'), findsWidgets);
    expect(find.text('Official Roster Card'), findsOneWidget);
    expect(find.text('PSEUDO_3D'), findsOneWidget);
  });

  testWidgets(
    'broadcast route reuses the bootstrapped session on first mount',
    (WidgetTester tester) async {
      final _FakeViewerRepository repository = _FakeViewerRepository(
        viewState: buildBroadcastTestViewState(),
        bootstrapInitialViewState: buildBroadcastTestViewState(),
      );

      await tester.pumpWidget(_buildWidget(repository: repository));
      await tester.pumpAndSettle();

      expect(repository.loadViewStateCalls, 0);
      expect(find.text('Broadcast Package'), findsWidgets);
    },
  );

  testWidgets(
    'broadcast route degrades cleanly when optional buckets are absent',
    (WidgetTester tester) async {
      final MatchPresentationPackage reducedPackage = MatchPresentationPackage(
        matchLabel: 'Lagos Stars vs Abuja City',
        home: const MatchPresentationTeam(
          teamId: 'home',
          teamName: 'Lagos Stars',
          shortName: 'LAG',
          formation: '4-3-3',
          starters: <MatchPresentationPlayer>[
            MatchPresentationPlayer(
              playerId: 'home-1',
              playerName: 'Adebayo',
              shirtNumber: 1,
              role: 'goalkeeper',
              line: 'goalkeeper',
              x: 90,
              y: 50,
            ),
          ],
        ),
        away: const MatchPresentationTeam(
          teamId: 'away',
          teamName: 'Abuja City',
          shortName: 'ABJ',
          formation: '4-2-3-1',
          starters: <MatchPresentationPlayer>[
            MatchPresentationPlayer(
              playerId: 'away-1',
              playerName: 'Yusuf',
              shirtNumber: 1,
              role: 'goalkeeper',
              line: 'goalkeeper',
              x: 90,
              y: 50,
            ),
          ],
        ),
      );

      await tester.pumpWidget(
        _buildWidget(
          repository: _FakeViewerRepository(
            viewState: buildBroadcastTestViewState(
              presentationPackage: reducedPackage,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Broadcast Package'), findsWidgets);
      expect(find.byKey(const Key('storyline-panel')), findsNothing);
      expect(find.text('Standings snapshot'), findsNothing);
    },
  );

  testWidgets('broadcast route shows blocked state when bootstrap fails', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildWidget(
        repository: _FakeViewerRepository(
          error: GteApiException(
            type: GteApiErrorType.notFound,
            message: 'Match viewer payload for blocked-match was not found.',
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('BLOCKED'), findsWidgets);
  });
}

Widget _buildWidget({required LiveMatchViewerRepository repository}) {
  return ProviderScope(
    overrides: [
      liveMatchViewerRepositoryProvider.overrideWithValue(repository),
    ],
    child: const MaterialApp(
      home: Scaffold(body: MatchBroadcastScreen(matchKey: 'live-match-001')),
    ),
  );
}

class _FakeViewerRepository implements LiveMatchViewerRepository {
  _FakeViewerRepository({
    this.viewState,
    this.error,
    this.bootstrapInitialViewState,
  });

  final MatchViewState? viewState;
  final Object? error;
  final MatchViewState? bootstrapInitialViewState;
  int loadViewStateCalls = 0;

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    loadViewStateCalls += 1;
    if (error != null) {
      throw error!;
    }
    return viewState!;
  }

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    if (error != null) {
      throw error!;
    }
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: const <String, Object?>{'title': 'Broadcast route fixture'},
      initialViewState: bootstrapInitialViewState,
      competition: CompetitionSummary(
        id: matchKey,
        name: 'Broadcast Route Fixture',
        format: CompetitionFormat.league,
        visibility: CompetitionVisibility.public,
        status: CompetitionStatus.inProgress,
        creatorId: 'gtex',
        creatorName: 'GTEX',
        participantCount: 2,
        capacity: 2,
        currency: 'coin',
        entryFee: 0,
        platformFeePct: 0,
        hostFeePct: 0,
        platformFeeAmount: 0,
        hostFeeAmount: 0,
        prizePool: 0,
        payoutStructure: const <CompetitionPayoutBreakdown>[],
        rulesSummary: 'Broadcast route test fixture.',
        matchType: MatchType.gtexHosted,
        joinEligibility: const CompetitionJoinEligibility(eligible: false),
        beginnerFriendly: true,
        createdAt: DateTime.utc(2026, 1, 1),
        updatedAt: DateTime.utc(2026, 1, 1),
      ),
    );
  }
}
