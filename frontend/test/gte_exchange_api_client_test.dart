import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/match_view_state.dart';

void main() {
  test('standard client defaults to live mode', () {
    final GteExchangeApiClient client = GteExchangeApiClient.standard(
      baseUrl: 'https://example.test',
    );

    expect(client.config.mode, GteBackendMode.live);
  });

  test('fixture client paginates and filters the market directory', () async {
    final GteExchangeApiClient client = GteExchangeApiClient.fixture();

    final firstPage = await client.fetchPlayers(
      query: const GteMarketPlayersQuery(limit: 2),
    );
    final secondPage = await client.fetchPlayers(
      query: GteMarketPlayersQuery(limit: 2, cursor: firstPage.nextCursor),
    );
    final filtered = await client.fetchPlayers(
      query: const GteMarketPlayersQuery(search: 'Yamal'),
    );

    expect(firstPage.items, isNotEmpty);
    expect(firstPage.hasMore, isTrue);
    expect(firstPage.nextCursor, isNotNull);
    expect(firstPage.total, greaterThan(0));
    expect(secondPage.items, isNotEmpty);
    expect(
      secondPage.items.any(
        (GteMarketPlayerListItem player) => firstPage.items.any(
          (GteMarketPlayerListItem firstPagePlayer) =>
              firstPagePlayer.playerId == player.playerId,
        ),
      ),
      isFalse,
    );
    expect(filtered.items, hasLength(1));
    expect(filtered.items.single.playerName, 'Lamine Yamal');
  });

  test(
    'fixture client composes player detail, ticker, candles, and order book',
    () async {
      final GteExchangeApiClient client = GteExchangeApiClient.fixture();

      final snapshot = await client.fetchPlayerMarket('lamine-yamal');

      expect(snapshot.detail.identity.playerName, 'Lamine Yamal');
      expect(snapshot.ticker.playerId, 'lamine-yamal');
      expect(snapshot.candles.candles, isNotEmpty);
      expect(snapshot.orderBook.bids, isNotEmpty);
    },
  );

  test(
    'fixture client exposes an illiquid player shape for sparse UI states',
    () async {
      final GteExchangeApiClient client = GteExchangeApiClient.fixture();

      final snapshot = await client.fetchPlayerMarket('victor-osimhen');

      expect(snapshot.candles.candles, hasLength(1));
      expect(snapshot.orderBook.bids, isEmpty);
      expect(snapshot.orderBook.asks, isNotEmpty);
    },
  );

  test(
    'fixture client exposes lifecycle snapshot data from fixture builders',
    () async {
      final GteExchangeApiClient client = GteExchangeApiClient.fixture();

      final GtePlayerLifecycleSnapshot? snapshot = await client
          .fetchPlayerLifecycleSnapshot('lamine-yamal');

      expect(snapshot, isNotNull);
      expect(snapshot?.playerId, 'lamine-yamal');
      expect(snapshot?.availabilityBadge.available, isTrue);
    },
  );

  test(
    'match viewer requests include the selected mode query parameter',
    () async {
      final _RecordingTransport transport = _RecordingTransport();
      final GteExchangeApiClient client = GteExchangeApiClient(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        repository: GteMockApi(),
      );

      await client.fetchMatchViewer('match-001', mode: MatchMode.cinematic);

      expect(transport.lastRequest, isNotNull);
      expect(transport.lastRequest!.uri.path, '/api/v1/match-viewer/match-001');
      expect(transport.lastRequest!.uri.queryParameters['mode'], 'cinematic');
    },
  );

  test(
    'live client routes market discovery through the unified players query',
    () async {
      final _RecordingTransport transport = _RecordingTransport();
      final GteExchangeApiClient client = GteExchangeApiClient(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        repository: GteMockApi(),
      );

      await client.fetchPlayers(
        query: const GteMarketPlayersQuery(
          limit: 20,
          search: 'ronaldo',
          position: 'ST',
          country: 'Nigeria',
          minAge: 18,
          maxAge: 28,
          availability: 'free_agent',
        ),
      );

      expect(transport.lastRequest, isNotNull);
      expect(transport.lastRequest!.uri.path, '/api/v1/market/players');
      expect(transport.lastRequest!.uri.queryParameters['search'], 'ronaldo');
      expect(transport.lastRequest!.uri.queryParameters['position'], 'ST');
      expect(
        transport.lastRequest!.uri.queryParameters['nationality'],
        'Nigeria',
      );
      expect(transport.lastRequest!.uri.queryParameters['min_age'], '18');
      expect(transport.lastRequest!.uri.queryParameters['max_age'], '28');
      expect(transport.lastRequest!.uri.queryParameters['availability'], isNull);
    },
  );

  test(
    'live spectate sessions fail closed without the real backend repository',
    () async {
      final GteExchangeApiClient client = GteExchangeApiClient(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: _RecordingTransport(),
        repository: GteMockApi(),
      );

      expect(
        () => client.joinMatchSpectateSession('match-001'),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.unavailable,
          ),
        ),
      );
    },
  );

  test(
    'live client fails closed for public player surfaces without consulting fixture builders',
    () async {
      await _expectPlayerSurfaceFailuresWithoutFixtureFallback(
        GteBackendMode.live,
      );
    },
  );

  test(
    'liveThenFixture client falls back to fixture builders for public player surfaces',
    () async {
      final _CountingFixtureRepository fixtures = _CountingFixtureRepository();
      final GteExchangeApiClient client = GteExchangeApiClient(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        repository: fixtures,
      );

      final GteMarketPlayerListView market = await client.fetchPlayers();
      final GteMarketPlayerDetailView detail = await client.fetchPlayerDetail(
        'lamine-yamal',
      );
      final GtePlayerOverview overview = await client.fetchPlayerOverview(
        'lamine-yamal',
      );
      final List<GteCareerEntry> career = await client.fetchPlayerCareer(
        'lamine-yamal',
      );
      final GtePlayerLifecycleSnapshot? lifecycle = await client
          .fetchPlayerLifecycleSnapshot('lamine-yamal');

      expect(market.items, isNotEmpty);
      expect(detail.playerId, 'lamine-yamal');
      expect(overview.playerId, 'lamine-yamal');
      expect(career, isNotEmpty);
      expect(lifecycle?.playerId, 'lamine-yamal');
      expect(fixtures.fetchPlayersCalls, 1);
      expect(fixtures.fetchPlayerProfileCalls, 4);
    },
  );
}

