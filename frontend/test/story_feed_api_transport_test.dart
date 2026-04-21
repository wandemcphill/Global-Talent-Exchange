import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/story_feed_api.dart';

void main() {
  test('story feed api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_storyJson('story-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'top_stories': <Object?>[_storyJson('story-1')],
            'country_spotlight': const <Object?>[],
            'feature_stories': <Object?>[_storyJson('story-1')],
          },
        ),
        GteTransportResponse(statusCode: 200, body: _storyJson('story-2')),
      ],
    );
    final StoryFeedApi api = StoryFeedApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listFeed(limit: 25);
    await api.fetchDigest();
    await api.publishStory(
      storyType: 'featured_update',
      title: 'Transfer window heating up',
      body: 'Several clubs are circling academy standouts this week.',
      countryCode: 'NG',
      featured: true,
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v1/story-feed',
        '/api/v1/story-feed/digest',
        '/api/v1/admin/story-feed',
      ],
    );
    expect(transport.requests.first.uri.queryParameters['limit'], '25');
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

Map<String, Object?> _storyJson(String id) => <String, Object?>{
  'id': id,
  'story_type': 'announcement',
  'title': 'Matchday watchlist opens',
  'body': 'Tonight\'s matchday feed is now live with cinematic loops.',
  'audience': 'all',
  'subject_type': 'club_sale_transfer',
  'subject_id': 'club_transfer_demo',
  'country_code': 'NG',
  'featured': true,
  'created_at': '2026-03-12T08:00:00Z',
  'metadata_json': const <String, Object?>{},
};
