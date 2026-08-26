import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_hub/presentation/club_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/clubs/gtex_club_owner_dashboard_screen_v2.dart';
import 'package:http/http.dart' as http;

void main() {
  test('new feature deep links round-trip through the parser', () {
    final List<GteAppRouteData> routes = <GteAppRouteData>[
      const StreamerTournamentsListRouteData(),
      const StreamerTournamentDetailRouteData(tournamentId: 'showcase-cup'),
      const FanPredictionMatchRouteData(matchId: 'match-1'),
      const PlayerCardsBrowseRouteData(),
      const PlayerCardDetailRouteData(playerId: 'player-9'),
      const PlayerCardsInventoryRouteData(),
      const CreatorShareMarketClubRouteData(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      ),
      const CreatorShareMarketAdminControlRouteData(),
      const ClubSaleMarketListingsRouteData(),
      const ClubSaleMarketDetailRouteData(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      ),
      const ClubSaleMarketOwnerOffersRouteData(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      ),
      const WorldOverviewRouteData(),
      const RegenUniverseRouteData(),
      const WorldAwardsRouteData(),
      const NewsDeskRouteData(),
      const FanWarsRouteData(),
      const WorldClubContextRouteData(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      ),
      const WorldCompetitionContextRouteData(competitionId: 'nations-cup'),
      const NationalTeamCompetitionsRouteData(),
      const NationalTeamEntryRouteData(entryId: 'entry-1'),
      const NationalTeamHistoryRouteData(),
      const FootballTransferCenterRouteData(tab: GteTransferCenterTab.calendar),
      const CreatorStadiumClubRouteData(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      ),
      const CreatorStadiumMatchRouteData(matchId: 'match-1'),
      const CreatorStadiumAdminControlRouteData(),
      const CreatorLeagueFinancialReportRouteData(seasonId: 'creator-season-1'),
      const CreatorLeagueSettlementsRouteData(seasonId: 'creator-season-1'),
      const GiftStabilizerRouteData(),
    ];

    for (final GteAppRouteData route in routes) {
      final GteAppRouteData? parsed = GteNavigationHelpers.parseDeepLink(
        route.toUri().toString(),
      );
      expect(parsed, isNotNull, reason: route.name);
      expect(parsed!.toUri().toString(), route.toUri().toString());
      expect(
        GteNavigationHelpers.requireNamedRoute(
          route.name,
          pathParameters: _pathParametersFor(route),
          queryParameters: route.toUri().queryParameters,
        ).toUri().toString(),
        route.toUri().toString(),
      );
    }
  });

  test('legacy deep links resolve into premium GTEX route data', () {
    final Map<String, Type> aliases = <String, Type>{
      '/market': PlayerCardsBrowseRouteData,
      '/market/transfers': FootballTransferCenterRouteData,
      '/world/regens': RegenUniverseRouteData,
      '/awards': WorldAwardsRouteData,
      '/world/awards': WorldAwardsRouteData,
      '/fan-wars': FanWarsRouteData,
      '/clips': NewsDeskRouteData,
      '/news': NewsDeskRouteData,
      '/competitions/hosted': CompetitionsDiscoveryRouteData,
      '/competitions/gtex': CompetitionsDiscoveryRouteData,
      '/competitions/hosted/comp-1': CompetitionDetailRouteData,
      '/competitions/gtex/comp-2': CompetitionDetailRouteData,
    };

    for (final MapEntry<String, Type> entry in aliases.entries) {
      final GteAppRouteData? parsed = GteNavigationHelpers.parseDeepLink(
        entry.key,
      );
      expect(parsed, isNotNull, reason: entry.key);
      expect(parsed.runtimeType, entry.value, reason: entry.key);
    }

    expect(
      (GteNavigationHelpers.parseDeepLink('/competitions/hosted')
              as CompetitionsDiscoveryRouteData)
          .highlight,
      'hosted',
    );
    expect(
      (GteNavigationHelpers.parseDeepLink('/competitions/gtex')
              as CompetitionsDiscoveryRouteData)
          .highlight,
      'gtex',
    );
    expect(
      (GteNavigationHelpers.parseDeepLink('/competitions/hosted/comp-1')
              as CompetitionDetailRouteData)
          .competitionId,
      'comp-1',
    );
  });

  testWidgets('guest users hit sign-in gating on protected routes', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(),
        route: const PlayerCardsInventoryRouteData(),
        label: 'Open route',
      ),
    );

    await tester.tap(find.text('Open route'));
    await tester.pumpAndSettle();

    expect(find.text('Sign in required'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });

  testWidgets('guest users hit admin gating on finance routes', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(),
        route: const CreatorLeagueFinancialReportRouteData(
          seasonId: 'creator-season-1',
        ),
        label: 'Open finance',
      ),
    );

    await tester.tap(find.text('Open finance'));
    await tester.pumpAndSettle();

    expect(find.text('Admin sign-in required'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });

  testWidgets('fan prediction placeholder routes stay explicitly guarded', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(isAuthenticated: true),
        route: const FanPredictionMatchRouteData(matchId: 'featured'),
        label: 'Open prediction',
      ),
    );

    await tester.tap(find.text('Open prediction'));
    await tester.pumpAndSettle();

    expect(find.text('Canonical match id required'), findsOneWidget);
    expect(find.text('Resolve match id'), findsOneWidget);
  });

  testWidgets('owner offer inbox surfaces counter actions in fixture mode', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(isAuthenticated: true),
        route: const ClubSaleMarketOwnerOffersRouteData(
          clubId: 'royal-lagos-fc',
          clubName: 'Royal Lagos FC',
        ),
        label: 'Open inbox',
      ),
    );

    await tester.tap(find.text('Open inbox'));
    await tester.pumpAndSettle();

    expect(find.text('Counter'), findsOneWidget);
    expect(find.text('Accept'), findsOneWidget);
    expect(find.text('Reject'), findsOneWidget);
  });

  testWidgets('creator-share admin control mounts live admin surface', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(
          isAuthenticated: true,
          isAdmin: true,
          clubId: null,
          clubName: null,
        ),
        route: const CreatorShareMarketAdminControlRouteData(),
        label: 'Open control',
      ),
    );

    await tester.tap(find.text('Open control'));
    await _pumpUntilText(tester, 'Creator share control');

    expect(find.text('Creator share control'), findsOneWidget);
    expect(find.text('Club selection required'), findsNothing);
  });

  testWidgets(
    'navigation shell uses the canonical session club instead of the royal lagos fallback',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );
      controller.openOrderTotal = 1;

      await tester.pumpWidget(
        MaterialApp(
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.club(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final GtexClubOwnerDashboardScreenV2 clubHub = tester
          .widget<GtexClubOwnerDashboardScreenV2>(
            find.byType(GtexClubOwnerDashboardScreenV2),
          );
      expect(clubHub.clubId, 'ibadan-lions');
      expect(clubHub.clubName, 'Ibadan Lions FC');
    },
  );

  testWidgets(
    'authenticated no-club session reaches shared onboarding in Home and opens club market',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-no-club',
        userName: 'No Club Owner',
        clubId: null,
        clubName: null,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.home(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Build your club command center'), findsOneWidget);
      expect(find.text('Create club'), findsWidgets);
      expect(find.text('Transfer Hub'), findsWidgets);
      expect(find.text('No canonical club is selected'), findsNothing);
      expect(find.text('Create or join a club to unlock Home'), findsNothing);
      expect(
        find.widgetWithText(FilledButton, 'Create Club unavailable'),
        findsNothing,
      );
      expect(
        find.widgetWithText(FilledButton, 'Join Club unavailable'),
        findsNothing,
      );

      final Finder browseClubMarketButton = find.text('Transfer Hub').first;
      expect(browseClubMarketButton, findsOneWidget);

      await _scrollUntilVisible(
        tester,
        browseClubMarketButton,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(browseClubMarketButton);
      await _pumpUntilText(tester, 'Transfer Hub');
      await tester.pumpAndSettle();

      expect(find.text('Transfer Hub'), findsWidgets);
    },
  );

  testWidgets('home expansion lanes open deep-link routes', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      _screenHost(
        dependencies: _dependencies(
          clubId: 'ibadan-lions',
          clubName: 'Ibadan Lions FC',
        ),
        home: HomeDashboardScreen(
          exchangeController: controller,
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          clubId: 'ibadan-lions',
          clubName: 'Ibadan Lions FC',
          navigationDependencies: _dependencies(
            clubId: 'ibadan-lions',
            clubName: 'Ibadan Lions FC',
          ),
        ),
      ),
    );
    await _pumpUntilText(tester, 'Expansion lanes');

    expect(find.text('Expansion lanes'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
    final Finder fanPredictionsButton = find.widgetWithText(
      FilledButton,
      'Fan predictions (live match only)',
    );
    expect(tester.widget<FilledButton>(fanPredictionsButton).onPressed, isNull);
    expect(
      find.text(
        'Fan predictions unlock from live-match routes after a canonical match id is present.',
      ),
      findsOneWidget,
    );

    final Finder playerCardsButton = find.text('Player cards');
    await tester.ensureVisible(playerCardsButton);
    await tester.tap(playerCardsButton);
    await _pumpUntilText(tester, 'Transfer desk');

    expect(find.text('Transfer desk'), findsWidgets);
  });

  testWidgets(
    'home dashboard shows shared no-club onboarding with working arena path',
    (WidgetTester tester) async {
      final _CountingExchangeApiClient api =
          _CountingExchangeApiClient.fixture();
      final GteExchangeController controller = GteExchangeController(api: api);
      controller.session = _authenticatedSession(
        userId: 'user-no-club',
        userName: 'No Club Owner',
        clubId: null,
        clubName: null,
      );
      final _HttpRequestProbe probe = _HttpRequestProbe();
      int openClubTabCount = 0;
      int openCompetitionsCount = 0;
      final GteHttpClientFactory previousClientFactory =
          GteHttpTransport.clientFactory;

      GteHttpTransport.clientFactory = () => _ProbeHttpClient(probe);
      addTearDown(() {
        GteHttpTransport.clientFactory = previousClientFactory;
      });

      await tester.pumpWidget(
        MaterialApp(
          home: HomeDashboardScreen(
            exchangeController: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.live,
            onOpenClubTab: () {
              openClubTabCount += 1;
            },
            onOpenCompetitionsTab: () {
              openCompetitionsCount += 1;
            },
            navigationDependencies: _dependencies(
              isAuthenticated: true,
              clubId: null,
              clubName: null,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CLUB SETUP'), findsOneWidget);
      expect(find.text('This account has no club yet'), findsOneWidget);
      final Finder browseClubMarketButton =
          find.widgetWithText(FilledButton, 'Browse club market').first;
      final Finder exploreCompetitionsButton =
          find.widgetWithText(OutlinedButton, 'Explore competitions').first;

      expect(find.text('Create Club unavailable'), findsNothing);
      expect(find.text('Join Club unavailable'), findsNothing);
      expect(find.text('Create or join a club to unlock Home'), findsNothing);
      expect(find.text('Browse club market'), findsWidgets);
      expect(find.text('Explore competitions'), findsWidgets);
      expect(find.text('No canonical club is selected'), findsNothing);
      expect(
        find.text(
          'Home requires a canonical club context before club-scoped surfaces can load.',
        ),
        findsNothing,
      );
      expect(
        tester.widget<FilledButton>(browseClubMarketButton).onPressed,
        isNotNull,
      );
      expect(
        tester.widget<OutlinedButton>(exploreCompetitionsButton).onPressed,
        isNotNull,
      );

      await tester.ensureVisible(exploreCompetitionsButton);
      await tester.pumpAndSettle();
      await tester.tap(exploreCompetitionsButton);
      await tester.pumpAndSettle();

      expect(openClubTabCount, 0);
      expect(openCompetitionsCount, 1);
      expect(probe.sendCount, 0);
      expect(api.listOrdersCount, 0);
    },
  );

  testWidgets(
    'authenticated no-club Club tab shows shared onboarding and opens club market',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'clubless-shell-user',
        userName: 'Clubless Shell User',
        clubId: null,
        clubName: null,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.club(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Build your club command center'), findsOneWidget);
      expect(find.text('Create club'), findsWidgets);
      expect(find.text('Open home'), findsNothing);
      expect(find.text('No canonical club is selected'), findsNothing);

      final Finder browseClubMarketButton = find.text('Transfer Hub').first;
      expect(browseClubMarketButton, findsOneWidget);

      await _scrollUntilVisible(
        tester,
        browseClubMarketButton,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(browseClubMarketButton);
      await _pumpUntilText(tester, 'Transfer Hub');
      await tester.pumpAndSettle();

      expect(find.text('Transfer Hub'), findsWidgets);
    },
  );

  testWidgets('arena quick links expose launch routes and hide streamer engine', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'user-1',
      currentUserName: 'Tester',
    );
    await controller.bootstrap();

    await tester.pumpWidget(
      _screenHost(
        dependencies: _dependencies(),
        home: GteCompetitionsHubScreen(
          controller: controller,
          currentDestination: CompetitionHubDestination.overview,
          onDestinationChanged: (_) {},
          navigationDependencies: _dependencies(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await _scrollUntilVisible(
      tester,
      find.text('Competition routes'),
      scrollable: find.byType(ListView).first,
    );

    expect(find.text('Competition routes'), findsWidgets);
    final Finder fanPredictionsButton = find.widgetWithText(
      FilledButton,
      'Fan predictions (live match only)',
    );
    expect(tester.widget<FilledButton>(fanPredictionsButton).onPressed, isNull);
    expect(
      find.text(
        'Fan predictions stay disabled here until a live-match route supplies the canonical match id.',
      ),
      findsOneWidget,
    );
    expect(find.text('Streamer tournaments'), findsNothing);
    expect(find.text('Streamer tournament engine'), findsNothing);
  });

  testWidgets('club hub quick links open world context routes', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _screenHost(
        dependencies: _dependencies(
          isAuthenticated: true,
          clubId: 'royal-lagos-fc',
          clubName: 'Royal Lagos FC',
        ),
        home: ClubHubScreen(
          clubId: 'royal-lagos-fc',
          clubName: 'Royal Lagos FC',
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          isAuthenticated: true,
          navigationDependencies: _dependencies(
            isAuthenticated: true,
            clubId: 'royal-lagos-fc',
            clubName: 'Royal Lagos FC',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final Finder worldContextButton = find.widgetWithText(
      FilledButton,
      'World context',
    );
    await _scrollUntilVisible(
      tester,
      worldContextButton,
      scrollable: find.byType(ListView).first,
    );
    await tester.ensureVisible(worldContextButton);
    await tester.tap(worldContextButton);
    await _pumpUntilFound(tester, find.textContaining('public view'));

    expect(find.textContaining('public view'), findsOneWidget);
  });

  testWidgets('club hub demotes owner inbox when owner workspace is unknown', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: ClubHubScreen(
          clubId: 'royal-lagos-fc',
          clubName: 'Royal Lagos FC',
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          isAuthenticated: true,
          navigationDependencies: _dependencies(
            isAuthenticated: true,
            clubId: 'ibadan-lions',
            clubName: 'Ibadan Lions FC',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final Finder ownerInboxButton = find.widgetWithText(
      FilledButton,
      'Owner offer inbox',
    );
    await _scrollUntilVisible(
      tester,
      ownerInboxButton,
      scrollable: find.byType(ListView).first,
    );
    expect(tester.widget<FilledButton>(ownerInboxButton).onPressed, isNull);
    expect(
      find.text(
        'Switch into this club owner workspace before opening owner offer review.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('gift stabilizer route mounts for admin sessions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _RouteLauncherHost(
        dependencies: _dependencies(
          isAuthenticated: true,
          isAdmin: true,
          clubId: null,
          clubName: null,
        ),
        route: const GiftStabilizerRouteData(),
        label: 'Open gift stabilizer',
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Open gift stabilizer'));
    await _pumpUntilText(tester, 'Gift economy stabilizer');

    expect(find.text('Gift economy stabilizer'), findsOneWidget);
  });
}

Map<String, String> _pathParametersFor(GteAppRouteData route) {
  if (route is StreamerTournamentDetailRouteData) {
    return <String, String>{'tournamentId': route.tournamentId};
  }
  if (route is FanPredictionMatchRouteData) {
    return <String, String>{'matchId': route.matchId};
  }
  if (route is PlayerCardDetailRouteData) {
    return <String, String>{'playerId': route.playerId};
  }
  if (route is GteClubScopedRouteData) {
    return <String, String>{'clubId': route.clubId};
  }
  if (route is WorldCompetitionContextRouteData) {
    return <String, String>{'competitionId': route.competitionId};
  }
  if (route is NationalTeamEntryRouteData) {
    return <String, String>{'entryId': route.entryId};
  }
  if (route is CreatorStadiumMatchRouteData) {
    return <String, String>{'matchId': route.matchId};
  }
  return const <String, String>{};
}

GteNavigationDependencies _dependencies({
  bool isAuthenticated = false,
  bool isAdmin = false,
  String? clubId = 'royal-lagos-fc',
  String? clubName = 'Royal Lagos FC',
}) {
  return GteNavigationDependencies(
    apiBaseUrl: 'http://127.0.0.1:8000',
    backendMode: GteBackendMode.fixture,
    currentUserId: 'user-1',
    currentUserName: 'Tester',
    currentUserRole: isAdmin ? 'admin' : 'user',
    currentClubId: clubId,
    currentClubName: clubName,
    accessToken: isAuthenticated || isAdmin ? 'token-123' : null,
    isAuthenticated: isAuthenticated || isAdmin,
    onOpenLogin: (_) async => true,
  );
}

/// Hosts [home] inside the central GoRouter runtime that
/// [GteNavigationHelpers.pushRoute] requires. The legacy material-route
/// fallback is disabled in strict live mode, so a bare `MaterialApp` host makes
/// every push fail with a StateError before the target screen can mount. Any
/// GTEX route pushed from [home] resolves through the same registry the
/// production router uses.
Widget _screenHost({
  required Widget home,
  required GteNavigationDependencies dependencies,
}) {
  final GoRouter router = GoRouter(
    initialLocation: '/',
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        builder: (BuildContext context, GoRouterState state) => home,
      ),
      GoRoute(
        path: '/:rest(.*)',
        builder: (BuildContext context, GoRouterState state) {
          final GteAppRouteData? route = GteNavigationHelpers.parseDeepLink(
            state.uri.toString(),
          );
          if (route == null) {
            return const Scaffold(
              body: Center(child: Text('Route unavailable')),
            );
          }
          return GteAppRouteRegistry(
            dependencies: dependencies,
          ).guardedScreenFor(route);
        },
      ),
    ],
  );
  return MaterialApp.router(routerConfig: router);
}

class _RouteLauncherHost extends StatelessWidget {
  const _RouteLauncherHost({
    required this.dependencies,
    required this.route,
    required this.label,
  });

  final GteNavigationDependencies dependencies;
  final GteAppRouteData route;
  final String label;

  @override
  Widget build(BuildContext context) {
    // GteNavigationHelpers.pushRoute requires the central GoRouter runtime;
    // the legacy material-route fallback is disabled in strict live mode, so a
    // plain MaterialApp host would make every push fail with a StateError.
    // Mirror production by serving the route under test through GoRouter,
    // delegating to the same registry the real router uses.
    final GoRouter router = GoRouter(
      initialLocation: '/',
      routes: <RouteBase>[
        GoRoute(
          path: '/',
          builder:
              (BuildContext context, GoRouterState state) => Scaffold(
                body: Center(
                  child: Builder(
                    builder: (BuildContext context) {
                      return FilledButton(
                        onPressed:
                            () => GteNavigationHelpers.pushRoute<void>(
                              context,
                              route: route,
                              dependencies: dependencies,
                            ),
                        child: Text(label),
                      );
                    },
                  ),
                ),
              ),
        ),
        GoRoute(
          path: route.toUri().path,
          builder:
              (BuildContext context, GoRouterState state) =>
                  GteAppRouteRegistry(
                    dependencies: dependencies,
                  ).guardedScreenFor(route),
        ),
      ],
    );
    return MaterialApp.router(routerConfig: router);
  }
}

Future<void> _pumpUntilText(
  WidgetTester tester,
  String text, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 120,
}) async {
  final Finder finder = find.text(text);
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  expect(finder, findsOneWidget);
}

Future<void> _pumpUntilFound(
  WidgetTester tester,
  Finder finder, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 120,
}) async {
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  expect(finder, findsOneWidget);
}

Future<void> _scrollUntilVisible(
  WidgetTester tester,
  Finder finder, {
  required Finder scrollable,
  Offset moveStep = const Offset(0, -300),
  int maxIteration = 20,
}) async {
  if (finder.evaluate().isEmpty) {
    await tester.dragUntilVisible(
      finder,
      scrollable,
      moveStep,
      maxIteration: maxIteration,
    );
  } else {
    await tester.ensureVisible(finder);
  }
  await tester.pump();
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    if (clubName != null) 'current_club_name': clubName,
    'user': <String, Object?>{
      'id': userId,
      'email': '$userId@gtex.test',
      'username': userId,
      'display_name': userName,
      'role': 'user',
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
    },
  });
}

class _CountingExchangeApiClient extends GteExchangeApiClient {
  _CountingExchangeApiClient._(this._delegate)
    : super(
        config: _delegate.config,
        transport: _delegate.transport,
        repository: _delegate.repository,
      );

  factory _CountingExchangeApiClient.fixture() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _CountingExchangeApiClient._(delegate);
  }

  final GteExchangeApiClient _delegate;
  int listOrdersCount = 0;

  @override
  Future<GteOrderListView> listOrders({
    int limit = 20,
    int offset = 0,
    List<GteOrderStatus>? statuses,
  }) {
    listOrdersCount += 1;
    return _delegate.listOrders(
      limit: limit,
      offset: offset,
      statuses: statuses,
    );
  }
}

class _HttpRequestProbe {
  int sendCount = 0;
}

class _ProbeHttpClient extends http.BaseClient {
  _ProbeHttpClient(this._probe);

  final _HttpRequestProbe _probe;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    _probe.sendCount += 1;
    return http.StreamedResponse(
      Stream<List<int>>.fromIterable(<List<int>>[utf8.encode('{}')]),
      200,
      headers: const <String, String>{'content-type': 'application/json'},
    );
  }
}
