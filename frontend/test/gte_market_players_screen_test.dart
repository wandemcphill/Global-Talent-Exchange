import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
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

      expect(find.text('Club'), findsOneWidget);
      expect(find.text('League'), findsOneWidget);
      expect(find.text('National team'), findsOneWidget);
      expect(
        find.text('Search player, club, league, nationality, or team'),
        findsOneWidget,
      );
    },
  );
}
