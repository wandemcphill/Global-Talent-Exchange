import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
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
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';

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
      final GteAppRouteData? parsed =
          GteNavigationHelpers.parseDeepLink(route.toUri().toString());
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

  testWidgets('guest users hit sign-in gating on protected routes',
      (WidgetTester tester) async {
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

  testWidgets('guest users hit admin gating on finance routes',
      (WidgetTester tester) async {
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

  testWidgets('fan prediction placeholder routes stay explicitly guarded',
      (WidgetTester tester) async {
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

  testWidgets('owner offer inbox surfaces counter actions in fixture mode',
      (WidgetTester tester) async {
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

  testWidgets('creator-share admin control opens the admin control surface',
      (WidgetTester tester) async {
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
    await _pumpUntilText(tester, 'Creator share market control');

    expect(find.text('Creator share market control'), findsOneWidget);
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

    final ClubHubScreen clubHub =
        tester.widget<ClubHubScreen>(find.byType(ClubHubScreen));
    expect(clubHub.clubId, 'ibadan-lions');
    expect(clubHub.clubName, 'Ibadan Lions FC');
  });

  testWidgets('home expansion lanes open deep-link routes',
      (WidgetTester tester) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
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

    final Finder playerCardsButton = find.text('Player cards');
    await tester.ensureVisible(playerCardsButton);
    await tester.tap(playerCardsButton);
    await _pumpUntilText(tester, 'Player-card marketplace');

    expect(find.text('Player-card marketplace'), findsOneWidget);
  });

  testWidgets(
      'home dashboard shows guided onboarding and stays offline without a canonical club',
      (WidgetTester tester) async {
    final _CountingExchangeApiClient api = _CountingExchangeApiClient.fixture();
    final GteExchangeController controller = GteExchangeController(
      api: api,
    );
    controller.session = _authenticatedSession(
      userId: 'user-no-club',
      userName: 'No Club Owner',
      clubId: null,
      clubName: null,
    );
    final _HttpRequestProbe probe = _HttpRequestProbe();

    await HttpOverrides.runZoned<Future<void>>(
      () async {
        await tester.pumpWidget(
          MaterialApp(
            home: HomeDashboardScreen(
              exchangeController: controller,
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.live,
              onOpenClubTab: () {},
              onOpenCompetitionsTab: () {},
              navigationDependencies: _dependencies(
                isAuthenticated: true,
                clubId: null,
                clubName: null,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
      },
      createHttpClient: (SecurityContext? _) => _ProbeHttpClient(probe),
    );

    expect(find.text('Create or join a club to unlock Home'), findsOneWidget);
    expect(find.text('Create Club'), findsWidgets);
    expect(find.text('Join Club'), findsWidgets);
    expect(find.text('Explore Arena'), findsWidgets);
    expect(find.text('No canonical club is selected'), findsNothing);
    expect(
      find.text(
        'Home requires a canonical club context before club-scoped surfaces can load.',
      ),
      findsNothing,
    );
    expect(probe.openUrlCount, 0);
    expect(api.listOrdersCount, 0);
  });

  testWidgets('market quick links open public club sale listings',
      (WidgetTester tester) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
          navigationDependencies: _dependencies(
            clubId: 'royal-lagos-fc',
            clubName: 'Royal Lagos FC',
          ),
        ),
      ),
    );
    await _pumpUntilText(tester, 'Market extensions');

    expect(find.text('Market extensions'), findsOneWidget);

    final Finder clubSaleMarketButton = find.text('Club sale market');
    await tester.ensureVisible(clubSaleMarketButton);
    await tester.tap(clubSaleMarketButton);
    await _pumpUntilText(tester, 'Refresh market');

    expect(find.text('Refresh market'), findsOneWidget);
    expect(find.text('Open club market'), findsOneWidget);
  });

  testWidgets('market creator-share shortcut requires a canonical club id',
      (WidgetTester tester) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
          navigationDependencies: _dependencies(
            clubId: null,
            clubName: null,
          ),
        ),
      ),
    );
    await _pumpUntilText(tester, 'Market extensions');

    final Finder creatorSharesButton = find.text('Creator shares');
    await tester.ensureVisible(creatorSharesButton);
    await tester.tap(creatorSharesButton);
    await _pumpUntilText(tester, 'Club selection required');

    expect(find.text('Club selection required'), findsOneWidget);
    expect(
      find.textContaining('Creator-share market routes are club-scoped'),
      findsOneWidget,
    );
  });

  testWidgets(
      'market creator-share shortcut opens when a canonical club is derivable',
      (WidgetTester tester) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
          navigationDependencies: _dependencies(
            isAuthenticated: true,
            clubId: 'ibadan-lions',
            clubName: 'Ibadan Lions FC',
          ),
        ),
      ),
    );
    await _pumpUntilText(tester, 'Market extensions');

    final Finder creatorSharesButton = find.text('Creator shares');
    await tester.ensureVisible(creatorSharesButton);
    await tester.tap(creatorSharesButton);
    await _pumpUntilText(tester, 'Ibadan Lions FC creator shares');

    expect(find.text('Ibadan Lions FC creator shares'), findsOneWidget);
    expect(find.text('Club selection required'), findsNothing);
  });

  testWidgets('arena quick links open tournament routes',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'user-1',
      currentUserName: 'Tester',
    );
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
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
      find.text('Arena extensions'),
      scrollable: find.byType(ListView).first,
    );

    expect(find.text('Arena extensions'), findsOneWidget);

    final Finder streamerTournamentsButton = find.text('Streamer tournaments');
    await tester.ensureVisible(streamerTournamentsButton);
    await tester.tap(streamerTournamentsButton);
    await _pumpUntilText(tester, 'Streamer tournament engine');

    expect(find.text('Streamer tournament engine'), findsOneWidget);
  });

  testWidgets('club hub quick links open world context routes',
      (WidgetTester tester) async {
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
            clubId: 'royal-lagos-fc',
            clubName: 'Royal Lagos FC',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await _scrollUntilVisible(
      tester,
      find.text('Club extensions'),
      scrollable: find.byType(ListView).first,
    );

    expect(find.text('Club extensions'), findsOneWidget);

    final Finder worldContextButton = find.text('World context');
    await tester.ensureVisible(worldContextButton);
    await tester.tap(worldContextButton);
    await _pumpUntilFound(
      tester,
      find.textContaining('canonical football-world simulation'),
    );

    expect(
      find.textContaining('canonical football-world simulation'),
      findsOneWidget,
    );
  });

  testWidgets('admin command center opens gift stabilizer route',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AdminCommandCenterScreen(
          baseUrl: 'http://127.0.0.1:8000',
          accessToken: 'admin-token',
          backendMode: GteBackendMode.fixture,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Command routes'), findsOneWidget);

    await tester.tap(find.text('Gift stabilizer'));
    await tester.pumpAndSettle();

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
    return MaterialApp(
      home: Scaffold(
        body: Center(
          child: Builder(
            builder: (BuildContext context) {
              return FilledButton(
                onPressed: () => GteNavigationHelpers.pushRoute<void>(
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
    );
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
  return GteAuthSession.fromJson(
    <String, Object?>{
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
    },
  );
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
  int openUrlCount = 0;
}

class _ProbeHttpClient implements HttpClient {
  _ProbeHttpClient(this._probe);

  final _HttpRequestProbe _probe;

  @override
  Duration? connectionTimeout;

  @override
  void close({bool force = false}) {}

  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) async {
    _probe.openUrlCount += 1;
    return _ProbeHttpRequest();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ProbeHttpRequest implements HttpClientRequest {
  @override
  final HttpHeaders headers = _ProbeHttpHeaders();

  @override
  Future<HttpClientResponse> close() async => _ProbeHttpResponse();

  @override
  void write(Object? object) {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ProbeHttpResponse extends Stream<List<int>>
    implements HttpClientResponse {
  final Stream<List<int>> _delegate = Stream<List<int>>.fromIterable(
    <List<int>>[utf8.encode('{}')],
  );

  @override
  HttpHeaders get headers => _ProbeHttpHeaders();

  @override
  int get statusCode => 200;

  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int> event)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) {
    return _delegate.listen(
      onData,
      onError: onError,
      onDone: onDone,
      cancelOnError: cancelOnError,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ProbeHttpHeaders implements HttpHeaders {
  @override
  void add(String name, Object value, {bool preserveHeaderCase = false}) {}

  @override
  void forEach(void Function(String name, List<String> values) action) {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
