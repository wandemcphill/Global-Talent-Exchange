import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/competitions/live_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/match/match_screen.dart';
import 'package:gte_frontend/features/profile/profile_admin_screen.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/tasks/tasks_screen.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/transfer_market/transfer_market_screen.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/features/world/world_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  final AuthSession session = AuthSession(
    userId: 'user-1',
    accessToken: 'token',
    sessionId: 'session-1',
    role: 'user',
  );

  testWidgets(
    'market screen renders live player discovery and honest blocked transfer actions',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith((Ref ref) => session),
            marketDashboardProvider.overrideWith((Ref ref) async {
              return const MarketDashboardData(
                playerShares: <PlayerShareSummary>[
                  PlayerShareSummary(
                    playerId: 'player-1',
                    playerName: 'Kobbie Mainoo',
                    position: 'CM',
                    nationality: 'England',
                    currentClubName: 'Manchester United',
                    age: 20,
                    currentValueCredits: 1200,
                    marketInterestScore: 92,
                    marketStatus: 'active',
                    marketMessage: 'Share market is live.',
                    sharePriceCoin: 18,
                    totalShares: 1000,
                    circulatingShares: 640,
                  ),
                ],
                holdings: <PlayerShareHoldingSummary>[],
                transferListings: <TransferListingSummary>[
                  TransferListingSummary(
                    id: 'listing-1',
                    playerId: 'player-1',
                    playerName: 'Kobbie Mainoo',
                    currentClubName: 'Manchester United',
                    currentHighestBid: 80,
                    basePrice: 70,
                    status: 'open',
                    watchlistCount: 4,
                    bidCount: 2,
                    marketSignal: 'Live transfer listing',
                    channel: 'market:listing-1',
                    timeRemaining: 600,
                  ),
                ],
                wallet: MarketWalletSnapshot(
                  coinBalance: 120,
                  creditBalance: 40,
                  totalEquity: 160,
                  canTradeMarket: true,
                  canDeposit: true,
                  canWithdraw: true,
                  complianceMessage:
                      'Wallet and compliance state loaded from live backend.',
                ),
                authenticated: true,
                warnings: <String>[],
              );
            }),
          ],
          child: const MaterialApp(
            home: Scaffold(body: TransferMarketScreen()),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Player Shares'), findsOneWidget);
      expect(find.text('Kobbie Mainoo'), findsWidgets);
      expect(
        find.text(
          'Bidding and watchlisting are blocked because this session has no verified club context.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets('competition hub renders live GTEX competition family listing', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          competitionHubProvider.overrideWith((Ref ref) async {
            return CompetitionHubData(
              gtexCompetitions: <CompetitionSummary>[_sampleCompetition()],
              hostedCompetitions: const [],
              streamerTournaments: const [],
            );
          }),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: LiveCompetitionsHubScreen(
              family: CompetitionFamilyRoute.gtex,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('GTEX Spotlight Cup'), findsOneWidget);
    expect(find.text('View detail'), findsOneWidget);
  });

  testWidgets('world screen renders live regen summary', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          worldAggregateProvider.overrideWith((Ref ref) async {
            return WorldAggregateData(
              risingStars: const <Map<String, Object?>>[
                <String, Object?>{
                  'player_name': 'Ayo Akin',
                  'position': 'ST',
                  'nationality': 'Nigeria',
                },
              ],
              scoutingFeed: const <Map<String, Object?>>[
                <String, Object?>{
                  'headline': 'Ayo Akin spikes in scouting feed',
                },
              ],
              seasons: const <Map<String, Object?>>[
                <String, Object?>{'name': '2031 season'},
              ],
              awards: const <Map<String, Object?>>[
                <String, Object?>{'name': 'Golden Regen'},
              ],
              hallOfFame: const <Map<String, Object?>>[
                <String, Object?>{'player_name': 'Legend One'},
              ],
              federations: const <Map<String, Object?>>[
                <String, Object?>{'name': 'West Africa Federation'},
              ],
              tracking: const <String, Object?>{'season_phase': 'midseason'},
              competitions: CompetitionHubData(
                gtexCompetitions: const <CompetitionSummary>[],
                hostedCompetitions: const [],
                streamerTournaments: const [],
              ),
              federationJoinReason:
                  'Federation membership is blocked: this session has no verified club context.',
            );
          }),
        ],
        child: const MaterialApp(home: Scaffold(body: WorldScreen())),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Ayo Akin'), findsOneWidget);
    expect(find.text('West Africa Federation'), findsOneWidget);
  });

  testWidgets('matches hub separates live viewer variants and simulation', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MatchScreen())),
    );

    await tester.pumpAndSettle();

    expect(find.text('2D Viewer'), findsOneWidget);
    expect(find.text('Broadcast+'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Open Flutter 3D'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Open Flutter 3D'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Simulate'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Simulate'), findsOneWidget);
  });

  testWidgets('tasks screen renders live daily challenges', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveTasksProvider.overrideWith((Ref ref) async {
            return const LiveTasksData(
              featureEnabled: true,
              authenticated: true,
              currentStreak: 4,
              longestStreak: 8,
              nextBonusAmount: 25,
              claimsToday: <Map<String, Object?>>[
                <String, Object?>{'challenge_key': 'login-bonus'},
              ],
              challenges: <DailyChallengeSummary>[
                DailyChallengeSummary(
                  challengeKey: 'login-bonus',
                  title: 'Login bonus',
                  description: 'Claim your daily login reward.',
                  rewardSummary: '25 coins',
                  claimLimitPerDay: 1,
                  availableToday: true,
                ),
              ],
            );
          }),
        ],
        child: const MaterialApp(home: Scaffold(body: TasksScreen())),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Daily challenges'), findsOneWidget);
    expect(find.text('Login bonus'), findsOneWidget);
    expect(find.text('Current streak 4'), findsOneWidget);
  });

  testWidgets('profile admin screen stays blocked for signed-out users', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: Scaffold(body: ProfileAdminScreen())),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Admin tooling is blocked'), findsOneWidget);
    expect(find.text('You are not signed in.'), findsOneWidget);
  });
}

CompetitionSummary _sampleCompetition() {
  return CompetitionSummary(
    id: 'gtex-1',
    name: 'GTEX Spotlight Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.openForJoin,
    creatorId: 'gtex',
    creatorName: 'GTEX',
    participantCount: 12,
    capacity: 16,
    currency: 'coin',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 100,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Platform-run competition',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}
