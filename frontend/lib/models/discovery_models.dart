import 'package:gte_frontend/data/gte_models.dart';

class DiscoveryItem {
  const DiscoveryItem({
    required this.itemType,
    required this.itemId,
    required this.title,
    required this.subtitle,
    required this.railKey,
    required this.score,
    required this.metadata,
  });

  final String itemType;
  final String itemId;
  final String title;
  final String subtitle;
  final String? railKey;
  final double score;
  final Map<String, Object?> metadata;

  factory DiscoveryItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'discovery item');
    return DiscoveryItem(
      itemType: GteJson.string(json, <String>['item_type', 'itemType']),
      itemId: GteJson.string(json, <String>['item_id', 'itemId']),
      title: GteJson.string(json, <String>['title']),
      subtitle: GteJson.string(json, <String>['subtitle'], fallback: ''),
      railKey: GteJson.stringOrNull(json, <String>['rail_key', 'railKey']),
      score: GteJson.number(json, <String>['score'], fallback: 0),
      metadata: GteJson.map(json, <String>['metadata'], fallback: const <String, Object?>{}),
    );
  }
}

class FeaturedRail {
  const FeaturedRail({
    required this.id,
    required this.railKey,
    required this.title,
    required this.railType,
    required this.audience,
    required this.queryHint,
    required this.subtitle,
    required this.displayOrder,
    required this.active,
    required this.metadata,
  });

  final String id;
  final String railKey;
  final String title;
  final String railType;
  final String audience;
  final String? queryHint;
  final String subtitle;
  final int displayOrder;
  final bool active;
  final Map<String, Object?> metadata;

  factory FeaturedRail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'featured rail');
    return FeaturedRail(
      id: GteJson.string(json, <String>['id']),
      railKey: GteJson.string(json, <String>['rail_key', 'railKey']),
      title: GteJson.string(json, <String>['title']),
      railType: GteJson.string(json, <String>['rail_type', 'railType']),
      audience: GteJson.string(json, <String>['audience'], fallback: 'public'),
      queryHint: GteJson.stringOrNull(json, <String>['query_hint', 'queryHint']),
      subtitle: GteJson.string(json, <String>['subtitle'], fallback: ''),
      displayOrder: GteJson.integer(json, <String>['display_order', 'displayOrder'], fallback: 0),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      metadata: GteJson.map(json, <String>['metadata_json', 'metadataJson', 'metadata'], fallback: const <String, Object?>{}),
    );
  }
}

class SavedSearch {
  const SavedSearch({
    required this.id,
    required this.query,
    required this.entityScope,
    required this.alertsEnabled,
    required this.metadata,
  });

  final String id;
  final String query;
  final String entityScope;
  final bool alertsEnabled;
  final Map<String, Object?> metadata;

  factory SavedSearch.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'saved search');
    return SavedSearch(
      id: GteJson.string(json, <String>['id']),
      query: GteJson.string(json, <String>['query']),
      entityScope:
          GteJson.string(json, <String>['entity_scope', 'entityScope'], fallback: 'all'),
      alertsEnabled: GteJson.boolean(
          json, <String>['alerts_enabled', 'alertsEnabled'],
          fallback: false),
      metadata: GteJson.map(json, <String>['metadata_json', 'metadataJson', 'metadata'], fallback: const <String, Object?>{}),
    );
  }
}

class DiscoveryHome {
  const DiscoveryHome({
    required this.featuredRails,
    required this.featuredItems,
    required this.recommendedItems,
    required this.liveNowItems,
    required this.savedSearches,
  });

  final List<FeaturedRail> featuredRails;
  final List<DiscoveryItem> featuredItems;
  final List<DiscoveryItem> recommendedItems;
  final List<DiscoveryItem> liveNowItems;
  final List<SavedSearch> savedSearches;

  factory DiscoveryHome.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'discovery home');
    return DiscoveryHome(
      featuredRails: GteJson.typedList(
        json,
        <String>['featured_rails', 'featuredRails'],
        FeaturedRail.fromJson,
      ),
      featuredItems: GteJson.typedList(
        json,
        <String>['featured_items', 'featuredItems'],
        DiscoveryItem.fromJson,
      ),
      recommendedItems: GteJson.typedList(
        json,
        <String>['recommended_items', 'recommendedItems'],
        DiscoveryItem.fromJson,
      ),
      liveNowItems: GteJson.typedList(
        json,
        <String>['live_now_items', 'liveNowItems'],
        DiscoveryItem.fromJson,
      ),
      savedSearches: GteJson.typedList(
        json,
        <String>['saved_searches', 'savedSearches'],
        SavedSearch.fromJson,
      ),
    );
  }
}
