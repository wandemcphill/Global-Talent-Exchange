import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/models/match_view_state.dart';

void main() {
  test('fixture client paginates and filters the market directory', () async {
    final GteExchangeApiClient client = GteExchangeApiClient.fixture();

    final firstPage = await client.fetchPlayers();
    final filtered = await client.fetchPlayers(
      query: const GteMarketPlayersQuery(search: 'Yamal'),
    );

    expect(firstPage.items, isNotEmpty);
    expect(firstPage.total, greaterThan(0));
    expect(filtered.items, hasLength(1));
    expect(filtered.items.single.playerName, 'Lamine Yamal');
  });

  test('fixture client composes player detail, ticker, candles, and order book',
      () async {
    final GteExchangeApiClient client = GteExchangeApiClient.fixture();

    final snapshot = await client.fetchPlayerMarket('lamine-yamal');

    expect(snapshot.detail.identity.playerName, 'Lamine Yamal');
    expect(snapshot.ticker.playerId, 'lamine-yamal');
    expect(snapshot.candles.candles, isNotEmpty);
    expect(snapshot.orderBook.bids, isNotEmpty);
  });

  test('fixture client exposes an illiquid player shape for sparse UI states',
      () async {
    final GteExchangeApiClient client = GteExchangeApiClient.fixture();

    final snapshot = await client.fetchPlayerMarket('victor-osimhen');

    expect(snapshot.candles.candles, hasLength(1));
    expect(snapshot.orderBook.bids, isEmpty);
    expect(snapshot.orderBook.asks, isNotEmpty);
  });

  test('match viewer requests include the selected mode query parameter',
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

    await client.fetchMatchViewer(
      'match-001',
      mode: MatchMode.cinematic,
    );

    expect(transport.lastRequest, isNotNull);
    expect(transport.lastRequest!.uri.path, '/api/match-viewer/match-001');
    expect(transport.lastRequest!.uri.queryParameters['mode'], 'cinematic');
  });
}

class _RecordingTransport implements GteTransport {
  GteTransportRequest? lastRequest;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    lastRequest = request;
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
