import 'package:gte_frontend/data/gte_models.dart';

class StoryFeedItem {
  const StoryFeedItem({
    required this.id,
    required this.storyType,
    required this.title,
    required this.body,
    required this.audience,
    required this.subjectType,
    required this.subjectId,
    required this.countryCode,
    required this.featured,
    required this.createdAt,
    required this.metadata,
  });

  final String id;
  final String storyType;
  final String title;
  final String body;
  final String audience;
  final String? subjectType;
  final String? subjectId;
  final String? countryCode;
  final bool featured;
  final DateTime createdAt;
  final Map<String, Object?> metadata;

  factory StoryFeedItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'story feed item');
    return StoryFeedItem(
      id: GteJson.string(json, <String>['id']),
      storyType:
          GteJson.string(json, <String>['story_type', 'storyType'], fallback: 'announcement'),
      title: GteJson.string(json, <String>['title']),
      body: GteJson.string(json, <String>['body']),
      audience: GteJson.string(json, <String>['audience'], fallback: 'all'),
      subjectType:
          GteJson.stringOrNull(json, <String>['subject_type', 'subjectType']),
      subjectId:
          GteJson.stringOrNull(json, <String>['subject_id', 'subjectId']),
      countryCode:
          GteJson.stringOrNull(json, <String>['country_code', 'countryCode']),
      featured: GteJson.boolean(json, <String>['featured'], fallback: false),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}

class StoryDigest {
  const StoryDigest({
    required this.topStories,
    required this.countrySpotlight,
    required this.featureStories,
  });

  final List<StoryFeedItem> topStories;
  final List<StoryFeedItem> countrySpotlight;
  final List<StoryFeedItem> featureStories;

  factory StoryDigest.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'story digest');
    return StoryDigest(
      topStories: GteJson.typedList(
        json,
        <String>['top_stories', 'topStories'],
        StoryFeedItem.fromJson,
      ),
      countrySpotlight: GteJson.typedList(
        json,
        <String>['country_spotlight', 'countrySpotlight'],
        StoryFeedItem.fromJson,
      ),
      featureStories: GteJson.typedList(
        json,
        <String>['feature_stories', 'featureStories'],
        StoryFeedItem.fromJson,
      ),
    );
  }
}
