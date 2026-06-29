import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/awards/gtex_awards_screen_v2.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_screen.dart';
import 'package:gte_frontend/features/coin_trader_redesign/coin_trader_redesign.dart';
import 'package:gte_frontend/features/launch_control_redesign/gtex_feature_flags_launch_control_screen_v2.dart';
import 'package:gte_frontend/features/federations/federations_hub_screen.dart';
import 'package:gte_frontend/features/football_world_simulation/presentation/football_world_simulation_screen.dart';
import 'package:gte_frontend/features/match/gte_live_match_hub_route_screen.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_screen.dart';
import 'package:gte_frontend/features/news_agency/gtex_news_agency_screen_v2.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/features/regens/regens_screen_v2.dart';
import 'package:gte_frontend/features/trust_ops_redesign/trust_ops_redesign.dart'
    show GtexAdminTrustOpsScreen;
import 'package:gte_frontend/features/viral_feed/presentation/viral_feed_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen_v2.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_notification_matrix_screen.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_trust_ops_screen_v2.dart';
import 'package:gte_frontend/screens/gtex_public_landing_screen_v2.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/auth/gtex_account_signup_screens.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_live_profile_screen.dart';
import 'package:gte_frontend/screens/support/gte_support_dispute_screens.dart';
import 'package:gte_frontend/screens/wallet/gte_kyc_screen.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

