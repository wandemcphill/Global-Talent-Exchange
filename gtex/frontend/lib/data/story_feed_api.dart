import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/story_feed_models.dart';

class StoryFeedApi {
  StoryFeedApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final _StoryFeedFixtures? fixtures;

  factory StoryFeedApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    final GteTransport resolvedTransport = transport ?? GteHttpTransport();
    return StoryFeedApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: resolvedTransport,
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: null,
    );
  }

  factory StoryFeedApi.fixture() {
    assertFixtureFactoryAllowed('StoryFeedApi.fixture');
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
    return client.withFallback<List<StoryFeedItem>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/story-feed',
        query: <String, Object?>{'limit': limit},
        auth: false,
      );
      return payload.map(StoryFeedItem.fromJson).toList(growable: false);
    }, () => _requireFixtures().feed());
  }

  Future<List<StoryFeedItem>> listAdminFeed({int limit = 100}) {
    return client.withFallback<List<StoryFeedItem>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/admin/story-feed',
        query: <String, Object?>{'limit': limit},
      );
      return payload.map(StoryFeedItem.fromJson).toList(growable: false);
    }, () => _requireFixtures().feed());
  }

  Future<StoryDigest> fetchDigest() {
    return client.withFallback<StoryDigest>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/story-feed/digest',
        auth: false,
      );
      return StoryDigest.fromJson(payload);
    }, () => _requireFixtures().digest());
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
    DateTime? scheduledFor,
  }) {
    return client.withFallback<StoryFeedItem>(() async {
      final Object? payload = await client.request(
        'POST',
        '/api/admin/story-feed',
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
          if (scheduledFor != null)
            'scheduled_for': scheduledFor.toUtc().toIso8601String(),
        },
      );
      return StoryFeedItem.fromJson(payload);
    }, () async => _requireFixtures().publishStory(title: title, body: body));
  }

  Future<StoryFeedItem> scheduleStory({
    required String storyId,
    required DateTime scheduledFor,
  }) {
    return client.withFallback<StoryFeedItem>(() async {
      final Object? payload = await client.request(
        'POST',
        '/api/admin/story-feed/$storyId/schedule',
        body: <String, Object?>{
          'scheduled_for': scheduledFor.toUtc().toIso8601String(),
        },
      );
      return StoryFeedItem.fromJson(payload);
    }, () async => _requireFixtures().scheduleStory(storyId: storyId, scheduledFor: scheduledFor));
  }

  Future<StoryFeedItem> rejectStory({
    required String storyId,
    String? reason,
  }) {
    return client.withFallback<StoryFeedItem>(() async {
      final Object? payload = await client.request(
        'POST',
        '/api/admin/story-feed/$storyId/reject',
        body: <String, Object?>{
          if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
        },
      );
      return StoryFeedItem.fromJson(payload);
    }, () async => _requireFixtures().rejectStory(storyId: storyId, reason: reason));
  }

  _StoryFeedFixtures _requireFixtures() {
    final _StoryFeedFixtures? resolvedFixtures = fixtures;
    if (resolvedFixtures == null) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message:
            'Story feed fixtures are not registered in strict-live runtime.',
      );
    }
    return resolvedFixtures;
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

  Future<StoryFeedItem> scheduleStory({
    required String storyId,
    required DateTime scheduledFor,
  }) async {
    final int index = _items.indexWhere((StoryFeedItem item) => item.id == storyId);
    if (index < 0) {
      throw StateError('Fixture story $storyId was not found.');
    }
    final StoryFeedItem current = _items[index];
    final StoryFeedItem updated = StoryFeedItem(
      id: current.id,
      storyType: current.storyType,
      title: current.title,
      body: current.body,
      audience: current.audience,
      subjectType: current.subjectType,
      subjectId: current.subjectId,
      countryCode: current.countryCode,
      featured: current.featured,
      createdAt: current.createdAt,
      metadata: current.metadata,
      moderationStatus: 'scheduled',
      scheduledFor: scheduledFor.toUtc(),
    );
    _items[index] = updated;
    return updated;
  }

  Future<StoryFeedItem> rejectStory({
    required String storyId,
    String? reason,
  }) async {
    final int index = _items.indexWhere((StoryFeedItem item) => item.id == storyId);
    if (index < 0) {
      throw StateError('Fixture story $storyId was not found.');
    }
    final StoryFeedItem current = _items[index];
    final StoryFeedItem updated = StoryFeedItem(
      id: current.id,
      storyType: current.storyType,
      title: current.title,
      body: current.body,
      audience: current.audience,
      subjectType: current.subjectType,
      subjectId: current.subjectId,
      countryCode: current.countryCode,
      featured: false,
      createdAt: current.createdAt,
      metadata: <String, Object?>{
        ...current.metadata,
        if (reason != null && reason.trim().isNotEmpty) 'reject_reason': reason.trim(),
      },
      moderationStatus: 'rejected',
    );
    _items[index] = updated;
    return updated;
  }
}
