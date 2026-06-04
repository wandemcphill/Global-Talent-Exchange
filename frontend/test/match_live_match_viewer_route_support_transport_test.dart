import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/match_center/live_match_viewer_route_support.dart';

void main() {
  test(
    'resolveBootstrap does not duplicate a 404 match-viewer bootstrap request through a legacy alias',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'not found'},
          ),
        ],
      );
      final ApiLiveMatchViewerRepository repository =
          ApiLiveMatchViewerRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
            ),
            isAuthenticated: false,
          );

      await expectLater(
        repository.resolveBootstrap('match-001'),
        throwsA(isA<GteApiException>()),
      );

      expect(transport.requests, hasLength(1));
      expect(
        transport.requests.single.uri.path,
        '/api/v2/match-viewer/match-001',
      );
    },
  );

  test(
    'loadViewState does not duplicate a 404 match-viewer session request through a legacy alias',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'not found'},
          ),
        ],
      );
      final ApiLiveMatchViewerRepository repository =
          ApiLiveMatchViewerRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
            ),
            isAuthenticated: false,
          );

      await expectLater(
        repository.loadViewState('match-001', continuationToken: 'segment-2'),
        throwsA(isA<GteApiException>()),
      );

      expect(transport.requests, hasLength(1));
      expect(
        transport.requests.single.uri.path,
        '/api/v2/match-viewer/match-001/session',
      );
      expect(
        transport.requests.single.uri.queryParameters['token'],
        'segment-2',
      );
    },
  );

  test('resolveBootstrap uses backend competition_summary payload', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'match_id': 'match-001',
            'title': 'Viewer title must not become competition metadata',
            'competition_summary': _competitionSummaryPayload(),
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _sessionPayload('match-001'),
        ),
      ],
    );
    final ApiLiveMatchViewerRepository repository =
        ApiLiveMatchViewerRepository(
          api: GteAuthedApi(
            config: const GteRepositoryConfig(
              baseUrl: 'http://127.0.0.1:8000',
              mode: GteBackendMode.live,
            ),
            transport: transport,
          ),
          isAuthenticated: false,
        );

    final LiveMatchViewerBootstrap bootstrap = await repository
        .resolveBootstrap('match-001');

    expect(bootstrap.competition.id, 'competition-001');
    expect(bootstrap.competition.name, 'Backend Authored Cup');
    expect(bootstrap.competition.createdAt, DateTime.utc(2026, 1, 1));
    expect(bootstrap.competition.updatedAt, DateTime.utc(2026, 1, 2));
    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/match-viewer/match-001',
        '/api/v2/match-viewer/match-001/session',
      ],
    );
  });

  test(
    'resolveBootstrap carries the canonical spectate session when authenticated',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'match_id': 'match-001',
              'competition_summary': _competitionSummaryPayload(),
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: _sessionPayload('match-001'),
          ),
          GteTransportResponse(
            statusCode: 200,
            body: _spectateSessionPayload('match-001'),
          ),
        ],
      );
      final ApiLiveMatchViewerRepository repository =
          ApiLiveMatchViewerRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
              accessToken: 'viewer-token',
            ),
            isAuthenticated: true,
          );

      final LiveMatchViewerBootstrap bootstrap = await repository
          .resolveBootstrap('match-001');

      expect(bootstrap.spectateSession, isNotNull);
      expect(bootstrap.spectateSession!.matchId, 'match-001');
      expect(
        bootstrap.spectateSession!.websocketPath,
        '/api/matches/match-001/stream?session_id=session-001',
      );
      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/match-viewer/match-001',
          '/api/v2/match-viewer/match-001/session',
          '/api/v2/matches/match-001/spectate',
        ],
      );
    },
  );

  test('resolveBootstrap blocks when competition summary is missing', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'match_id': 'match-001',
            'title': 'Synthetic metadata source',
          },
        ),
      ],
    );
    final ApiLiveMatchViewerRepository repository =
        ApiLiveMatchViewerRepository(
          api: GteAuthedApi(
            config: const GteRepositoryConfig(
              baseUrl: 'http://127.0.0.1:8000',
              mode: GteBackendMode.live,
            ),
            transport: transport,
          ),
          isAuthenticated: false,
        );

    await expectLater(
      repository.resolveBootstrap('match-001'),
      throwsA(isA<GteApiException>()),
    );

    expect(transport.requests, hasLength(1));
    expect(
      transport.requests.single.uri.path,
      '/api/v2/match-viewer/match-001',
    );
  });

  test('buildLiveViewerCompetition rejects incomplete summaries', () {
    expect(
      () => buildLiveViewerCompetition('match-001', <String, Object?>{
        'competition_summary': <String, Object?>{
          'id': 'competition-001',
          'name': 'Incomplete Cup',
        },
      }),
      throwsA(isA<GteApiException>()),
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

Map<String, Object?> _competitionSummaryPayload() {
  return <String, Object?>{
    'id': 'competition-001',
    'name': 'Backend Authored Cup',
    'format': 'cup',
    'visibility': 'public',
    'status': 'in_progress',
    'creator_id': 'gtex-live',
    'creator_name': 'GTEX Live Ops',
    'participant_count': 2,
    'capacity': 2,
    'currency': 'coin',
    'entry_fee': 0,
    'platform_fee_pct': 0,
    'host_fee_pct': 0,
    'platform_fee_amount': 0,
    'host_fee_amount': 0,
    'prize_pool': 0,
    'payout_structure': <Object?>[],
    'rules_summary': 'Backend-authored live match summary.',
    'join_eligibility': <String, Object?>{
      'eligible': false,
      'reason': 'spectate_only',
    },
    'beginner_friendly': true,
    'created_at': '2026-01-01T00:00:00Z',
    'updated_at': '2026-01-02T00:00:00Z',
  };
}

Map<String, Object?> _spectateSessionPayload(String matchId) {
  return <String, Object?>{
    'id': 'session-001',
    'match_id': matchId,
    'channel': 'match:$matchId:events',
    'websocket_path': '/api/matches/$matchId/stream?session_id=session-001',
    'commentary_websocket_path':
        '/api/matches/$matchId/commentary/stream?session_id=session-001',
    'presence_channel': 'match:$matchId:events',
    'presence_websocket_path': '/ws/spectate/$matchId',
    'replay_route': '/api/matches/$matchId/replay',
    'speed_modes': <Object?>[
      <String, Object?>{
        'key': 'normal',
        'label': 'Normal',
        'target_duration_seconds': 90,
      },
    ],
  };
}

Map<String, Object?> _sessionPayload(String matchId) {
  return <String, Object?>{
    'match_id': matchId,
    'source': 'test',
    'duration_seconds': 90,
    'home_team': <String, Object?>{
      'team_id': 'home',
      'team_name': 'Home FC',
      'short_name': 'HOM',
      'side': 'home',
      'formation': '4-3-3',
      'primary_color': '#FFFFFF',
      'secondary_color': '#111827',
      'accent_color': '#FDB022',
      'goalkeeper_color': '#EC4899',
    },
    'away_team': <String, Object?>{
      'team_id': 'away',
      'team_name': 'Away FC',
      'short_name': 'AWY',
      'side': 'away',
      'formation': '4-3-3',
      'primary_color': '#111827',
      'secondary_color': '#FFFFFF',
      'accent_color': '#FDE68A',
      'goalkeeper_color': '#FDE68A',
    },
    'events': <Object?>[],
    'frames': <Object?>[],
  };
}
