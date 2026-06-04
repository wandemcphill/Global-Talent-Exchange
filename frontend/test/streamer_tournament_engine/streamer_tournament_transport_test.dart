import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/compete/domain/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/compete/repositories/streamer_tournament_engine_repository.dart';

void main() {
  test('streamer tournament api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'tournaments': <Object?>[_tournamentJson('tournament-1')],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'tournaments': <Object?>[_tournamentJson('tournament-1')],
          },
        ),
        GteTransportResponse(
          statusCode: 201,
          body: _tournamentJson('tournament-1'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _tournamentJson('tournament-1'),
        ),
        GteTransportResponse(statusCode: 200, body: _policyJson()),
        GteTransportResponse(statusCode: 200, body: _policyJson()),
        GteTransportResponse(
          statusCode: 200,
          body: _tournamentJson('tournament-1'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_riskSignalJson('signal-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _riskSignalJson('signal-1'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'tournament': _tournamentJson('tournament-1'),
            'grants': const <Object?>[
              <String, Object?>{
                'id': 'grant-1',
                'user_id': 'user-2',
                'reward_type': 'coin',
                'reward_amount': 50.0,
              },
            ],
          },
        ),
      ],
    );
    final StreamerTournamentEngineApiRepository repository =
        StreamerTournamentEngineApiRepository(
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

    await repository.listPublicTournaments();
    await repository.listMyTournaments();
    await repository.createTournament(
      const StreamerTournamentCreateRequest(
        title: 'Weekend Creator Cup',
        tournamentType: 'knockout',
      ),
    );
    await repository.fetchTournament('tournament-1');
    await repository.fetchPolicy();
    await repository.upsertPolicy(
      const StreamerTournamentPolicyUpsertRequest(),
    );
    await repository.reviewTournament(
      'tournament-1',
      const StreamerTournamentReviewRequest(approve: true),
    );
    await repository.listRiskSignals();
    await repository.reviewRiskSignal(
      'signal-1',
      const StreamerTournamentRiskReviewRequest(action: 'resolve'),
    );
    await repository.settleTournament(
      'tournament-1',
      const StreamerTournamentSettleRequest(
        placements: <StreamerTournamentSettlementPlacement>[
          StreamerTournamentSettlementPlacement(userId: 'user-2', placement: 1),
        ],
      ),
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/streamer-tournaments',
        '/api/v2/streamer-tournaments/mine',
        '/api/v2/streamer-tournaments',
        '/api/v2/streamer-tournaments/tournament-1',
        '/api/v2/admin/streamer-tournaments/policy',
        '/api/v2/admin/streamer-tournaments/policy',
        '/api/v2/admin/streamer-tournaments/tournament-1/review',
        '/api/v2/admin/streamer-tournaments/risk-signals',
        '/api/v2/admin/streamer-tournaments/risk-signals/signal-1/review',
        '/api/v2/admin/streamer-tournaments/tournament-1/settle',
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

Map<String, Object?> _tournamentJson(String id) => <String, Object?>{
  'id': id,
  'host_user_id': 'user-1',
  'creator_profile_id': 'profile-1',
  'creator_club_id': 'club-1',
  'season_id': 'season-1',
  'linked_competition_id': 'competition-1',
  'playoff_source_competition_id': 'competition-2',
  'slug': 'weekend-creator-cup',
  'title': 'Weekend Creator Cup',
  'description': 'Knockout bracket for creator squads.',
  'tournament_type': 'knockout',
  'status': 'published',
  'approval_status': 'approved',
  'max_participants': 8,
  'requires_admin_approval': true,
  'high_reward_flag': false,
  'starts_at': '2026-04-18T10:00:00Z',
  'ends_at': '2026-04-18T12:00:00Z',
  'submitted_at': '2026-04-18T08:00:00Z',
  'approved_at': '2026-04-18T09:00:00Z',
  'rejected_at': null,
  'completed_at': null,
  'approved_by_user_id': 'admin-1',
  'rejected_by_user_id': null,
  'submission_notes': 'Ready for review',
  'approval_notes': 'Approved',
  'entry_rules_json': const <String, Object?>{'mode': 'invite'},
  'metadata_json': const <String, Object?>{'theme': 'creator'},
  'rewards': const <Object?>[],
  'invites': const <Object?>[],
  'entries': const <Object?>[],
  'open_risk_signals': const <Object?>[],
};

Map<String, Object?> _policyJson() => const <String, Object?>{
  'id': 'policy-1',
  'policy_key': 'default',
  'reward_coin_approval_limit': 500.0,
  'reward_credit_approval_limit': 5000.0,
  'max_cosmetic_rewards_without_review': 10,
  'max_reward_slots': 12,
  'max_invites_per_tournament': 64,
  'top_gifter_rank_limit': 25,
  'active': true,
  'config_json': <String, Object?>{},
};

Map<String, Object?> _riskSignalJson(String id) => <String, Object?>{
  'id': id,
  'tournament_id': 'tournament-1',
  'signal_key': 'reward-threshold',
  'severity': 'medium',
  'status': 'open',
  'summary': 'Reward plan requires admin review.',
  'detail': 'Credit rewards are above the automatic approval limit.',
  'detected_at': '2026-04-18T09:30:00Z',
  'reviewed_at': null,
  'reviewed_by_user_id': null,
  'metadata_json': const <String, Object?>{},
};
