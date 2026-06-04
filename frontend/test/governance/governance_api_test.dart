import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/governance_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test('governance api uses canonical api governance routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'proposals': <Object?>[
              <String, Object?>{
                'id': 'gov-1',
                'club_id': 'club-1',
                'proposer_user_id': 'user-1',
                'scope': 'club',
                'status': 'open',
                'title': 'Raise academy scouting budget',
                'summary': 'Increase academy scouting allocation.',
                'category': 'budget',
                'voting_starts_at_iso': '2026-03-12T10:00:00Z',
                'voting_ends_at_iso': '2026-03-19T10:00:00Z',
                'minimum_tokens_required': 5,
                'quorum_token_weight': 100,
                'yes_weight': 45,
                'no_weight': 12,
                'abstain_weight': 3,
                'unique_voter_count': 18,
                'result_summary': null,
                'metadata_json': <String, Object?>{'lane': 'club'},
                'created_at': '2026-03-12T10:00:00Z',
                'updated_at': '2026-03-12T10:00:00Z',
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'proposal': <String, Object?>{
              'id': 'gov-1',
              'club_id': 'club-1',
              'proposer_user_id': 'user-1',
              'scope': 'club',
              'status': 'open',
              'title': 'Raise academy scouting budget',
              'summary': 'Increase academy scouting allocation.',
              'category': 'budget',
              'voting_starts_at_iso': '2026-03-12T10:00:00Z',
              'voting_ends_at_iso': '2026-03-19T10:00:00Z',
              'minimum_tokens_required': 5,
              'quorum_token_weight': 100,
              'yes_weight': 45,
              'no_weight': 12,
              'abstain_weight': 3,
              'unique_voter_count': 18,
              'result_summary': null,
              'metadata_json': <String, Object?>{'lane': 'club'},
              'created_at': '2026-03-12T10:00:00Z',
              'updated_at': '2026-03-12T10:00:00Z',
            },
            'votes': <Object?>[],
            'my_vote': null,
            'user_eligible': true,
            'eligibility_reason': null,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'open_proposal_count': 1,
            'clubs_with_tokens': 1,
            'eligible_club_ids': <Object?>['club-1'],
            'recent_vote_count': 4,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'proposal': <String, Object?>{
              'id': 'gov-1',
              'club_id': 'club-1',
              'proposer_user_id': 'user-1',
              'scope': 'club',
              'status': 'open',
              'title': 'Raise academy scouting budget',
              'summary': 'Increase academy scouting allocation.',
              'category': 'budget',
              'voting_starts_at_iso': '2026-03-12T10:00:00Z',
              'voting_ends_at_iso': '2026-03-19T10:00:00Z',
              'minimum_tokens_required': 5,
              'quorum_token_weight': 100,
              'yes_weight': 55,
              'no_weight': 12,
              'abstain_weight': 3,
              'unique_voter_count': 19,
              'result_summary': null,
              'metadata_json': <String, Object?>{'lane': 'club'},
              'created_at': '2026-03-12T10:00:00Z',
              'updated_at': '2026-03-13T10:00:00Z',
            },
            'vote': <String, Object?>{
              'id': 'vote-1',
              'proposal_id': 'gov-1',
              'voter_user_id': 'user-1',
              'club_id': 'club-1',
              'choice': 'yes',
              'token_weight': 10,
              'influence_weight': 10,
              'comment': 'Ship it',
              'is_proxy_vote': false,
              'metadata_json': <String, Object?>{},
              'created_at': '2026-03-13T10:00:00Z',
              'updated_at': '2026-03-13T10:00:00Z',
            },
            'summary': 'Vote recorded.',
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'id': 'gov-1',
            'club_id': 'club-1',
            'proposer_user_id': 'user-1',
            'scope': 'club',
            'status': 'closed',
            'title': 'Raise academy scouting budget',
            'summary': 'Increase academy scouting allocation.',
            'category': 'budget',
            'voting_starts_at_iso': '2026-03-12T10:00:00Z',
            'voting_ends_at_iso': '2026-03-19T10:00:00Z',
            'minimum_tokens_required': 5,
            'quorum_token_weight': 100,
            'yes_weight': 55,
            'no_weight': 12,
            'abstain_weight': 3,
            'unique_voter_count': 19,
            'result_summary': 'Closed by admin.',
            'metadata_json': <String, Object?>{'lane': 'club'},
            'created_at': '2026-03-12T10:00:00Z',
            'updated_at': '2026-03-13T12:00:00Z',
          },
        ),
      ],
    );
    final GovernanceApi api = GovernanceApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listProposals(clubId: 'club-1');
    await api.fetchProposal('gov-1');
    await api.fetchOverview();
    await api.vote(proposalId: 'gov-1', choice: 'yes', comment: 'Ship it');
    await api.updateProposalStatus(
      proposalId: 'gov-1',
      status: 'closed',
      resultSummary: 'Closed by admin.',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/governance/proposals',
        '/api/v2/governance/proposals/gov-1',
        '/api/v2/governance/me/overview',
        '/api/v2/governance/proposals/gov-1/vote',
        '/api/v2/admin/governance/proposals/gov-1/status',
      ],
    );
    expect(transport.requests.first.uri.queryParameters['club_id'], 'club-1');
    expect(
      (transport.requests[3].body as Map<String, Object?>)['choice'],
      'yes',
    );
    expect(
      (transport.requests[4].body as Map<String, Object?>)['status'],
      'closed',
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
