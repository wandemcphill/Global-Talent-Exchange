import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match_center/live_match_session.dart';
import 'package:gte_frontend/features/compete/providers/live_competitions_provider.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_create_screen.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_discovery_screen.dart';
import 'package:gte_frontend/features/compete/presentation/streamer_tournament_engine_screen.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/match_center/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/compete/domain/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/capital/liquidity/creator_share_market/presentation/creator_share_market_admin_control_screen.dart';
import 'package:gte_frontend/features/capital/liquidity/creator_share_market/presentation/creator_share_market_screen.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/navigation/app_router.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets(
    'router mounts live 2D routes, quarantines retired match lanes, and profile admin',
    (WidgetTester tester) async {
      final ProviderContainer container = _buildContainer(
        session: const AuthSession(
          userId: 'admin-1',
          accessToken: 'token-1',
          refreshToken: 'refresh-token-1',
          sessionId: 'session-1',
          role: 'admin',
          permissions: <String>['legacy_match_runtime'],
        ),
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

      router.go(AppRoutes.matchesViewerLocation('live-match-001'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('match-center-scorebug')), findsWidgets);
      expect(find.byKey(const Key('match-center-pitch-shell')), findsWidgets);
      expect(find.text('Route blocked'), findsNothing);

      router.go(AppRoutes.matchesBroadcastLocation('live-match-001'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('match-center-scorebug')), findsNothing);
      expect(find.byKey(const Key('match-center-pitch-shell')), findsNothing);
      expect(find.text('Route unavailable'), findsOneWidget);

      router.go(AppRoutes.legacyMatchRuntimeLocation('live-match-001'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('match-center-scorebug')), findsNothing);
      expect(find.byKey(const Key('match-center-pitch-shell')), findsNothing);
      expect(find.text('Route unavailable'), findsOneWidget);

      router.go(AppRoutes.legacyBlockedMatchRuntime);
      await tester.pumpAndSettle();
      expect(find.text('Route unavailable'), findsOneWidget);

      router.go(AppRoutes.matchesSpectate);
      await tester.pumpAndSettle();
      expect(find.text('Route unavailable'), findsOneWidget);

      router.go(AppRoutes.matchesSimulate);
      await tester.pumpAndSettle();
      expect(find.text('Route unavailable'), findsOneWidget);

      router.go(AppRoutes.streamerEngine);
      await tester.pumpAndSettle();
      expect(find.byType(GteExchangeShellScreen), findsOneWidget);
      expect(find.text('Streamer tournaments coming soon'), findsNothing);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/streamer-tournaments');
      await tester.pumpAndSettle();
      expect(find.byType(StreamerTournamentEngineScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/competitions/streamer');
      await tester.pumpAndSettle();
      expect(find.byType(StreamerTournamentEngineScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/player-cards');
      await tester.pumpAndSettle();
      expect(find.byType(PlayerCardMarketplaceScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/player-cards/inventory');
      await tester.pumpAndSettle();
      expect(find.byType(PlayerCardMarketplaceScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/competitions/gtex');
      await tester.pumpAndSettle();
      expect(find.byType(CompetitionDiscoveryScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/competitions/create');
      await tester.pumpAndSettle();
      expect(find.byType(CompetitionCreateScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/creator-share-market/clubs/royal-lagos-fc');
      await tester.pumpAndSettle();
      expect(find.byType(CreatorShareMarketScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go('/admin/creator-share-market/control');
      await tester.pumpAndSettle();
      expect(find.byType(CreatorShareMarketAdminControlScreen), findsOneWidget);
      expect(find.text('Route unavailable'), findsNothing);

      router.go(AppRoutes.profileAdmin);
      await tester.pumpAndSettle();
      expect(find.byType(GteExchangeShellScreen), findsOneWidget);
      expect(find.text('Admin'), findsWidgets);
      expect(find.text('Route unavailable'), findsNothing);
    },
  );

  testWidgets('profile route exposes the auth entry path for guest sessions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(
            const GteAppConfig(
              apiBaseUrl: 'https://example.test',
              backendMode: GteBackendMode.live,
            ),
          ),
          profileDataProvider.overrideWith(
            (Ref ref) async => const ProfileData.unauthenticated(),
          ),
        ],
        child: const MaterialApp(home: Scaffold(body: HomeScreen())),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Sign in'), findsOneWidget);
  });

  testWidgets(
    'guest sessions reach the canonical community shell through the clips alias',
    (WidgetTester tester) async {
      final ProviderContainer container = _buildContainer(session: null);
      addTearDown(container.dispose);
      final router = container.read(appRouterProvider);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      router.go(AppRoutes.clips);
      await tester.pumpAndSettle();

      expect(find.byType(GteExchangeShellScreen), findsOneWidget);
      expect(find.text('Community'), findsWidgets);
      expect(find.text('Clips are blocked'), findsNothing);
    },
  );
}

ProviderContainer _buildContainer({AuthSession? session}) {
  const CompetitionHubData emptyHub = CompetitionHubData(
    gtexCompetitions: <CompetitionSummary>[],
    hostedCompetitions: <HostedCompetition>[],
    streamerTournaments: <StreamerTournament>[],
  );
  final MatchViewState viewState = buildBroadcastTestViewState();
  final CompetitionSummary competition = _buildCompetition(
    id: 'live-match-001',
    name: 'Route Mount Derby',
  );
  return ProviderContainer(
    overrides: [
      appConfigProvider.overrideWithValue(
        const GteAppConfig(
          apiBaseUrl: 'https://example.test',
          backendMode: GteBackendMode.live,
        ),
      ),
      authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
      deviceIdentityStoreProvider.overrideWithValue(
        MemoryDeviceIdentityStore(),
      ),
      initialAuthSessionProvider.overrideWithValue(session),
      deviceIdProvider.overrideWithValue('device-1'),
      liveMatchViewerRepositoryProvider.overrideWithValue(
        _FakeLiveMatchViewerRepository(
          competition: competition,
          viewState: viewState,
        ),
      ),
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
          risingStars: <Map<String, Object?>>[],
          scoutingFeed: <Map<String, Object?>>[],
          seasons: <Map<String, Object?>>[],
          awards: <Map<String, Object?>>[],
          hallOfFame: <Map<String, Object?>>[],
          federations: <Map<String, Object?>>[],
          tracking: <String, Object?>{},
          competitions: emptyHub,
          federationJoinReason: 'Blocked for guest route test.',
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
  );
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
      spectateSession: LiveMatchSpectateSession(
        id: 'route-test-session',
        matchId: matchKey,
        channel: 'match:$matchKey:events',
        websocketPath:
            '/api/matches/$matchKey/stream?session_id=route-test-session',
        commentaryWebsocketPath:
            '/api/matches/$matchKey/commentary/stream?session_id=route-test-session',
      ),
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
    engagement: state.engagement,
    presentationPackage: state.presentationPackage,
  );
}

CompetitionSummary _buildCompetition({
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
    rulesSummary: 'Active shell route mount test competition.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: false),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}
