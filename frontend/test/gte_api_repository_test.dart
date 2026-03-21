import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';

void main() {
  test('live-then-fixture mode falls back to fixtures for market reads',
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
  });

  test('login does not fall back to fixture auth on transport failure',
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
  });

  test('fetch current user does not fall back to fixture auth on transport failure',
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

    expect(
      repository.fetchCurrentUser,
      throwsA(isA<GteApiException>()),
    );
  });

  test('login persists token and reuses it on authenticated requests',
      () async {
    final _RecordingTransport transport =
        _RecordingTransport(<GteTransportResponse>[
      GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'access_token': 'live-token',
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
    ]);
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    final GteReliableApiRepository repository = GteReliableApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: GteMockApi(latency: Duration.zero),
      tokenStore: tokenStore,
    );

    final GteAuthSession session = await repository.login(
      const GteAuthLoginRequest(
        email: 'qa@example.com',
        password: 'DemoPass123',
      ),
    );
    final GteCurrentUser user = await repository.fetchCurrentUser();

    expect(session.accessToken, 'live-token');
    expect(await tokenStore.readToken(), 'live-token');
    expect(user.username, 'qa_user');
    expect(
      transport.requests.last.headers['Authorization'],
      'Bearer live-token',
    );
  });

  test('list orders serializes repeated status filters for open order queries',
      () async {
    final _RecordingTransport transport =
        _RecordingTransport(<GteTransportResponse>[
      const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'items': <Object?>[],
          'limit': 10,
          'offset': 0,
          'total': 0,
        },
      ),
    ]);
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
  });
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
