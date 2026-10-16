import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/club_redesign/data/gtex_club_ownership_api.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';

void main() {
  test('fetchMyClubPortfolio reads GET /api/portfolio/clubs', () async {
    const Map<String, Object?> body = <String, Object?>{
      'club_count': 1,
      'total_market_value_coin': 39.6,
      'total_cost_basis_coin': 30,
      'total_unrealized_pl_coin': 9.6,
      'holdings': <Map<String, Object?>>[
        <String, Object?>{
          'club_id': 'club-1',
          'club_name': 'Port Harcourt Dynamos',
          'tokens_owned': 30,
          'avg_price_coin': 1,
          'share_price_coin': 1.32,
          'market_value_coin': 39.6,
          'cost_basis_coin': 30,
          'unrealized_pl_coin': 9.6,
          'governance_enabled': true,
        },
      ],
    };

    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 200, body: body),
      ],
    );
    final GtexClubOwnershipApi api = GtexClubOwnershipApi(
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

    final GtexClubOwnershipPortfolio portfolio = await api.fetchMyClubPortfolio();

    expect(portfolio.clubCount, 1);
    expect(portfolio.holdings.single.clubName, 'Port Harcourt Dynamos');
    expect(transport.requests.single.method, 'GET');
    expect(transport.requests.single.uri.path, '/api/v2/portfolio/clubs');
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
