import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';

void main() {
  testWidgets(
    'market screen exposes dedicated club, league, and national team filters',
    (WidgetTester tester) async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: GteMarketPlayersScreen(
            controller: controller,
            onOpenPlayer: (_) {},
            onOpenLogin: () {},
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Club'), findsOneWidget);
      expect(find.text('League'), findsOneWidget);
      expect(find.text('National team'), findsOneWidget);
      expect(
        find.text('Search player, club, league, nationality, or team'),
        findsOneWidget,
      );
    },
  );

  testWidgets('market player cards render real network images when available', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.marketPage = const GteMarketPlayerListView(
      items: <GteMarketPlayerListItem>[
        GteMarketPlayerListItem(
          playerId: 'player-photo-1',
          playerName: 'Photo Forward',
          position: 'forward',
          nationality: 'Nigeria',
          currentClubName: 'Alpha FC',
          age: 21,
          currentValueCredits: 210,
          movementPct: 0.08,
          trendScore: 88,
          marketInterestScore: 92,
          averageRating: 7.8,
          imageUrl: 'https://cdn.sportmonks.test/players/photo-forward.png',
        ),
      ],
      limit: 20,
      hasMore: false,
      offset: 0,
      total: 1,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GteMarketPlayersScreen(
          controller: controller,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('market-player-network-image')), findsWidgets);
  });

  test('market player model parses snake-case image_url', () {
    final GteMarketPlayerListItem item =
        GteMarketPlayerListItem.fromJson(<String, Object?>{
          'player_id': 'player-photo-2',
          'player_name': 'Image Midfielder',
          'position': 'midfielder',
          'nationality': 'Spain',
          'current_club_name': 'Beta United',
          'age': 23,
          'current_value_credits': 190,
          'movement_pct': 0.04,
          'trend_score': 80,
          'market_interest_score': 70,
          'average_rating': 7.2,
          'image_url': 'https://cdn.sportmonks.test/players/image-mid.png',
        });

    expect(item.imageUrl, 'https://cdn.sportmonks.test/players/image-mid.png');
  });
}
