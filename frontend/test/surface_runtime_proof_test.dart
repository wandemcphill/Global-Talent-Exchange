import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/federations/federations_hub_screen.dart';
import 'package:gte_frontend/features/federations/live_federations_provider.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/national_teams/national_teams_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/transfer_center_screen.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/navigation/app_router.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

typedef JsonMap = Map<String, Object?>;

void main() {
  testWidgets(
    'router mounts federations, national teams, and transfer center routes',
    (WidgetTester tester) async {
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();
      final _FakeNationalTeamsApi nationalTeamsApi = _FakeNationalTeamsApi();
      final _FakeTransferCenterApi transferCenterApi =
          _FakeTransferCenterApi();
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
      expect(find.text('West Africa Federation'), findsOneWidget);
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
        AppRoutes.transferCenterDetailLocation(_FakeTransferCenterApi.listingId),
      );
      await tester.pumpAndSettle();
      expect(find.text('Victor Osimhen'), findsOneWidget);
      expect(find.text('Negotiation state'), findsOneWidget);
    },
  );

  testWidgets(
    'federation detail submits membership requests with a club context',
    (WidgetTester tester) async {
      final _FakeFederationsApi federationsApi = _FakeFederationsApi();

      await tester.pumpWidget(
        _screenHost(
          child: const FederationDetailScreen(
            federationId: _FakeFederationsApi.id,
          ),
          session: _clubSession(),
          overrides: [
            federationsApiProvider.overrideWithValue(federationsApi),
          ],
        ),
      );
      await tester.pumpAndSettle();

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
    'national team detail falls back to direct competition fetch and runs auto-build',
    (WidgetTester tester) async {
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

      await tester.tap(find.widgetWithText(OutlinedButton, 'Watchlist'));
      await tester.pumpAndSettle();

      expect(transferCenterApi.watchlistRequests, 1);
      expect(find.text('Victor Osimhen added to watchlist.'), findsOneWidget);
    },
  );
}

ProviderContainer _buildRouterContainer({
  required AuthSession session,
  required _FakeFederationsApi federationsApi,
  required _FakeNationalTeamsApi nationalTeamsApi,
  required _FakeTransferCenterApi transferCenterApi,
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

  return ProviderContainer(
    overrides: [
      authProvider.overrideWith((Ref ref) => session),
      authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
      deviceIdentityStoreProvider.overrideWithValue(
        MemoryDeviceIdentityStore(),
      ),
      deviceIdProvider.overrideWithValue('device-router'),
      profileDataProvider.overrideWith(
        (Ref ref) async => const ProfileData.unauthenticated(),
      ),
      competitionHubProvider.overrideWith((Ref ref) async => emptyHub),
      marketDashboardProvider.overrideWith((Ref ref) async => emptyMarket),
      worldAggregateProvider.overrideWith((Ref ref) async {
        return const WorldAggregateData(
          risingStars: <Map<String, Object?>>[],
          scoutingFeed: <Map<String, Object?>>[],
          seasons: <Map<String, Object?>>[],
          awards: <Map<String, Object?>>[],
          hallOfFame: <Map<String, Object?>>[],
          federations: <Map<String, Object?>>[],
          tracking: <String, Object?>{'season_phase': 'live'},
          competitions: emptyHub,
          federationJoinReason:
              'Dedicated federation and national-team routes now handle the live flows.',
        );
      }),
      liveTasksProvider.overrideWith((Ref ref) async {
        return const LiveTasksData(
          authenticated: true,
          featureEnabled: true,
          challenges: <DailyChallengeSummary>[],
          claimsToday: <Map<String, Object?>>[],
          currentStreak: 0,
          longestStreak: 0,
          nextBonusAmount: 0,
        );
      }),
      federationsApiProvider.overrideWithValue(federationsApi),
      nationalTeamsApiProvider.overrideWithValue(nationalTeamsApi),
      transferCenterApiProvider.overrideWithValue(transferCenterApi),
    ],
  );
}

Widget _screenHost({
  required Widget child,
  AuthSession? session,
  List overrides = const [],
}) {
  return ProviderScope(
    overrides: [
      authProvider.overrideWith((Ref ref) => session),
      ...overrides,
    ],
    child: MaterialApp(home: Scaffold(body: child)),
  );
}

AuthSession _clubSession() {
  return const AuthSession(
    userId: 'user-1',
    accessToken: 'token-1',
    sessionId: 'session-1',
    role: 'user',
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
      'rules': <String, Object?>{
        'salary_cap': 'enabled',
        'foreign_limit': 5,
      },
      'members': <Map<String, Object?>>[
        <String, Object?>{'club_id': 'ibadan-lions', 'status': 'active'},
      ],
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
      'proposals': <Map<String, Object?>>[
        <String, Object?>{
          'title': 'Expand regional qualifiers',
          'status': 'open',
          'yes_votes': 7,
          'no_votes': 2,
          'abstain_votes': 1,
        },
      ],
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
    return const FederationMembershipResult(
      status: 'active',
      role: 'member_club',
      violations: <String>[],
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

  static const TransferCenterListingRecord _listing = TransferCenterListingRecord(
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
  }) async {}

  @override
  Future<void> submitContractOffer({
    required String listingId,
    required String clubId,
    required double wageOfferAmount,
    required int contractYears,
    String? expectedRole,
  }) async {}
}
