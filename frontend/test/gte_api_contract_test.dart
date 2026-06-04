import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_contract.dart';
import 'package:gte_frontend/data/generated/gte_api_contract.g.dart';

void main() {
  group('GTE API contract', () {
    test('resolves canonical transfer-market UI routes', () {
      expect(
        gteCanonicalApiPath('/api/transfer-market/players'),
        '/api/v2/transfer-market/players',
      );
      expect(
        gteCanonicalApiPath('/api/transfer-market/checkout'),
        '/api/v2/transfer-market/checkout',
      );
      expect(
        gteCanonicalApiPath('/api/transfer-market/activity'),
        '/api/v2/transfer-market/activity',
      );
    });

    test('resolves templated transfer-market player and bid routes', () {
      expect(
        gteCanonicalApiPath('/api/transfer-market/players/player-7'),
        '/api/v2/transfer-market/players/player-7',
      );
      expect(
        gteCanonicalApiPath('/api/transfer-market/bid/bid-42'),
        '/api/v2/transfer-market/bid/bid-42',
      );
      expect(
        gteCanonicalApiPath('/api/transfer-market/basket/player-7'),
        '/api/v2/transfer-market/basket/player-7',
      );
    });

    test('declares transfer-market routes in generated canonical set', () {
      expect(
        gteApiCanonicalPaths,
        containsAll(<String>{
          '/api/v2/transfer-market/players',
          '/api/v2/transfer-market/players/{player_id}',
          '/api/v2/transfer-market/bids',
          '/api/v2/transfer-market/bid/{bid_id}',
          '/api/v2/transfer-market/basket',
          '/api/v2/transfer-market/basket/{player_id}',
          '/api/v2/transfer-market/checkout',
          '/api/v2/transfer-market/activity',
          '/api/v2/transfer-market/history',
        }),
      );
    });
  });
}