Future<void> _expectPlayerSurfaceFailuresWithoutFixtureFallback(
  GteBackendMode mode,
) async {
  final _CountingFixtureRepository fixtures = _CountingFixtureRepository();
  final GteExchangeApiClient client = GteExchangeApiClient(
    config: GteRepositoryConfig(baseUrl: 'https://example.test', mode: mode),
    transport: _ThrowingTransport(),
    repository: fixtures,
  );

  Future<void> expectNetworkError(Future<Object?> Function() action) async {
    await expectLater(
      action(),
      throwsA(
        isA<GteApiException>().having(
          (GteApiException error) => error.type,
          'type',
          GteApiErrorType.network,
        ),
      ),
    );
  }

  await expectNetworkError(() => client.fetchPlayers());
  await expectNetworkError(() => client.fetchPlayerDetail('lamine-yamal'));
  await expectNetworkError(() => client.fetchPlayerOverview('lamine-yamal'));
  await expectNetworkError(() => client.fetchPlayerCareer('lamine-yamal'));
  await expectNetworkError(
    () => client.fetchPlayerLifecycleSnapshot('lamine-yamal'),
  );

  expect(fixtures.fetchPlayersCalls, 0);
}

class _RecordingTransport implements GteTransport {
  GteTransportRequest? lastRequest;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    lastRequest = request;
    if (request.uri.path == '/api/v1/market/players') {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'items': <Object?>[],
          'limit': 20,
          'offset': 0,
          'has_more': false,
          'total': 0,
        },
      );
    }
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'match_id': 'match-001',
        'source': 'simulation',
        'match_mode': 'cinematic',
        'supports_offside': true,
        'duration_seconds': 720,
        'home_team': <String, Object?>{
          'team_id': 'home',
          'team_name': 'Home',
          'short_name': 'HOM',
          'side': 'home',
          'formation': '4-3-3',
          'primary_color': '#000000',
          'secondary_color': '#FFFFFF',
          'accent_color': '#FFAA00',
          'goalkeeper_color': '#333333',
        },
        'away_team': <String, Object?>{
          'team_id': 'away',
          'team_name': 'Away',
          'short_name': 'AWY',
          'side': 'away',
          'formation': '4-3-3',
          'primary_color': '#111111',
          'secondary_color': '#EEEEEE',
          'accent_color': '#FF5500',
          'goalkeeper_color': '#222222',
        },
        'events': <Object?>[],
        'frames': <Object?>[],
      },
    );
  }
}

class _ThrowingTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw Exception('network down');
  }
}

class _CountingFixtureRepository extends GteMockApi {
  _CountingFixtureRepository() : super(latency: Duration.zero);

  int fetchPlayersCalls = 0;
  int fetchPlayerProfileCalls = 0;

  @override
  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20}) {
    fetchPlayersCalls += 1;
    return super.fetchPlayers(limit: limit);
  }

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    fetchPlayerProfileCalls += 1;
    return super.fetchPlayerProfile(playerId);
  }
}
