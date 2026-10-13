import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/jackpot_admin_api.dart';

void main() {
  test('jackpot admin api uses canonical admin routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: _runtimeJson()),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'hist-1',
              'round_number': 1,
              'status': 'settled',
              'distribution_mode': 'single_winner',
              'current_balance': '100.0000',
              'winning_user_id': 'user-1',
              'triggered_at': '2026-10-13T12:00:00Z',
              'settled_at': '2026-10-13T12:01:00Z',
              'payouts': const <Object?>[],
            },
          ],
        ),
        GteTransportResponse(statusCode: 200, body: _runtimeJson()),
        GteTransportResponse(statusCode: 200, body: _runtimeJson()),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'detail': 'Triggered',
            'triggered_round_id': 'round-1',
            'triggered_round_number': 1,
            'next_round_id': 'round-2',
            'next_round_number': 2,
          },
        ),
      ],
    );
    final JackpotAdminApi api = JackpotAdminApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-1',
        mode: GteBackendMode.live,
      ),
    );

    await api.fetchRuntime();
    await api.fetchHistory(limit: 12);
    await api.updateRuntime(<String, Object?>{
      'threshold_amount': '1000.0000',
      'probability_limit': '0.5000',
      'probability_cap': '0.2500',
      'failsafe_hours': 12,
      'contribution_rate': '0.0500',
      'distribution_mode': 'single_winner',
      'top_split_percent': '0.6000',
      'min_activity_score': '1.0000',
    });
    await api.updateBalance(balance: '250.0000', reason: 'desk top-up');
    await api.triggerRound();

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/admin/jackpot/runtime',
        '/api/v2/jackpot/history',
        '/api/v2/admin/jackpot/runtime',
        '/api/v2/admin/jackpot/balance',
        '/api/v2/admin/jackpot/trigger',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['limit'], '12');
    expect(transport.requests[3].method, 'PATCH');
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

Map<String, Object?> _runtimeJson() => <String, Object?>{
      'round_id': 'round-1',
      'round_number': 1,
      'status': 'open',
      'balance': '120.0000',
      'threshold_amount': '1000.0000',
      'probability_limit': '0.5000',
      'probability_cap': '0.2500',
      'contribution_rate': '0.0500',
      'participant_count': 4,
      'failsafe_at': '2026-10-14T12:00:00Z',
      'distribution_mode': 'single_winner',
      'top_split_percent': '0.6000',
      'min_activity_score': '1.0000',
      'failsafe_hours': 12,
      'last_winner_user_id': null,
      'last_trigger_mode': null,
      'settings_source': 'runtime',
    };
