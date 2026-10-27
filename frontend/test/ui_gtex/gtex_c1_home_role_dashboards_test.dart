import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/data/gtex_home_digest_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/home/models/gtex_home_digest_models.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  const GteAppConfig testAppConfig = GteAppConfig(
    apiBaseUrl: 'http://127.0.0.1:8000',
    backendMode: GteBackendMode.fixture,
  );

  GtexHomeDigest buildDigest({
    List<GtexHomeAttentionItem> attentionItems =
        const <GtexHomeAttentionItem>[],
  }) {
    return GtexHomeDigest(
      userState: GtexHomeUserState.multiAsset,
      headline: 'Your football empire is active today.',
      ownedPlayers: const <GtexHomePlayerHighlight>[],
      yourMoversToday: const <GtexHomeMoverHighlight>[],
      opportunityMovers: const <GtexHomeMoverHighlight>[],
      clubs: const <GtexHomeClubHighlight>[],
      regens: const <GtexHomeRegenHighlight>[],
      attentionItems: attentionItems,
      recentActivity: const <GtexHomeActivityItem>[],
      warnings: const <String>[],
    );
  }

  Widget buildHomeHost({
    required ProfileData profileData,
    GtexHomeDigest? digest,
  }) {
    const CompetitionHubData emptyHub = CompetitionHubData(
      gtexCompetitions: <CompetitionSummary>[],
      hostedCompetitions: <HostedCompetition>[],
      streamerTournaments: <StreamerTournament>[],
    );
    return ProviderScope(
      overrides: [
        appConfigProvider.overrideWithValue(testAppConfig),
        isAuthenticatedProvider.overrideWithValue(profileData.authenticated),
        profileDataProvider.overrideWith((Ref ref) async => profileData),
        competitionHubProvider.overrideWith((Ref ref) async => emptyHub),
        marketDashboardProvider.overrideWith(
          (Ref ref) async => const MarketDashboardData(
            playerShares: <PlayerShareSummary>[],
            holdings: <PlayerShareHoldingSummary>[],
            transferListings: <TransferListingSummary>[],
            wallet: MarketWalletSnapshot(
              coinBalance: 25000,
              creditBalance: 1200,
              totalEquity: 48000,
              canTradeMarket: true,
              canDeposit: true,
              canWithdraw: true,
              complianceMessage: 'Verified account',
            ),
            authenticated: true,
            warnings: <String>[],
          ),
        ),
        worldAggregateProvider.overrideWith(
          (Ref ref) async => const WorldAggregateData(
            risingStars: <Map<String, Object?>>[
              <String, Object?>{
                'player_name': 'Kelechi Regen',
                'position': 'ST',
              },
            ],
            scoutingFeed: <Map<String, Object?>>[],
            seasons: <Map<String, Object?>>[],
            awards: <Map<String, Object?>>[],
            hallOfFame: <Map<String, Object?>>[],
            federations: <Map<String, Object?>>[],
            tracking: <String, Object?>{},
            competitions: emptyHub,
            federationJoinReason: 'Open federation entry',
          ),
        ),
        liveTasksProvider.overrideWith(
          (Ref ref) async => const LiveTasksData(
            authenticated: true,
            featureEnabled: true,
            currentStreak: 4,
            longestStreak: 7,
            nextBonusAmount: 50,
            claimsToday: <DailyChallengeClaimSummary>[],
            challenges: <DailyChallengeSummary>[],
          ),
        ),
        homeDigestProvider.overrideWith(
          (Ref ref) async => digest ?? buildDigest(),
        ),
      ],
      child: MaterialApp(
        theme: GteShellTheme.build(),
        home: const Scaffold(body: HomeScreen()),
      ),
    );
  }

  group('Phase C1 — Role Dashboards on Home (G1–G6)', () {
    testWidgets('G1: Owner Home renders club operations desk & quick actions', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1440, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        buildHomeHost(
          profileData: const ProfileData(
            authenticated: true,
            user: <String, Object?>{
              'id': 'u-owner',
              'display_name': 'Ayo Manager',
              'role': 'user',
            },
            affinityProfile: <String, Object?>{},
            club: <String, Object?>{'id': 'c-1', 'name': 'Lagos Stars FC'},
            followers: 12,
            following: 4,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CLUB OWNER'), findsWidgets);
      expect(
        find.text('RUN Lagos Stars FC LIKE A REAL FOOTBALL OFFICE'),
        findsOneWidget,
      );
      expect(find.text('Enter competitions'), findsOneWidget);
      expect(find.text('Sign players'), findsOneWidget);
      expect(find.text('Hire coaches'), findsOneWidget);
      expect(find.text('Set lineup'), findsOneWidget);
      expect(find.textContaining('coming soon'), findsNothing);
    });

    testWidgets('G2: Fan / No-Club Home renders user desk & quick actions', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1440, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        buildHomeHost(
          profileData: const ProfileData(
            authenticated: true,
            user: <String, Object?>{
              'id': 'u-fan',
              'display_name': 'Supporter',
              'role': 'user',
            },
            affinityProfile: <String, Object?>{},
            club: null,
            followers: 0,
            following: 0,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('USER DESK'), findsWidgets);
      expect(
        find.text('GET READY TO OWN A FOOTBALL OPERATION'),
        findsOneWidget,
      );
      expect(find.text('Buy players'), findsOneWidget);
      expect(find.text('Search regens'), findsOneWidget);
    });

    testWidgets(
      'G3: Scouting Home renders scouting & recruitment desk for scout/agent roles',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 2400);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(
          buildHomeHost(
            profileData: const ProfileData(
              authenticated: true,
              user: <String, Object?>{
                'id': 'u-scout',
                'display_name': 'Chief Scout',
                'role': 'scout',
              },
              affinityProfile: <String, Object?>{},
              club: null,
              followers: 0,
              following: 0,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('SCOUTING DESK'), findsWidgets);
        expect(
          find.text('FIND THE NEXT GENERATION BEFORE THE MARKET MOVES'),
          findsOneWidget,
        );
        expect(find.text('Search players'), findsOneWidget);
        expect(find.text('Search regens'), findsOneWidget);
        expect(find.text('Scout tasks'), findsOneWidget);
      },
    );

    testWidgets(
      'HomeAttentionPanel renders GtexAttentionCard items and truthful empty state',
      (WidgetTester tester) async {
        String? openedRoute;
        String? wentRoute;

        // 1. Empty state ("Nothing needs you right now")
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: HomeAttentionPanel(
                digestValue: AsyncValue.data(buildDigest()),
                onOpen: (String route) => openedRoute = route,
                onGo: (String route) => wentRoute = route,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-home-attention-empty')),
          findsOneWidget,
        );
        expect(find.text('Nothing needs you right now'), findsOneWidget);
        expect(find.byType(GtexAttentionCard), findsNothing);

        // 2. Populated state with GtexAttentionCard
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: HomeAttentionPanel(
                digestValue: AsyncValue.data(
                  buildDigest(
                    attentionItems: const <GtexHomeAttentionItem>[
                      GtexHomeAttentionItem(
                        id: 'att-1',
                        label: 'Review 2 pending transfer bids',
                        routeLocation: '/transfer-center',
                        useGo: false,
                      ),
                      GtexHomeAttentionItem(
                        id: 'att-2',
                        label: 'Confirm matchday lineup',
                        routeLocation: '/app/matches',
                        useGo: true,
                      ),
                    ],
                  ),
                ),
                onOpen: (String route) => openedRoute = route,
                onGo: (String route) => wentRoute = route,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(GtexAttentionCard), findsNWidgets(2));
        expect(find.text('Review 2 pending transfer bids'), findsOneWidget);
        expect(find.text('Confirm matchday lineup'), findsOneWidget);

        await tester.tap(find.text('Review 2 pending transfer bids'));
        await tester.pumpAndSettle();
        expect(openedRoute, '/transfer-center');

        await tester.tap(find.text('Confirm matchday lineup'));
        await tester.pumpAndSettle();
        expect(wentRoute, '/app/matches');
      },
    );

    test('home_screen.dart contains zero raw Color(0x...) hex literals', () {
      final File file = File('lib/features/home/home_screen.dart');
      final String source = file.readAsStringSync();
      expect(
        RegExp(r'Color\(0x[0-9A-Fa-f]+\)').hasMatch(source),
        isFalse,
        reason:
            'home_screen.dart must use GtexNavyColors/GtexFloodlit tokens.',
      );
      expect(
        source.contains('is coming soon.'),
        isFalse,
        reason: 'home_screen.dart must not render coming-soon snackbars.',
      );
    });
  });
}
