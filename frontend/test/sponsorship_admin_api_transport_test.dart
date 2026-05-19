import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/sponsorship_admin_api.dart';

void main() {
  test('sponsorship admin api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_packageJson('pkg-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_contractJson('contract-1', 'club-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _contractJson('contract-1', 'club-1'),
        ),
      ],
    );
    final SponsorshipAdminApi api = SponsorshipAdminApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listPackages();
    await api.listClubContracts('club-1');
    await api.reviewContract(contractId: 'contract-1', action: 'approve');

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/admin/sponsorship/packages',
        '/api/v2/sponsorship/clubs/club-1/contracts',
        '/api/v2/admin/sponsorship/contracts/contract-1/review',
      ],
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

Map<String, Object?> _packageJson(String id) => <String, Object?>{
  'id': id,
  'code': 'gold',
  'name': 'Gold visibility package',
  'asset_type': 'stadium',
  'base_amount_minor': 2500000,
  'currency': 'USD',
  'default_duration_months': 12,
  'payout_schedule': 'quarterly',
  'description': 'High visibility inventory rights.',
  'is_active': true,
};

Map<String, Object?> _contractJson(String id, String clubId) =>
    <String, Object?>{
      'id': id,
      'club_id': clubId,
      'package_id': 'pkg-1',
      'asset_type': 'stadium',
      'sponsor_name': 'Prime Sportswear',
      'status': 'pending',
      'contract_amount_minor': 2500000,
      'currency': 'USD',
      'duration_months': 12,
      'payout_schedule': 'quarterly',
      'start_at': '2026-04-01T00:00:00Z',
      'end_at': '2027-03-31T00:00:00Z',
      'moderation_required': true,
      'moderation_status': 'pending',
      'custom_copy': null,
      'custom_logo_url': null,
      'performance_bonus_minor': 0,
      'settled_amount_minor': 0,
      'outstanding_amount_minor': 2500000,
      'created_at': '2026-03-12T00:00:00Z',
      'updated_at': '2026-03-12T00:00:00Z',
    };

