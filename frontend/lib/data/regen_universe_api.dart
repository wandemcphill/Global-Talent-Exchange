import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';
import '../models/regen_universe_models.dart';

class RegenUniverseApi {
  RegenUniverseApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final _RegenUniverseFixtures fixtures;

  factory RegenUniverseApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return RegenUniverseApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        mode: mode,
      ),
      fixtures: _RegenUniverseFixtures.seed(),
    );
  }

  factory RegenUniverseApi.fixture() {
    return RegenUniverseApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        mode: GteBackendMode.fixture,
      ),
      fixtures: _RegenUniverseFixtures.seed(),
    );
  }

  Future<List<RegenRisingStar>> listRisingStars({int limit = 8}) {
    return client.withFallback<List<RegenRisingStar>>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/rising-stars',
        query: <String, Object?>{'limit': limit},
        auth: false,
      );
      final List<Object?> items = GteJson.list(
        payload['entries'] ?? const <Object?>[],
      );
      return items.map(RegenRisingStar.fromJson).toList(growable: false);
    }, () async => fixtures.risingStars(limit: limit));
  }

  Future<List<RegenScoutingFeedItem>> listScoutingFeed({int limit = 8}) {
    return client.withFallback<List<RegenScoutingFeedItem>>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/scouting-feed',
        query: <String, Object?>{'limit': limit},
        auth: false,
      );
      final List<Object?> items = GteJson.list(
        payload['items'] ?? const <Object?>[],
      );
      return items.map(RegenScoutingFeedItem.fromJson).toList(growable: false);
    }, () async => fixtures.scoutingFeed(limit: limit));
  }

  Future<List<NationalRegenSeed>> listNationalRegens({
    int limit = 8,
    int ageMax = 17,
  }) {
    return client.withFallback<List<NationalRegenSeed>>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/national-regens',
        query: <String, Object?>{'limit': limit, 'age_max': ageMax},
        auth: false,
      );
      final List<Object?> items = GteJson.list(
        payload['items'] ?? const <Object?>[],
      );
      return items.map(NationalRegenSeed.fromJson).toList(growable: false);
    }, () async => fixtures.nationalRegens(limit: limit));
  }

  Future<RegenGenerationTracking> fetchTracking() {
    return client.withFallback<RegenGenerationTracking>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/tracking',
        auth: false,
      );
      return RegenGenerationTracking.fromJson(payload);
    }, fixtures.tracking);
  }
}

class _RegenUniverseFixtures {
  const _RegenUniverseFixtures({
    required List<RegenRisingStar> risingStars,
    required List<RegenScoutingFeedItem> feed,
    required List<NationalRegenSeed> nationalRegens,
    required RegenGenerationTracking tracking,
  }) : _risingStars = risingStars,
       _feed = feed,
       _nationalRegens = nationalRegens,
       _tracking = tracking;

  final List<RegenRisingStar> _risingStars;
  final List<RegenScoutingFeedItem> _feed;
  final List<NationalRegenSeed> _nationalRegens;
  final RegenGenerationTracking _tracking;

