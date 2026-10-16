import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test('ticker parsing accepts mixed numeric encodings', () {
    final GteMarketTicker ticker = GteMarketTicker.fromJson(<String, Object?>{
      'player_id': 'player-123',
      'symbol': 'A. Prospect',
      'last_price': '120.5',
      'best_bid': 118,
      'best_ask': '122.0',
      'spread': 4,
      'mid_price': '120.0',
      'reference_price': 119.5,
      'day_change': '5.0',
      'day_change_percent': 4.3478,
      'volume_24h': '3.5',
    });

    expect(ticker.playerId, 'player-123');
    expect(ticker.lastPrice, 120.5);
    expect(ticker.bestBid, 118);
    expect(ticker.bestAsk, 122);
    expect(ticker.volume24h, 3.5);
  });

  test('candles parsing preserves order and timestamps', () {
    final GteMarketCandles candles = GteMarketCandles.fromJson(<String, Object?>{
      'player_id': 'player-123',
      'interval': '1h',
      'candles': <Map<String, Object?>>[
        <String, Object?>{
          'timestamp': '2026-03-11T10:00:00Z',
          'open': '118.0',
          'high': 122,
          'low': '117.5',
          'close': 120.0,
          'volume': '2.0',
        },
        <String, Object?>{
          'timestamp': '2026-03-11T11:00:00Z',
          'open': 120,
          'high': '124.0',
          'low': 119.0,
          'close': '123.5',
          'volume': 3,
        },
      ],
    });

    expect(candles.playerId, 'player-123');
    expect(candles.candles, hasLength(2));
    expect(candles.candles.first.timestamp.toIso8601String(), '2026-03-11T10:00:00.000Z');
    expect(candles.candles.last.close, 123.5);
  });

  test('order book parsing accepts string and numeric levels', () {
    final GteOrderBook orderBook = GteOrderBook.fromJson(<String, Object?>{
      'player_id': 'player-123',
      'generated_at': '2026-03-11T12:00:00Z',
      'bids': <Map<String, Object?>>[
        <String, Object?>{'price': '12.5', 'quantity': '8.0', 'order_count': 2},
      ],
      'asks': <Map<String, Object?>>[
        <String, Object?>{'price': 13, 'quantity': 4.0, 'order_count': '1'},
      ],
    });

    expect(orderBook.playerId, 'player-123');
    expect(orderBook.generatedAt?.toIso8601String(), '2026-03-11T12:00:00.000Z');
    expect(orderBook.bids.single.price, 12.5);
    expect(orderBook.asks.single.orderCount, 1);
  });
}
