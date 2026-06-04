import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/market/data/market_api_service.dart';
import 'package:gte_frontend/features/market/domain/market_models.dart';
import 'package:gte_frontend/features/market/repository/market_repository.dart';

void main() {
  test('search players reads the canonical market players contract', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'items': <Object?>[_listingJson()],
            'total': 1,
            'page': 1,
            'page_size': 24,
          },
        ),
      ],
    );
    final BackendMarketRepository repository = _repository(transport);

    final MarketPage<MarketPlayerDTO> page = await repository.searchPlayers(
      MarketFilters.empty(),
    );

    expect(page.items, hasLength(1));
    expect(page.items.single.id, 'player-1');
    expect(
      transport.requests.single.uri.path,
      '/api/v2/transfer-market/players',
    );
    expect(transport.requests.single.uri.queryParameters['status'], 'open');
  });

  test('checkout uses backend readiness contract', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'ready': false,
            'blocked_reasons': <Object?>['Owner approval required'],
            'items': <Object?>[
              <String, Object?>{
                'id': 'basket-1',
                'player_id': 'player-1',
                'added_at': '2026-05-01T12:00:00Z',
                'checkout_eligible': true,
              },
            ],
          },
        ),
      ],
    );
    final BackendMarketRepository repository = _repository(transport);

    final MarketCheckoutDTO checkout = await repository.getCheckout();

    expect(checkout.ready, isFalse);
    expect(checkout.blockedReasons, contains('Owner approval required'));
    expect(checkout.items, hasLength(1));
    expect(
      transport.requests.single.uri.path,
      '/api/v2/transfer-market/checkout',
    );
  });

  test(
    'submit checkout posts the canonical market checkout contract',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'ready': true,
              'audit_ref': 'checkout-audit-1',
            },
          ),
        ],
      );
      final MarketApiService api = _api(transport);

      final JsonMap payload = await api.submitCheckout(
        idempotencyKey: 'checkout-audit-1',
        notes: 'Ready to submit',
      );

      expect(payload['audit_ref'], 'checkout-audit-1');
      expect(transport.requests.single.method, 'POST');
      expect(
        transport.requests.single.uri.path,
        '/api/v2/transfer-market/checkout',
      );
      expect(transport.requests.single.body, <String, Object?>{
        'idempotency_key': 'checkout-audit-1',
        'notes': 'Ready to submit',
      });
    },
  );

  test('active bids block when reservation truth is missing', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'bid-1',
              'player_id': 'player-1',
              'buying_club_id': 'buyer-club',
              'selling_club_id': 'seller-club',
              'amount': '300.0000',
              'status': 'pending',
              'created_at': '2026-05-01T12:00:00Z',
            },
          ],
        ),
      ],
    );
    final BackendMarketRepository repository = _repository(transport);

    expect(
      () => repository.getActiveBids(const MarketBidsRequest()),
      throwsA(
        isA<MarketBackendDataException>().having(
          (MarketBackendDataException e) => e.code,
          'code',
          'market.wallet_reservation_truth_missing',
        ),
      ),
    );
  });

  test(
    'withdraw bid without window id uses market bid withdraw contract',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'id': 'bid-1',
              'listing_id': 'listing-1',
              'player_id': 'player-1',
              'buying_club_id': 'buyer-club',
              'selling_club_id': 'seller-club',
              'amount': '300.0000',
              'status': 'withdrawn',
              'created_at': '2026-05-01T12:00:00Z',
            },
          ),
        ],
      );
      final BackendMarketRepository repository = _repository(transport);

      final MarketBidDTO bid = await repository.withdrawBid(
        const WithdrawBidRequest(
          windowId: '',
          bidId: 'bid-1',
          reason: 'No longer pursuing',
        ),
      );

      expect(bid.status, MarketBidStatus.withdrawn);
      expect(transport.requests.single.method, 'POST');
      expect(
        transport.requests.single.uri.path,
        '/api/v2/transfer-market/bid/bid-1/withdraw',
      );
      expect(transport.requests.single.body, <String, Object?>{
        'reason': 'No longer pursuing',
      });
    },
  );
}

BackendMarketRepository _repository(_RecordingTransport transport) {
  return BackendMarketRepository(api: _api(transport));
}

MarketApiService _api(_RecordingTransport transport) {
  final GteAuthedApi client = GteAuthedApi(
    config: const GteRepositoryConfig(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.live,
    ),
    transport: transport,
    accessToken: 'token-1',
    mode: GteBackendMode.live,
  );
  return MarketApiService(client: client);
}

Map<String, Object?> _listingJson() {
  return const <String, Object?>{
    'id': 'listing-1',
    'player_id': 'player-1',
    'selling_club_id': 'seller-club',
    'base_price': '1700000.0000',
    'status': 'open',
    'player': <String, Object?>{
      'id': 'player-1',
      'full_name': 'Reserved Funds Forward',
      'normalized_position': 'forward',
      'current_club_name': 'Seller FC',
    },
  };
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport([List<GteTransportResponse>? responses])
    : _responses = responses ?? <GteTransportResponse>[];

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    if (_responses.isEmpty) {
      return const GteTransportResponse(statusCode: 200, body: <Object?>[]);
    }
    return _responses.removeAt(0);
  }
}
