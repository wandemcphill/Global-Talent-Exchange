import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test('community api writes audit metadata for watchlist mutations', () async {
    final _CaptureTransport transport = _CaptureTransport();
    final CommunityApi api = CommunityApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.addWatchlist(
      competitionKey: 'creator-cup',
      competitionTitle: 'Creator Cup',
      competitionType: 'creator',
    );

    final GteTransportRequest request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/api/v2/community/watchlist');
    final Map<String, Object?> body = request.body! as Map<String, Object?>;
    final Map<String, Object?> metadata =
        body['metadata_json']! as Map<String, Object?>;
    expect(metadata['surface'], 'community');
    expect(metadata['action'], 'watchlist.add');
    expect(metadata['role_required'], 'authenticated_member');
    expect(metadata['realtime_topic'], 'community.watchlist');
    expect(metadata['audit_schema'], 'community.surface.v1');
  });
}

class _CaptureTransport implements GteTransport {
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'id': 'watch-1',
        'competition_key': 'creator-cup',
        'competition_title': 'Creator Cup',
        'competition_type': 'creator',
        'notify_on_story': true,
        'notify_on_launch': true,
        'metadata_json': const <String, Object?>{},
        'created_at': DateTime.utc(2026, 1, 1).toIso8601String(),
        'updated_at': DateTime.utc(2026, 1, 1).toIso8601String(),
      },
    );
  }
}
