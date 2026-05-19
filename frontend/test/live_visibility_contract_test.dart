import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/federations/live_federations_provider.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  test(
    'player market client parses live /api/market/players payloads',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/market/players': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[
                <String, Object?>{
                  'player_id': 'player-osimhen',
                  'player_name': 'Victor Osimhen',
                  'position': 'ST',
                  'nationality': 'Nigeria',
                  'current_club_name': 'Galata Lions',
                  'age': 27,
                  'current_value_credits': 1450.0,
                  'movement_pct': 12.0,
                  'trend_score': 8.5,
                  'market_interest_score': 91,
                  'average_rating': 7.8,
                },
              ],
              'limit': 20,
              'offset': 0,
              'total': 1,
            },
          ),
        },
      );
      final GteExchangeApiClient client = GteExchangeApiClient(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        repository: GteMockApi(),
      );

      final market = await client.fetchPlayers();

      expect(transport.requests.single.uri.path, '/api/v2/market/players');
      expect(market.items, hasLength(1));
      expect(market.items.single.playerId, 'player-osimhen');
      expect(market.items.single.availabilityLabel, 'Available now');
      expect(market.total, 1);
    },
  );

  test('world aggregate provider parses map-backed regen payloads', () async {
    final ProviderContainer container = _buildContainer(
      transport: _PathTransport(<String, GteTransportResponse>{
        '/api/v2/regen-universe/rising-stars': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'entries': <Object?>[
              <String, Object?>{
                'player_id': 'regen-1',
                'player_name': 'Ayo Star',
              },
            ],
          },
        ),
        '/api/v2/regen-universe/scouting-feed': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'id': 'scout-1', 'headline': 'New wonderkid'},
            ],
          },
        ),
        '/api/v2/regen-universe/seasons': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'season_id': 'season-1', 'label': '2026/27'},
            ],
          },
        ),
        '/api/v2/regen-universe/awards': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'award_id': 'award-1', 'title': 'Golden Boy'},
            ],
          },
        ),
        '/api/v2/regen-universe/hall-of-fame': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'entries': <Object?>[
              <String, Object?>{
                'player_id': 'legend-1',
                'player_name': 'Legend One',
              },
            ],
          },
        ),
        '/api/v2/federations': const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{'id': 'fed-1', 'name': 'West Africa Federation'},
          ],
        ),
        '/api/v2/regen-universe/tracking': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'season_phase': 'live'},
        ),
      }),
      overrides: [
        competitionHubProvider.overrideWith((Ref ref) async {
          return const CompetitionHubData(
            gtexCompetitions: [],
            hostedCompetitions: [],
            streamerTournaments: [],
          );
        }),
      ],
    );
    addTearDown(container.dispose);

    final WorldAggregateData aggregate = await container.read(
      worldAggregateProvider.future,
    );

    expect(aggregate.risingStars, hasLength(1));
    expect(aggregate.scoutingFeed, hasLength(1));
    expect(aggregate.seasons, hasLength(1));
    expect(aggregate.awards, hasLength(1));
    expect(aggregate.federations, hasLength(1));
    expect(aggregate.tracking['season_phase'], 'live');
  });

  test(
    'community api maps live follow, watchlist, thread, and direct-message actions',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/community/creator-clubs/ibadan-lions/follow':
              const GteTransportResponse(
                statusCode: 201,
                body: <String, Object?>{'status': 'created'},
              ),
          '/api/v2/community/watchlist': GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'id': 'watch-2',
              'competition_key': 'all-stars',
              'competition_title': 'All Stars Cup',
              'competition_type': 'creator',
              'notify_on_story': true,
              'notify_on_launch': true,
              'metadata_json': const <String, Object?>{},
              'created_at': DateTime.utc(2026, 4, 13).toIso8601String(),
              'updated_at': DateTime.utc(2026, 4, 13).toIso8601String(),
            },
          ),
          '/api/v2/community/live-threads': GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'id': 'thread-2',
              'thread_key': 'all-stars-watch',
              'competition_key': 'all-stars',
              'title': 'All Stars Watch Party',
              'created_by_user_id': 'user-1',
              'status': 'open',
              'pinned': false,
              'last_message_at': null,
              'metadata_json': const <String, Object?>{},
              'created_at': DateTime.utc(2026, 4, 13).toIso8601String(),
              'updated_at': DateTime.utc(2026, 4, 13).toIso8601String(),
            },
          ),
          '/api/v2/community/private-messages/threads': GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'id': 'pm-2',
              'thread_key': 'all-stars-dm',
              'created_by_user_id': 'user-1',
              'status': 'open',
              'subject': 'All Stars prep',
              'last_message_at': null,
              'metadata_json': const <String, Object?>{},
              'created_at': DateTime.utc(2026, 4, 13).toIso8601String(),
              'updated_at': DateTime.utc(2026, 4, 13).toIso8601String(),
              'participants': <Object?>[
                <String, Object?>{
                  'id': 'part-1',
                  'thread_id': 'pm-2',
                  'user_id': 'user-1',
                  'is_muted': false,
                  'last_read_at': null,
                  'joined_at': DateTime.utc(2026, 4, 13).toIso8601String(),
                  'metadata_json': const <String, Object?>{},
                },
                <String, Object?>{
                  'id': 'part-2',
                  'thread_id': 'pm-2',
                  'user_id': 'user-7',
                  'is_muted': false,
                  'last_read_at': null,
                  'joined_at': DateTime.utc(2026, 4, 13).toIso8601String(),
                  'metadata_json': const <String, Object?>{},
                },
              ],
            },
          ),
        },
      );
      final CommunityApi api = CommunityApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      await api.followCreatorClub(clubId: 'ibadan-lions');
      final watchlist = await api.addWatchlist(
        competitionKey: 'all-stars',
        competitionTitle: 'All Stars Cup',
        competitionType: 'creator',
      );
      final thread = await api.createLiveThread(
        threadKey: 'all-stars-watch',
        title: 'All Stars Watch Party',
        competitionKey: 'all-stars',
      );
      final privateThread = await api.createPrivateThread(
        participantUserIds: const <String>['user-7'],
        initialMessage: 'Let us align before kickoff.',
        subject: 'All Stars prep',
      );

      expect(
        transport.requests.map((GteTransportRequest request) => request.method),
        <String>['POST', 'POST', 'POST', 'POST'],
      );
      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/community/creator-clubs/ibadan-lions/follow',
          '/api/v2/community/watchlist',
          '/api/v2/community/live-threads',
          '/api/v2/community/private-messages/threads',
        ],
      );
      expect(
        (transport.requests[1].body as Map<String, Object?>)['competition_key'],
        'all-stars',
      );
      expect(
        (transport.requests[2].body as Map<String, Object?>)['thread_key'],
        'all-stars-watch',
      );
      expect(
        (transport.requests[3].body
            as Map<String, Object?>)['participant_user_ids'],
        const <String>['user-7'],
      );
      expect(watchlist.competitionTitle, 'All Stars Cup');
      expect(thread.title, 'All Stars Watch Party');
      expect(privateThread.subject, 'All Stars prep');
    },
  );

  test(
    'federations hub provider composes live rankings and regional rollups',
    () async {
      final ProviderContainer container = _buildContainer(
        transport: _PathTransport(<String, GteTransportResponse>{
          '/api/v2/federations': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'id': 'fed-1',
                'name': 'West Africa Federation',
                'ranking_score': 84.2,
                'reputation_score': 79.5,
                'audience_size': 240000,
                'treasury_balance': 3500.0,
                'members_json': <Object?>[
                  <String, Object?>{'club_id': 'club-1'},
                ],
                'is_public': true,
                'default_reality_mode': 'hybrid',
              },
            ],
          ),
          '/api/v2/federations/rankings': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'federation_id': 'fed-1',
                'name': 'West Africa Federation',
                'ranking_score': 84.2,
                'reputation_score': 79.5,
                'audience_size': 240000,
                'activity_score': 88.0,
                'competitiveness_score': 82.0,
              },
            ],
          ),
          '/api/v2/federations/regional-tournaments':
              const GteTransportResponse(
                statusCode: 200,
                body: <Object?>[
                  <String, Object?>{
                    'region_code': 'west-africa',
                    'region_label': 'West Africa',
                    'federation_count': 1,
                    'active_league_count': 3,
                    'total_member_clubs': 12,
                  },
                ],
              ),
        }),
      );
      addTearDown(container.dispose);

      final FederationHubData hub = await container.read(
        federationsHubProvider.future,
      );

      expect(hub.federations, hasLength(1));
      expect(hub.rankings, hasLength(1));
      expect(hub.regionalTournaments, hasLength(1));
      expect(hub.regionalTournaments.single.regionLabel, 'West Africa');
    },
  );

  test(
    'federations api posts live governance proposal and vote actions',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/federations/fed-1/proposals': const GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'id': 'proposal-1',
              'title': 'Expand qualifiers',
              'status': 'open',
            },
          ),
          '/api/v2/federations/proposals/proposal-1/votes':
              const GteTransportResponse(
                statusCode: 200,
                body: <String, Object?>{
                  'id': 'vote-1',
                  'proposal_id': 'proposal-1',
                  'vote_type': 'yes',
                },
              ),
        },
      );
      final FederationsApi api = FederationsApi(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'https://example.test',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: 'token',
          mode: GteBackendMode.live,
        ),
      );

      final FederationProposalActionResult created = await api.createProposal(
        federationId: 'fed-1',
        title: 'Expand qualifiers',
        summary: 'Increase regional qualifier access for the next season.',
      );
      final FederationProposalActionResult voted = await api.castProposalVote(
        proposalId: 'proposal-1',
        voteType: 'yes',
      );

      expect(created.id, 'proposal-1');
      expect(voted.voteType, 'yes');
      expect(transport.requests, hasLength(2));
      expect(
        transport.requests.first.uri.path,
        '/api/v2/federations/fed-1/proposals',
      );
      expect(
        transport.requests.first.body,
        isA<Map<String, Object?>>()
            .having(
              (Map<String, Object?> body) => body['proposal_type'],
              'proposal_type',
              'rule_change',
            )
            .having(
              (Map<String, Object?> body) => body['title'],
              'title',
              'Expand qualifiers',
            ),
      );
      expect(
        transport.requests.last.uri.path,
        '/api/v2/federations/proposals/proposal-1/votes',
      );
      expect(
        transport.requests.last.body,
        isA<Map<String, Object?>>().having(
          (Map<String, Object?> body) => body['vote_type'],
          'vote_type',
          'yes',
        ),
      );
    },
  );

  test(
    'national teams hub provider parses map-backed national regen seeds',
    () async {
      final ProviderContainer container = _buildContainer(
        transport: _PathTransport(<String, GteTransportResponse>{
          '/api/v2/national-team-engine/competitions':
              const GteTransportResponse(
                statusCode: 200,
                body: <Object?>[
                  <String, Object?>{
                    'id': 'competition-1',
                    'key': 'nations-cup-2030',
                    'title': 'Nations Cup 2030',
                    'season_label': '2030',
                    'region_type': 'global',
                    'age_band': 'senior',
                    'format_type': 'cup',
                    'status': 'open',
                    'notes': 'Seeded live contract test',
                    'active': true,
                    'created_at': '2026-04-05T00:00:00Z',
                    'updated_at': '2026-04-05T00:00:00Z',
                  },
                ],
              ),
          '/api/v2/national-team-engine/rankings': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'country_code': 'NG',
                'country_name': 'Nigeria',
                'elo_rating': 1850,
                'matches_played': 12,
                'wins': 8,
                'draws': 2,
                'losses': 2,
                'titles': 1,
              },
            ],
          ),
          '/api/v2/regen-universe/national-regens': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[
                <String, Object?>{
                  'id': 'regen-seed-1',
                  'display_name': 'Chinonso Prospect',
                  'country_code': 'NG',
                  'country_name': 'Nigeria',
                  'seed_type': 'elite',
                  'primary_position': 'ST',
                  'current_rating': 72,
                  'potential_rating': 90,
                  'rarity_tier': 'rare',
                  'status': 'tracked',
                },
              ],
            },
          ),
        }),
      );
      addTearDown(container.dispose);

      final NationalTeamsHubData hub = await container.read(
        nationalTeamsHubProvider.future,
      );

      expect(hub.competitions, hasLength(1));
      expect(hub.rankings, hasLength(1));
      expect(hub.nationalRegens, hasLength(1));
      expect(hub.nationalRegens.single.displayName, 'Chinonso Prospect');
      expect(hub.nationalRegens.single.nationalPoolOnly, isTrue);
    },
  );

  test(
    'transfer center detail keeps the listing when negotiation returns unauthorized',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/transfer-market/listings/listing-1':
              const GteTransportResponse(
                statusCode: 200,
                body: <String, Object?>{
                  'id': 'listing-1',
                  'player_id': 'player-1',
                  'selling_club_id': 'club-1',
                  'base_price': 75.0,
                  'current_highest_bid': 82.0,
                  'status': 'open',
                  'expires_at': '2026-04-06T00:00:00Z',
                  'time_remaining': 600,
                  'player': <String, Object?>{
                    'id': 'player-1',
                    'full_name': 'Victor Osimhen',
                    'current_club_name': 'Galata Lions',
                  },
                  'bidders': <Object?>[],
                  'watchlist_count': 4,
                  'bid_count': 2,
                  'suggested_price': 78.0,
                  'market_signal': 'Live transfer listing',
                  'channel': 'market:listing-1',
                },
              ),
          '/api/v2/transfer-market/listings/listing-1/negotiation':
              const GteTransportResponse(
                statusCode: 401,
                body: <String, Object?>{'detail': 'Authentication required.'},
              ),
        },
      );
      final AuthSession session = const AuthSession(
        userId: 'user-1',
        accessToken: 'token-1',
        refreshToken: '',
        sessionId: 'session-1',
        role: 'user',
      );
      final ProviderContainer container = _buildContainer(
        transport: transport,
        session: session,
      );
      addTearDown(container.dispose);

      final TransferCenterDetailData detail = await container.read(
        transferCenterDetailProvider('listing-1').future,
      );

      expect(detail.listing['id'], 'listing-1');
      expect(detail.negotiation, isNull);
      expect(
        transport.requests.last.headers['Authorization'],
        'Bearer token-1',
      );
    },
  );

  test(
    'market dashboard provider reads buyable player shares from /players/markets payload',
    () async {
      final ProviderContainer container = _buildContainer(
        transport: _PathTransport(<String, GteTransportResponse>{
          '/api/v2/players/markets': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[
                <String, Object?>{
                  'player_id': 'player-1',
                  'player_name': 'Harry Kane',
                  'position': 'ST',
                  'nationality': 'England',
                  'current_club_name': 'Bayern Munich',
                  'status': 'active',
                  'share_price_coin': 18.5,
                  'total_shares': 1000,
                  'circulating_shares': 620,
                },
              ],
              'total': 1,
              'page': 1,
              'per_page': 24,
            },
          ),
          '/api/v2/transfer-market/listings': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'id': 'listing-1',
                'player_id': 'player-1',
                'base_price': 7000000.0,
                'current_highest_bid': 7250000.0,
                'status': 'open',
                'watchlist_count': 4,
                'bid_count': 2,
                'market_signal': 'Live transfer listing',
                'channel': 'market:listing-1',
                'time_remaining': 3600,
                'player': <String, Object?>{
                  'full_name': 'Harry Kane',
                  'current_club_name': 'Bayern Munich',
                },
              },
            ],
          ),
        }),
      );
      addTearDown(container.dispose);

      final MarketDashboardData dashboard = await container.read(
        marketDashboardProvider.future,
      );

      expect(dashboard.playerShares, hasLength(1));
      expect(dashboard.playerShares.single.playerName, 'Harry Kane');
      expect(dashboard.playerShares.single.marketStatus, 'active');
      expect(dashboard.transferListings, hasLength(1));
      expect(dashboard.transferListings.single.playerName, 'Harry Kane');
    },
  );

  test(
    'market dashboard provider reads search-only discovery players from the unified players list payload',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/players/markets': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[],
              'total': 0,
              'page': 1,
              'per_page': 24,
            },
          ),
          '/api/v2/players': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'players': <Object?>[
                <String, Object?>{
                  'player_id': 'player-2',
                  'player_name': 'Jamal Musiala',
                  'position': 'AM',
                  'nationality': 'Germany',
                  'current_club_name': 'Bayern Munich',
                  'current_value_credits': 660.0,
                  'market_interest_score': 198,
                },
              ],
              'limit': 24,
              'has_more': false,
              'total': 1,
            },
          ),
          '/api/v2/transfer-market/listings': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[],
          ),
        },
      );
      final ProviderContainer container = _buildContainer(transport: transport);
      addTearDown(container.dispose);

      container.read(marketSearchQueryProvider.notifier).setQuery('musiala');

      final MarketDashboardData dashboard = await container.read(
        marketDashboardProvider.future,
      );

      expect(dashboard.playerShares, hasLength(1));
      expect(dashboard.discoveryOnlyPlayerShares, hasLength(1));
      expect(
        dashboard.discoveryOnlyPlayerShares.single.playerName,
        'Jamal Musiala',
      );
      expect(
        dashboard.discoveryOnlyPlayerShares.single.marketStatus,
        'inactive',
      );
      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        containsAll(<String>['/api/v2/players/markets', '/api/v2/players']),
      );
      expect(
        transport.requests
            .where(
              (GteTransportRequest request) =>
                  request.uri.path == '/api/v2/players',
            )
            .single
            .uri
            .queryParameters['search'],
        'musiala',
      );
    },
  );
}

ProviderContainer _buildContainer({
  required _PathTransport transport,
  AuthSession? session,
  List overrides = const [],
}) {
  final GteAuthedApi api = GteAuthedApi(
    config: const GteRepositoryConfig(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.live,
    ),
    transport: transport,
    authSession: session,
    deviceId: 'device-test',
    mode: GteBackendMode.live,
  );
  return ProviderContainer(
    overrides: [
      authProvider.overrideWith((Ref ref) => session),
      authedApiProvider.overrideWith((Ref ref) => api),
      ...overrides,
    ],
  );
}

class _PathTransport implements GteTransport {
  _PathTransport(this.responses);

  final Map<String, GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return responses[request.uri.path] ??
        const GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'Not found.'},
        );
  }
}

