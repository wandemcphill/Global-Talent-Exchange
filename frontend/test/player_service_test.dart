import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/data/player_service.dart';
import 'package:gte_frontend/models/player.dart';

void main() {
  test(
    'player model parses real-universe detail payload via backend mapper',
    () {
      final Player player = Player.fromBackend(<String, Object?>{
        'player_id': 'player-osimhen',
        'player_name': 'Victor Osimhen',
        'primary_position': 'Striker',
        'age': 27,
        'nationality': 'Nigeria',
        'current_club_name': 'Istanbul Lions',
        'metadata_json': <String, Object?>{
          'image_url': 'https://cdn.gtex.test/osimhen.png',
        },
      });

      expect(player.id, 'player-osimhen');
      expect(player.name, 'Victor Osimhen');
      expect(player.position, 'Striker');
      expect(player.age, 27);
      expect(player.country, 'Nigeria');
      expect(player.club, 'Istanbul Lions');
      expect(player.imageUrl, 'https://cdn.gtex.test/osimhen.png');
    },
  );

  test('get player reads from real-universe detail route', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-osimhen',
            'player_name': 'Victor Osimhen',
            'position': 'Striker',
            'age': 27,
            'nationality': 'Nigeria',
            'current_club_name': 'Istanbul Lions',
          },
        ),
      ],
    );
    final PlayerService service = PlayerService(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: null,
        mode: GteBackendMode.live,
      ),
    );

    final Player player = await service.getPlayer('player-osimhen');

    expect(player.name, 'Victor Osimhen');
    expect(
      transport.requests.single.uri.path,
      '/api/v1/players/real-universe/player-osimhen',
    );
    expect(
      transport.requests.single.headers.containsKey('Authorization'),
      isFalse,
    );
  });

  test(
    'list players uses unified players route when search term is present',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Map<String, Object?>>[
                <String, Object?>{
                  'player_id': 'player-saliba',
                  'player_name': 'William Saliba',
                  'position': 'Centre-Back',
                  'age': 25,
                  'nationality': 'France',
                  'current_club_name': 'North London Reds',
                },
              ],
              'limit': 20,
              'offset': 0,
              'total': 1,
            },
          ),
        ],
      );
      final PlayerService service = PlayerService(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: null,
          mode: GteBackendMode.live,
        ),
      );

      final List<Player> players = await service.listPlayers(search: 'Saliba');

      expect(players, hasLength(1));
      expect(players.single.id, 'player-saliba');
      expect(transport.requests.single.uri.path, '/api/v1/players');
      expect(transport.requests.single.uri.queryParameters['search'], 'Saliba');
    },
  );

  test('get players derives cursor pagination from offset payload', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Map<String, Object?>>[
              <String, Object?>{
                'player_id': 'player-saka',
                'player_name': 'Bukayo Saka',
                'position': 'Winger',
                'age': 24,
                'nationality': 'England',
                'current_club_name': 'North London Reds',
              },
            ],
            'limit': 1,
            'offset': 0,
            'total': 2,
          },
        ),
      ],
    );
    final PlayerService service = PlayerService(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: null,
        mode: GteBackendMode.live,
      ),
    );

    final PaginatedPlayers page = await service.getPlayers(limit: 1);

    expect(page.players, hasLength(1));
    expect(page.players.single.id, 'player-saka');
    expect(page.nextCursor, '1');
    expect(page.hasMore, isTrue);
    expect(transport.requests.single.uri.queryParameters['limit'], '1');
  });

  test('get players honors explicit cursor response fields', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'players': <Map<String, Object?>>[
              <String, Object?>{
                'player_id': 'player-osimhen',
                'player_name': 'Victor Osimhen',
                'position': 'Striker',
                'age': 27,
                'nationality': 'Nigeria',
                'current_club_name': 'Istanbul Lions',
              },
            ],
            'next_cursor': 'opaque-cursor-2',
            'has_more': true,
          },
        ),
      ],
    );
    final PlayerService service = PlayerService(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: null,
        mode: GteBackendMode.live,
      ),
    );

    final PaginatedPlayers page = await service.getPlayers(
      cursor: '1',
      limit: 1,
    );

    expect(page.players, hasLength(1));
    expect(page.players.single.id, 'player-osimhen');
    expect(page.nextCursor, 'opaque-cursor-2');
    expect(page.hasMore, isTrue);
    expect(transport.requests.single.uri.queryParameters['cursor'], '1');
  });

  test(
    'get players stops pagination when offset payload is exhausted',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Map<String, Object?>>[
                <String, Object?>{
                  'player_id': 'player-saliba',
                  'player_name': 'William Saliba',
                  'position': 'Centre-Back',
                  'age': 25,
                  'nationality': 'France',
                  'current_club_name': 'North London Reds',
                },
              ],
              'limit': 1,
              'offset': 1,
              'total': 2,
            },
          ),
        ],
      );
      final PlayerService service = PlayerService(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: null,
          mode: GteBackendMode.live,
        ),
      );

      final PaginatedPlayers page = await service.getPlayers(
        cursor: '1',
        limit: 1,
      );

      expect(page.players, hasLength(1));
      expect(page.players.single.id, 'player-saliba');
      expect(page.nextCursor, isNull);
      expect(page.hasMore, isFalse);
    },
  );

  test('get players includes unified filter query parameters', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'players': <Map<String, Object?>>[],
            'has_more': false,
          },
        ),
      ],
    );
    final PlayerService service = PlayerService(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: null,
        mode: GteBackendMode.live,
      ),
    );

    await service.getPlayers(
      limit: 20,
      search: 'ronaldo',
      position: 'ST',
      country: 'Nigeria',
      minAge: 18,
      maxAge: 28,
      availability: 'free_agent',
    );

    expect(transport.requests.single.uri.path, '/api/v1/players');
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('search', 'ronaldo'),
    );
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('position', 'ST'),
    );
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('country', 'Nigeria'),
    );
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('min_age', '18'),
    );
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('max_age', '28'),
    );
    expect(
      transport.requests.single.uri.queryParameters,
      containsPair('availability', 'free_agent'),
    );
  });

  test(
    'list players keeps offset compatibility on the unified route',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Map<String, Object?>>[],
              'limit': 20,
              'offset': 20,
              'total': 20,
            },
          ),
        ],
      );
      final PlayerService service = PlayerService(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: null,
          mode: GteBackendMode.live,
        ),
      );

      await service.listPlayers(offset: 20);

      expect(transport.requests.single.uri.path, '/api/v1/players');
      expect(transport.requests.single.uri.queryParameters['offset'], '20');
      expect(
        transport.requests.single.uri.queryParameters.containsKey('cursor'),
        isFalse,
      );
    },
  );

  test(
    'player actions fail closed before transport when routes are not mounted',
    () async {
      final _RecordingTransport transport =
          _RecordingTransport(<GteTransportResponse>[
            const GteTransportResponse(statusCode: 200, body: null),
            const GteTransportResponse(statusCode: 200, body: null),
            const GteTransportResponse(statusCode: 200, body: null),
          ]);
      final PlayerService service = PlayerService(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: 'demo-token',
          mode: GteBackendMode.live,
        ),
      );

      await expectLater(
        service.scout('player-osimhen'),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.unavailable,
          ),
        ),
      );
      await expectLater(
        service.shortlist('player-osimhen'),
        throwsA(isA<GteApiException>()),
      );
      await expectLater(
        service.contact('player-osimhen'),
        throwsA(isA<GteApiException>()),
      );
      expect(transport.requests, isEmpty);
    },
  );

  test(
    'player action failures stay unavailable across all legacy entry points',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found'},
          ),
          GteTransportResponse(
            statusCode: 503,
            body: <String, Object?>{'detail': 'Unavailable'},
          ),
          GteTransportResponse(
            statusCode: 500,
            body: <String, Object?>{'detail': 'Error'},
          ),
        ],
      );
      final PlayerService service = PlayerService(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.live,
          ),
          transport: transport,
          accessToken: 'demo-token',
          mode: GteBackendMode.live,
        ),
      );

      await expectLater(
        service.scout('player-osimhen'),
        throwsA(isA<GteApiException>()),
      );
      await expectLater(
        service.shortlist('player-osimhen'),
        throwsA(isA<GteApiException>()),
      );
      await expectLater(
        service.contact('player-osimhen'),
        throwsA(isA<GteApiException>()),
      );

      expect(transport.requests, isEmpty);
    },
  );
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
