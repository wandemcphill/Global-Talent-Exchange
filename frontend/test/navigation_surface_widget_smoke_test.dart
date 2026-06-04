import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/compete/domain/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/compete/providers/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/match_center/blocked_match_runtime_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/features/world/world_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets('home quick actions surface live world routing honestly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_surfaceHost(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('World'), findsOneWidget);
    expect(find.text('World Preview'), findsNothing);
    expect(find.text('Matchday'), findsOneWidget);
    expect(find.text('Arena'), findsOneWidget);
  });

  testWidgets('world route presents live route truth without preview badges', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(_surfaceHost(const WorldScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Preview'), findsNothing);
    expect(find.text('World desk'), findsOneWidget);
  });

  testWidgets('blocked match runtime route stays hidden and blocked', (
    WidgetTester tester,
  ) async {
    final AppRouteSurface? nativeRuntime = appRouteSurfaceFor(
      AppRoutes.legacyBlockedMatchRuntime,
    );

    expect(nativeRuntime, isNotNull);
    expect(nativeRuntime!.state, AppRouteSurfaceState.hidden);
    expect(nativeRuntime.label, 'Coming soon');
    expect(nativeRuntime.summary, contains('quarantined'));

    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: BlockedMatchRuntimeScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Route blocked'), findsWidgets);
    expect(find.textContaining('2D match viewer'), findsWidgets);
  });
}

Widget _surfaceHost(Widget child) {
  const CompetitionHubData emptyHub = CompetitionHubData(
    gtexCompetitions: <CompetitionSummary>[],
    hostedCompetitions: <HostedCompetition>[],
    streamerTournaments: <StreamerTournament>[],
  );

  return ProviderScope(
    overrides: [
      appConfigProvider.overrideWithValue(_testAppConfig),
      profileDataProvider.overrideWith(
        (Ref ref) async => const ProfileData.unauthenticated(),
      ),
      competitionHubProvider.overrideWith((Ref ref) async => emptyHub),
      marketDashboardProvider.overrideWith((Ref ref) async {
        return const MarketDashboardData(
          playerShares: <PlayerShareSummary>[],
          holdings: <PlayerShareHoldingSummary>[],
          transferListings: <TransferListingSummary>[],
          wallet: null,
          authenticated: false,
          warnings: <String>[],
        );
      }),
      worldAggregateProvider.overrideWith((Ref ref) async {
        return const WorldAggregateData(
          risingStars: <Map<String, Object?>>[
            <String, Object?>{'player_name': 'Ada Prospect', 'position': 'CM'},
          ],
          scoutingFeed: <Map<String, Object?>>[
            <String, Object?>{
              'headline': 'Ada Prospect scouted',
              'club': 'GTEX',
            },
          ],
          seasons: <Map<String, Object?>>[
            <String, Object?>{'name': '2030'},
          ],
          awards: <Map<String, Object?>>[
            <String, Object?>{'name': 'Golden Boot'},
          ],
          hallOfFame: <Map<String, Object?>>[
            <String, Object?>{'name': 'Legacy Star'},
          ],
          federations: <Map<String, Object?>>[
            <String, Object?>{'name': 'West Africa Federation', 'id': 'waf'},
          ],
          tracking: <String, Object?>{'season_phase': 'live'},
          competitions: emptyHub,
          federationJoinReason:
              'Federation membership creation requires a live club-backed action flow and remains disabled from the summary tab.',
        );
      }),
      liveTasksProvider.overrideWith((Ref ref) async {
        return const LiveTasksData(
          authenticated: false,
          featureEnabled: true,
          challenges: <DailyChallengeSummary>[],
          claimsToday: <DailyChallengeClaimSummary>[],
          currentStreak: 0,
          longestStreak: 0,
          nextBonusAmount: 0,
        );
      }),
    ],
    child: MaterialApp(home: Scaffold(body: child)),
  );
}

const GteAppConfig _testAppConfig = GteAppConfig(
  apiBaseUrl: 'https://example.test',
  backendMode: GteBackendMode.live,
);
