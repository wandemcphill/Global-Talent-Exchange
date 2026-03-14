import 'dart:math';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/discovery_models.dart';

class DiscoveryApi {
  DiscoveryApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _DiscoveryFixtures fixtures;

  factory DiscoveryApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return DiscoveryApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _DiscoveryFixtures.seed(),
    );
  }

  factory DiscoveryApi.fixture() {
    return DiscoveryApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _DiscoveryFixtures.seed(),
    );
  }

  Future<DiscoveryHome> fetchHome() {
    return client.withFallback<DiscoveryHome>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/discovery/home');
        return DiscoveryHome.fromJson(payload);
      },
      fixtures.home,
    );
  }

  Future<List<DiscoveryItem>> search({
    required String query,
    String entityScope = 'all',
    int limit = 20,
  }) {
    return client.withFallback<List<DiscoveryItem>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/discovery/search',
          query: <String, Object?>{
            'q': query,
            'entity_scope': entityScope,
            'limit': limit,
          },
        );
        return payload
            .map(DiscoveryItem.fromJson)
            .toList(growable: false);
      },
      () async => fixtures.search(query: query, limit: limit),
    );
  }

  Future<List<SavedSearch>> listSavedSearches() {
    return client.withFallback<List<SavedSearch>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/discovery/saved-searches');
        return payload.map(SavedSearch.fromJson).toList(growable: false);
      },
      fixtures.savedSearches,
    );
  }

  Future<SavedSearch> createSavedSearch({
    required String query,
    String entityScope = 'all',
    bool alertsEnabled = false,
  }) {
    return client.withFallback<SavedSearch>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/discovery/saved-searches',
          body: <String, Object?>{
            'query': query,
            'entity_scope': entityScope,
            'alerts_enabled': alertsEnabled,
          },
        );
        return SavedSearch.fromJson(payload);
      },
      () async => fixtures.createSavedSearch(query: query),
    );
  }

  Future<void> deleteSavedSearch(String searchId) {
    return client.withFallback<void>(
      () async {
        await client.request(
          'DELETE',
          '/discovery/saved-searches/$searchId',
        );
      },
      () async => fixtures.deleteSavedSearch(searchId),
    );
  }

  Future<List<FeaturedRail>> listFeaturedRails() {
    return client.withFallback<List<FeaturedRail>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/discovery/featured-rails');
        return payload.map(FeaturedRail.fromJson).toList(growable: false);
      },
      fixtures.featuredRails,
    );
  }

  Future<FeaturedRail> upsertFeaturedRail({
    required String railKey,
    required String title,
    String railType = 'story',
    String audience = 'public',
    String? queryHint,
    String subtitle = '',
    int displayOrder = 0,
    bool active = true,
  }) {
    return client.withFallback<FeaturedRail>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/discovery/featured-rails',
          body: <String, Object?>{
            'rail_key': railKey,
            'title': title,
            'rail_type': railType,
            'audience': audience,
            'query_hint': queryHint,
            'subtitle': subtitle,
            'display_order': displayOrder,
            'active': active,
          },
        );
        return FeaturedRail.fromJson(payload);
      },
      () async => fixtures.upsertRail(
        railKey: railKey,
        title: title,
      ),
    );
  }
}

class _DiscoveryFixtures {
  _DiscoveryFixtures(this._home, this._searches, this._rails);

  final DiscoveryHome _home;
  final List<SavedSearch> _searches;
  final List<FeaturedRail> _rails;

