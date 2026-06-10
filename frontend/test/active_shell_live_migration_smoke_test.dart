import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/compete/presentation/live_competitions_hub_screen.dart';
import 'package:gte_frontend/features/compete/providers/live_competitions_provider.dart';
import 'package:gte_frontend/features/compete/domain/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/match_center/live_match_overview_provider.dart';
import 'package:gte_frontend/features/match_center/match_screen.dart';
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
    refreshToken: 'refresh-token',
    sessionId: 'session-1',
    role: 'user',
  );

  testWidgets(
    'market screen renders live player discovery and honest blocked transfer actions',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appConfigProvider.overrideWithValue(_testAppConfig),
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

      await _scrollTo(tester, find.text('Transfer Market'));
      expect(find.text('Transfer Market'), findsWidgets);
      expect(find.text('Scout players'), findsOneWidget);
    },
  );

  testWidgets('competition hub renders live GTEX competition family listing', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
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

    await _scrollTo(tester, find.text('GTEX Spotlight Cup'));
    expect(find.text('GTEX Spotlight Cup'), findsOneWidget);
    expect(find.text('View detail'), findsOneWidget);
  });

  testWidgets(
    'competition hub renders live streamer competition family listing',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appConfigProvider.overrideWithValue(_testAppConfig),
            competitionHubProvider.overrideWith((Ref ref) async {
              return CompetitionHubData(
                gtexCompetitions: const <CompetitionSummary>[],
                hostedCompetitions: const [],
                streamerTournaments: <StreamerTournament>[
                  _sampleStreamerTournament(),
                ],
              );
            }),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: LiveCompetitionsHubScreen(
                family: CompetitionFamilyRoute.streamer,
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await _scrollTo(tester, find.text('Streamer Sprint Series'));
      expect(find.text('Streamer Sprint Series'), findsOneWidget);
      expect(find.text('View detail'), findsOneWidget);
      expect(find.text('Streamer competitions coming soon'), findsNothing);
    },
  );

  testWidgets('world screen renders live regen summary', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
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

    await _scrollTo(tester, find.text('Ayo Akin'));
    expect(find.text('Ayo Akin'), findsOneWidget);
    await _scrollTo(tester, find.text('West Africa Federation'));
    expect(find.text('West Africa Federation'), findsOneWidget);
  });

  testWidgets('matches hub separates live viewer variants and simulation', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
          authProvider.overrideWith((Ref ref) => session),
          liveMatchOverviewProvider.overrideWith(
            (Ref ref) async => const LiveMatchOverview(
              entries: <LiveMatchOverviewEntry>[
                LiveMatchOverviewEntry(
                  matchKey: 'live-1',
                  title: 'GTEX Matchday',
                  subtitle: 'Broadcast live from Lagos.',
                  channelLabel: 'Featured channel',
                  isFeatured: true,
                  isLive: true,
                ),
              ],
              generatedAt: null,
              sourcePath: '/api/broadcast/home',
            ),
          ),
        ],
        child: const MaterialApp(home: Scaffold(body: MatchScreen())),
      ),
    );

    await tester.pumpAndSettle();

    await _scrollTo(tester, find.text('Open Match'));
    expect(find.text('Open Match'), findsOneWidget);
    expect(find.text('Open 2D'), findsNothing);
    expect(find.text('Open Broadcast+'), findsNothing);
    expect(find.text('Open 3D'), findsNothing);
    expect(find.text('View coming soon note'), findsNothing);
    expect(find.text('Open simulate'), findsNothing);
    expect(find.text('Open simulation'), findsNothing);
  });

  testWidgets('tasks screen renders live daily challenges', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
          liveTasksProvider.overrideWith((Ref ref) async {
            return const LiveTasksData(
              featureEnabled: true,
              authenticated: true,
              currentStreak: 4,
              longestStreak: 8,
              nextBonusAmount: 25,
              claimsToday: <DailyChallengeClaimSummary>[
                DailyChallengeClaimSummary(
                  claimId: 'claim-1',
                  challengeKey: 'login-bonus',
                  challengeTitle: 'Login bonus',
                  rewardLabel: '25 coins',
                  bonusAwardedLabel: '',
                  claimedAt: null,
                  streakBeforeClaim: 3,
                ),
              ],
              challenges: <DailyChallengeSummary>[
                DailyChallengeSummary(
                  challengeKey: 'login-bonus',
                  title: 'Login bonus',
                  description: 'Claim your daily login reward.',
                  rewardSummary: '25 coins',
                  claimLimitPerDay: 1,
                  claimedToday: true,
                  availableToday: false,
                ),
              ],
            );
          }),
        ],
        child: const MaterialApp(home: Scaffold(body: TasksScreen())),
      ),
    );

    await tester.pumpAndSettle();

    await _scrollTo(tester, find.text('Daily challenges'));
    expect(find.text('Daily challenges'), findsOneWidget);
    expect(find.text('Login bonus'), findsWidgets);
    expect(find.text('CURRENT STREAK'), findsWidgets);
    expect(find.text('4'), findsWidgets);
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

const GteAppConfig _testAppConfig = GteAppConfig(
  apiBaseUrl: 'https://example.test',
  backendMode: GteBackendMode.live,
);

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

StreamerTournament _sampleStreamerTournament() {
  return StreamerTournament.fromJson(<String, Object?>{
    'id': 'streamer-1',
    'host_user_id': 'host-1',
    'creator_profile_id': 'profile-1',
    'creator_club_id': 'club-1',
    'season_id': 'season-1',
    'linked_competition_id': null,
    'playoff_source_competition_id': null,
    'slug': 'streamer-sprint-series',
    'title': 'Streamer Sprint Series',
    'description': 'Creator-hosted streamer tournament',
    'tournament_type': 'elimination',
    'status': 'open',
    'approval_status': 'approved',
    'max_participants': 8,
    'requires_admin_approval': false,
    'high_reward_flag': false,
    'starts_at': '2026-06-10T12:00:00Z',
    'ends_at': null,
    'submitted_at': '2026-06-09T12:00:00Z',
    'approved_at': '2026-06-09T13:00:00Z',
    'rejected_at': null,
    'completed_at': null,
    'approved_by_user_id': 'admin-1',
    'rejected_by_user_id': null,
    'submission_notes': null,
    'approval_notes': null,
    'entry_rules_json': <String, Object?>{},
    'metadata_json': <String, Object?>{},
    'rewards': const <Object?>[],
    'invites': const <Object?>[],
    'entries': <Object?>[
      <String, Object?>{'user_id': 'user-1', 'status': 'joined'},
    ],
    'open_risk_signals': const <Object?>[],
  });
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    240,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}
