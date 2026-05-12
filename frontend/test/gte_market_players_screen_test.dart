import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen_v2.dart';

void main() {
  testWidgets('legacy market import delegates to the GTEX Transfer Hub V2', (
    WidgetTester tester,
  ) async {
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

    expect(find.byType(GteMarketPlayersScreenV2), findsOneWidget);
    expect(find.text('Transfer Hub'), findsWidgets);
    expect(find.text('My Shortlist'), findsOneWidget);
    expect(
      find.text('Search player, club, league, nationality'),
      findsOneWidget,
    );
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
