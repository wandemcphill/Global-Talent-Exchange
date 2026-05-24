import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test('wallet repository uses canonical plural wallet routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'id': 'wallet-1',
            'user_id': 'user-1',
            'balance': 1250,
            'currency': 'coin',
            'compliance_status': 'verified',
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'txn-1',
              'user_id': 'user-1',
              'type': 'top_up',
              'amount': 250,
              'status': 'confirmed',
              'reference': 'topup-1',
            },
          ],
        ),
        const GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'reference': 'topup-2',
            'payment_link': 'https://example.test/pay/topup-2',
            'amount': 500,
            'currency': 'NGN',
            'provider': 'korapay',
            'status': 'pending',
            'mock_mode': false,
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'wallet': <String, Object?>{
              'id': 'wallet-1',
              'user_id': 'user-1',
              'balance': 1750,
              'currency': 'coin',
              'compliance_status': 'verified',
            },
            'transaction': <String, Object?>{
              'id': 'txn-2',
              'user_id': 'user-1',
              'type': 'top_up',
              'amount': 500,
              'status': 'confirmed',
              'reference': 'topup-2',
            },
          },
        ),
      ],
    );
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    await tokenStore.writeToken('token-1');
    final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: GteMockApi(),
      tokenStore: tokenStore,
    );

    await repository.fetchWallet();
    await repository.listWalletTransactions(limit: 25);
    await repository.initiateWalletTopUp(
      const GteWalletTopUpInitiateRequest(amount: 500),
    );
    await repository.verifyWalletTopUp('topup-2');

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/wallets',
        '/api/v2/wallets/transactions',
        '/api/v2/wallets/top-up/initiate',
        '/api/v2/wallets/top-up/verify',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['limit'], '25');
    expect(transport.requests[3].body, <String, Object?>{
      'reference': 'topup-2',
    });
    expect(
      transport.requests.map(
        (GteTransportRequest request) => request.headers['Authorization'],
      ),
      everyElement('Bearer token-1'),
    );
  });

  test(
    'wallet repository falls back to ledger history when transactions are empty',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(statusCode: 200, body: <Object?>[]),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'page': 1,
              'page_size': 8,
              'total': 2,
              'items': <Object?>[
                <String, Object?>{
                  'id': 'entry-1',
                  'transaction_id': 'txn-1',
                  'amount': '250.0000',
                  'reference': 'wallet-topup-1',
                  'created_at': '2026-05-06T12:00:00Z',
                },
                <String, Object?>{
                  'id': 'entry-2',
                  'transaction_id': 'txn-2',
                  'amount': '-50.0000',
                  'reference': 'gift-1',
                  'created_at': '2026-05-06T12:05:00Z',
                },
              ],
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('token-2');
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(),
        tokenStore: tokenStore,
      );

      final List<GteWalletTransactionRecord> transactions = await repository
          .listWalletTransactions(limit: 8);

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>['/api/v2/wallets/transactions', '/api/v2/wallets/ledger'],
      );
      expect(transport.requests[1].uri.queryParameters, <String, String>{
        'page': '1',
        'page_size': '8',
      });
      expect(transactions, hasLength(2));
      expect(transactions.first.type, 'credit');
      expect(transactions.first.amount, 250);
      expect(transactions.last.type, 'debit');
      expect(transactions.last.amount, 50);
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
