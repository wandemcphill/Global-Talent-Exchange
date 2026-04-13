import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/match/match_native_3d_blocked_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/features/world/world_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  test('primary nav excludes placeholder routes and records live routes', () {
    final Set<String> primaryLocations =
        appDestinations
            .map((AppDestination destination) => destination.location)
            .toSet();

    expect(primaryLocations, contains(AppRoutes.world));
    expect(primaryLocations, isNot(contains(AppRoutes.matchesNativeThreeD)));
    expect(
      appRouteSurfaceFor(AppRoutes.world)?.state,
      AppRouteSurfaceState.live,
    );
    expect(
      appRouteSurfaceFor(AppRoutes.matchesNativeThreeD)?.state,
      AppRouteSurfaceState.placeholder,
    );
    expect(
      appRouteSurfaceFor(AppRoutes.matchesSimulate)?.state,
      AppRouteSurfaceState.hidden,
    );
    expect(appRouteSurfaceFor('/profile/admin/god-mode'), isNull);
  });

  test('quick-action inventory excludes placeholder and hidden routes', () {
    final Set<String> quickActionLocations =
        appRouteInventory
            .where((AppRouteSurface surface) => surface.showInQuickActions)
            .map((AppRouteSurface surface) => surface.location)
            .toSet();

    expect(quickActionLocations, contains(AppRoutes.world));
    expect(
      quickActionLocations,
      isNot(contains(AppRoutes.matchesNativeThreeD)),
    );
    expect(quickActionLocations, isNot(contains(AppRoutes.matchesSimulate)));
  });

  test('all visible route surfaces stay live', () {
    final Iterable<AppRouteSurface> visibleSurfaces = appRouteInventory.where(
      (AppRouteSurface surface) =>
          surface.showInPrimaryNav || surface.showInQuickActions,
    );

    expect(visibleSurfaces, isNotEmpty);
    for (final AppRouteSurface surface in visibleSurfaces) {
      expect(
        surface.state,
        AppRouteSurfaceState.live,
        reason:
            'Visible route surface ${surface.label} (${surface.location}) '
            'must stay live.',
      );
    }
  });

  test(
    'Flutter 3D inventory stays truthful about gating and rendering mode',
    () {
      final AppRouteSurface? threeD = appRouteSurfaceFor(
        AppRoutes.matchesThreeD,
      );

      expect(threeD, isNotNull);
      expect(threeD!.summary, contains('Flutter-rendered'));
      expect(threeD.summary, contains('entitlement'));
      expect(threeD.summary.toLowerCase(), isNot(contains('native 3d')));
    },
  );

  test(
    'simulation inventory stays fixture-gated instead of live-shell visible',
    () {
      final AppRouteSurface? simulation = appRouteSurfaceFor(
        AppRoutes.matchesSimulate,
      );

      expect(simulation, isNotNull);
      expect(simulation!.state, AppRouteSurfaceState.hidden);
      expect(simulation.summary, contains('fixture-mode'));
      expect(simulation.summary.toLowerCase(), contains('blocked'));
    },
  );

  testWidgets('home quick actions surface live world routing honestly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_surfaceHost(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('World'), findsOneWidget);
    expect(find.text('World Preview'), findsNothing);
    expect(find.text('Matches'), findsOneWidget);
    expect(find.text('Competitions'), findsOneWidget);
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
    expect(find.text('World route'), findsOneWidget);
  });

  testWidgets('native 3D route is labeled as coming soon', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MatchNative3dBlockedScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Coming soon'), findsWidgets);
    expect(find.text('Native 3D is coming soon'), findsOneWidget);
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
