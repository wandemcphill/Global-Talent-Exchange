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
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return RegenUniverseApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(
          connectionTimeout: const Duration(seconds: 20),
        ),
        mode: resolvedMode,
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
        transport: GteHttpTransport(
          connectionTimeout: const Duration(seconds: 20),
        ),
        mode: GteBackendMode.fixture,
      ),
      fixtures: _RegenUniverseFixtures.seed(),
    );
  }

  factory RegenUniverseApi.withClient({required GteAuthedApi client}) {
    return RegenUniverseApi(
      client: client,
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

  Future<List<RegenAwardResult>> listAwards({int limit = 8}) {
    return client.withFallback<List<RegenAwardResult>>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/awards',
        query: <String, Object?>{'limit': limit},
        auth: false,
      );
      final List<Object?> items = GteJson.list(
        payload['items'] ?? const <Object?>[],
      );
      return items.map(RegenAwardResult.fromJson).toList(growable: false);
    }, () async => fixtures.awards(limit: limit));
  }

  Future<List<RegenBloodlineChain>> listBloodlines({int limit = 8}) {
    return client.withFallback<List<RegenBloodlineChain>>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/bloodlines',
        query: <String, Object?>{'limit': limit},
        auth: false,
      );
      final List<Object?> items = GteJson.list(
        payload['entries'] ?? const <Object?>[],
      );
      return items.map(RegenBloodlineChain.fromJson).toList(growable: false);
    }, () async => fixtures.bloodlines(limit: limit));
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
    required List<RegenAwardResult> awards,
    required List<RegenBloodlineChain> bloodlines,
    required RegenGenerationTracking tracking,
  }) : _risingStars = risingStars,
       _feed = feed,
       _nationalRegens = nationalRegens,
       _awards = awards,
       _bloodlines = bloodlines,
       _tracking = tracking;

  final List<RegenRisingStar> _risingStars;
  final List<RegenScoutingFeedItem> _feed;
  final List<NationalRegenSeed> _nationalRegens;
  final List<RegenAwardResult> _awards;
  final List<RegenBloodlineChain> _bloodlines;
  final RegenGenerationTracking _tracking;

  static _RegenUniverseFixtures seed() {
    const RegenMarketAccess nationalOnlyAccess = RegenMarketAccess(
      marketEligible: false,
      shareMarketEligible: false,
      tradable: false,
      buyable: false,
      transferable: false,
      cardMintEligible: false,
      buyCtaAllowed: false,
      isPreseededNationalRegen: true,
      nationalPoolOnly: true,
    );
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
      clubId: null,
      marketAccess: nationalOnlyAccess,
    );
    const RegenUniversePlayer starTwo = RegenUniversePlayer(
      id: 'regen:ng-21',
      name: 'Chidera Onwubiko',
      age: 18,
      nationality: 'Nigeria',
      nationalityCode: 'NG',
      position: 'AM',
      potential: 90,
      currentRating: 72,
      growthCurve: 0.79,
      sourceType: 'generated',
      clubId: 'lagos-atlas',
    );
    const NationalRegenSeed seedOne = NationalRegenSeed(
      id: 'national-seed-ng-1',
      seedKey: 'seed:ng:1',
      displayName: 'Azeez Salisu',
      age: 16,
      ageBand: 'u17',
      countryCode: 'NG',
      countryName: 'Nigeria',
      seedType: 'national_seed',
      primaryPosition: 'RW',
      currentRating: 71,
      potentialRating: 90,
      growthCurve: 0.82,
      rarityTier: 'elite',
      status: 'active',
      preseedBatch: 'u17_batch',
      metadata: <String, Object?>{'growth_curve': 0.82},
      marketEligible: false,
      shareMarketEligible: false,
      tradable: false,
      buyable: false,
      transferable: false,
      cardMintEligible: false,
      buyCtaAllowed: false,
      isPreseededNationalRegen: true,
      nationalPoolOnly: true,
    );
    const NationalRegenSeed seedTwo = NationalRegenSeed(
      id: 'national-seed-br-1',
      seedKey: 'seed:br:1',
      displayName: 'Mateus Sol',
      age: 17,
      ageBand: 'u17',
      countryCode: 'BR',
      countryName: 'Brazil',
      seedType: 'national_seed',
      primaryPosition: 'ST',
      currentRating: 74,
      potentialRating: 94,
      growthCurve: 0.89,
      rarityTier: 'legendary',
      status: 'active',
      preseedBatch: 'u17_batch',
      metadata: <String, Object?>{'growth_curve': 0.89},
      marketEligible: false,
      shareMarketEligible: false,
      tradable: false,
      buyable: false,
      transferable: false,
      cardMintEligible: false,
      buyCtaAllowed: false,
      isPreseededNationalRegen: true,
      nationalPoolOnly: true,
    );
    return _RegenUniverseFixtures(
      risingStars: const <RegenRisingStar>[
        RegenRisingStar(
          playerId: 'seed:br-17',
          player: starOne,
          momentumLabel: 'Wonderkid surge',
          storySnippet:
              'Street striker carrying elite acceleration and a ruthless final action.',
          badges: <String>['Elite Potential'],
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
          badges: const <String>['Elite'],
          player: starOne,
        ),
        RegenScoutingFeedItem(
          feedId: 'spike-regen-ng-21',
          feedType: 'potential_spike',
          title: 'Midfielder potential spike tracked',
          summary:
              'Chidera Onwubiko has widened his ceiling after another heavy-creation block in training.',
          occurredAt: DateTime.parse('2026-04-01T07:20:00Z'),
          importance: 0.84,
          badges: const <String>['surging'],
          player: starTwo,
        ),
      ],
      nationalRegens: const <NationalRegenSeed>[seedOne, seedTwo],
      awards: <RegenAwardResult>[
        RegenAwardResult(
          award: const RegenAwardDefinition(
            id: 'award-world-player',
            code: 'BALLON_DOR',
            name: 'GTEX World Player of the Year',
            description:
                'Best overall regen season across club and national play.',
            category: 'season',
          ),
          season: RegenAwardSeason(
            id: 'season-2026',
            seasonNumber: 2026,
            startDate: DateTime.parse('2026-01-01T00:00:00Z'),
            endDate: DateTime.parse('2026-12-31T00:00:00Z'),
          ),
          winners: <RegenAwardWinner>[
            RegenAwardWinner(
              id: 'winner-1',
              playerId: starTwo.id,
              playerName: starTwo.name,
              rankingScore: 98.2,
              rank: 1,
              awardedAt: DateTime.parse('2026-12-30T18:00:00Z'),
              metadata: const <String, Object?>{
                'source_type': 'generated',
                'club_id': 'lagos-atlas',
                'position': 'AM',
                'country_name': 'Nigeria',
                'country_code': 'NG',
              },
            ),
          ],
        ),
        RegenAwardResult(
          award: const RegenAwardDefinition(
            id: 'award-u17-golden-ball',
            code: 'U17_WORLD_CUP_GOLDEN_BALL',
            name: 'GTEX U17 World Cup Golden Ball',
            description: 'Top U17 tournament performer.',
            category: 'tournament',
          ),
          season: RegenAwardSeason(
            id: 'season-2026',
            seasonNumber: 2026,
            startDate: DateTime.parse('2026-01-01T00:00:00Z'),
            endDate: DateTime.parse('2026-12-31T00:00:00Z'),
          ),
          winners: <RegenAwardWinner>[
            RegenAwardWinner(
              id: 'winner-2',
              playerId: seedTwo.id,
              playerName: seedTwo.displayName,
              rankingScore: 95.4,
              rank: 1,
              awardedAt: DateTime.parse('2026-08-02T18:00:00Z'),
              metadata: const <String, Object?>{
                'source_type': 'national_seed',
                'national_pool_only': true,
                'position': 'ST',
                'country_name': 'Brazil',
                'country_code': 'BR',
              },
            ),
          ],
        ),
      ],
      bloodlines: const <RegenBloodlineChain>[],
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
            bucket: 'generated',
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

  Future<List<RegenAwardResult>> awards({required int limit}) async =>
      _awards.take(limit).toList(growable: false);

  Future<List<RegenBloodlineChain>> bloodlines({required int limit}) async =>
      _bloodlines.take(limit).toList(growable: false);

  Future<RegenGenerationTracking> tracking() async => _tracking;
}
