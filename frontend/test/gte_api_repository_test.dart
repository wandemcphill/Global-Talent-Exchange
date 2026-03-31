import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'live-then-fixture mode falls back to fixtures for market reads',
    () async {
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: GteMockApi(latency: Duration.zero),
      );

      final List<PlayerSnapshot> players = await repository.fetchPlayers();

      expect(players, hasLength(4));
      expect(players.first.id, 'lamine-yamal');
    },
  );

  test(
    'login does not fall back to fixture auth on transport failure',
    () async {
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: GteMockApi(latency: Duration.zero),
      );

      expect(
        () => repository.login(
          const GteAuthLoginRequest(
            email: 'qa@example.com',
            password: 'DemoPass123',
          ),
        ),
        throwsA(isA<GteApiException>()),
      );
    },
  );

  test(
    'fetch current user does not fall back to fixture auth on transport failure',
    () async {
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('stale-token');
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
      );

      expect(repository.fetchCurrentUser, throwsA(isA<GteApiException>()));
    },
  );

  test(
    'fetch player profile maps native live market detail without fixture profile copy',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'identity': <String, Object?>{
              'player_name': 'Active Runtime Prospect',
              'current_club_name': 'Ibadan Lions FC',
              'nationality': 'Nigeria',
              'position': 'CM',
              'age': 21,
            },
            'value': <String, Object?>{
              'current_value_credits': 1200,
              'movement_pct': 4.5,
            },
            'trend': <String, Object?>{
              'global_scouting_index': 88,
              'average_rating': 7.2,
            },
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'symbol': 'A. Prospect',
            'last_price': 1200,
            'best_bid': 1190,
            'best_ask': 1210,
            'spread': 20,
            'mid_price': 1200,
            'reference_price': 1180,
            'day_change': 20,
            'day_change_percent': 1.69,
            'volume_24h': 4,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'interval': '1h',
            'candles': <Map<String, Object?>>[
              <String, Object?>{
                'timestamp': '2026-03-31T10:00:00Z',
                'open': 1180,
                'high': 1210,
                'low': 1175,
                'close': 1200,
                'volume': 4,
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'generated_at': '2026-03-31T10:00:00Z',
            'bids': <Map<String, Object?>>[
              <String, Object?>{'price': 1190, 'quantity': 3, 'order_count': 1},
            ],
            'asks': <Map<String, Object?>>[
              <String, Object?>{'price': 1210, 'quantity': 2, 'order_count': 1},
            ],
          },
        ),
      ]);
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: _ThrowingProfileFixtureApi(),
      );

      final PlayerProfile profile = await repository.fetchPlayerProfile(
        'player-123',
      );

      expect(profile.snapshot.id, 'player-123');
      expect(profile.snapshot.name, 'Active Runtime Prospect');
      expect(profile.snapshot.club, 'Ibadan Lions FC');
      expect(profile.snapshot.marketCredits, 1200);
      expect(profile.snapshot.gsi, 88);
      expect(profile.snapshot.formRating, 7.2);
      expect(profile.snapshot.valueTrend, hasLength(1));
      expect(profile.gsiTrend, hasLength(1));
      expect(profile.awards, isEmpty);
      expect(profile.statBlocks, isEmpty);
      expect(profile.ticker?.playerId, 'player-123');
      expect(profile.orderBook?.playerId, 'player-123');
      expect(profile.candles?.playerId, 'player-123');
    },
  );

  test(
    'fetch player profile in live-then-fixture mode does not load legacy compatibility fixtures when live detail succeeds',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'identity': <String, Object?>{
              'player_name': 'Live Only Prospect',
              'current_club_name': 'Abuja Stars FC',
              'nationality': 'Nigeria',
              'position': 'ST',
              'age': 20,
            },
            'value': <String, Object?>{
              'current_value_credits': 950,
              'movement_pct': 2.5,
            },
            'trend': <String, Object?>{
              'global_scouting_index': 79,
              'average_rating': 7.0,
            },
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'symbol': 'L. Only',
            'last_price': 950,
            'best_bid': 940,
            'best_ask': 960,
            'spread': 20,
            'mid_price': 950,
            'reference_price': 930,
            'day_change': 20,
            'day_change_percent': 2.15,
            'volume_24h': 3,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'interval': '1h',
            'candles': <Map<String, Object?>>[
              <String, Object?>{
                'timestamp': '2026-03-31T10:00:00Z',
                'open': 930,
                'high': 960,
                'low': 925,
                'close': 950,
                'volume': 3,
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'generated_at': '2026-03-31T10:00:00Z',
            'bids': <Map<String, Object?>>[
              <String, Object?>{'price': 940, 'quantity': 2, 'order_count': 1},
            ],
            'asks': <Map<String, Object?>>[
              <String, Object?>{'price': 960, 'quantity': 2, 'order_count': 1},
            ],
          },
        ),
      ]);
      final _RecordingProfileFixtureApi fixtures =
          _RecordingProfileFixtureApi();
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: transport,
        fixtures: fixtures,
      );

      final PlayerProfile profile = await repository.fetchPlayerProfile(
        'player-123',
      );

      expect(profile.snapshot.name, 'Live Only Prospect');
      expect(fixtures.fetchPlayerProfileCalls, 0);
    },
  );

  test(
    'fetch player profile in live mode does not fall back to fixture truth on transport failure',
    () async {
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: _ThrowingTransport(),
        fixtures: _ThrowingProfileFixtureApi(),
      );

      expect(
        () => repository.fetchPlayerProfile('player-123'),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.network,
          ),
        ),
      );
    },
  );

  test(
    'login persists token and reuses it on authenticated requests',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'access_token': 'live-token',
              'session_id': 'live-session',
              'token_type': 'bearer',
              'expires_in': 3600,
              'user': <String, Object?>{
                'id': 'user-1',
                'email': 'qa@example.com',
                'username': 'qa_user',
                'display_name': 'QA User',
                'role': 'user',
              },
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'id': 'user-1',
              'email': 'qa@example.com',
              'username': 'qa_user',
              'display_name': 'QA User',
              'role': 'user',
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
        authSessionStore: authSessionStore,
      );

      final GteAuthSession session = await repository.login(
        const GteAuthLoginRequest(
          email: 'qa@example.com',
          password: 'DemoPass123',
        ),
      );
      final GteCurrentUser user = await repository.fetchCurrentUser();

      expect(session.accessToken, 'live-token');
      expect(session.sessionId, 'live-session');
      expect(await tokenStore.readToken(), 'live-token');
      expect((await authSessionStore.readSession())?.userId, 'user-1');
      expect((await authSessionStore.readSession())?.sessionId, 'live-session');
      expect(user.username, 'qa_user');
      expect(
        transport.requests.last.headers['Authorization'],
        'Bearer live-token',
      );
    },
  );

  test('logout clears persisted auth session', () async {
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
    final GteReliableApiRepository repository = GteReliableApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: _RecordingTransport(const <GteTransportResponse>[]),
      fixtures: GteMockApi(latency: Duration.zero),
      tokenStore: tokenStore,
      authSessionStore: authSessionStore,
    );

    await tokenStore.writeToken('live-token');
    await authSessionStore.writeSession(
      const AuthSession(
        userId: 'user-1',
        accessToken: 'live-token',
        sessionId: 'session-1',
      ),
    );

    await repository.logout();

    expect(await tokenStore.readToken(), isNull);
    expect(await authSessionStore.readSession(), isNull);
  });

  test(
    'list orders serializes repeated status filters for open order queries',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[],
              'limit': 10,
              'offset': 0,
              'total': 0,
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('orders-token');
      final GteReliableApiRepository repository = GteReliableApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
      );

      await repository.listOrders(
        limit: 10,
        statuses: const <GteOrderStatus>[
          GteOrderStatus.open,
          GteOrderStatus.partiallyFilled,
        ],
      );

      expect(
        transport.requests.single.uri.queryParametersAll['status'],
        <String>['open', 'partially_filled'],
      );
      expect(
        transport.requests.single.headers['Authorization'],
        'Bearer orders-token',
      );
    },
  );
}

class _ThrowingTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw Exception('network down');
  }
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

class _ThrowingProfileFixtureApi extends GteMockApi {
  _ThrowingProfileFixtureApi() : super(latency: Duration.zero);

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    throw Exception('fixture profile unavailable');
  }
}

class _RecordingProfileFixtureApi extends GteMockApi {
  _RecordingProfileFixtureApi() : super(latency: Duration.zero);

  int fetchPlayerProfileCalls = 0;

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    fetchPlayerProfileCalls += 1;
    return super.fetchPlayerProfile(playerId);
  }
}
