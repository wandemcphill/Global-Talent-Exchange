import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';

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
}