  static _RegenUniverseFixtures seed() {
    const RegenUniversePlayer starOne = RegenUniversePlayer(
      id: 'seed:br-17',
      name: 'Joao Aurora',
      age: 17,
      nationality: 'Brazil',
      nationalityCode: 'BR',
      position: 'ST',
      potential: 93,
      currentRating: 74,
      growthCurve: 0.86,
      sourceType: 'national_seed',
      clubId: 'national-pool-br',
    );
    const RegenUniversePlayer starTwo = RegenUniversePlayer(
      id: 'regen:ng-21',
      name: 'Tunde Skyline',
      age: 18,
      nationality: 'Nigeria',
      nationalityCode: 'NG',
      position: 'AM',
      potential: 90,
      currentRating: 72,
      growthCurve: 0.79,
      sourceType: 'regen',
      clubId: 'lagos-atlas',
    );
    const NationalRegenSeed seedOne = NationalRegenSeed(
      id: 'national-seed-ng-1',
      seedKey: 'seed:ng:1',
      displayName: 'Kelechi Meridian',
      age: 16,
      countryCode: 'NG',
      countryName: 'Nigeria',
      seedType: 'national_seed',
      primaryPosition: 'RW',
      currentRating: 71,
      potentialRating: 90,
      rarityTier: 'elite',
      preseedBatch: 'system_start',
      metadata: <String, Object?>{'growth_curve': 0.82},
    );
    const NationalRegenSeed seedTwo = NationalRegenSeed(
      id: 'national-seed-br-1',
      seedKey: 'seed:br:1',
      displayName: 'Mateus Sol',
      age: 17,
      countryCode: 'BR',
      countryName: 'Brazil',
      seedType: 'legendary_seed',
      primaryPosition: 'ST',
      currentRating: 74,
      potentialRating: 94,
      rarityTier: 'legendary',
      preseedBatch: 'system_start',
      metadata: <String, Object?>{'growth_curve': 0.89},
    );
    return _RegenUniverseFixtures(
      risingStars: const <RegenRisingStar>[
        RegenRisingStar(
          playerId: 'seed:br-17',
          player: starOne,
          momentumLabel: 'Wonderkid surge',
          storySnippet:
              'Street striker carrying elite acceleration and a ruthless final action.',
          badges: <String>['Elite Potential', 'National Pool'],
          marketValueCoin: 342000,
        ),
        RegenRisingStar(
          playerId: 'regen:ng-21',
          player: starTwo,
          momentumLabel: 'Breakout form',
          storySnippet:
              'Advanced creator finding the final pass early and often.',
          badges: <String>['Scouting Pulse'],
          marketValueCoin: 276000,
        ),
      ],
      feed: <RegenScoutingFeedItem>[
        RegenScoutingFeedItem(
          feedId: 'discover-seed-br-17',
          feedType: 'new_regen_discovered',
          title: '17-year-old striker from Brazil discovered',
          summary:
              'Joao Aurora is carrying 74 to 93 upside and forcing his way onto elite watchlists.',
          occurredAt: DateTime.parse('2026-04-01T09:00:00Z'),
          importance: 0.91,
          badges: const <String>['national_seed', 'Elite'],
          player: starOne,
        ),
        RegenScoutingFeedItem(
          feedId: 'spike-regen-ng-21',
          feedType: 'potential_spike',
          title: 'Midfielder potential spike tracked',
          summary:
              'Tunde Skyline has widened his ceiling after another heavy-creation block in training.',
          occurredAt: DateTime.parse('2026-04-01T07:20:00Z'),
          importance: 0.84,
          badges: const <String>['potential_spike', 'surging'],
          player: starTwo,
        ),
      ],
      nationalRegens: const <NationalRegenSeed>[seedOne, seedTwo],
      tracking: const RegenGenerationTracking(
        totalSeededPlayers: 248,
        seedTypes: <RegenGenerationTrackingEntry>[
          RegenGenerationTrackingEntry(
            bucket: 'national_seed',
            count: 214,
            peakRating: 93,
            achievements: <String>['u17_callups'],
            metadata: <String, Object?>{},
          ),
          RegenGenerationTrackingEntry(
            bucket: 'legendary_seed',
            count: 34,
            peakRating: 96,
            achievements: <String>['elite_watchlists'],
            metadata: <String, Object?>{},
          ),
        ],
        rarityBreakdown: <RegenGenerationTrackingEntry>[
          RegenGenerationTrackingEntry(
            bucket: 'elite',
            count: 57,
            peakRating: 94,
            achievements: <String>[],
            metadata: <String, Object?>{},
          ),
          RegenGenerationTrackingEntry(
            bucket: 'legendary',
            count: 12,
            peakRating: 96,
            achievements: <String>[],
            metadata: <String, Object?>{},
          ),
        ],
        countryDistribution: <RegenGenerationTrackingEntry>[
          RegenGenerationTrackingEntry(
            bucket: 'Nigeria',
            count: 22,
            peakRating: 90,
            achievements: <String>['u17_callups'],
            metadata: <String, Object?>{},
          ),
          RegenGenerationTrackingEntry(
            bucket: 'Brazil',
            count: 26,
            peakRating: 94,
            achievements: <String>['elite_watchlists'],
            metadata: <String, Object?>{},
          ),
        ],
        globalPeakRating: 96,
        trackedAchievements: <String>[
          'u17_callups',
          'elite_watchlists',
          'breakout_debuts',
        ],
      ),
    );
  }

  Future<List<RegenRisingStar>> risingStars({required int limit}) async =>
      _risingStars.take(limit).toList(growable: false);

  Future<List<RegenScoutingFeedItem>> scoutingFeed({
    required int limit,
  }) async => _feed.take(limit).toList(growable: false);

  Future<List<NationalRegenSeed>> nationalRegens({required int limit}) async =>
      _nationalRegens.take(limit).toList(growable: false);

  Future<RegenGenerationTracking> tracking() async => _tracking;
}
