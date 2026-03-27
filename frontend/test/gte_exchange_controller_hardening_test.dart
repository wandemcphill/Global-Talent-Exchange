import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('bootstrap reuses the same in-flight future and stamps market sync',
      () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(
        latency: const Duration(milliseconds: 10),
      ),
    );

    final Future<void> first = controller.bootstrap();
    final Future<void> second = controller.bootstrap();

    expect(identical(first, second), isTrue);

    await first;

    expect(controller.players, isNotEmpty);
    expect(controller.marketSyncedAt, isNotNull);
  });

  test('account refresh stamps both portfolio and order sync times', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(email: 'demo@gtex.test', password: 'password');
    await controller.refreshAccount();

    expect(controller.walletSummary, isNotNull);
    expect(controller.portfolio, isNotNull);
    expect(controller.portfolioSyncedAt, isNotNull);
    expect(controller.ordersSyncedAt, isNotNull);
  });

  test(
      'loadMarket falls back to offset pagination and dedupes overlapping players',
      () async {
    final _OverlappingMarketApiClient api = _OverlappingMarketApiClient();
    final GteExchangeController controller = GteExchangeController(api: api);

    await controller.bootstrap();
    await controller.loadMarket(reset: false);

    expect(api.queries, hasLength(2));
    expect(api.queries.first.offset, 0);
    expect(api.queries.first.cursor, isNull);
    expect(api.queries[1].offset, 2);
    expect(api.queries[1].cursor, isNull);
    expect(
      controller.players
          .map((GteMarketPlayerListItem player) => player.playerId)
          .toList(growable: false),
      <String>['player-1', 'player-2', 'player-3'],
    );
    expect(controller.hasMorePlayers, isFalse);
  });

  test('loadMarket resets the market page when filters change', () async {
    final _FilterResetMarketApiClient api = _FilterResetMarketApiClient();
    final GteExchangeController controller = GteExchangeController(api: api);

    await controller.loadMarket(reset: true);
    expect(
      controller.players
          .map((GteMarketPlayerListItem player) => player.playerId)
          .toList(growable: false),
      <String>['player-1', 'player-2'],
    );

    await controller.loadMarket(
      filter: const PlayerFilter(position: 'ST', availability: 'free_agent'),
      reset: false,
    );

    expect(api.queries, hasLength(2));
    expect(api.queries[1].offset, 0);
    expect(api.queries[1].cursor, isNull);
    expect(api.queries[1].position, 'ST');
    expect(api.queries[1].availability, 'free_agent');
    expect(
      controller.players
          .map((GteMarketPlayerListItem player) => player.playerId)
          .toList(growable: false),
      <String>['player-3'],
    );
    expect(controller.marketFilter.position, 'ST');
    expect(controller.marketFilter.availability, 'free_agent');
  });
}

class _OverlappingMarketApiClient extends GteExchangeApiClient {
  _OverlappingMarketApiClient._(GteExchangeApiClient delegate)
      : super(
          config: delegate.config,
          transport: delegate.transport,
          repository: delegate.repository,
        );

  factory _OverlappingMarketApiClient() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _OverlappingMarketApiClient._(delegate);
  }

  final List<GteMarketPlayersQuery> queries = <GteMarketPlayersQuery>[];
  int _pageIndex = 0;

  @override
  Future<GteMarketPlayerListView> fetchPlayers({
    GteMarketPlayersQuery query = const GteMarketPlayersQuery(),
  }) async {
    queries.add(query);
    final List<GteMarketPlayerListView> pages = <GteMarketPlayerListView>[
      GteMarketPlayerListView(
        items: <GteMarketPlayerListItem>[
          _player('player-1', 'Player One'),
          _player('player-2', 'Player Two'),
        ],
        limit: 2,
        hasMore: true,
        nextCursor: null,
        offset: 0,
        total: 3,
      ),
      GteMarketPlayerListView(
        items: <GteMarketPlayerListItem>[
          _player('player-2', 'Player Two'),
          _player('player-3', 'Player Three'),
        ],
        limit: 2,
        hasMore: false,
        nextCursor: null,
        offset: 2,
        total: 3,
      ),
    ];
    final int safeIndex =
        _pageIndex >= pages.length ? pages.length - 1 : _pageIndex;
    _pageIndex += 1;
    return pages[safeIndex];
  }

  static GteMarketPlayerListItem _player(String id, String name) {
    return GteMarketPlayerListItem(
      playerId: id,
      playerName: name,
      position: 'CM',
      nationality: 'Nigeria',
      currentClubName: 'GTEX FC',
      age: 22,
      currentValueCredits: 100,
      movementPct: 1.5,
      trendScore: 75,
      marketInterestScore: 80,
      averageRating: 7.2,
    );
  }
}

class _FilterResetMarketApiClient extends GteExchangeApiClient {
  _FilterResetMarketApiClient._(GteExchangeApiClient delegate)
      : super(
          config: delegate.config,
          transport: delegate.transport,
          repository: delegate.repository,
        );

  factory _FilterResetMarketApiClient() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _FilterResetMarketApiClient._(delegate);
  }

  final List<GteMarketPlayersQuery> queries = <GteMarketPlayersQuery>[];

  @override
  Future<GteMarketPlayerListView> fetchPlayers({
    GteMarketPlayersQuery query = const GteMarketPlayersQuery(),
  }) async {
    queries.add(query);
    if (query.position == 'ST' && query.availability == 'free_agent') {
      return GteMarketPlayerListView(
        items: <GteMarketPlayerListItem>[
          _OverlappingMarketApiClient._player('player-3', 'Free Agent Nine'),
        ],
        limit: query.limit,
        hasMore: false,
        nextCursor: null,
        offset: 0,
        total: 1,
      );
    }
    return GteMarketPlayerListView(
      items: <GteMarketPlayerListItem>[
        _OverlappingMarketApiClient._player('player-1', 'Player One'),
        _OverlappingMarketApiClient._player('player-2', 'Player Two'),
      ],
      limit: query.limit,
      hasMore: false,
      nextCursor: null,
      offset: 0,
      total: 2,
    );
  }
}
