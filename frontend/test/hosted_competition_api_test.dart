import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/hosted_competition_api.dart';

void main() {
  test('hosted competition api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(statusCode: 200, body: <Object?>[]),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competitions': <Object?>[]},
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competitions': <Object?>[]},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'competition': _competitionJson('comp-1'),
            'template': _templateJson('tpl-1'),
            'participants': const <Object?>[],
            'current_participants': 0,
            'join_open': true,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_inviteJson('invite-1', 'comp-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'competition': _competitionJson('comp-1'),
            'invites': <Object?>[_inviteJson('invite-1', 'comp-1')],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_standingJson('standing-1', 'comp-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: const <String, Object?>{
            'currency': 'FAN',
            'participant_count': 8,
            'entry_fee_fancoin': 5,
            'gross_collected': 40,
            'projected_reward_pool': 80,
            'projected_platform_fee': 6,
            'escrow_balance': 34,
            'settled_prizes': 0,
            'settled_platform_fee': 0,
            'status': 'open',
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
        const GteTransportResponse(statusCode: 200, body: <Object?>[]),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
      ],
    );
    final HostedCompetitionApi api = HostedCompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listTemplates();
    await api.listCompetitions();
    await api.listMyCompetitions();
    await api.fetchDetail('comp-1');
    await api.createCompetition(
      templateKey: 'creator-cup',
      title: 'Creator Cup',
    );
    await api.joinCompetition('comp-1');
    await api.listInvites('comp-1');
    await api.createInvites(
      competitionId: 'comp-1',
      recipientUserIds: const <String>['user-2'],
    );
    await api.acceptInvite(competitionId: 'comp-1', inviteId: 'invite-1');
    await api.listStandings('comp-1');
    await api.fetchFinance('comp-1');
    await api.launchCompetition('comp-1');
    await api.seedTemplates();
    await api.finalizeCompetition(
      competitionId: 'comp-1',
      placements: const <Map<String, Object?>>[],
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v1/hosted-competitions/templates',
        '/api/v1/hosted-competitions',
        '/api/v1/hosted-competitions/mine',
        '/api/v1/hosted-competitions/comp-1',
        '/api/v1/hosted-competitions',
        '/api/v1/hosted-competitions/comp-1/join',
        '/api/v1/hosted-competitions/comp-1/invites',
        '/api/v1/hosted-competitions/comp-1/invites',
        '/api/v1/hosted-competitions/comp-1/invites/accept',
        '/api/v1/hosted-competitions/comp-1/standings',
        '/api/v1/hosted-competitions/comp-1/finance',
        '/api/v1/hosted-competitions/comp-1/launch',
        '/api/v1/admin/hosted-competitions/seed',
        '/api/v1/admin/hosted-competitions/comp-1/finalize',
      ],
    );
  });

  test('seed templates uses POST on the admin seed endpoint', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final HostedCompetitionApi api = HostedCompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'admin-token',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.seedTemplates();

    expect(transport.requests, hasLength(1));
    expect(transport.requests.single.method, 'POST');
    expect(
      transport.requests.single.uri.path,
      '/api/v1/admin/hosted-competitions/seed',
    );
  });

  test('join and admin create send launch competition fields', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'competition': _competitionJson('comp-1')},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'competition': _competitionJson(
              'comp-2',
              metadata: const <String, Object?>{
                'gtex_hosted': true,
                'host_type': 'gtex_hosted',
              },
            ),
          },
        ),
      ],
    );
    final HostedCompetitionApi api = HostedCompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'admin-token',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.joinCompetition('comp-1', passcode: 'cup-123');
    await api.adminCreateCompetition(
      templateKey: 'user-hosted-cup-8',
      title: 'GTEX Weekend Cup',
      gtexHosted: true,
      entryFeeFancoin: 0,
      joinPasscode: 'vip',
    );

    expect(
      transport.requests.first.uri.path,
      '/api/v1/hosted-competitions/comp-1/join',
    );
    expect(transport.requests.first.body, <String, Object?>{
      'passcode': 'cup-123',
    });
    expect(
      transport.requests.last.uri.path,
      '/api/v1/admin/hosted-competitions',
    );
    expect(transport.requests.last.body, containsPair('gtex_hosted', true));
    expect(transport.requests.last.body, containsPair('join_passcode', 'vip'));
  });
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

Map<String, Object?> _templateJson(String id) => <String, Object?>{
  'id': id,
  'template_key': 'creator-cup',
  'title': 'Creator Cup',
  'description': 'Invite-driven creator competition.',
  'competition_type': 'creator',
  'team_type': 'club',
  'age_grade': 'senior',
  'cup_or_league': 'cup',
  'participants': 16,
  'viewing_mode': 'broadcast',
  'gift_rules': const <String, Object?>{},
  'seeding_method': 'balanced',
  'is_user_hostable': true,
  'entry_fee_fancoin': 5,
  'reward_pool_fancoin': 80,
  'platform_fee_bps': 800,
  'metadata_json': const <String, Object?>{},
  'active': true,
};

Map<String, Object?> _competitionJson(
  String id, {
  Map<String, Object?> metadata = const <String, Object?>{},
}) => <String, Object?>{
  'id': id,
  'template_id': 'tpl-1',
  'host_user_id': 'user-1',
  'title': 'Creator Cup',
  'slug': 'creator-cup',
  'description': 'Invite-driven creator competition.',
  'status': 'open',
  'visibility': 'public',
  'max_participants': 16,
  'entry_fee_fancoin': 5,
  'reward_pool_fancoin': 80,
  'platform_fee_amount': 6,
  'metadata_json': metadata,
  'created_at': '2026-03-10T12:00:00Z',
  'updated_at': '2026-03-10T12:00:00Z',
};

Map<String, Object?> _inviteJson(String id, String competitionId) =>
    <String, Object?>{
      'competition_id': competitionId,
      'invite_id': id,
      'invited_by_user_id': 'user-1',
      'recipient_user_id': 'user-2',
      'status': 'pending',
      'message': 'Join the cup.',
      'created_at': '2026-03-12T12:00:00Z',
    };

Map<String, Object?> _standingJson(String id, String competitionId) =>
    <String, Object?>{
      'id': id,
      'competition_id': competitionId,
      'user_id': 'user-1',
      'final_rank': 1,
      'points': 12,
      'wins': 4,
      'draws': 0,
      'losses': 0,
      'goals_for': 10,
      'goals_against': 2,
      'payout_amount': 50,
      'metadata_json': const <String, Object?>{},
      'created_at': '2026-03-10T12:00:00Z',
      'updated_at': '2026-03-10T12:00:00Z',
    };
