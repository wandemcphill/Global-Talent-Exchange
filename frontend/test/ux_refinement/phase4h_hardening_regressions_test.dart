import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_club_ownership_panel.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_movers_rail.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/screens/wallet/gtex_wallet_overview_screen_v2.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

/// PHASE 4H - one test per defect the audit found. Each fails on the code as
/// it stood before this branch.
void main() {
  Future<void> pumpShell(
    WidgetTester tester, {
    required double width,
    required String path,
    required GteExchangeController controller,
    double height = 900,
  }) async {
    tester.view.physicalSize = Size(width, height);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteExchangeShellScreen.fromPath(
          controller: controller,
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          initialPath: path,
        ),
      ),
    );
    for (int pump = 0; pump < 60; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  group('P0 - the Matchday summary rail keeps all of its content', () {
    // The rail was a bare Column in a fixed-height pane. Its live-payload
    // panel sat 213px below the clipped edge at every width that admits the
    // rail, with no scroll to reach it.
    for (final double width in <double>[1280, 1440, 1920]) {
      testWidgets('no clipped content at ${width.toInt()}px', (
        WidgetTester tester,
      ) async {
        await pumpShell(
          tester,
          width: width,
          path: '/app/play',
          controller: GteExchangeController(
            api: GteExchangeApiClient.fixture(),
          ),
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'the Matchday summary rail overflowed its pane at '
              '${width.toInt()}px',
        );
      });
    }
  });

  group('P1 - GteStatePanel measures its own box, not the window', () {
    // The panel is the app's universal loading/empty/error surface and
    // renders inside 330px browse rails and 360px summary rails on wide
    // windows. It used to read the window, so a narrow rail on a wide screen
    // kept the side-by-side header and squeezed the copy.
    Future<void> pumpInBox(WidgetTester tester, double boxWidth) async {
      tester.view.physicalSize = const Size(1920, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: boxWidth,
                child: const SingleChildScrollView(
                  child: GteStatePanel(
                    title: 'Live club snapshot unavailable',
                    message:
                        'The club workspace could not reach the ownership '
                        'service. Nothing here is guessed while it is down.',
                    icon: Icons.warning_amber_rounded,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
    }

    testWidgets('stacks inside a narrow rail on a 1920px window', (
      WidgetTester tester,
    ) async {
      await pumpInBox(tester, 330);
      expect(tester.takeException(), isNull);

      final Offset title = tester.getTopLeft(
        find.text('Live club snapshot unavailable'),
      );
      final Offset badge = tester.getTopLeft(
        find.byIcon(Icons.warning_amber_rounded),
      );
      expect(
        badge.dy,
        greaterThan(title.dy),
        reason:
            'the status badge is still beside the copy inside a 330px rail - '
            'the panel is reading the window instead of its own box',
      );
    });

    testWidgets('keeps the side-by-side header in a wide pane', (
      WidgetTester tester,
    ) async {
      await pumpInBox(tester, 900);
      expect(tester.takeException(), isNull);

      final Offset title = tester.getTopLeft(
        find.text('Live club snapshot unavailable'),
      );
      final Offset badge = tester.getTopLeft(
        find.byIcon(Icons.warning_amber_rounded),
      );
      expect(
        badge.dx,
        greaterThan(title.dx),
        reason: 'a 900px pane has room for the badge beside the copy',
      );
    });
  });

  group('P1 - the market movers rail is admitted by its pane', () {
    testWidgets('hidden where the board pane cannot carry it', (
      WidgetTester tester,
    ) async {
      // A 1024px window hands the board about 544px: too narrow for the
      // rail's row layout, so it would stack into three full-width lanes
      // above the listing. The window said 1024 and the rail used to appear.
      await pumpShell(
        tester,
        width: 1024,
        path: '/app/market',
        controller: GteExchangeController(api: GteExchangeApiClient.fixture()),
      );
      expect(
        find.byType(GtexMarketMoversRail),
        findsNothing,
        reason:
            'the movers rail was admitted into a board pane too narrow to '
            'lay it out as a rail',
      );
      tester.takeException();
    });

    testWidgets('shown where the board pane can carry it', (
      WidgetTester tester,
    ) async {
      await pumpShell(
        tester,
        width: 1280,
        path: '/app/market',
        controller: GteExchangeController(api: GteExchangeApiClient.fixture()),
      );
      expect(
        find.byType(GtexMarketMoversRail),
        findsOneWidget,
        reason: 'a 1280px window gives the board an 800px pane - room for it',
      );
      tester.takeException();
    });

    testWidgets('never crowds the listing out of a short pane', (
      WidgetTester tester,
    ) async {
      // At a 719px window the board pane is 247px tall. A 132px rail left no
      // room for a single player card, so the market opened on movers and
      // the listing itself started below the fold.
      await pumpShell(
        tester,
        width: 719,
        path: '/app/market',
        controller: GteExchangeController(api: GteExchangeApiClient.fixture()),
      );
      expect(
        find.byType(GtexMarketMoversRail),
        findsNothing,
        reason: 'the rail took a short pane that had no room for the listing',
      );
      tester.takeException();
    });
  });

  group('P1 - Home is the personalised board for every session', () {
    testWidgets('a club owner lands on Home, not the club workspace', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1440, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      late GteExchangeController controller;
      await tester.runAsync(() async {
        controller = GteExchangeController(api: GteExchangeApiClient.fixture());
        await controller.bootstrap();
        await controller.signIn(
          email: 'fixture.trader@gte.local',
          password: 'DemoPass123', // pragma: allowlist secret
        );
      });

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.home(),
          ),
        ),
      );
      for (int pump = 0; pump < 60; pump += 1) {
        await tester.pump(const Duration(milliseconds: 50));
      }

      expect(
        find.byType(HomeScreen),
        findsOneWidget,
        reason:
            'Home handed club owners the club workspace, so Home and the '
            'Club lane rendered the same screen and the personalised Home '
            'was reachable only by users who owned no club',
      );
      tester.takeException();
    });

    testWidgets('a coin trader lands on Home, not the wallet desk', (
      WidgetTester tester,
    ) async {
      // The other half of the same defect: a trader session was sent to the
      // wallet desk's trader-dashboard module, which the Wallet lane already
      // renders at /app/capital/trader-dashboard. `HomeScreen` carries a
      // coinTrader persona of its own - trader desk copy, capabilities and
      // quick actions - which no trader could reach.
      tester.view.physicalSize = const Size(1440, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _traderSession();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.home(),
          ),
        ),
      );
      for (int pump = 0; pump < 60; pump += 1) {
        await tester.pump(const Duration(milliseconds: 50));
      }

      expect(
        find.byType(HomeScreen),
        findsOneWidget,
        reason:
            'Home handed coin traders the wallet trader dashboard, so Home '
            'and the Wallet lane rendered the same screen',
      );
      expect(
        find.byType(GtexWalletOverviewScreenV2),
        findsNothing,
        reason: 'the wallet desk belongs to the Wallet lane, not to Home',
      );
      tester.takeException();
    });

    testWidgets('a coin trader can still reach the wallet desk in one tap', (
      WidgetTester tester,
    ) async {
      // Removing the override must not strand the desk: the Wallet lane has
      // to stay in a trader's own navigation.
      tester.view.physicalSize = const Size(1440, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _traderSession();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.home(),
          ),
        ),
      );
      for (int pump = 0; pump < 60; pump += 1) {
        await tester.pump(const Duration(milliseconds: 50));
      }

      final Finder walletLane = find.text(
        GtePrimaryDestination.wallet.label,
      );
      expect(
        walletLane,
        findsWidgets,
        reason: 'a coin trader lost the Wallet lane from their navigation',
      );

      await tester.tap(walletLane.first);
      for (int pump = 0; pump < 60; pump += 1) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      expect(
        find.byType(GtexWalletOverviewScreenV2),
        findsOneWidget,
        reason: 'the Wallet lane no longer opens the wallet desk',
      );
      tester.takeException();
    });
  });

  group('P1 - club ownership claims no holder count it was not given', () {
    Future<void> pumpHolding(
      WidgetTester tester,
      GtexClubShareHolding holding,
    ) async {
      tester.view.physicalSize = const Size(1280, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: GtexClubOwnershipPanel(
                portfolio: GtexClubOwnershipPortfolio(
                  clubCount: 1,
                  totalMarketValueCoin: holding.marketValueCoin,
                  totalCostBasisCoin: holding.costBasisCoin,
                  totalUnrealizedPlCoin: holding.unrealizedPlCoin,
                  holdings: <GtexClubShareHolding>[holding],
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
    }

    testWidgets('a missing holder_count renders no owners chip', (
      WidgetTester tester,
    ) async {
      await pumpHolding(
        tester,
        GtexClubShareHolding.fromJson(const <String, dynamic>{
          'club_id': 'ibadan-lions',
          'club_name': 'Ibadan Lions FC',
          'tokens_owned': 40,
          'avg_price_coin': 1,
          'share_price_coin': 1.32,
          'market_value_coin': 52.8,
          'cost_basis_coin': 40,
          'unrealized_pl_coin': 12.8,
        }),
      );
      expect(
        find.textContaining('0 owners'),
        findsNothing,
        reason:
            'an absent holder count was coerced to zero and rendered as '
            '"0 owners" on a holding the reader themselves owns',
      );
      tester.takeException();
    });

    testWidgets('a holder count the backend sent is shown', (
      WidgetTester tester,
    ) async {
      await pumpHolding(
        tester,
        const GtexClubShareHolding(
          clubId: 'ibadan-lions',
          clubName: 'Ibadan Lions FC',
          sharesOwned: 40,
          averagePriceCoin: 1,
          sharePriceCoin: 1.32,
          marketValueCoin: 52.8,
          costBasisCoin: 40,
          unrealizedPlCoin: 12.8,
          holderCount: 18,
        ),
      );
      expect(find.textContaining('18 owners'), findsOneWidget);
      tester.takeException();
    });
  });
}

/// A signed-in session the shell resolves as a coin trader.
GteAuthSession _traderSession() {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'phase4h-trader-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    'user': <String, Object?>{
      'id': 'phase4h-trader',
      'email': 'phase4h-trader@gtex.test',
      'username': 'phase4h-trader',
      'display_name': 'Phase 4H Trader',
      'role': 'coin_trader',
    },
  });
}
