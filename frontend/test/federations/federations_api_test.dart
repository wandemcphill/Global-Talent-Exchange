import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/federations/live_federations_provider.dart';

void main() {
  test('federations api uses canonical api federation routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: const <Object?>[
            <String, Object?>{
              'id': 'west-africa',
              'name': 'West Africa Federation',
              'ranking_score': 88,
              'reputation_score': 81,
              'audience_size': 1200000,
              'treasury_balance': 2000,
              'members_json': <Object?>[],
              'is_public': true,
              'default_reality_mode': 'hybrid',
            },
          ],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <Object?>[
            <String, Object?>{
              'federation_id': 'west-africa',
              'name': 'West Africa Federation',
              'ranking_score': 88,
              'reputation_score': 81,
              'audience_size': 1200000,
              'activity_score': 72,
              'competitiveness_score': 75,
            },
          ],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <Object?>[
            <String, Object?>{
              'region_code': 'wa',
              'region_label': 'West Africa',
              'federation_count': 4,
              'active_league_count': 6,
              'total_member_clubs': 24,
            },
          ],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'leagues': <Object?>[],
            'rules': <String, Object?>{},
            'members': <Object?>[],
            'reputation': <String, Object?>{},
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'proposals': <Object?>[],
            'votes': <Object?>[],
            'sanctions': <Object?>[],
          },
        ),
        GteTransportResponse(statusCode: 200, body: const <Object?>[]),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'status': 'active',
            'role': 'member_club',
            'metadata_json': <String, Object?>{
              'entry_violations': <Object?>[],
            },
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'id': 'proposal-1',
            'title': 'Expand league',
            'status': 'open',
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'proposal_id': 'proposal-1',
            'proposal_title': 'Expand league',
            'vote_type': 'approve',
          },
        ),
      ],
    );
    final FederationsApi api = FederationsApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-1',
        mode: GteBackendMode.live,
      ),
    );

    await api.listFederations();
    await api.listRankings();
    await api.listRegionalTournaments();
    await api.fetchDashboard('west-africa');
    await api.fetchGovernance('west-africa');
    await api.fetchNarratives('west-africa');
    await api.createMembership(
      federationId: 'west-africa',
      clubId: 'ibadan-lions',
    );
    await api.createProposal(
      federationId: 'west-africa',
      title: 'Expand league',
      summary: 'Add another tier',
    );
    await api.castProposalVote(proposalId: 'proposal-1', voteType: 'approve');

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/federations',
        '/api/v2/federations/rankings',
        '/api/v2/federations/regional-tournaments',
        '/api/v2/federations/west-africa',
        '/api/v2/federations/west-africa/governance',
        '/api/v2/federations/west-africa/narratives',
        '/api/v2/federations/west-africa/memberships',
        '/api/v2/federations/west-africa/proposals',
        '/api/v2/federations/proposals/proposal-1/votes',
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
