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
}

class _RegenUniverseFixtures {
  const _RegenUniverseFixtures({
    required List<RegenRisingStar> risingStars,
    required List<RegenScoutingFeedItem> feed,
  }) : _risingStars = risingStars,
       _feed = feed;

  final List<RegenRisingStar> _risingStars;
  final List<RegenScoutingFeedItem> _feed;

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
    );
  }

  Future<List<RegenRisingStar>> risingStars({required int limit}) async =>
      _risingStars.take(limit).toList(growable: false);

  Future<List<RegenScoutingFeedItem>> scoutingFeed({
    required int limit,
  }) async => _feed.take(limit).toList(growable: false);
}
