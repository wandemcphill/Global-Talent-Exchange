import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/navigation/app_router.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets(
    'router mounts blocked 2D routes, live broadcast, gated Flutter 3D, and admin redirect',
    (WidgetTester tester) async {
      final ProviderContainer container = _buildContainer(
        session: const AuthSession(
          userId: 'admin-1',
          accessToken: 'token-1',
          refreshToken: 'refresh-token-1',
          sessionId: 'session-1',
          role: 'admin',
          permissions: <String>['match_3d_premium'],
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
      expect(find.text('2D Match Viewer'), findsWidgets);
      expect(find.text('Route blocked'), findsOneWidget);

      router.go(AppRoutes.matchesBroadcastLocation('live-match-001'));
      await tester.pumpAndSettle();
      expect(find.text('Broadcast Package'), findsWidgets);

      router.go(AppRoutes.matchesThreeDLocation('live-match-001'));
      await tester.pumpAndSettle();
      expect(find.text('3D Match Viewer'), findsWidgets);
      expect(find.text('Route blocked'), findsNothing);
      expect(find.text('FLUTTER_3D'), findsOneWidget);

      router.go(AppRoutes.matchesNativeThreeD);
      await tester.pumpAndSettle();
      expect(find.text('Native 3D is coming soon'), findsOneWidget);

      router.go(AppRoutes.streamerEngine);
      await tester.pumpAndSettle();
      expect(find.text('Streamer Tournament Engine'), findsOneWidget);

      router.go(AppRoutes.profileGodMode);
      await tester.pumpAndSettle();
      expect(find.text('Profile > Admin'), findsOneWidget);
      expect(find.text('Admin tooling is blocked'), findsOneWidget);
      expect(find.text('God Mode blocked'), findsNothing);
    },
  );

  testWidgets('profile route exposes the auth entry path for guest sessions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
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
    'guest sessions see clips route as blocked instead of mounting the live feed',
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

      expect(find.text('Clips are blocked'), findsOneWidget);
      expect(find.text('Sign in'), findsOneWidget);
    },
  );
}

Future<void> _pumpViewerRoute(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 64));
  await tester.pump(const Duration(milliseconds: 64));
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
          claimsToday: <Map<String, Object?>>[],
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
