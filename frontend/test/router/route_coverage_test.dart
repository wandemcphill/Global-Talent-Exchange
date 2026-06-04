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
import 'package:gte_frontend/features/capital/liquidity/club_sale_market/presentation/club_sale_market_screen.dart';
import 'package:gte_frontend/features/match_center/gte_live_match_hub_route_screen.dart';
import 'package:gte_frontend/features/match_center/match_viewer_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/features/regens/regens_screen.dart';
import 'package:gte_frontend/features/transfer_news_calendar/presentation/transfer_news_calendar_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/router/route_constants.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';

void main() {
  group('route coverage', () {
    test('canonical route constants match the GTEX app shell tree', () {
      expect(GtexCanonicalAppRoutes.app, '/app');
      expect(GtexCanonicalAppRoutes.shellRoots, <String>[
        '/app/world',
        '/app/market',
        '/app/club',
        '/app/compete',
        '/app/capital',
        '/app/community',
        '/app/creator',
        '/app/admin',
      ]);
    });

    testWidgets('canonical shell URLs resolve through the operating shell', (
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

      for (final String path in GtexCanonicalAppRoutes.shellRoots) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('canonical-root-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byType(GteExchangeShellScreen),
          findsOneWidget,
          reason: path,
        );
      }
    });

    testWidgets(
      'canonical shell subroutes resolve through the operating shell',
      (WidgetTester tester) async {
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
          '${GtexCanonicalAppRoutes.world}/regens/build-a-son',
          '${GtexCanonicalAppRoutes.market}/search',
          '${GtexCanonicalAppRoutes.club}/squad/player-001',
          '${GtexCanonicalAppRoutes.compete}/detail/competition-001/fixtures',
          '${GtexCanonicalAppRoutes.capital}/orders/order-001',
          '${GtexCanonicalAppRoutes.community}/chat/global',
          '${GtexCanonicalAppRoutes.creator}/campaigns/campaign-001',
          '${GtexCanonicalAppRoutes.admin}/queue/payment-reviews',
        ]) {
          await tester.pumpWidget(
            GteFrontendApp(
              key: ValueKey<String>('canonical-subroute-$path'),
              controller: controller,
              config: const GteAppConfig(
                apiBaseUrl: 'http://127.0.0.1:8000',
                backendMode: GteBackendMode.fixture,
              ),
              initialPath: path,
            ),
          );
          await tester.pumpAndSettle();
          expect(
            find.byType(GteExchangeShellScreen),
            findsOneWidget,
            reason: path,
          );
        }
      },
    );

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
        '/trader',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('legacy-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byType(GteExchangeShellScreen),
          findsOneWidget,
          reason: path,
        );
      }
    });

    testWidgets('router-owned fixture and debug URLs stay unavailable', (
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
        '/fixtures/market',
        '/test/fixtures/market',
        '/app/fixture',
        '/app/test',
        '/app/debug',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('fixture-block-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(GteExchangeShellScreen), findsNothing, reason: path);
        expect(find.text('Route unavailable'), findsOneWidget, reason: path);
      }
    });

    testWidgets('legacy match rendering URLs are not production-mounted', (
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
        '/matches/${'3d'}/live-match-001',
        '/matches/unity/live-match-001',
        '/matches/native-3d/live-match-001',
        '/matches/pseudo-3d/live-match-001',
        '/matches/broadcast/live-match-001',
        '/matches/simulate/live-match-001',
        '/broadcast/live',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('legacy-match-block-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(GteExchangeShellScreen), findsNothing, reason: path);
        expect(find.text('Route unavailable'), findsOneWidget, reason: path);
      }
    });

    test('visible route metadata does not promote legacy match surfaces', () {
      final List<String> violations = <String>[];

      for (final GteAppRouteRegistration registration
          in GteAppRouteCatalog.registrations) {
        final String metadata = '${registration.name} ${registration.path}';
        if (_legacyMatchRoutePatterns.any(
          (RegExp pattern) => pattern.hasMatch(metadata),
        )) {
          violations.add(metadata);
        }
      }

      expect(
        violations,
        isEmpty,
        reason:
            'Production route metadata must keep legacy 3D, Unity, pseudo-3D, '
            'broadcast, spectate, and simulate match surfaces quarantined while '
            'allowing the canonical 2D match hub/viewer.',
      );
    });

    test('route parser rejects quarantined legacy match surfaces', () {
      for (final String path in <String>[
        '/matches/${'3d'}/live-match-001',
        '/matches/unity/live-match-001',
        '/matches/native-3d/live-match-001',
        '/matches/pseudo-3d/live-match-001',
        '/matches/broadcast/live-match-001',
        '/matches/spectate/live-match-001',
        '/matches/simulate/live-match-001',
        '/broadcast/live',
      ]) {
        expect(GteAppRouteParser.parse(path), isNull, reason: path);
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
        route: const RegenBuildASonRouteData(),
        expectedType: BuildASonScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const LiveMatchHubRouteData(),
        expectedType: GteLiveMatchHubRouteScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const LiveMatchViewerRouteData(matchKey: 'live-match-001'),
        expectedType: MatchViewerRouteScreen,
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

final List<RegExp> _legacyMatchRoutePatterns = <RegExp>[
  RegExp(
    r'(^|\s|[./:_-])(3d|unity|pseudo-?3d|native-?3d)(\s|$|[./:_-])',
    caseSensitive: false,
  ),
  RegExp(
    r'(^|\s)/matches/(3d|unity|pseudo-?3d|native-?3d|broadcast|spectate|simulate)(/|\s|$)',
    caseSensitive: false,
  ),
  RegExp(r'(^|\s)/broadcast/live(\s|$)', caseSensitive: false),
  RegExp(
    r'(^|\s|[./:_-])match[_-]?(broadcast|spectate|simulate)(\s|$|[./:_-])',
    caseSensitive: false,
  ),
];
