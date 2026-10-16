import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/gtex_watchlist_controller.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/player_card_watchlist_api.dart';
import 'package:gte_frontend/features/player_market_redesign/presentation/gtex_market_ownership_desk_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  group('Market + Ownership Responsive Layout Tests', () {
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

    Widget buildTestWidget(Size size) {
      return MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: SizedBox(
            width: size.width,
            height: size.height,
            child: GtexMarketOwnershipDeskScreen(
              controller: exchangeController,
              watchlistController: watchlistController,
              onOpenPlayer: (_) {},
              onOpenLogin: () {},
            ),
          ),
        ),
      );
    }

    testWidgets('renders cleanly on Mobile 390x844 viewport without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildTestWidget(const Size(390, 844)));
      await tester.pumpAndSettle();

      expect(find.text('TRANSFER INTELLIGENCE'), findsOneWidget);
      expect(find.text('Transfer Hub'), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('renders cleanly on Tablet 768x1024 viewport without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(768, 1024);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildTestWidget(const Size(768, 1024)));
      await tester.pumpAndSettle();

      expect(find.text('TRANSFER INTELLIGENCE'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('renders cleanly on Desktop 1440x900 viewport without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildTestWidget(const Size(1440, 900)));
      await tester.pumpAndSettle();

      expect(find.text('TRANSFER INTELLIGENCE'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
