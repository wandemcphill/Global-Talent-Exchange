import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(const <String, Object>{});

  test(
    'bootstrap reuses the same in-flight future and stamps market sync',
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
    },
  );

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
    },
  );

  test('bootstrap keeps a warm market page instead of reloading it', () async {
    final _OverlappingMarketApiClient api = _OverlappingMarketApiClient();
    final GteExchangeController controller = GteExchangeController(api: api);

    await controller.bootstrap();
    await controller.bootstrap();

    expect(api.queries, hasLength(1));
    expect(controller.players, isNotEmpty);
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

  test(
    'live openPlayer resolves from market snapshot without loading compatibility profile',
    () async {
      final _LiveSnapshotOnlyApiClient api = _LiveSnapshotOnlyApiClient();
      final GteExchangeController controller = GteExchangeController(api: api);

      await controller.openPlayer('player-live-1');

      expect(api.fetchPlayerProfileCalls, 0);
      expect(controller.selectedPlayer?.detail.playerId, 'player-live-1');
      expect(controller.selectedProfile, isNull);
      expect(controller.playerError, isNull);
      expect(controller.playerProfileError, isNull);
    },
  );
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

class _LiveSnapshotOnlyApiClient extends GteExchangeApiClient {
  _LiveSnapshotOnlyApiClient()
    : super(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: _UnexpectedTransport(),
        repository: GteMockApi(latency: Duration.zero),
      );

  int fetchPlayerProfileCalls = 0;

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    fetchPlayerProfileCalls += 1;
    throw StateError(
      'Live player detail should not request compatibility data',
    );
  }

  @override
  Future<GtePlayerMarketSnapshot> fetchPlayerMarket(
    String playerId, {
    String interval = '1h',
    int limit = 30,
  }) async {
    return _buildLiveSnapshot(playerId, interval: interval);
  }

  static GtePlayerMarketSnapshot _buildLiveSnapshot(
    String playerId, {
    String interval = '1h',
  }) {
    return GtePlayerMarketSnapshot(
      detail: GteMarketPlayerDetailView.fromJson(<String, Object?>{
        'player_id': playerId,
        'identity': <String, Object?>{
          'player_name': 'Live Midfield Prospect',
          'position': 'CM',
          'normalized_position': 'cm',
          'nationality': 'Nigeria',
          'nationality_code': 'NG',
          'age': 21,
          'current_club_name': 'Ibadan Lions FC',
        },
        'market_profile': <String, Object?>{
          'is_tradable': true,
          'liquidity_band': 'deep',
          'trade_trust_score': 8.1,
        },
        'value': <String, Object?>{
          'current_value_credits': 1200,
          'previous_value_credits': 1160,
          'movement_pct': 0.045,
        },
        'trend': <String, Object?>{
          'trend_score': 88.0,
          'market_interest_score': 84,
          'average_rating': 7.2,
          'global_scouting_index': 88.0,
          'drivers': <String>['Line-breaking passing', 'Press resistance'],
        },
      }),
      ticker: GteMarketTicker.fromJson(<String, Object?>{
        'player_id': playerId,
        'symbol': 'L. Prospect',
        'last_price': 1200,
        'best_bid': 1190,
        'best_ask': 1210,
        'spread': 20,
        'mid_price': 1200,
        'reference_price': 1180,
        'day_change': 20,
        'day_change_percent': 1.69,
        'volume_24h': 4,
      }),
      candles: GteMarketCandles.fromJson(<String, Object?>{
        'player_id': playerId,
        'interval': interval,
        'candles': <Map<String, Object?>>[
          <String, Object?>{
            'timestamp': '2026-03-31T10:00:00Z',
            'open': 1180,
            'high': 1210,
            'low': 1175,
            'close': 1200,
            'volume': 4,
          },
          <String, Object?>{
            'timestamp': '2026-03-31T11:00:00Z',
            'open': 1200,
            'high': 1220,
            'low': 1195,
            'close': 1210,
            'volume': 5,
          },
        ],
      }),
      orderBook: GteOrderBook.fromJson(<String, Object?>{
        'player_id': playerId,
        'generated_at': '2026-03-31T11:00:00Z',
        'bids': <Map<String, Object?>>[
          <String, Object?>{'price': 1190, 'quantity': 3, 'order_count': 1},
        ],
        'asks': <Map<String, Object?>>[
          <String, Object?>{'price': 1210, 'quantity': 2, 'order_count': 1},
        ],
      }),
      overview: GtePlayerOverview.fromJson(<String, Object?>{
        'player_id': playerId,
        'player_name': 'Live Midfield Prospect',
        'position': 'CM',
        'overview_generated_on': '2026-03-31T11:00:00Z',
        'career_summary': <String, Object?>{
          'player_id': playerId,
          'player_name': 'Live Midfield Prospect',
          'current_club_name': 'Ibadan Lions FC',
          'current_competition_name': 'Premier League',
          'totals': <String, Object?>{
            'appearances': 33,
            'goals': 6,
            'assists': 11,
            'minutes': 2710,
          },
          'seasonal_progression': <Map<String, Object?>>[
            <String, Object?>{
              'season_label': '2025/26',
              'club_name': 'Ibadan Lions FC',
              'appearances': 33,
              'goals': 6,
              'assists': 11,
              'average_rating': 7.2,
            },
          ],
        },
        'availability_badge': <String, Object?>{
          'status': 'available',
          'label': 'Available',
          'available': true,
        },
        'transfer_status': <String, Object?>{
          'window_open': true,
          'eligible': true,
          'reason': 'Open to a move if the role expands.',
          'window_label': 'Open market',
        },
        'recent_events': <Map<String, Object?>>[
          <String, Object?>{
            'event_type': 'market_signal',
            'summary': 'Line-breaking passing',
            'occurred_on': '2026-03-31T10:00:00Z',
          },
        ],
      }),
      careerEntries: <GteCareerEntry>[
        GteCareerEntry(
          id: '$playerId-2025',
          playerId: playerId,
          clubId: 'ibadan-lions',
          clubName: 'Ibadan Lions FC',
          seasonLabel: '2025/26',
          squadRole: 'First team',
          appearances: 33,
          goals: 6,
          assists: 11,
          averageRating: 7,
          notes: 'Live market breakout season',
          startOn: DateTime.utc(2025, 7, 1),
          endOn: DateTime.utc(2026, 5, 31),
          updatedAt: DateTime.utc(2026, 3, 31),
        ),
      ],
      lifecycle: GtePlayerLifecycleSnapshot.fromJson(<String, Object?>{
        'player_id': playerId,
        'player_name': 'Live Midfield Prospect',
        'availability_badge': <String, Object?>{
          'status': 'available',
          'label': 'Available',
          'available': true,
        },
        'transfer_status': <String, Object?>{
          'window_open': true,
          'eligible': true,
          'reason': 'Open to a move if the role expands.',
          'window_label': 'Open market',
        },
        'recent_events': const <Object?>[],
      }),
    );
  }
}

class _UnexpectedTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw UnimplementedError(
      'Unexpected transport call: ${request.method} ${request.uri}',
    );
  }
}
