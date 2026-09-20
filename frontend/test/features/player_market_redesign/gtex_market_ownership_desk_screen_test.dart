import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/gtex_watchlist_controller.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/player_card_watchlist_api.dart';
import 'package:gte_frontend/features/player_market_redesign/presentation/gtex_market_ownership_desk_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  group('GtexMarketOwnershipDeskScreen Widget Tests', () {
    late GteExchangeController exchangeController;
    late GtexWatchlistController watchlistController;

    setUp(() {
      exchangeController = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      watchlistController = GtexWatchlistController(
        api: FixturePlayerCardWatchlistApi(),
      );
    });

    Widget buildTestWidget({
      GtexMarketDeskMode initialMode = GtexMarketDeskMode.market,
    }) {
      return MaterialApp(
        home: GtexMarketOwnershipDeskScreen(
          controller: exchangeController,
          watchlistController: watchlistController,
          initialMode: initialMode,
          onOpenPlayer: (_) {},
          onOpenLogin: () {},
        ),
      );
    }

    testWidgets('renders masthead mode buttons and switches modes', (WidgetTester tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('TRANSFER INTELLIGENCE'), findsOneWidget);
      expect(find.text('MY OWNERSHIP'), findsOneWidget);

      // Tap MY OWNERSHIP mode
      await tester.tap(find.text('MY OWNERSHIP'));
      await tester.pumpAndSettle();

      // Should show squad/holdings view
      expect(find.text('Your squad is empty'), findsOneWidget);

      // Switch back to TRANSFER INTELLIGENCE
      await tester.tap(find.text('TRANSFER INTELLIGENCE'));
      await tester.pumpAndSettle();

      expect(find.text('Transfer Hub'), findsWidgets);
    });
  });
}