void main() {
  group('route coverage', () {
    test('production route hosts do not mount demo-only V2 wrappers', () {
      final List<File> routeHostFiles = <File>[
        File('lib/router/app_router.dart'),
        File(
          'lib/features/navigation/presentation/gte_navigation_shell_screen.dart',
        ),
        File('lib/features/app_routes/gte_app_route_registry.dart'),
        File('lib/features/app_routes/gte_feature_route_builders.dart'),
      ];
      const List<String> blockedTokens = <String>[
        'GtexKycScreenV2',
        'GtexDisputesScreenV2',
        'GtexAdminCommandCenterScreenV2',
        'GtexAdminCoinEconomyScreenV2',
        'GtexAdminJackpotScreenV2',
        'GtexAdminNewsroomScreenV2',
        'GtexChatScreenV2',
        'GtexProfileScreenV2',
        'GtexSocialFanHubScreenV2',
        'DemoRepository',
        '.demo(',
        '.fixture(',
        'FixtureRepository',
        'FixtureTransport',
        'GteMockApi(',
      ];

      for (final File file in routeHostFiles) {
        final String source = file.readAsStringSync();
        for (final String token in blockedTokens) {
          expect(
            source,
            isNot(contains(token)),
            reason: '${file.path}: $token',
          );
        }
      }
    });

    test('route registry and router paths do not collide accidentally', () {
      final Set<String> routeNames = <String>{};
      final Set<String> duplicateNames = <String>{};
      final Set<String> catalogPaths = <String>{};
      final Set<String> duplicateCatalogPaths = <String>{};

      for (final GteAppRouteRegistration registration
          in GteAppRouteCatalog.registrations) {
        if (!routeNames.add(registration.name)) {
          duplicateNames.add(registration.name);
        }
        if (!catalogPaths.add(registration.path)) {
          duplicateCatalogPaths.add(registration.path);
        }
      }

      expect(duplicateNames, isEmpty);
      expect(duplicateCatalogPaths, isEmpty);

      final String appRouterSource =
          File('lib/router/app_router.dart').readAsStringSync();
      final Iterable<String> directRouterPaths = RegExp("path:\\s*'([^']+)'")
          .allMatches(appRouterSource)
          .map((RegExpMatch match) => match.group(1)!)
          .where((String path) => path.startsWith('/'));

      final Set<String> seenDirectPaths = <String>{};
      final Set<String> duplicateDirectPaths = <String>{};
      for (final String path in directRouterPaths) {
        if (!seenDirectPaths.add(path)) {
          duplicateDirectPaths.add(path);
        }
      }
      expect(duplicateDirectPaths, isEmpty);

      const Set<String> intentionallyShellOwnedCatalogPaths = <String>{
        '/competitions',
        '/player-cards',
        '/world',
        '/world/regens',
        '/world/federations',
        '/world/awards',
        '/national-team',
        '/football/transfer-center',
        '/streamer-tournaments',
        '/viral-feed',
      };
      final Set<String> directCatalogCollisions =
          seenDirectPaths.where(catalogPaths.contains).toSet();
      expect(
        directCatalogCollisions,
        intentionallyShellOwnedCatalogPaths,
        reason:
            'Any catalog route also declared directly in app_router.dart must be intentionally shell-owned.',
      );
    });

    test('production-facing V2 wrappers default to live backend mode', () {
      const GtexAwardsScreenV2 awards = GtexAwardsScreenV2();
      expect(awards.backendMode, GteBackendMode.live);

      const GtexAdminTrustOpsScreenV2 trustOpsWrapper =
          GtexAdminTrustOpsScreenV2();
      expect(trustOpsWrapper.backendMode, GteBackendMode.live);

      const GtexAdminTrustOpsScreen trustOps = GtexAdminTrustOpsScreen();
      expect(trustOps.backendMode, GteBackendMode.live);
    });

    testWidgets('root URL opens public GTEX landing for guest sessions', (
      WidgetTester tester,
    ) async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexPublicLandingRouteScreenV2), findsOneWidget);
      expect(find.text('GTEX'), findsWidgets);
    });

    testWidgets('landing Sign in navigates to the login screen', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1200, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/',
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      expect(find.byType(GteLoginScreen), findsOneWidget);
    });

    testWidgets('landing Create free account navigates to user signup', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1200, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/',
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create free account'));
      await tester.pumpAndSettle();

      expect(find.byType(GtexUserSignupScreen), findsOneWidget);
    });

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
        '/home',
        '/player-cards',
        '/market',
        '/player-market',
        '/competitions/hosted',
        '/club',
        '/wallet',
        '/coin-traders',
        '/trader-dashboard',
        '/orders',
        '/payments',
        '/social',
        '/chat',
        '/inbox',
        '/play',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('shell-$path'),
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

    testWidgets('legacy content URLs resolve to live V2 surfaces', (
      WidgetTester tester,
    ) async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      for (final MapEntry<String, Type> expectation
          in <String, Type>{
            '/clips': GtexNewsAgencyScreenV2,
            '/news': GtexNewsAgencyScreenV2,
            '/world': FootballWorldSimulationScreen,
            '/world/regens': RegensScreenV2,
            '/world/awards': GtexAwardsScreenV2,
            '/awards': GtexAwardsScreenV2,
            '/world/federations': FederationsHubRouteScreen,
            '/federations': FederationsHubRouteScreen,
            '/viral': ViralFeedScreen,
            '/viral-feed': ViralFeedScreen,
            '/regens': RegensScreenV2,
            '/regen-world': RegensScreenV2,
            '/profile': GtexLiveProfileScreen,
            '/settings': GtexLiveProfileScreen,
            '/account': GtexLiveProfileScreen,
            '/notifications': GteNotificationsScreenV2,
            '/kyc': GteKycScreen,
            '/compliance': GteKycScreen,
            '/disputes': GteDisputeHubScreen,
            '/support': GteDisputeHubScreen,
            '/admin': GteRouteIntegrityScreen,
            '/admin/launch-control': GteRouteIntegrityScreen,
            '/admin/coin-traders': GteRouteIntegrityScreen,
            '/admin/notifications': GteRouteIntegrityScreen,
            '/admin/trust-ops': GteRouteIntegrityScreen,
            '/admin/matchday-economy': GteRouteIntegrityScreen,
          }.entries) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('legacy-${expectation.key}'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: expectation.key,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byType(expectation.value),
          findsOneWidget,
          reason: expectation.key,
        );
      }

      for (final String path in <String>[
        '/match',
        '/match-center',
        '/broadcast',
        '/broadcast/live',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('launch-gated-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text('Broadcast unavailable'), findsOneWidget);
        expect(find.text('Rights worker paused.'), findsOneWidget);
      }
    });

    testWidgets('admin launch-control route mounts for admin sessions', (
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
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/admin/launch-control',
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byType(GtexFeatureFlagsLaunchControlScreenV2),
        findsOneWidget,
      );
      expect(find.text('Feature flags'), findsOneWidget);
    });

    testWidgets('admin trust-ops route mounts for admin sessions', (
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
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/admin/trust-ops',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexAdminTrustOpsScreenV2), findsOneWidget);
      expect(find.text('Admin Trust Operations'), findsOneWidget);
    });

    testWidgets('admin coin-traders route mounts for admin sessions', (
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
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/admin/coin-traders',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexCoinTraderAdminScreen), findsOneWidget);
      expect(find.text('Coin Trader Ops'), findsOneWidget);
    });

    testWidgets('admin matchday economy route mounts for admin sessions', (
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
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/admin/matchday-economy',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexMatchdayEconomyAdminScreen), findsOneWidget);
      expect(find.text('Matchday economy'), findsOneWidget);
      expect(find.text('Federation Governance'), findsOneWidget);
    });

    testWidgets('admin notification matrix route mounts for admin sessions', (
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
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/admin/notifications',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexAdminNotificationMatrixScreen), findsOneWidget);
      expect(find.text('Admin Notification Matrix'), findsOneWidget);
      expect(find.text('Test dispatch'), findsOneWidget);
    });

    testWidgets(
      'Transfer Hub alias resolves through the existing market shell',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(2600, 2600);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );

        await tester.pumpWidget(
          GteFrontendApp(
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: '/app/transfer-hub',
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(GteExchangeShellScreen), findsOneWidget);
        expect(find.byType(GteMarketPlayersScreenV2), findsOneWidget);
        expect(find.text('Transfer Hub'), findsWidgets);
      },
    );

    testWidgets('Coin Trader app routes resolve through the active shell', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(2600, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      for (final String path in <String>[
        '/app/capital/orders',
        '/app/capital/holdings',
        '/app/coin-traders',
        '/app/trader-dashboard',
      ]) {
        await tester.pumpWidget(
          GteFrontendApp(
            key: ValueKey<String>('coin-trader-$path'),
            controller: controller,
            config: const GteAppConfig(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
            ),
            initialPath: path,
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(GteExchangeShellScreen), findsOneWidget);
        if (path == '/app/trader-dashboard') {
          expect(find.text('Trader dashboard locked'), findsOneWidget);
        }
      }
    });

    testWidgets('capital module tabs keep the browser route canonical', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(2600, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.syncSession(_adminSession());

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/app/capital',
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey<String>('capital-module-orders')),
      );
      await tester.pumpAndSettle();
      expect(_activePath(tester), '/app/capital/orders');

      await tester.tap(
        find.byKey(const ValueKey<String>('capital-module-coin-traders')),
      );
      await tester.pumpAndSettle();
      expect(_activePath(tester), '/app/coin-traders');

      await tester.tap(
        find.byKey(const ValueKey<String>('capital-module-trader-dashboard')),
      );
      await tester.pumpAndSettle();
      expect(_activePath(tester), '/app/trader-dashboard');

      await tester.tap(
        find.byKey(const ValueKey<String>('capital-module-wallet')),
      );
      await tester.pumpAndSettle();
      expect(_activePath(tester), '/app/capital');
    });

    testWidgets('locked capital landing can open public coin traders', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(2600, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        GteFrontendApp(
          controller: controller,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
          initialPath: '/app/capital',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Wallet locked'), findsOneWidget);

      await tester.tap(find.text('Browse traders'));
      await tester.pumpAndSettle();

      expect(_activePath(tester), '/app/coin-traders');
      expect(find.text('No approved coin traders yet'), findsOneWidget);
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
        expectedType: RegensScreenV2,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const NewsDeskRouteData(),
        expectedType: GtexNewsAgencyScreenV2,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const WorldFederationsRouteData(),
        expectedType: FederationsHubScreen,
      );
      await _expectRouteMounts(
        tester,
        registry: registry,
        route: const ViralFeedRouteData(),
        expectedType: ViralFeedScreen,
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

GteAuthSession _adminSession() {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'fixture-admin-token',
    'refresh_token': 'fixture-refresh-token',
    'session_id': 'fixture-admin-session',
    'token_type': 'bearer',
    'expires_in': 3600,
    'refresh_expires_in': 7200,
    'user': <String, Object?>{
      'id': 'fixture-admin',
      'email': 'admin@gtex.test',
      'username': 'fixture_admin',
      'display_name': 'Fixture Admin',
      'role': 'admin',
    },
  });
}

String _activePath(WidgetTester tester) {
  final BuildContext context = tester.element(
    find.byType(GteExchangeShellScreen),
  );
  return GoRouter.of(context).routeInformationProvider.value.uri.path;
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
        home: Scaffold(
          body: Builder(
            builder:
                (BuildContext context) => registry.buildScreen(context, route),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await tester.pumpAndSettle();
  expect(find.byType(expectedType), findsOneWidget);
}
