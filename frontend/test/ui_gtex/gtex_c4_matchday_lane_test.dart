import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/competitions/presentation/gtex_live_competitions_command_screen.dart';
import 'package:gte_frontend/features/match/match_viewer_route_screen.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_post_match_panel.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

CompetitionHubData _sampleCompetitionHub() {
  final DateTime now = DateTime.utc(2026, 10, 21, 12);
  return CompetitionHubData(
    gtexCompetitions: <CompetitionSummary>[
      CompetitionSummary(
        id: 'gtex-live-1',
        name: 'GTEX Premier Division',
        format: CompetitionFormat.league,
        visibility: CompetitionVisibility.public,
        status: CompetitionStatus.inProgress,
        creatorId: 'gtex',
        creatorName: 'GTEX',
        participantCount: 16,
        capacity: 20,
        currency: 'credits',
        entryFee: 0,
        platformFeePct: 0,
        hostFeePct: 0,
        platformFeeAmount: 0,
        hostFeeAmount: 0,
        prizePool: 2500,
        payoutStructure: const <CompetitionPayoutBreakdown>[],
        rulesSummary: 'GTEX league matchday.',
        matchType: MatchType.gtexHosted,
        joinEligibility: const CompetitionJoinEligibility(eligible: true),
        beginnerFriendly: true,
        createdAt: now,
        updatedAt: now,
      ),
    ],
    hostedCompetitions: <HostedCompetition>[
      HostedCompetition(
        id: 'hosted-1',
        templateId: 'tpl-1',
        hostUserId: 'host-1',
        title: 'Lagos Continental Cup',
        slug: 'lagos-continental-cup',
        description: 'Organizer hosted knockout.',
        status: 'open',
        visibility: 'public',
        startsAt: now,
        lockAt: now,
        maxParticipants: 16,
        entryFeeFancoin: 25,
        rewardPoolFancoin: 300,
        platformFeeAmount: 20,
        metadata: const <String, Object?>{},
        createdAt: now,
        updatedAt: now,
      ),
    ],
    streamerTournaments: <StreamerTournament>[
      StreamerTournament.fromJson(<String, Object?>{
        'id': 'streamer-1',
        'host_user_id': 'creator-1',
        'title': 'Creator Spotlight Clash',
        'description': 'Creator invitational circuit',
        'tournament_type': 'invitational',
        'status': 'published',
        'max_participants': 8,
        'requires_admin_approval': false,
        'high_reward_threshold': 500,
        'entries': const <Object?>[],
        'open_invitations': const <Object?>[],
      }),
    ],
  );
}

NationalTeamsHubData _sampleNationalHub() {
  final DateTime now = DateTime.utc(2026, 10, 21, 12);
  return NationalTeamsHubData(
    competitions: <NationalTeamCompetition>[
      NationalTeamCompetition(
        id: 'nt-comp-1',
        key: 'afcon-qualifiers',
        title: 'Continental Nations Championship',
        seasonLabel: '2026/27',
        regionType: 'caf',
        ageBand: 'senior',
        formatType: 'group_knockout',
        status: 'in_progress',
        notes: 'Qualifying window active',
        active: true,
        createdAt: now,
        updatedAt: now,
      ),
    ],
    rankings: const <NationalTeamCountryRankingRecord>[
      NationalTeamCountryRankingRecord(
        countryCode: 'NG',
        countryName: 'Nigeria',
        eloRating: 1845,
        matchesPlayed: 14,
        wins: 10,
        draws: 3,
        losses: 1,
        titles: 2,
      ),
    ],
    nationalRegens: const <NationalRegenSeed>[],
    regenScoutingFeed: const <RegenScoutingFeedItem>[],
    history: null,
  );
}

