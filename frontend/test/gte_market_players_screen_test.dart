import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/player_match_service.dart';
import 'package:gte_frontend/domain/match/match_weight_presets.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';

void main() {
  testWidgets(
      'player discovery screen keeps the scout layout on narrow viewports',
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

    expect(find.text('Welcome back,'), findsOneWidget);
    expect(find.text('Scout Talent'), findsOneWidget);
    expect(find.text('Search players, clubs...'), findsOneWidget);
    expect(find.text('Top Matches'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('top-matches-section')),
        findsOneWidget);
    expect(find.text('Scout brief'), findsAtLeastNWidgets(1));
    expect(find.text('Perfect position match'), findsOneWidget);
    expect(find.text('100%'), findsOneWidget);
    expect(find.text('Discover Players'), findsOneWidget);
    expect(find.text('View Profile'), findsWidgets);

    final GridView grid = tester.widget<GridView>(
      find.byKey(const ValueKey<String>('discover-player-grid')),
    );
    final SliverGridDelegateWithFixedCrossAxisCount delegate =
        grid.gridDelegate as SliverGridDelegateWithFixedCrossAxisCount;

    expect(delegate.crossAxisCount, 2);
  });

  testWidgets('player discovery screen auto-loads more pages on scroll',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final _PagedMarketApiClient api = _PagedMarketApiClient();
    final GteExchangeController controller = GteExchangeController(
      api: api,
    );
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

    for (int i = 0; i < 6 && controller.hasMorePlayers; i += 1) {
      await tester.drag(
        find.byKey(const ValueKey<String>('discover-player-scroll')),
        const Offset(0, -1400),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));
    }

    await tester.pump(const Duration(milliseconds: 700));

    expect(controller.players.length, greaterThan(initialCount));
    expect(controller.hasMorePlayers, isFalse);
    expect(api.requests, hasLength(2));
    expect(find.text('Load more players'), findsNothing);
    expect(find.text('No more players'), findsOneWidget);
  });

  testWidgets('player discovery screen applies match weight presets',
      (WidgetTester tester) async {
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

    await tester.tap(find.text('Weights'));
    await tester.pumpAndSettle();

    expect(find.text('Tune Matching Logic'), findsOneWidget);

    await tester.tap(find.text('Ready Now'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Apply'));
    await tester.tap(find.text('Apply'));
    await tester.pumpAndSettle();

    expect(controller.weights.cacheKey, MatchWeightPresets.readyNow().cacheKey);
    expect(find.text('Ready Now Mode'), findsOneWidget);
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
