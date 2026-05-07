import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/discovery_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test('discovery api uses canonical api routes', () async {
    final _RecordingTransport
    transport = _RecordingTransport(<GteTransportResponse>[
      GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'featured_rails': <Object?>[_featuredRailJson('rail-1')],
          'featured_items': <Object?>[_discoveryItemJson('story-1')],
          'recommended_items': <Object?>[_discoveryItemJson('comp-1')],
          'live_now_items': <Object?>[_discoveryItemJson('fixture-1')],
          'saved_searches': <Object?>[_savedSearchJson('search-1')],
        },
      ),
      GteTransportResponse(
        statusCode: 200,
        body: <Object?>[_discoveryItemJson('story-1')],
      ),
      GteTransportResponse(
        statusCode: 200,
        body: <Object?>[_savedSearchJson('search-1')],
      ),
      GteTransportResponse(statusCode: 200, body: _savedSearchJson('search-2')),
      const GteTransportResponse(statusCode: 204, body: null),
      GteTransportResponse(
        statusCode: 200,
        body: <Object?>[_featuredRailJson('rail-1')],
      ),
      GteTransportResponse(statusCode: 200, body: _featuredRailJson('rail-2')),
    ]);
    final DiscoveryApi api = DiscoveryApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.fetchHome();
    await api.search(query: 'lagos', entityScope: 'club', limit: 12);
    await api.listSavedSearches();
    await api.createSavedSearch(
      query: 'lagos',
      entityScope: 'club',
      alertsEnabled: true,
    );
    await api.deleteSavedSearch('search-1');
    await api.listFeaturedRails();
    await api.upsertFeaturedRail(
      railKey: 'live-now',
      title: 'Live now',
      queryHint: 'broadcast:live',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/discovery/home',
        '/api/v2/discovery/search',
        '/api/v2/discovery/saved-searches',
        '/api/v2/discovery/saved-searches',
        '/api/v2/discovery/saved-searches/search-1',
        '/api/v2/admin/discovery/featured-rails',
        '/api/v2/admin/discovery/featured-rails',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['q'], 'lagos');
    expect(transport.requests[1].uri.queryParameters['entity_scope'], 'club');
    expect(transport.requests[1].uri.queryParameters['limit'], '12');
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

Map<String, Object?> _featuredRailJson(String id) => <String, Object?>{
  'id': id,
  'rail_key': 'story-trending',
  'title': 'Trending storylines',
  'rail_type': 'story',
  'audience': 'public',
  'query_hint': 'story:trending',
  'subtitle': 'Most watched loops today',
  'display_order': 1,
  'active': true,
  'metadata_json': const <String, Object?>{'tone': 'spotlight'},
};

Map<String, Object?> _discoveryItemJson(String id) => <String, Object?>{
  'item_type': 'story',
  'item_id': id,
  'title': 'Derby day cinematic recap',
  'subtitle': '3 min highlight loop',
  'rail_key': 'story-trending',
  'score': 98,
  'metadata': const <String, Object?>{'lane': 'arena'},
};

Map<String, Object?> _savedSearchJson(String id) => <String, Object?>{
  'id': id,
  'query': 'lagos',
  'entity_scope': 'club',
  'alerts_enabled': true,
  'metadata_json': const <String, Object?>{},
};
