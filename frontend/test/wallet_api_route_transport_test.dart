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
            'provider': 'paystack',
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
        '/api/v1/wallets',
        '/api/v1/wallets/transactions',
        '/api/v1/wallets/top-up/initiate',
        '/api/v1/wallets/top-up/verify',
      ],
    );
    expect(
      transport.requests[1].uri.queryParameters['limit'],
      '25',
    );
    expect(
      transport.requests[3].body,
      <String, Object?>{'reference': 'topup-2'},
    );
    expect(
      transport.requests.map(
        (GteTransportRequest request) => request.headers['Authorization'],
      ),
      everyElement('Bearer token-1'),
    );
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