  static _DiscoveryFixtures seed() {
    final List<FeaturedRail> rails = <FeaturedRail>[
      FeaturedRail(
        id: 'rail-1',
        railKey: 'story-trending',
        title: 'Trending storylines',
        railType: 'story',
        audience: 'public',
        queryHint: 'story:trending',
        subtitle: 'Most watched loops today',
        displayOrder: 1,
        active: true,
        metadata: const <String, Object?>{'tone': 'spotlight'},
      ),
      FeaturedRail(
        id: 'rail-2',
        railKey: 'market-scout',
        title: 'Scout this tape',
        railType: 'market',
        audience: 'public',
        queryHint: 'market:watchlist',
        subtitle: 'Players heating up this week',
        displayOrder: 2,
        active: true,
        metadata: const <String, Object?>{'tone': 'market'},
      ),
    ];
    final List<DiscoveryItem> featured = <DiscoveryItem>[
      DiscoveryItem(
        itemType: 'story',
        itemId: 'story-1',
        title: 'Derby day cinematic recap',
        subtitle: '3 min highlight loop',
        railKey: rails.first.railKey,
        score: 98,
        metadata: const <String, Object?>{'lane': 'arena'},
      ),
      DiscoveryItem(
        itemType: 'player',
        itemId: 'player-44',
        title: 'Breakout winger surge',
        subtitle: 'Market interest +22%',
        railKey: rails.last.railKey,
        score: 92,
        metadata: const <String, Object?>{'lane': 'market'},
      ),
    ];
    final List<DiscoveryItem> recommended = <DiscoveryItem>[
      DiscoveryItem(
        itemType: 'competition',
        itemId: 'comp-22',
        title: 'Creator night cup',
        subtitle: 'Join open for 24h',
        railKey: 'recommendations',
        score: 88,
        metadata: const <String, Object?>{'lane': 'arena'},
      ),
    ];
    final List<DiscoveryItem> live = <DiscoveryItem>[
      DiscoveryItem(
        itemType: 'fixture',
        itemId: 'fixture-1',
        title: 'Live match story',
        subtitle: 'Match minute 54',
        railKey: 'live-now',
        score: 99,
        metadata: const <String, Object?>{'lane': 'arena'},
      ),
    ];
    final List<SavedSearch> searches = <SavedSearch>[
      SavedSearch(
        id: 'search-1',
        query: 'creator cups',
        entityScope: 'competitions',
        alertsEnabled: true,
        metadata: const <String, Object?>{'source': 'fixture'},
      ),
    ];
    return _DiscoveryFixtures(
      DiscoveryHome(
        featuredRails: rails,
        featuredItems: featured,
        recommendedItems: recommended,
        liveNowItems: live,
        savedSearches: searches,
      ),
      searches,
      rails,
    );
  }

  Future<DiscoveryHome> home() async => _home;

  Future<List<SavedSearch>> savedSearches() async =>
      List<SavedSearch>.of(_searches, growable: false);

  Future<SavedSearch> createSavedSearch({required String query}) async {
    final SavedSearch created = SavedSearch(
      id: 'search-${_searches.length + 1}',
      query: query,
      entityScope: 'all',
      alertsEnabled: false,
      metadata: const <String, Object?>{},
    );
    _searches.insert(0, created);
    return created;
  }

  Future<void> deleteSavedSearch(String searchId) async {
    _searches.removeWhere((SavedSearch item) => item.id == searchId);
  }

  Future<List<DiscoveryItem>> search({
    required String query,
    int limit = 20,
  }) async {
    if (query.trim().isEmpty) {
      return const <DiscoveryItem>[];
    }
    final Random random = Random(query.hashCode);
    return List<DiscoveryItem>.generate(
      min(limit, 5),
      (int index) => DiscoveryItem(
        itemType: index.isEven ? 'story' : 'player',
        itemId: 'result-$index',
        title: 'Result for "$query" ${index + 1}',
        subtitle: index.isEven ? 'Story lane' : 'Market lane',
        railKey: 'search',
        score: 60 + random.nextInt(40),
        metadata: const <String, Object?>{'source': 'fixture'},
      ),
    );
  }

  Future<List<FeaturedRail>> featuredRails() async =>
      List<FeaturedRail>.of(_rails, growable: false);

  Future<FeaturedRail> upsertRail({
    required String railKey,
    required String title,
  }) async {
    final FeaturedRail rail = FeaturedRail(
      id: 'rail-${_rails.length + 1}',
      railKey: railKey,
      title: title,
      railType: 'story',
      audience: 'public',
      queryHint: null,
      subtitle: '',
      displayOrder: _rails.length + 1,
      active: true,
      metadata: const <String, Object?>{},
    );
    _rails.insert(0, rail);
    return rail;
  }
}