void main() {
  group('Phase C4 — Matchday Lane (G15)', () {
    testWidgets(
      'renders all 5 G15 Matchday sub-tabs (Fixtures · Competitions · Live · National · Calendar) and switches cleanly',
      (WidgetTester tester) async {
        await tester.binding.setSurfaceSize(const Size(1440, 1000));
        addTearDown(() => tester.binding.setSurfaceSize(null));

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              competitionHubProvider.overrideWith(
                (Ref ref) async => _sampleCompetitionHub(),
              ),
              nationalTeamsHubProvider.overrideWith(
                (Ref ref) async => _sampleNationalHub(),
              ),
            ],
            child: MaterialApp(
              home: Scaffold(
                body: GtexLiveCompetitionsCommandScreen(
                  isAuthenticated: true,
                  onOpenLogin: () {},
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        // All 5 G15 sub-tabs exist
        for (final GtexMatchdaySubTab tab in GtexMatchdaySubTab.values) {
          expect(
            find.byKey(Key('gtex-matchday-subtab-${tab.name}')),
            findsOneWidget,
          );
        }

        // Default sub-tab is Competitions with separate GTEX / Hosted / Creator families (O-02)
        expect(find.text('GTEX competitions'), findsOneWidget);
        expect(find.text('Hosted competitions'), findsOneWidget);
        expect(find.text('Creator tournaments'), findsOneWidget);

        // Switch to Fixtures sub-tab
        await tester.tap(find.byKey(const Key('gtex-matchday-subtab-fixtures')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('gtex-matchday-fixtures-view')), findsOneWidget);
        expect(find.text('GTEX Premier Division'), findsOneWidget);
        expect(find.text('Lagos Continental Cup'), findsOneWidget);
        expect(find.text('Creator Spotlight Clash'), findsOneWidget);

        // Switch to Live sub-tab and verify 2D-only rule banner
        await tester.tap(find.byKey(const Key('gtex-matchday-subtab-live')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('gtex-matchday-live-view')), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-matchday-2d-rule-banner')),
          findsOneWidget,
        );
        expect(
          find.textContaining('Flutter Matchday stays 2D tactical'),
          findsOneWidget,
        );

        // Switch to National sub-tab and verify international competitions & ELO rankings
        await tester.tap(find.byKey(const Key('gtex-matchday-subtab-national')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('gtex-matchday-national-view')), findsOneWidget);
        expect(find.text('Continental Nations Championship'), findsOneWidget);
        expect(find.textContaining('Nigeria (NG)'), findsOneWidget);

        // Switch to Calendar sub-tab
        await tester.tap(find.byKey(const Key('gtex-matchday-subtab-calendar')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('gtex-matchday-calendar-view')), findsOneWidget);
        expect(
          find.textContaining('GTEX competitions: 1 scheduled windows'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'GtexPostMatchPanel surfaces Newsroom Match Report link at Full Time alongside Portfolio and Transfer Hub',
      (WidgetTester tester) async {
        bool openedNewsroom = false;
        const GtexLiveMatchState fullTimeMatch = GtexLiveMatchState(
          matchId: 'match-ft-c4',
          home: GtexMatchTeam(
            id: 'lagos',
            name: 'Lagos Crown FC',
            shortName: 'LAG',
            score: 3,
            formation: '4-3-3',
            players: <GtexLineupPlayer>[],
          ),
          away: GtexMatchTeam(
            id: 'accra',
            name: 'Accra Stars',
            shortName: 'ACC',
            score: 1,
            formation: '4-2-3-1',
            players: <GtexLineupPlayer>[],
          ),
          minute: 90,
          phase: GtexMatchPhase.fullTime,
          pitchPlayers: <GtexPitchPlayer>[],
          timeline: <GtexMatchTimelineEvent>[],
          stats: GtexMatchStats(
            homePossession: 58,
            awayPossession: 42,
            homeShots: 14,
            awayShots: 7,
            homeShotsOnTarget: 6,
            awayShotsOnTarget: 3,
            homeExpectedGoals: 2.1,
            awayExpectedGoals: 0.9,
            homePassAccuracy: 87,
            awayPassAccuracy: 81,
          ),
          highlights: <GtexMatchHighlight>[],
          economyImpacts: <GtexMatchEconomyImpact>[],
        );

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: GtexPostMatchPanel(
                match: fullTimeMatch,
                onOpenPortfolio: () {},
                onOpenMarket: () {},
                onOpenNewsroomReport: () => openedNewsroom = true,
              ),
            ),
          ),
        );

        expect(
          find.byKey(const Key('gtex-post-match-portfolio-btn')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-post-match-market-btn')),
          findsOneWidget,
        );
        final Finder newsroomBtn = find.byKey(
          const Key('gtex-post-match-newsroom-btn'),
        );
        expect(newsroomBtn, findsOneWidget);
        expect(find.text('Open Newsroom Match Report'), findsOneWidget);

        await tester.tap(newsroomBtn);
        await tester.pump();
        expect(openedNewsroom, isTrue);
      },
    );

    testWidgets(
      'MatchViewerRouteScreen wires onOpenMatchCenter recovery callback on non-retryable blocked state',
      (WidgetTester tester) async {
        await tester.binding.setSurfaceSize(const Size(1280, 1000));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        bool openedMatchCenter = false;

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              appConfigProvider.overrideWithValue(
                const GteAppConfig(
                  apiBaseUrl: 'https://example.test',
                  backendMode: GteBackendMode.live,
                ),
              ),
            ],
            child: MaterialApp(
              home: MatchViewerRouteScreen(
                matchKey: '   ',
                onOpenMatchCenter: () => openedMatchCenter = true,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('Match unavailable'), findsWidgets);
        final Finder openBtn = find.text('Open Match Center');
        expect(openBtn, findsOneWidget);

        await tester.ensureVisible(openBtn);
        await tester.tap(openBtn);
        await tester.pump();
        expect(openedMatchCenter, isTrue);
      },
    );
  });
}
