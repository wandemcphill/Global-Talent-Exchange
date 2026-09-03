import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_api.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_models.dart';

GtexCommunitySocialApi _api(_RecordingTransport transport) {
  return GtexCommunitySocialApi(
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
}

void main() {
  test('community social api uses the canonical club_social routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'follows': <Object?>[
              <String, Object?>{
                'id': 'f1',
                'target_key': 'player:p1',
                'target_type': 'player',
                'player_id': 'p1',
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'id': 'f2',
            'target_key': 'club:c1',
            'target_type': 'club',
            'club_id': 'c1',
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'status': 'deleted'},
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'club_id': 'c1',
            'challenges': <Object?>[
              <String, Object?>{
                'challenge_id': 'ch1',
                'title': 'Lagos derby',
                'issuing_club_id': 'c1',
                'issuing_club_name': 'Lagos Eclipse FC',
                'status': 'open',
                'share_count': 4,
              },
            ],
          },
        ),
      ],
    );
    final GtexCommunitySocialApi api = _api(transport);

    final List<GtexSocialFollow> follows = await api.listMyFollows();
    await api.follow(targetType: 'club', clubId: 'c1');
    await api.unfollow(targetType: 'club', clubId: 'c1');
    final List<GtexClubChallengeCard> challenges = await api.listClubChallenges(
      'c1',
    );

    expect(
      transport.requests.map((GteTransportRequest r) => r.uri.path),
      <String>[
        '/api/v2/social/follows/me',
        '/api/v2/social/follows',
        '/api/v2/social/follows',
        '/api/v2/clubs/c1/challenges',
      ],
    );
    expect(
      transport.requests.map((GteTransportRequest r) => r.method),
      <String>['GET', 'POST', 'DELETE', 'GET'],
    );

    // The three follow calls carry a bearer token; the public challenge read
    // does not require one.
    expect(
      transport.requests
          .take(3)
          .every((GteTransportRequest r) => r.headers.containsKey('Authorization')),
      isTrue,
    );
    expect(
      transport.requests.last.headers.containsKey('Authorization'),
      isFalse,
    );

    expect(follows.single.playerId, 'p1');
    expect(challenges.single.shareCount, 4);
    expect(challenges.single.issuingClubName, 'Lagos Eclipse FC');
  });

  test('a follow payload names exactly one target and no extra fields', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'id': 'f',
            'target_key': 'player:p1',
            'target_type': 'player',
            'player_id': 'p1',
          },
        ),
      ],
    );
    await _api(transport).follow(targetType: 'player', playerId: 'p1');
    final Object? body = transport.requests.single.body;
    expect(body, isA<Map<String, Object?>>());
    final Map<String, Object?> payload = body! as Map<String, Object?>;
    expect(payload.keys.toSet(), <String>{
      'target_type',
      'club_id',
      'player_id',
      'metadata_json',
    });
    expect(payload['target_type'], 'player');
    expect(payload['player_id'], 'p1');
    expect(payload['club_id'], isNull);
    // No client-supplied metadata: nothing the user types reaches this write,
    // so the payload cannot grow unbounded or carry attacker-chosen content.
    expect(payload['metadata_json'], isEmpty);
  });

  test('a missing challenge list is empty, not an exception', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'club_id': 'c1'},
        ),
      ],
    );
    expect(await _api(transport).listClubChallenges('c1'), isEmpty);
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
