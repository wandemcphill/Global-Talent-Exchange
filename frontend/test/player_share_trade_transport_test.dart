import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

/// Transport-level proof of the Phase 5A migration.
///
/// The player-share trading path must speak to the canonical System A market
/// (`POST /api/market/buy|sell`) using [PlayerShareTradeRequest]'s field names.
/// The endpoint accepts a *union* of request models, and the body's field
/// names are what select the branch: `share_count` reaches the player-share
/// market, whereas `shares` would silently reach the creator market instead.
void main() {
  const Map<String, Object?> tradeBody = <String, Object?>{
    'market': <String, Object?>{
      'player_id': 'player-1',
      'total_shares': 1000,
      'circulating_shares': 250,
      'share_price_coin': 12.5,
      'status': 'active',
    },
    'holding': <String, Object?>{
      'player_id': 'player-1',
      'share_count': 4,
      'average_cost_coin': 12.5,
    },
    'transaction_id': 'ledger-txn-1',
    'gross_amount_coin': 50.0,
    'fee_amount_coin': 1.0,
    'net_amount_coin': 51.0,
  };

  GteModeAwareApiRepository repositoryFor(_RecordingTransport transport) {
    return GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: GteMockApi(latency: Duration.zero),
    );
  }

  test('buying player shares posts to the canonical System A market', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 201, body: tradeBody),
      ],
    );

    final GtePlayerShareTradeResult result = await repositoryFor(transport)
        .buyPlayerShares(
      playerId: 'player-1',
      shareCount: 4,
      idempotencyKey: 'gtex-trade-player-1-buy-4-abcdefgh',
    );

    final GteTransportRequest request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/api/v2/market/buy');
    // System B's order-book endpoint must not be involved at all.
    expect(request.uri.path, isNot(contains('orders')));

    final Map<String, Object?> body = request.body! as Map<String, Object?>;
    expect(body['player_id'], 'player-1');
    // `share_count`, not `shares`: this is what routes to the player-share
    // branch of the union rather than the creator market.
    expect(body['share_count'], 4);
    expect(body.containsKey('shares'), isFalse);
    expect(body['idempotency_key'], 'gtex-trade-player-1-buy-4-abcdefgh');
    // The client never dictates the price - the server prices the trade.
    expect(body.containsKey('price'), isFalse);
    expect(body.containsKey('max_price'), isFalse);
    expect(body.containsKey('reference_price'), isFalse);

    // The result is server truth, including the ledger receipt.
    expect(result.transactionId, 'ledger-txn-1');
    expect(result.netAmountCoin, 51.0);
    expect(result.holding.shareCount, 4);
    expect(result.market.sharePriceCoin, 12.5);
  });

  test('selling player shares posts to the canonical System A market', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 201, body: tradeBody),
      ],
    );

    await repositoryFor(transport).sellPlayerShares(
      playerId: 'player-1',
      shareCount: 4,
      idempotencyKey: 'gtex-trade-player-1-sell-4-abcdefgh',
    );

    final GteTransportRequest request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/api/v2/market/sell');
    expect(request.uri.path, isNot(contains('orders')));

    final Map<String, Object?> body = request.body! as Map<String, Object?>;
    expect(body['share_count'], 4);
    expect(body.containsKey('shares'), isFalse);
    expect(body['idempotency_key'], 'gtex-trade-player-1-sell-4-abcdefgh');
  });

  test('a retried trade reuses the key rather than trading twice', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 201, body: tradeBody),
        const GteTransportResponse(statusCode: 201, body: tradeBody),
      ],
    );
    final GteModeAwareApiRepository repository = repositoryFor(transport);
    const String key = 'gtex-trade-player-1-buy-4-abcdefgh';

    // The same user action, attempted twice (as after a timeout).
    await repository.buyPlayerShares(
      playerId: 'player-1',
      shareCount: 4,
      idempotencyKey: key,
    );
    await repository.buyPlayerShares(
      playerId: 'player-1',
      shareCount: 4,
      idempotencyKey: key,
    );

    expect(transport.requests, hasLength(2));
    // Identical keys let the server replay the first trade instead of
    // creating a second one.
    expect(
      transport.requests
          .map((GteTransportRequest r) =>
              (r.body! as Map<String, Object?>)['idempotency_key'])
          .toSet(),
      <String>{key},
    );
  });

  test('a key too short for the server contract is omitted, not sent', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 201, body: tradeBody),
      ],
    );

    await repositoryFor(transport).buyPlayerShares(
      playerId: 'player-1',
      shareCount: 1,
      idempotencyKey: 'short',
    );

    final Map<String, Object?> body =
        transport.requests.single.body! as Map<String, Object?>;
    expect(body.containsKey('idempotency_key'), isFalse);
  });
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
