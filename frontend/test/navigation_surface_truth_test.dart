import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
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

    expect(primaryLocations, isNot(contains(AppRoutes.world)));
    expect(primaryLocations, isNot(contains(AppRoutes.matchesNativeThreeD)));
    expect(
      appRouteSurfaceFor(AppRoutes.world)?.state,
      AppRouteSurfaceState.live,
    );
    expect(
      appRouteSurfaceFor(AppRoutes.matchesNativeThreeD)?.state,
      AppRouteSurfaceState.hidden,
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

  test('3D inventory stays hidden while Unity is blocked', () {
    final AppRouteSurface? threeD = appRouteSurfaceFor(AppRoutes.matchesThreeD);

    expect(threeD, isNotNull);
    expect(threeD!.state, AppRouteSurfaceState.hidden);
    expect(threeD.label, '3D Match Redirect');
    expect(threeD.summary, contains('redirects to the 2D viewer'));
  });

  test('simulation inventory redirects to Matchday', () {
    final AppRouteSurface? simulation = appRouteSurfaceFor(
      AppRoutes.matchesSimulate,
    );

    expect(simulation, isNotNull);
    expect(simulation!.state, AppRouteSurfaceState.hidden);
    expect(simulation.summary, contains('redirects to the active Matchday'));
  });

  testWidgets('home quick actions surface live world routing honestly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_surfaceHost(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('WORLD PULSE RAIL'), findsOneWidget);
    expect(find.text('World Preview'), findsNothing);
    expect(find.text('Watch matchday'), findsOneWidget);
    expect(find.text('Read transfer hub'), findsOneWidget);
  });

  testWidgets('home dashboard copy reflects an admin bootstrap role', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _surfaceHost(
        const HomeScreen(),
        profileData: const ProfileData(
          authenticated: true,
          user: <String, Object?>{
            'display_name': 'Ops Lead',
            'role': 'admin',
            'permissions': <String>['manage_payment_rails'],
          },
          affinityProfile: <String, Object?>{},
          club: null,
          followers: 0,
          following: 0,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('ADMIN DESK'), findsOneWidget);
    expect(
      find.text('CONTROL THE LIVE FOOTBALL ECONOMY SAFELY'),
      findsOneWidget,
    );
    expect(find.text('PAYMENTS'), findsOneWidget);
  });

  testWidgets('home dashboard copy keeps coin trader identity distinct', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _surfaceHost(
        const HomeScreen(),
        profileData: const ProfileData(
          authenticated: true,
          user: <String, Object?>{
            'display_name': 'Liquidity Desk',
            'role': 'coin-trader',
            'permissions': <String>['manage_coin_trader_rates'],
          },
          affinityProfile: <String, Object?>{},
          club: null,
          followers: 0,
          following: 0,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('TRADER DESK'), findsOneWidget);
    expect(find.text('MAKE THE COIN MARKET FEEL ONLINE'), findsOneWidget);
    expect(find.text('GTC'), findsOneWidget);
    expect(find.text('FNC'), findsOneWidget);
  });

  testWidgets('native 3D route inventory is hidden while Unity is blocked', (
    WidgetTester tester,
  ) async {
    final AppRouteSurface? nativeThreeD = appRouteSurfaceFor(
      AppRoutes.matchesNativeThreeD,
    );

    expect(nativeThreeD, isNotNull);
    expect(nativeThreeD!.state, AppRouteSurfaceState.hidden);
    expect(nativeThreeD.label, 'Native 3D Redirect');
    expect(nativeThreeD.summary, contains('redirects to Matchday'));
  });
}

Widget _surfaceHost(
  Widget child, {
  ProfileData profileData = const ProfileData.unauthenticated(),
}) {
  const CompetitionHubData emptyHub = CompetitionHubData(
    gtexCompetitions: <CompetitionSummary>[],
    hostedCompetitions: <HostedCompetition>[],
    streamerTournaments: <StreamerTournament>[],
  );

  return ProviderScope(
    overrides: [
      appConfigProvider.overrideWithValue(_testAppConfig),
      isAuthenticatedProvider.overrideWith(
        (Ref ref) => profileData.authenticated,
      ),
      profileDataProvider.overrideWith((Ref ref) async => profileData),
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
