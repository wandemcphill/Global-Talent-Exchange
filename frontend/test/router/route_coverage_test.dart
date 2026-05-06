import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/features/regens/regens_screen.dart';
import 'package:gte_frontend/features/transfer_news_calendar/presentation/transfer_news_calendar_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';

void main() {
  group('route coverage', () {
    testWidgets('top-level legacy URLs resolve through the premium shell', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      for (final String path in <String>[
        '/player-cards',
        '/market',
        '/competitions/hosted',
        '/world/regens',
        '/news',
        '/clips',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(GteExchangeShellScreen), findsOneWidget, reason: path);
      }
    });

    testWidgets('canonical feature routes mount their registered widgets', (
      WidgetTester tester,
    ) async {
      final GteAppRouteRegistry registry = GteAppRouteRegistry(
        dependencies: const GteNavigationDependencies(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          currentUserId: 'fixture-user',
          currentUserName: 'Fixture User',
          isAuthenticated: true,
          accessToken: 'fixture-token',
        ),
      );

      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const PlayerCardsBrowseRouteData(),
        expectedType: PlayerCardMarketplaceScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const RegenUniverseRouteData(),
        expectedType: RegensScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const NewsDeskRouteData(),
        expectedType: TransferNewsCalendarScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const ClubSaleMarketListingsRouteData(),
        expectedType: ClubSaleMarketScreen,
      );
    });
  });
}

Future<void> _expectRouteMounts(
  WidgetTester tester, {
  required GteAppRouteRegistry registry,
  required GteAppRouteData route,
  required Type expectedType,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        home: Builder(
          builder:
              (BuildContext context) => registry.buildScreen(context, route),
        ),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await tester.pumpAndSettle();
  expect(find.byType(expectedType), findsOneWidget);
}
