import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/player_match_service.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';

void main() {
  testWidgets(
    'player market keeps the card layout stable on narrow viewports',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 800));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.marketPage = const GteMarketPlayerListView(
        items: <GteMarketPlayerListItem>[
          GteMarketPlayerListItem(
            playerId: 'player-1',
            playerName: 'Ayo Forward',
            position: 'ST',
            nationality: 'Nigeria',
            currentClubName: 'Free Agent',
            age: 20,
            currentValueCredits: 1200,
            movementPct: 0.08,
            trendScore: 8.2,
            marketInterestScore: 78,
            averageRating: 7.4,
          ),
          GteMarketPlayerListItem(
            playerId: 'player-2',
            playerName: 'Mina Creator',
            position: 'AM',
            nationality: 'Ghana',
            currentClubName: 'Accra Stars',
            age: 22,
            currentValueCredits: 980,
            movementPct: -0.03,
            trendScore: 6.8,
            marketInterestScore: 64,
            averageRating: 7.1,
          ),
        ],
        limit: 20,
        hasMore: false,
        offset: 0,
        total: 2,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: GteMarketPlayersScreen(
            controller: controller,
            onOpenPlayer: (_) {},
            onOpenLogin: () {},
            matchService: GtePlayerMatchService(latency: Duration.zero),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 700));

      expect(find.text('PLAYER MARKET'), findsOneWidget);
      expect(find.text('Board pulse'), findsOneWidget);
      expect(find.text('FILTERS'), findsOneWidget);
      expect(find.text('PLAYER BOARD'), findsOneWidget);
      expect(find.text('Ayo Forward'), findsOneWidget);
      expect(find.text('Mina Creator'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('player market loads more pages from the board CTA', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final _PagedMarketApiClient api = _PagedMarketApiClient();
    final GteExchangeController controller = GteExchangeController(api: api);
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
          matchService: GtePlayerMatchService(latency: Duration.zero),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    final int initialCount = controller.players.length;

    await tester.drag(
      find.byKey(const ValueKey<String>('trading-floor-scroll')),
      const Offset(0, -1600),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Load more players'));
    await tester.pumpAndSettle();
    expect(find.text('Load more players'), findsOneWidget);

    await tester.tap(find.text('Load more players'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(controller.players.length, greaterThan(initialCount));
    expect(controller.hasMorePlayers, isFalse);
    expect(api.requests, hasLength(2));
    expect(
      controller.players.any(
        (GteMarketPlayerListItem player) => player.playerId == 'player-3',
      ),
      isTrue,
    );
  });

  testWidgets('player market filters the visible board with focus chips', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.marketPage = const GteMarketPlayerListView(
      items: <GteMarketPlayerListItem>[
        GteMarketPlayerListItem(
          playerId: 'player-1',
          playerName: 'Ayo Forward',
          position: 'ST',
          nationality: 'Nigeria',
          currentClubName: 'Free Agent',
          age: 29,
          currentValueCredits: 1200,
          movementPct: 0.08,
          trendScore: 8.2,
          marketInterestScore: 78,
          averageRating: 7.4,
        ),
        GteMarketPlayerListItem(
          playerId: 'player-2',
          playerName: 'Mina Creator',
          position: 'ST',
          nationality: 'Nigeria',
          currentClubName: 'Accra Stars',
          age: 22,
          currentValueCredits: 980,
          movementPct: -0.03,
          trendScore: 6.8,
          marketInterestScore: 64,
          averageRating: 7.1,
        ),
      ],
      limit: 20,
      hasMore: false,
      offset: 0,
      total: 2,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
          matchService: GtePlayerMatchService(latency: Duration.zero),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.text('Ayo Forward'), findsOneWidget);
    expect(find.text('Mina Creator'), findsOneWidget);

    await tester.ensureVisible(find.text('Dips 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Dips 1'));
    await tester.pumpAndSettle();

    expect(find.text('Ayo Forward'), findsNothing);
    expect(find.text('Mina Creator'), findsOneWidget);

    await tester.ensureVisible(find.text('Watchlist 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Watchlist 1'));
    await tester.pumpAndSettle();

    expect(find.text('Ayo Forward'), findsOneWidget);
    expect(find.text('Mina Creator'), findsNothing);
  });
}

class _PagedMarketApiClient extends GteExchangeApiClient {
  _PagedMarketApiClient._(GteExchangeApiClient delegate)
    : super(
        config: delegate.config,
        transport: delegate.transport,
        repository: delegate.repository,
      );

  factory _PagedMarketApiClient() {
    final GteExchangeApiClient delegate = GteExchangeApiClient.fixture();
    return _PagedMarketApiClient._(delegate);
  }

  final List<GteMarketPlayersQuery> requests = <GteMarketPlayersQuery>[];

  @override
  Future<GteMarketPlayerListView> fetchPlayers({
    GteMarketPlayersQuery query = const GteMarketPlayersQuery(),
  }) async {
    requests.add(query);
    if (query.cursor == null && query.offset == 0) {
      return const GteMarketPlayerListView(
        items: <GteMarketPlayerListItem>[
          GteMarketPlayerListItem(
            playerId: 'player-1',
            playerName: 'Ayo Forward',
            position: 'ST',
            nationality: 'Nigeria',
            currentClubName: 'Free Agent',
            age: 20,
            currentValueCredits: 1200,
            movementPct: 0.08,
            trendScore: 8.2,
            marketInterestScore: 78,
            averageRating: 7.4,
          ),
          GteMarketPlayerListItem(
            playerId: 'player-2',
            playerName: 'Mina Creator',
            position: 'AM',
            nationality: 'Ghana',
            currentClubName: 'Accra Stars',
            age: 22,
            currentValueCredits: 980,
            movementPct: -0.03,
            trendScore: 6.8,
            marketInterestScore: 64,
            averageRating: 7.1,
          ),
        ],
        limit: 2,
        hasMore: true,
        nextCursor: 'page-2',
        offset: 0,
        total: 3,
      );
    }

    return const GteMarketPlayerListView(
      items: <GteMarketPlayerListItem>[
        GteMarketPlayerListItem(
          playerId: 'player-3',
          playerName: 'Dami Anchor',
          position: 'CB',
          nationality: 'Nigeria',
          currentClubName: 'Lagos United',
          age: 24,
          currentValueCredits: 1100,
          movementPct: 0.02,
          trendScore: 7.1,
          marketInterestScore: 70,
          averageRating: 7.0,
        ),
      ],
      limit: 2,
      hasMore: false,
      nextCursor: null,
      offset: 2,
      total: 3,
    );
  }
}
