import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/hosted_competition_api.dart';
import 'package:gte_frontend/features/competitions/live_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/federations/federations_hub_screen.dart';
import 'package:gte_frontend/features/federations/live_federations_provider.dart';
import 'package:gte_frontend/features/match/live_match_overview_provider.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/national_teams/national_teams_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_repository.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/transfer_center_screen.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/navigation/app_router.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';

import 'support/gtex_match_broadcast_fixture.dart';

typedef JsonMap = Map<String, Object?>;

void main() {
  testWidgets(
    'router mounts federations, national teams, and transfer center routes',
    (WidgetTester tester) async {
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();
      final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();
      final ProviderContainer container = _buildRouterContainer(
        session: _clubSession(),
        federationsApi: federationsApi,
        nationalTeamsApi: nationalTeamsApi,
        transferCenterApi: transferCenterApi,
      );
      addTearDown(container.dispose);
      final router = container.read(appRouterProvider);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      router.go(AppRoutes.federations);
      await tester.pumpAndSettle();
      expect(find.text('Regional tournaments'), findsOneWidget);

      router.go(AppRoutes.federationDetailLocation(_FakeFederationsApi.id));
      await tester.pumpAndSettle();
      expect(find.text('West Africa Federation'), findsWidgets);
      expect(find.text('Governance'), findsOneWidget);

      router.go(AppRoutes.nationalTeams);
      await tester.pumpAndSettle();
      expect(find.text('National Teams'), findsOneWidget);
      expect(find.text('Country rankings'), findsOneWidget);

      router.go(
        AppRoutes.nationalTeamDetailLocation(
          _FakeNationalTeamsApi.archivedCompetitionId,
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Nations Cup 2030'), findsOneWidget);
      expect(find.text('Build draft squad'), findsOneWidget);

      router.go(AppRoutes.transferCenter);
      await tester.pumpAndSettle();
      expect(find.text('Transfer Center'), findsOneWidget);
      expect(find.text('Live listings'), findsOneWidget);

      router.go(
        AppRoutes.transferCenterDetailLocation(
          _FakeTransferCenterApi.listingId,
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Victor Osimhen'), findsOneWidget);
      expect(find.text('Negotiation state'), findsOneWidget);
    },
  );

  testWidgets(
    'federation detail submits membership requests with a club context',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();

      await tester.pumpWidget(
        _screenHost(
          child: const FederationDetailScreen(
            federationId: _FakeFederationsApi.id,
          ),
          session: _clubSession(),
          overrides: [federationsApiProvider.overrideWithValue(federationsApi)],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(
        find.widgetWithText(FilledButton, 'Request membership'),
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Request membership'));
      await tester.pumpAndSettle();

      expect(federationsApi.membershipRequests, 1);
      expect(
        find.textContaining('membership request recorded as active'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'federation detail creates governance proposals for active participants',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();

      await tester.pumpWidget(
        _screenHost(
          child: const FederationDetailScreen(
            federationId: _FakeFederationsApi.id,
          ),
          session: _clubSession(),
          overrides: [federationsApiProvider.overrideWithValue(federationsApi)],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(
        find.widgetWithText(FilledButton, 'Create proposal'),
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Create proposal'));
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Title'),
        'Expand youth qualifier slots',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Summary'),
        'Increase the number of youth qualification spots for the next cycle.',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(federationsApi.proposalCreates, 1);
      expect(
        find.textContaining(
          'proposal "Expand youth qualifier slots" is now open',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'federation detail records governance votes for active participants',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();

      await tester.pumpWidget(
        _screenHost(
          child: const FederationDetailScreen(
            federationId: _FakeFederationsApi.id,
          ),
          session: _clubSession(),
          overrides: [federationsApiProvider.overrideWithValue(federationsApi)],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Vote'));
      await tester.tap(find.widgetWithText(FilledButton, 'Vote'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Vote yes'));
      await tester.pumpAndSettle();

      expect(federationsApi.proposalVotes, 1);
      expect(
        find.textContaining(
          'Vote yes recorded for "Expand regional qualifiers"',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'national team detail falls back to direct competition fetch and runs auto-build',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();

      await tester.pumpWidget(
        _screenHost(
          child: const NationalTeamCompetitionDetailScreen(
            competitionId: _FakeNationalTeamsApi.archivedCompetitionId,
          ),
          overrides: [
            nationalTeamsApiProvider.overrideWithValue(nationalTeamsApi),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Nations Cup 2030'), findsOneWidget);

      await tester.ensureVisible(
        find.widgetWithText(FilledButton, 'Build draft squad'),
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Build draft squad'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Run'));
      await tester.pumpAndSettle();

      expect(nationalTeamsApi.autoBuildCalls, 1);
      expect(find.text('Draft squad result'), findsOneWidget);
      expect(find.text('Victor Boniface'), findsOneWidget);
    },
  );

  testWidgets(
    'transfer center detail adds players to the watchlist with club context',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();

      await tester.pumpWidget(
        _screenHost(
          child: const TransferCenterDetailScreen(
            listingId: _FakeTransferCenterApi.listingId,
          ),
          session: _clubSession(),
          overrides: [
            transferCenterApiProvider.overrideWithValue(transferCenterApi),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(
        find.widgetWithText(OutlinedButton, 'Watchlist'),
      );
      await tester.tap(find.widgetWithText(OutlinedButton, 'Watchlist'));
      await tester.pumpAndSettle();

      expect(transferCenterApi.watchlistRequests, 1);
      expect(find.text('Victor Osimhen added to watchlist.'), findsOneWidget);
    },
  );

  testWidgets(
    'transfer center detail places bids through the premium live dialog',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();

      await tester.pumpWidget(
        _screenHost(
          child: const TransferCenterDetailScreen(
            listingId: _FakeTransferCenterApi.listingId,
          ),
          session: _clubSession(),
          overrides: [
            transferCenterApiProvider.overrideWithValue(transferCenterApi),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Bid'));
      await tester.tap(find.widgetWithText(FilledButton, 'Bid'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField).first, '101000000');
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(transferCenterApi.bidRequests, 1);
      expect(find.text('Bid submitted for Victor Osimhen.'), findsOneWidget);
    },
  );

  testWidgets(
    'transfer center detail submits contract offers through the premium live dialog',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();

      await tester.pumpWidget(
        _screenHost(
          child: const TransferCenterDetailScreen(
            listingId: _FakeTransferCenterApi.listingId,
          ),
          session: _clubSession(),
          overrides: [
            transferCenterApiProvider.overrideWithValue(transferCenterApi),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(
        find.widgetWithText(OutlinedButton, 'Contract offer'),
      );
      await tester.tap(find.widgetWithText(OutlinedButton, 'Contract offer'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(transferCenterApi.contractOfferRequests, 1);
      expect(find.text('Contract offer submitted.'), findsOneWidget);
    },
  );

  testWidgets('hub open buttons navigate from live lists to deep routes', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final _FakeFederationsApi federationsApi = _FakeFederationsApi();
    final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();
    final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();
    final ProviderContainer container = _buildRouterContainer(
      session: _clubSession(),
      federationsApi: federationsApi,
      nationalTeamsApi: nationalTeamsApi,
      transferCenterApi: transferCenterApi,
    );
    addTearDown(container.dispose);
    final router = container.read(appRouterProvider);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    router.go(AppRoutes.federations);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.widgetWithText(FilledButton, 'Open').first);
    await tester.tap(find.widgetWithText(FilledButton, 'Open').first);
    await tester.pumpAndSettle();
    expect(find.text('Governance'), findsOneWidget);

    router.go(AppRoutes.nationalTeams);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.widgetWithText(FilledButton, 'Open').first);
    await tester.tap(find.widgetWithText(FilledButton, 'Open').first);
    await tester.pumpAndSettle();
    expect(find.text('Build draft squad'), findsOneWidget);

    router.go(AppRoutes.transferCenter);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.widgetWithText(FilledButton, 'Open').first);
    await tester.tap(find.widgetWithText(FilledButton, 'Open').first);
    await tester.pumpAndSettle();
    expect(find.text('Negotiation state'), findsOneWidget);
  });

  testWidgets(
    'competition hub buttons route into hosted detail and streamer engine',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();
      final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();
      final _FakeHostedCompetitionApi hostedCompetitionApi =
          _FakeHostedCompetitionApi();
      final _FakeStreamerTournamentRepository streamerRepository =
          _FakeStreamerTournamentRepository();
      final ProviderContainer container = _buildRouterContainer(
        session: _hostSession(),
        federationsApi: federationsApi,
        nationalTeamsApi: nationalTeamsApi,
        transferCenterApi: transferCenterApi,
        competitionHub: CompetitionHubData(
          gtexCompetitions: const <CompetitionSummary>[],
          hostedCompetitions: <HostedCompetition>[
            hostedCompetitionApi.currentCompetition,
          ],
          streamerTournaments: <StreamerTournament>[
            streamerRepository.currentTournament,
          ],
        ),
        hostedCompetitionApi: hostedCompetitionApi,
        streamerRepository: streamerRepository,
      );
      addTearDown(container.dispose);
      final router = container.read(appRouterProvider);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      router.go(AppRoutes.competitions);
      await tester.pumpAndSettle();

      await tester.ensureVisible(
        find.widgetWithText(FilledButton, 'Open family').at(1),
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Open family').at(1));
      await tester.pumpAndSettle();
      expect(find.text('View detail'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'View detail'));
      await tester.pumpAndSettle();
      expect(find.text('Participants 3/16'), findsOneWidget);

      router.go(AppRoutes.competitions);
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.widgetWithText(OutlinedButton, 'Open full engine'),
      );
      await tester.tap(find.widgetWithText(OutlinedButton, 'Open full engine'));
      await tester.pumpAndSettle();
      expect(find.text('Streamer Tournament Engine'), findsOneWidget);
    },
  );

  testWidgets(
    'hosted competition detail actions answer with visible feedback',
    (WidgetTester tester) async {
      final _FakeHostedCompetitionApi hostedCompetitionApi =
          _FakeHostedCompetitionApi();

      await tester.pumpWidget(
        _screenHost(
          child: const LiveCompetitionDetailScreen(
            family: CompetitionFamilyRoute.hosted,
            competitionId: _FakeHostedCompetitionApi.id,
          ),
          session: _hostSession(),
          overrides: [
            hostedCompetitionApiProvider.overrideWithValue(
              hostedCompetitionApi,
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Join'));
      await tester.pumpAndSettle();
      expect(hostedCompetitionApi.joinCalls, 1);
      expect(find.text('Competition joined.'), findsOneWidget);

      await tester.pump(const Duration(seconds: 4));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, 'Launch'));
      await tester.pumpAndSettle();
      expect(hostedCompetitionApi.launchCalls, 1);
      expect(find.text('Competition launched.'), findsOneWidget);
    },
  );

  testWidgets(
    'streamer competition detail actions answer with visible feedback',
    (WidgetTester tester) async {
      final _FakeStreamerTournamentRepository streamerRepository =
          _FakeStreamerTournamentRepository();
      await tester.pumpWidget(
        _screenHost(
          child: const LiveCompetitionDetailScreen(
            family: CompetitionFamilyRoute.streamer,
            competitionId: _FakeStreamerTournamentRepository.id,
          ),
          session: _hostSession(),
          overrides: [
            streamerTournamentRepositoryProvider.overrideWithValue(
              streamerRepository,
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Join'));
      await tester.pumpAndSettle();
      expect(streamerRepository.joinCalls, 1);
      expect(find.text('Tournament joined.'), findsOneWidget);

      await tester.pump(const Duration(seconds: 4));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, 'Publish'));
      await tester.pumpAndSettle();
      expect(streamerRepository.publishCalls, 1);
      expect(find.text('Tournament published.'), findsOneWidget);
    },
  );

  testWidgets(
    'match buttons route into the shipped viewers and disclosed tools',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();
      final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();
      final _FakeTransferCenterApi transferCenterApi = _FakeTransferCenterApi();
      final _FakeLiveMatchViewerRepository matchViewerRepository =
          _FakeLiveMatchViewerRepository(
            competition: _buildViewerCompetition(
              id: 'live-match-001',
              name: 'Derby Live',
            ),
            viewState: buildBroadcastTestViewState(),
          );
      final ProviderContainer container = _buildRouterContainer(
        session: _clubSession(),
        federationsApi: federationsApi,
        nationalTeamsApi: nationalTeamsApi,
        transferCenterApi: transferCenterApi,
        matchOverview: const LiveMatchOverview(
          entries: <LiveMatchOverviewEntry>[
            LiveMatchOverviewEntry(
              matchKey: 'live-match-001',
              title: 'Derby Live',
              subtitle: 'Main event from the featured channel.',
              channelLabel: 'GTEX Prime',
              isFeatured: true,
              isLive: true,
            ),
          ],
          generatedAt: null,
          sourcePath: '/api/broadcast/home',
        ),
        matchViewerRepository: matchViewerRepository,
      );
      addTearDown(container.dispose);
      final router = container.read(appRouterProvider);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      router.go(AppRoutes.matches);
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Open 2D'));
      await tester.pumpAndSettle();
      expect(find.text('2D Match Viewer'), findsWidgets);
      expect(find.text('Viewer contract unavailable'), findsNothing);
      expect(find.text('Route blocked'), findsNothing);

      router.go(AppRoutes.matches);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, 'Open Broadcast+'));
      await tester.pumpAndSettle();
      expect(find.text('Broadcast Package'), findsWidgets);

      router.go(AppRoutes.matches);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, 'Open 3D'));
      await tester.pumpAndSettle();
      expect(find.text('3D Match Viewer'), findsWidgets);
      expect(find.text('Route blocked'), findsNothing);
      expect(find.text('FLUTTER_3D'), findsOneWidget);

      router.go(AppRoutes.matches);
      await tester.pumpAndSettle();
      expect(find.text('Open spectate probe'), findsNothing);
      expect(find.text('View coming soon note'), findsNothing);
      expect(find.text('Open simulation'), findsNothing);
    },
  );
}

Future<void> _pumpViewerRoute(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 64));
  await tester.pump(const Duration(milliseconds: 64));
}

ProviderContainer _buildRouterContainer({
  required AuthSession session,
  required _FakeFederationsApi federationsApi,
  required _FakeNationalTeamsApi nationalTeamsApi,
  required _FakeTransferCenterApi transferCenterApi,
  CompetitionHubData? competitionHub,
  HostedCompetitionApi? hostedCompetitionApi,
  StreamerTournamentEngineRepository? streamerRepository,
  LiveMatchOverview? matchOverview,
  LiveMatchViewerRepository? matchViewerRepository,
}) {
  const CompetitionHubData emptyHub = CompetitionHubData(
    gtexCompetitions: <CompetitionSummary>[],
    hostedCompetitions: <HostedCompetition>[],
    streamerTournaments: <StreamerTournament>[],
  );
  const MarketDashboardData emptyMarket = MarketDashboardData(
    playerShares: <PlayerShareSummary>[],
    holdings: <PlayerShareHoldingSummary>[],
    transferListings: <TransferListingSummary>[],
    wallet: null,
    authenticated: false,
    warnings: <String>[],
  );
  final CompetitionHubData seededHub = competitionHub ?? emptyHub;
  final LiveMatchOverview seededMatchOverview =
      matchOverview ??
      const LiveMatchOverview(
        entries: <LiveMatchOverviewEntry>[],
        generatedAt: null,
        sourcePath: '/api/broadcast/home',
      );

  return ProviderContainer(
    overrides: [
      appConfigProvider.overrideWithValue(_testAppConfig),
      authProvider.overrideWith((Ref ref) => session),
      authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
      deviceIdentityStoreProvider.overrideWithValue(
        MemoryDeviceIdentityStore(),
      ),
      deviceIdProvider.overrideWithValue('device-router'),
      profileDataProvider.overrideWith(
        (Ref ref) async => const ProfileData.unauthenticated(),
      ),
      competitionHubProvider.overrideWith((Ref ref) async => seededHub),
      marketDashboardProvider.overrideWith((Ref ref) async => emptyMarket),
      worldAggregateProvider.overrideWith((Ref ref) async {
        return WorldAggregateData(
          risingStars: <Map<String, Object?>>[],
          scoutingFeed: <Map<String, Object?>>[],
          seasons: <Map<String, Object?>>[],
          awards: <Map<String, Object?>>[],
          hallOfFame: <Map<String, Object?>>[],
          federations: <Map<String, Object?>>[],
          tracking: <String, Object?>{'season_phase': 'live'},
          competitions: seededHub,
          federationJoinReason:
              'Dedicated federation and national-team routes now handle the live flows.',
        );
      }),
      liveTasksProvider.overrideWith((Ref ref) async {
        return const LiveTasksData(
          authenticated: true,
          featureEnabled: true,
          challenges: <DailyChallengeSummary>[],
          claimsToday: <DailyChallengeClaimSummary>[],
          currentStreak: 0,
          longestStreak: 0,
          nextBonusAmount: 0,
        );
      }),
      federationsApiProvider.overrideWithValue(federationsApi),
      nationalTeamsApiProvider.overrideWithValue(nationalTeamsApi),
      transferCenterApiProvider.overrideWithValue(transferCenterApi),
      hostedCompetitionApiProvider.overrideWithValue(
        hostedCompetitionApi ?? _FakeHostedCompetitionApi(),
      ),
      streamerTournamentRepositoryProvider.overrideWithValue(
        streamerRepository ?? _FakeStreamerTournamentRepository(),
      ),
      liveMatchOverviewProvider.overrideWith(
        (Ref ref) async => seededMatchOverview,
      ),
      liveMatchViewerRepositoryProvider.overrideWithValue(
        matchViewerRepository ??
            _FakeLiveMatchViewerRepository(
              competition: _buildViewerCompetition(
                id: 'live-match-001',
                name: 'Route Mount Derby',
              ),
              viewState: buildBroadcastTestViewState(),
            ),
      ),
    ],
  );
}

const GteAppConfig _testAppConfig = GteAppConfig(
  apiBaseUrl: 'https://example.test',
  backendMode: GteBackendMode.live,
);

Widget _screenHost({
  required Widget child,
  AuthSession? session,
  List overrides = const [],
}) {
  return ProviderScope(
    overrides: [authProvider.overrideWith((Ref ref) => session), ...overrides],
    child: MaterialApp(home: Scaffold(body: child)),
  );
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1600, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

AuthSession _clubSession() {
  return const AuthSession(
    userId: 'user-1',
    accessToken: 'token-1',
    refreshToken: 'refresh-token-1',
    sessionId: 'session-1',
    role: 'user',
    permissions: <String>['match_3d_premium'],
    clubId: 'ibadan-lions',
    clubName: 'Ibadan Lions FC',
  );
}

AuthSession _hostSession() {
  return const AuthSession(
    userId: 'host-user-1',
    accessToken: 'host-token-1',
    refreshToken: 'host-refresh-token-1',
    sessionId: 'host-session-1',
    role: 'admin',
    permissions: <String>['match_3d_premium'],
    clubId: 'ibadan-lions',
    clubName: 'Ibadan Lions FC',
  );
}

GteAuthedApi _unusedAuthedApi() {
  return GteAuthedApi(
    config: const GteRepositoryConfig(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.live,
    ),
    transport: _UnexpectedTransport(),
    accessToken: 'unused-token',
  );
}

class _UnexpectedTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    throw UnimplementedError(
      'Unexpected transport call: ${request.method} ${request.uri}',
    );
  }
}

CompetitionSummary _buildViewerCompetition({
  required String id,
  required String name,
}) {
  return CompetitionSummary(
    id: id,
    name: name,
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
    rulesSummary: 'Route interaction proof competition.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: false),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}

class _FakeHostedCompetitionApi implements HostedCompetitionApi {
  _FakeHostedCompetitionApi()
    : _competition = HostedCompetition(
        id: id,
        templateId: templateId,
        hostUserId: 'host-user-1',
        title: title,
        slug: 'lagos-night-cup',
        description: 'Fast hosted competition with live actions.',
        status: 'open',
        visibility: 'public',
        startsAt: DateTime.utc(2026, 3, 30, 18),
        lockAt: DateTime.utc(2026, 3, 30, 17, 30),
        maxParticipants: 16,
        entryFeeFancoin: 5,
        rewardPoolFancoin: 80,
        platformFeeAmount: 6,
        metadata: const <String, Object?>{},
        createdAt: DateTime.utc(2026, 3, 28),
        updatedAt: DateTime.utc(2026, 3, 29),
      );

  static const String id = 'hosted-live-1';
  static const String title = 'Lagos Night Cup';
  static const String templateId = 'hosted-template-1';

  @override
  final GteAuthedApi client = _unusedAuthedApi();

  int joinCalls = 0;
  int launchCalls = 0;
  HostedCompetition _competition;

  HostedCompetition get currentCompetition => _competition;

  HostedCompetitionTemplate get _template => const HostedCompetitionTemplate(
    id: templateId,
    templateKey: 'creator-cup',
    title: 'Creator Cup',
    description: 'Invite-driven creator cup.',
    competitionType: 'creator',
    teamType: 'club',
    ageGrade: 'senior',
    cupOrLeague: 'cup',
    participants: 16,
    viewingMode: 'broadcast',
    giftRules: <String, Object?>{'gift_multiplier': 1.2},
    seedingMethod: 'balanced',
    isUserHostable: true,
    entryFeeFancoin: 5,
    rewardPoolFancoin: 80,
    platformFeeBps: 800,
    metadata: <String, Object?>{},
    active: true,
  );

  HostedCompetition _copyCompetition({required String status}) {
    return HostedCompetition(
      id: _competition.id,
      templateId: _competition.templateId,
      hostUserId: _competition.hostUserId,
      title: _competition.title,
      slug: _competition.slug,
      description: _competition.description,
      status: status,
      visibility: _competition.visibility,
      startsAt: _competition.startsAt,
      lockAt: _competition.lockAt,
      maxParticipants: _competition.maxParticipants,
      entryFeeFancoin: _competition.entryFeeFancoin,
      rewardPoolFancoin: _competition.rewardPoolFancoin,
      platformFeeAmount: _competition.platformFeeAmount,
      metadata: _competition.metadata,
      createdAt: _competition.createdAt,
      updatedAt: DateTime.utc(2026, 3, 30, 12),
    );
  }

  @override
  Future<List<HostedCompetitionTemplate>> listTemplates() async {
    return <HostedCompetitionTemplate>[_template];
  }

  @override
  Future<List<HostedCompetition>> listCompetitions() async {
    return <HostedCompetition>[_competition];
  }

  @override
  Future<List<HostedCompetition>> listMyCompetitions() async {
    return <HostedCompetition>[_competition];
  }

  @override
  Future<HostedCompetitionDetail> fetchDetail(String competitionId) async {
    return HostedCompetitionDetail(
      competition: _competition,
      template: _template,
      participants: <HostedCompetitionParticipant>[
        HostedCompetitionParticipant(
          id: 'participant-1',
          competitionId: competitionId,
          userId: 'host-user-1',
          joinedAt: DateTime.utc(2026, 3, 29),
          entryFeeFancoin: 5,
          payoutEligible: true,
          metadata: const <String, Object?>{},
        ),
      ],
      currentParticipants: 3,
      joinOpen: true,
    );
  }

  @override
  Future<HostedCompetition> createCompetition({
    required String templateKey,
    required String title,
    String description = '',
    String visibility = 'public',
    int? maxParticipants,
    double? entryFeeFancoin,
    double? rewardPoolFancoin,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<HostedCompetition> joinCompetition(String competitionId) async {
    joinCalls += 1;
    return _competition;
  }

  @override
  Future<List<HostedCompetitionStanding>> listStandings(
    String competitionId,
  ) async {
    return <HostedCompetitionStanding>[
      HostedCompetitionStanding(
        id: 'standing-1',
        competitionId: competitionId,
        userId: 'host-user-1',
        finalRank: 1,
        points: 9,
        wins: 3,
        draws: 0,
        losses: 0,
        goalsFor: 8,
        goalsAgainst: 2,
        payoutAmount: 50,
        metadata: const <String, Object?>{},
        createdAt: DateTime.utc(2026, 3, 29),
        updatedAt: DateTime.utc(2026, 3, 30),
      ),
    ];
  }

  @override
  Future<HostedCompetitionFinance> fetchFinance(String competitionId) async {
    return const HostedCompetitionFinance(
      currency: 'FAN',
      participantCount: 3,
      entryFeeFancoin: 5,
      grossCollected: 15,
      projectedRewardPool: 80,
      projectedPlatformFee: 6,
      escrowBalance: 9,
      settledPrizes: 0,
      settledPlatformFee: 0,
      status: 'open',
    );
  }

  @override
  Future<HostedCompetition> launchCompetition(String competitionId) async {
    launchCalls += 1;
    _competition = _copyCompetition(status: 'live');
    return _competition;
  }

  @override
  Future<List<HostedCompetitionTemplate>> seedTemplates() async {
    return <HostedCompetitionTemplate>[_template];
  }

  @override
  Future<HostedCompetition> finalizeCompetition({
    required String competitionId,
    required List<Map<String, Object?>> placements,
    String note = '',
  }) async {
    _competition = _copyCompetition(status: 'completed');
    return _competition;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeStreamerTournamentRepository
    implements StreamerTournamentEngineRepository {
  _FakeStreamerTournamentRepository()
    : _tournament = StreamerTournament.fromJson(<String, Object?>{
        'id': id,
        'host_user_id': 'host-user-1',
        'creator_profile_id': 'creator-1',
        'creator_club_id': 'ibadan-lions',
        'slug': 'creator-clash',
        'title': title,
        'description': 'Creator-hosted tournament with live actions.',
        'tournament_type': 'ladder',
        'status': 'draft',
        'approval_status': 'draft',
        'max_participants': 8,
        'requires_admin_approval': false,
        'high_reward_flag': false,
        'entry_rules_json': <String, Object?>{},
        'metadata_json': <String, Object?>{},
        'rewards': <Map<String, Object?>>[],
        'invites': <Map<String, Object?>>[],
        'entries': <Map<String, Object?>>[
          <String, Object?>{'user_id': 'entry-1'},
        ],
        'open_risk_signals': <Map<String, Object?>>[],
      });

  static const String id = 'streamer-1';
  static const String title = 'Creator Clash';

  int joinCalls = 0;
  int publishCalls = 0;
  StreamerTournament _tournament;

  StreamerTournament get currentTournament => _tournament;

  LeaderboardSeason get _season => LeaderboardSeason.fromJson(<String, Object?>{
    'id': 'season-1',
    'status': 'live',
    'default_rating': 1000,
    'k_factor': 32,
    'reset_strategy': 'soft',
    'soft_reset_factor': 0.85,
    'duration_days': 30,
    'days_remaining': 12,
    'rank_tiers': <Map<String, Object?>>[],
    'reward_tiers': <Map<String, Object?>>[],
    'metadata_json': <String, Object?>{},
  });

  StreamerTournament _replaceTournament(Map<String, Object?> patch) {
    return StreamerTournament.fromJson(<String, Object?>{
      ..._tournament.raw,
      ...patch,
    });
  }

  @override
  Future<StreamerTournamentList> listPublicTournaments() async {
    return StreamerTournamentList(
      tournaments: <StreamerTournament>[_tournament],
    );
  }

  @override
  Future<StreamerTournamentList> listMyTournaments() async {
    return StreamerTournamentList(
      tournaments: <StreamerTournament>[_tournament],
    );
  }

  @override
  Future<LeaderboardBoard> fetchGlobalLeaderboard({int limit = 12}) async {
    throw UnimplementedError();
  }

  @override
  Future<LeaderboardSeason> fetchCurrentSeason() async {
    return _season;
  }

  @override
  Future<LeaderboardSeasonHistory> fetchSeasonHistory({int limit = 4}) async {
    throw UnimplementedError();
  }

  @override
  Future<LeaderboardPlayerRanks> fetchPlayerRanks(String playerId) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> createTournament(
    StreamerTournamentCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> fetchTournament(String tournamentId) async {
    return _tournament;
  }

  @override
  Future<StreamerTournament> updateTournament(
    String tournamentId,
    StreamerTournamentUpdateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> replaceRewardPlan(
    String tournamentId,
    StreamerTournamentRewardPlanReplaceRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> createInvite(
    String tournamentId,
    StreamerTournamentInviteCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> joinTournament(
    String tournamentId,
    StreamerTournamentJoinRequest request,
  ) async {
    joinCalls += 1;
    _tournament = _replaceTournament(<String, Object?>{
      'entries': <Map<String, Object?>>[
        ..._tournament.entries,
        <String, Object?>{'user_id': 'host-user-1'},
      ],
    });
    return _tournament;
  }

  @override
  Future<StreamerTournament> publishTournament(
    String tournamentId,
    StreamerTournamentPublishRequest request,
  ) async {
    publishCalls += 1;
    _tournament = _replaceTournament(<String, Object?>{
      'status': 'published',
      'approval_status': 'submitted',
    });
    return _tournament;
  }

  @override
  Future<StreamerTournamentPolicy> fetchPolicy() async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournamentPolicy> upsertPolicy(
    StreamerTournamentPolicyUpsertRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournament> reviewTournament(
    String tournamentId,
    StreamerTournamentReviewRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<List<StreamerTournamentRiskSignal>> listRiskSignals() async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournamentRiskSignal> reviewRiskSignal(
    String signalId,
    StreamerTournamentRiskReviewRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<StreamerTournamentSettlement> settleTournament(
    String tournamentId,
    StreamerTournamentSettleRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<LeaderboardSeasonLifecycle> archiveSeason() async {
    throw UnimplementedError();
  }

  @override
  Future<LeaderboardSeasonLifecycle> resetSeason() async {
    throw UnimplementedError();
  }
}

class _FakeLiveMatchViewerRepository implements LiveMatchViewerRepository {
  const _FakeLiveMatchViewerRepository({
    required this.competition,
    required this.viewState,
  });

  final CompetitionSummary competition;
  final MatchViewState viewState;

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    return _routeQualifiedViewState(matchKey, viewState);
  }

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: <String, Object?>{'title': competition.name},
      competition: competition,
    );
  }
}

MatchViewState _routeQualifiedViewState(String matchKey, MatchViewState state) {
  final int lastFrameSecond =
      state.frames.isEmpty ? 0 : state.frames.last.timeSeconds.ceil();
  final int segmentEndSeconds =
      state.segmentEndSeconds < lastFrameSecond
          ? lastFrameSecond
          : state.segmentEndSeconds;
  final int durationSeconds =
      state.durationSeconds < segmentEndSeconds
          ? segmentEndSeconds
          : state.durationSeconds;
  return MatchViewState(
    matchId: matchKey,
    source: state.source,
    supportsOffside: state.supportsOffside,
    deterministicSeed: state.deterministicSeed,
    matchMode: state.matchMode,
    durationSeconds: durationSeconds,
    homeTeam: state.homeTeam,
    awayTeam: state.awayTeam,
    events: state.events,
    frames: state.frames,
    fairnessIndicator: state.fairnessIndicator,
    timelineProof: state.timelineProof,
    scoreRevealLocked: state.scoreRevealLocked,
    segmentStartSeconds: state.segmentStartSeconds,
    segmentEndSeconds: segmentEndSeconds,
    hasMoreSegments: state.hasMoreSegments,
    nextSegmentToken: state.nextSegmentToken,
    monetization: state.monetization,
    presentationPackage: state.presentationPackage,
  );
}

class _FakeFederationsApi extends FederationsApi {
  _FakeFederationsApi() : super(client: _unusedAuthedApi());

  static const String id = 'fed-west-africa';

  static const FederationRecord _federation = FederationRecord(
    id: id,
    name: 'West Africa Federation',
    rankingScore: 94.2,
    reputationScore: 91.4,
    audienceSize: 420000,
    treasuryBalance: 1250000,
    memberCount: 12,
    isPublic: true,
    defaultRealityMode: 'hybrid',
  );

  int membershipRequests = 0;
  int proposalCreates = 0;
  int proposalVotes = 0;

  final List<JsonMap> _members = <JsonMap>[
    <String, Object?>{'club_id': 'ibadan-lions', 'status': 'active'},
  ];
  final List<JsonMap> _proposals = <JsonMap>[
    <String, Object?>{
      'id': 'proposal-1',
      'title': 'Expand regional qualifiers',
      'summary': 'Increase the federation qualifier slots for the next cycle.',
      'status': 'open',
      'yes_votes': 7,
      'no_votes': 2,
      'abstain_votes': 1,
    },
  ];
  final List<JsonMap> _votes = <JsonMap>[];

  @override
  Future<List<FederationRecord>> listFederations() async {
    return const <FederationRecord>[_federation];
  }

  @override
  Future<List<FederationRankingRecord>> listRankings() async {
    return const <FederationRankingRecord>[
      FederationRankingRecord(
        federationId: id,
        name: 'West Africa Federation',
        rankingScore: 94.2,
        reputationScore: 91.4,
        audienceSize: 420000,
        activityScore: 88.0,
        competitivenessScore: 86.0,
      ),
    ];
  }

  @override
  Future<List<RegionalTournamentRecord>> listRegionalTournaments() async {
    return const <RegionalTournamentRecord>[
      RegionalTournamentRecord(
        regionCode: 'west_africa',
        regionLabel: 'West Africa',
        federationCount: 1,
        activeLeagueCount: 2,
        totalMemberClubs: 12,
      ),
    ];
  }

  @override
  Future<JsonMap> fetchDashboard(String federationId) async {
    return <String, Object?>{
      'leagues': <Map<String, Object?>>[
        <String, Object?>{
          'name': 'WAF Nations League',
          'competition_type': 'league',
          'status': 'active',
          'season_label': '2030',
        },
      ],
      'rules': <String, Object?>{'salary_cap': 'enabled', 'foreign_limit': 5},
      'members': _members,
      'reputation': <String, Object?>{
        'score': 91.4,
        'ranking_score': 94.2,
        'audience_size': 420000,
      },
    };
  }

  @override
  Future<JsonMap> fetchGovernance(String federationId) async {
    return <String, Object?>{
      'proposals': _proposals,
      'votes': _votes,
      'sanctions': <Map<String, Object?>>[
        <String, Object?>{
          'sanction_type': 'fine',
          'reason': 'Late registration paperwork.',
        },
      ],
    };
  }

  @override
  Future<List<JsonMap>> fetchNarratives(String federationId) async {
    return <JsonMap>[
      <String, Object?>{
        'headline': 'West Africa race tightens',
        'body': 'Three clubs are separated by two points.',
      },
    ];
  }

  @override
  Future<FederationMembershipResult> createMembership({
    required String federationId,
    required String clubId,
    String? userId,
  }) async {
    membershipRequests += 1;
    final bool alreadyMember = _members.any(
      (JsonMap item) => (item['club_id']?.toString() ?? '') == clubId,
    );
    if (!alreadyMember) {
      _members.add(<String, Object?>{'club_id': clubId, 'status': 'active'});
    }
    return const FederationMembershipResult(
      status: 'active',
      role: 'member_club',
      violations: <String>[],
    );
  }

  @override
  Future<FederationProposalActionResult> createProposal({
    required String federationId,
    required String title,
    required String summary,
    String proposalType = 'rule_change',
    String? leagueId,
    DateTime? votingEndsAt,
  }) async {
    proposalCreates += 1;
    _proposals.insert(0, <String, Object?>{
      'id': 'proposal-${proposalCreates + 1}',
      'title': title,
      'summary': summary,
      'status': 'open',
      'yes_votes': 0,
      'no_votes': 0,
      'abstain_votes': 0,
      'proposal_type': proposalType,
      'league_id': leagueId,
      'voting_ends_at': votingEndsAt?.toIso8601String(),
    });
    return FederationProposalActionResult(
      id: _proposals.first['id']?.toString() ?? '',
      title: title,
      status: 'open',
    );
  }

  @override
  Future<FederationProposalActionResult> castProposalVote({
    required String proposalId,
    required String voteType,
    String? comment,
  }) async {
    proposalVotes += 1;
    for (final JsonMap proposal in _proposals) {
      if ((proposal['id']?.toString() ?? '') != proposalId) {
        continue;
      }
      final int yesVotes = (proposal['yes_votes'] as num?)?.toInt() ?? 0;
      final int noVotes = (proposal['no_votes'] as num?)?.toInt() ?? 0;
      final int abstainVotes =
          (proposal['abstain_votes'] as num?)?.toInt() ?? 0;
      proposal['yes_votes'] = voteType == 'yes' ? yesVotes + 1 : yesVotes;
      proposal['no_votes'] = voteType == 'no' ? noVotes + 1 : noVotes;
      proposal['abstain_votes'] =
          voteType == 'abstain' ? abstainVotes + 1 : abstainVotes;
      _votes.insert(0, <String, Object?>{
        'proposal_id': proposalId,
        'user_id': 'user-1',
        'vote_type': voteType,
      });
      return FederationProposalActionResult(
        id: proposalId,
        title: proposal['title']?.toString() ?? 'Proposal',
        status: proposal['status']?.toString() ?? 'open',
        voteType: voteType,
      );
    }
    return FederationProposalActionResult(
      id: proposalId,
      title: 'Proposal',
      status: 'open',
      voteType: voteType,
    );
  }
}

class _FakeNationalTeamsApi extends NationalTeamsApi {
  _FakeNationalTeamsApi() : super(client: _unusedAuthedApi());

  static const String activeCompetitionId = 'nations-live-1';
  static const String archivedCompetitionId = 'nations-2030';

  final NationalTeamCompetition _activeCompetition = NationalTeamCompetition(
    id: activeCompetitionId,
    key: 'nations-live',
    title: 'Nations Cup Live',
    seasonLabel: '2031',
    regionType: 'global',
    ageBand: 'senior',
    formatType: 'cup',
    status: 'open',
    notes: 'Active competition',
    active: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );

  final NationalTeamCompetition _archivedCompetition = NationalTeamCompetition(
    id: archivedCompetitionId,
    key: 'nations-2030',
    title: 'Nations Cup 2030',
    seasonLabel: '2030',
    regionType: 'global',
    ageBand: 'senior',
    formatType: 'cup',
    status: 'completed',
    notes: 'Archived competition used for deep-link fallback.',
    active: false,
    createdAt: DateTime.utc(2025, 1, 1),
    updatedAt: DateTime.utc(2025, 12, 31),
  );

  int autoBuildCalls = 0;

  @override
  Future<List<NationalTeamCompetition>> listCompetitions() async {
    return <NationalTeamCompetition>[_activeCompetition];
  }

  @override
  Future<List<NationalTeamCountryRankingRecord>> listRankings({
    int limit = 20,
  }) async {
    return const <NationalTeamCountryRankingRecord>[
      NationalTeamCountryRankingRecord(
        countryCode: 'NG',
        countryName: 'Nigeria',
        eloRating: 1884.0,
        matchesPlayed: 18,
        wins: 12,
        draws: 4,
        losses: 2,
        titles: 1,
      ),
    ];
  }

  @override
  Future<NationalTeamCompetition> fetchCompetition(String competitionId) async {
    if (competitionId == archivedCompetitionId) {
      return _archivedCompetition;
    }
    return _activeCompetition;
  }

  @override
  Future<JsonMap> fetchLifecycle(String competitionId) async {
    return <String, Object?>{
      'current_stage': 'qualifiers',
      'representative_entries': <Map<String, Object?>>[
        <String, Object?>{
          'country_name': 'Nigeria',
          'status': 'qualified',
          'strength_rating': 91.0,
        },
      ],
      'qualified_entries': <Map<String, Object?>>[
        <String, Object?>{
          'country_name': 'Nigeria',
          'status': 'qualified',
          'strength_rating': 91.0,
        },
      ],
      'submitted_entries': <Map<String, Object?>>[
        <String, Object?>{
          'country_name': 'Nigeria',
          'status': 'submitted',
          'strength_rating': 89.5,
        },
      ],
      'stage_history': <Map<String, Object?>>[
        <String, Object?>{
          'stage': 'entries_open',
          'summary': 'Country submissions opened worldwide.',
        },
      ],
    };
  }

  @override
  Future<JsonMap> fetchPresentation(String competitionId) async {
    return <String, Object?>{
      'active_theme': <String, Object?>{'visual_style': 'continental'},
      'active_ads': <Map<String, Object?>>[
        <String, Object?>{
          'placement': 'touchline_led',
          'asset_url': 'https://example.test/ad-1.png',
        },
      ],
      'story_events': <Map<String, Object?>>[
        <String, Object?>{
          'type': 'headline',
          'narrative_text': 'Nigeria opens as one of the title favorites.',
        },
      ],
    };
  }

  @override
  Future<NationalTeamUserHistory> fetchUserHistory() async {
    return NationalTeamUserHistory(
      managedEntries: <NationalTeamEntry>[
        NationalTeamEntry(
          id: 'entry-2030-ng',
          competitionId: archivedCompetitionId,
          countryCode: 'NG',
          countryName: 'Nigeria',
          managerUserId: 'user-1',
          squadSize: 23,
          metadata: const <String, Object?>{},
          createdAt: DateTime.utc(2025, 1, 1),
          updatedAt: DateTime.utc(2025, 12, 31),
        ),
      ],
      squadMemberships: const <NationalTeamSquadMember>[],
    );
  }

  @override
  Future<List<JsonMap>> listNationalRegens({
    int limit = 12,
    int? ageMin = 14,
    int? ageMax = 17,
    String? preseedBatch = 'u17_batch',
  }) async {
    return <JsonMap>[
      <String, Object?>{
        'id': 'seed-ng-14',
        'display_name': 'Sodiq Adebayo',
        'age': 14,
        'country_code': 'NG',
        'country_name': 'Nigeria',
        'primary_position': 'AM',
        'current_rating': 66,
        'potential_rating': 89,
        'rarity_tier': 'elite',
        'preseed_batch': 'u17_batch',
      },
      <String, Object?>{
        'id': 'seed-gh-16',
        'display_name': 'Kojo Mensah',
        'age': 16,
        'country_code': 'GH',
        'country_name': 'Ghana',
        'primary_position': 'CB',
        'current_rating': 68,
        'potential_rating': 87,
        'rarity_tier': 'rare',
        'preseed_batch': 'u17_batch',
      },
    ];
  }

  @override
  Future<JsonMap> buildAutoSquad({
    required String competitionId,
    required String countryCode,
    required double budgetCoin,
    required String tactic,
  }) async {
    autoBuildCalls += 1;
    return <String, Object?>{
      'formation': '4-3-3',
      'selected_count': 2,
      'requested_budget_coin': budgetCoin,
      'remaining_budget_coin': budgetCoin - 1300000,
      'players': <Map<String, Object?>>[
        <String, Object?>{
          'player_name': 'Victor Boniface',
          'assigned_slot': 'ST',
          'primary_position': 'ST',
          'loan_price_coin': 700000,
        },
        <String, Object?>{
          'player_name': 'Calvin Bassey',
          'assigned_slot': 'CB',
          'primary_position': 'CB',
          'loan_price_coin': 600000,
        },
      ],
    };
  }
}

class _FakeTransferCenterApi extends TransferCenterApi {
  _FakeTransferCenterApi() : super(client: _unusedAuthedApi());

  static const String listingId = 'listing-1';

  static const TransferCenterListingRecord _listing =
      TransferCenterListingRecord(
        id: listingId,
        playerId: 'player-osimhen',
        playerName: 'Victor Osimhen',
        sellingClubId: 'napoli',
        currentClubName: 'Napoli',
        basePrice: 90000000,
        currentHighestBid: 97000000,
        highestBidderId: 'ibadan-lions',
        status: 'open',
        watchlistCount: 14,
        bidCount: 3,
        marketSignal: 'Premier clubs are circling.',
        channel: 'transfer:listing-1',
        timeRemaining: 5400,
        negotiationId: 'negotiation-1',
        bidders: <JsonMap>[
          <String, Object?>{
            'club_id': 'ibadan-lions',
            'club_name': 'Ibadan Lions FC',
            'amount': 97000000,
            'is_highest': true,
          },
        ],
      );

  int watchlistRequests = 0;
  int bidRequests = 0;
  int contractOfferRequests = 0;

  @override
  Future<List<TransferCenterListingRecord>> listListings({
    String? status,
    String? playerId,
  }) async {
    return const <TransferCenterListingRecord>[_listing];
  }

  @override
  Future<JsonMap> fetchListing(String listingId) async {
    return <String, Object?>{
      'id': listingId,
      'player_id': 'player-osimhen',
      'status': 'open',
      'base_price': 90000000,
      'current_highest_bid': 97000000,
      'time_remaining': 5400,
      'channel': 'transfer:listing-1',
      'market_signal': 'Premier clubs are circling.',
      'player': <String, Object?>{
        'full_name': 'Victor Osimhen',
        'current_club_name': 'Napoli',
      },
      'bidders': <Map<String, Object?>>[
        <String, Object?>{
          'club_id': 'ibadan-lions',
          'club_name': 'Ibadan Lions FC',
          'amount': 97000000,
          'is_highest': true,
        },
      ],
    };
  }

  @override
  Future<JsonMap?> fetchNegotiation(String listingId) async {
    return <String, Object?>{
      'status': 'counter_offer',
      'contract_years': 4,
      'wage_offer_amount': 350000,
      'player_decision': <String, Object?>{
        'action': 'delay',
        'decision_score': 62.0,
      },
      'coach_opinion': <String, Object?>{
        'stance': 'approve',
        'reason': 'Fits the press-first attack.',
      },
      'agent_negotiation': <String, Object?>{
        'action': 'counter_offer',
        'notes': 'Higher loyalty bonus requested.',
      },
    };
  }

  @override
  Future<void> addToWatchlist({
    required String clubId,
    required String playerId,
    required String listingId,
  }) async {
    watchlistRequests += 1;
  }

  @override
  Future<void> placeBid({
    required String listingId,
    required String clubId,
    required double amount,
  }) async {
    bidRequests += 1;
  }

  @override
  Future<void> submitContractOffer({
    required String listingId,
    required String clubId,
    required double wageOfferAmount,
    required int contractYears,
    String? expectedRole,
  }) async {
    contractOfferRequests += 1;
  }
}
