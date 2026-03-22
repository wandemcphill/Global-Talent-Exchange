import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/story_feed_models.dart';

class StoryFeedApi {
  StoryFeedApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _StoryFeedFixtures fixtures;

  factory StoryFeedApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return StoryFeedApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _StoryFeedFixtures.seed(),
    );
  }

  factory StoryFeedApi.fixture() {
    return StoryFeedApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _StoryFeedFixtures.seed(),
    );
  }

  Future<List<StoryFeedItem>> listFeed({int limit = 50}) {
    return client.withFallback<List<StoryFeedItem>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/story-feed',
          query: <String, Object?>{'limit': limit},
          auth: false,
        );
        return payload.map(StoryFeedItem.fromJson).toList(growable: false);
      },
      fixtures.feed,
    );
  }

  Future<StoryDigest> fetchDigest() {
    return client.withFallback<StoryDigest>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/story-feed/digest', auth: false);
        return StoryDigest.fromJson(payload);
      },
      fixtures.digest,
    );
  }

  Future<StoryFeedItem> publishStory({
    required String storyType,
    required String title,
    required String body,
    String audience = 'all',
    String? subjectType,
    String? subjectId,
    String? countryCode,
    bool featured = false,
  }) {
    return client.withFallback<StoryFeedItem>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/story-feed',
          body: <String, Object?>{
            'story_type': storyType,
            'title': title,
            'body': body,
            'audience': audience,
            if (subjectType != null) 'subject_type': subjectType,
            if (subjectId != null) 'subject_id': subjectId,
            if (countryCode != null) 'country_code': countryCode,
            'featured': featured,
            'metadata_json': <String, Object?>{},
          },
        );
        return StoryFeedItem.fromJson(payload);
      },
      () async => fixtures.publishStory(title: title, body: body),
    );
  }
}

class _StoryFeedFixtures {
  _StoryFeedFixtures(this._items);

  final List<StoryFeedItem> _items;

  static _StoryFeedFixtures seed() {
    return _StoryFeedFixtures(<StoryFeedItem>[
      StoryFeedItem(
        id: 'story-1',
        storyType: 'announcement',
        title: 'Matchday watchlist opens',
        body: 'Tonight’s matchday feed is now live with cinematic loops.',
        audience: 'all',
        subjectType: null,
        subjectId: null,
        countryCode: null,
        featured: true,
        createdAt: DateTime.parse('2026-03-12T08:00:00Z'),
        metadata: const <String, Object?>{},
      ),
    ]);
  }

  Future<List<StoryFeedItem>> feed() async =>
      List<StoryFeedItem>.of(_items, growable: false);

  Future<StoryDigest> digest() async {
    return StoryDigest(
      topStories: _items,
      countrySpotlight: const <StoryFeedItem>[],
      featureStories: _items,
    );
  }

  Future<StoryFeedItem> publishStory({
    required String title,
    required String body,
  }) async {
    final StoryFeedItem item = StoryFeedItem(
      id: 'story-${_items.length + 1}',
      storyType: 'announcement',
      title: title,
      body: body,
      audience: 'all',
      subjectType: null,
      subjectId: null,
      countryCode: null,
      featured: false,
      createdAt: DateTime.now().toUtc(),
      metadata: const <String, Object?>{},
    );
    _items.insert(0, item);
    return item;
  }
}
