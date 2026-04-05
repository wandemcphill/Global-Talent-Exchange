import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/federations/live_federations_provider.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  test(
    'player market client parses live /marketplace/players payloads',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v1/marketplace/players': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'players': <Object?>[
                <String, Object?>{
                  'player_id': 'player-osimhen',
                  'player_name': 'Victor Osimhen',
                  'position': 'ST',
                  'nationality': 'Nigeria',
                  'current_club_name': 'Galata Lions',
                  'age': 27,
                  'current_value_credits': 1450.0,
                  'movement_pct': 0.12,
                  'trend_score': 8.5,
                  'market_interest_score': 91,
                  'average_rating': 7.8,
                  'is_available': true,
                  'availability_label': 'Available now',
                  'asking_type': 'transfer',
                  'agent_user_id': 'agent-1',
                  'agent_name': 'Seed Agent',
                },
              ],
              'limit': 20,
              'has_more': false,
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

      expect(transport.requests.single.uri.path, '/api/v1/marketplace/players');
      expect(market.items, hasLength(1));
      expect(market.items.single.playerId, 'player-osimhen');
      expect(market.items.single.agentName, 'Seed Agent');
      expect(market.total, 1);
    },
  );

  test('world aggregate provider parses map-backed regen payloads', () async {
    final ProviderContainer container = _buildContainer(
      transport: _PathTransport(<String, GteTransportResponse>{
        '/api/v1/regen-universe/rising-stars': const GteTransportResponse(
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
        '/api/v1/regen-universe/scouting-feed': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'id': 'scout-1', 'headline': 'New wonderkid'},
            ],
          },
        ),
        '/api/v1/regen-universe/seasons': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'season_id': 'season-1', 'label': '2026/27'},
            ],
          },
        ),
        '/api/v1/regen-universe/awards': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[
              <String, Object?>{'award_id': 'award-1', 'title': 'Golden Boy'},
            ],
          },
        ),
        '/api/v1/regen-universe/hall-of-fame': const GteTransportResponse(
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
        '/api/v1/federations': const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{'id': 'fed-1', 'name': 'West Africa Federation'},
          ],
        ),
        '/api/v1/regen-universe/tracking': const GteTransportResponse(
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
    'federations hub provider composes live rankings and regional rollups',
    () async {
      final ProviderContainer container = _buildContainer(
        transport: _PathTransport(<String, GteTransportResponse>{
          '/api/v1/federations': const GteTransportResponse(
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
          '/api/v1/federations/rankings': const GteTransportResponse(
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
          '/api/v1/federations/regional-tournaments':
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
    'national teams hub provider parses map-backed national regen seeds',
    () async {
      final ProviderContainer container = _buildContainer(
        transport: _PathTransport(<String, GteTransportResponse>{
          '/api/v1/national-team-engine/competitions':
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
          '/api/v1/national-team-engine/rankings': const GteTransportResponse(
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
          '/api/v1/regen-universe/national-regens': const GteTransportResponse(
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
      expect(hub.nationalRegens.single['display_name'], 'Chinonso Prospect');
    },
  );

  test(
    'transfer center detail keeps the listing when negotiation returns unauthorized',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v1/transfer-market/listings/listing-1':
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
          '/api/v1/transfer-market/listings/listing-1/negotiation':
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
