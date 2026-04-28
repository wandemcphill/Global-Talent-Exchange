import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/wallet/gte_wallet_overview_screen.dart';
import 'package:gte_frontend/theme/gte_theme_controller.dart';
import 'package:gte_frontend/theme/gte_theme_metadata.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/theme/gte_theme_scope.dart';
import 'package:gte_frontend/theme/gte_theme_store.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('controlled merge source contract', () {
    test('app entry preserves theme bootstrap and root hookup', () {
      final String mainSource = _readSource('lib/main.dart');
      final String appSource = _readSource('lib/app/gte_frontend_app.dart');

      expect(mainSource, contains('GteThemeController.bootstrap('));
      expect(
        mainSource,
        contains('child: GtexApp(themeController: themeController),'),
      );
      expect(appSource, contains('GteThemeControllerScope('));
      expect(
        appSource,
        contains('theme: GteShellTheme.build(_themeController.activeTheme),'),
      );
      expect(appSource, contains("initialPath: '/app/home',"));
    });

    test(
      'navigation shell preserves protected lane order and utility access',
      () {
        final String shellSource = _readSource(
          'lib/features/navigation/presentation/gte_navigation_shell_screen.dart',
        );

        final int home = _indexOfOrThrow(
          shellSource,
          'GtePrimaryDestination.home,',
        );
        final int play = _indexOfOrThrow(
          shellSource,
          'GtePrimaryDestination.competitions,',
        );
        final int market = _indexOfOrThrow(
          shellSource,
          'GtePrimaryDestination.market,',
        );
        final int hub = _indexOfOrThrow(
          shellSource,
          'GtePrimaryDestination.hub,',
        );
        final int club = _indexOfOrThrow(
          shellSource,
          'GtePrimaryDestination.club,',
        );

        expect(home, lessThan(play));
        expect(play, lessThan(market));
        expect(market, lessThan(hub));
        expect(hub, lessThan(club));
        expect(shellSource, contains('_buildThemePickerAction(context)'));
        expect(shellSource, contains('_buildCapitalAction()'));
        expect(shellSource, contains("tooltip: 'Club funds'"));
        expect(shellSource, contains('GteThemePickerSheet'));
        expect(shellSource, contains('destination.label,'));
      },
    );

    test('home dashboard preserves hero to secondary information order', () {
      final String homeSource = _readSource(
        'lib/features/home_dashboard/home_dashboard_screen.dart',
      );

      final int hero = _indexOfOrThrow(homeSource, '_HomeHeroPanel(');
      final int status = _indexOfOrThrow(homeSource, 'GteSyncStatusCard(');
      final int banner = _indexOfOrThrow(
        homeSource,
        'HomeFeaturedEventBanner(',
      );
      final int majorMoves = _indexOfOrThrow(
        homeSource,
        "eyebrow: 'RIGHT NOW'",
      );
      final int quickActions = _indexOfOrThrow(
        homeSource,
        '_HomeQuickActionsStrip(',
      );
      final int journey = _indexOfOrThrow(homeSource, '_HomeJourneyPanel(');
      final int quieterSignals = _indexOfOrThrow(
        homeSource,
        "eyebrow: 'QUIETER SIGNALS'",
      );

      expect(hero, lessThan(status));
      expect(status, lessThan(banner));
      expect(banner, lessThan(majorMoves));
      expect(majorMoves, lessThan(quickActions));
      expect(quickActions, lessThan(journey));
      expect(journey, lessThan(quieterSignals));
    });
  });

  group('controlled merge runtime contract', () {
    test('theme registry still exposes five selectable themes', () {
      expect(GteThemeRegistry.themes, hasLength(5));
      expect(
        GteThemeRegistry.themes.map(
          (GteThemeDefinition definition) => definition.metadata.id,
        ),
        orderedEquals(GteThemeId.values),
      );
    });

    test('route aliases still preserve shell compatibility', () {
      expect(
        GteNavigationRoute.parse('/app/play').primaryDestination,
        GtePrimaryDestination.competitions,
      );
      expect(
        GteNavigationRoute.parse('/app/competitions').primaryDestination,
        GtePrimaryDestination.competitions,
      );
      expect(
        GteNavigationRoute.parse('/app/community').primaryDestination,
        GtePrimaryDestination.hub,
      );
      expect(
        GteNavigationRoute.parse('/app/capital').primaryDestination,
        GtePrimaryDestination.wallet,
      );
      expect(
        GteNavigationRoute.parse('/app/wallet').primaryDestination,
        GtePrimaryDestination.wallet,
      );
    });

    testWidgets('theme picker switches themes and persists selection', (
      WidgetTester tester,
    ) async {
      final GteMemoryThemeStore store = GteMemoryThemeStore();
      final GteThemeController controller = GteThemeController(store: store);

      await tester.pumpWidget(_ThemePickerHarness(controller: controller));

      await tester.tap(find.text('Open theme picker'));
      await tester.pumpAndSettle();

      final Finder pickerScrollView = find.byType(Scrollable).last;
      for (final GteThemeDefinition definition in GteThemeRegistry.themes) {
        await tester.scrollUntilVisible(
          find.text(definition.metadata.label),
          200,
          scrollable: pickerScrollView,
        );
        await tester.pumpAndSettle();
        expect(find.text(definition.metadata.label), findsOneWidget);
      }

      await tester.tap(find.text('Ultra Red'));
      await tester.pumpAndSettle();

      expect(controller.activeThemeId, GteThemeId.ultraRed);

      final GteThemeController restored = GteThemeController(store: store);
      await restored.restore();
      expect(restored.activeThemeId, GteThemeId.ultraRed);
    });

    testWidgets('wallet overview surface opens against fixture data', (
      WidgetTester tester,
    ) async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        MaterialApp(home: GteWalletOverviewScreen(controller: controller)),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle();

      expect(find.text('Club funds'), findsOneWidget);
      expect(find.text('TRANSFER BALANCE'), findsOneWidget);
      expect(find.text('CLUB CREDIT'), findsOneWidget);
      expect(find.text('Deposit'), findsOneWidget);
    });

    testWidgets('club sale market surface opens against fixture data', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClubSaleMarketScreen(
            baseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle();

      expect(find.text('Club sale market'), findsOneWidget);
      expect(find.text('CLUB SALE MARKET'), findsOneWidget);
      expect(
        find.text(
          'Public valuations, asking prices, and live deal posture stay readable.',
        ),
        findsOneWidget,
      );
    });
  });
}

class _ThemePickerHarness extends StatelessWidget {
  const _ThemePickerHarness({required this.controller});

  final GteThemeController controller;

  @override
  Widget build(BuildContext context) {
    return GteThemeControllerScope(
      controller: controller,
      child: AnimatedBuilder(
        animation: controller,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp(
            theme: GteShellTheme.build(controller.activeTheme),
            home: Builder(
              builder:
                  (BuildContext context) => Scaffold(
                    body: Center(
                      child: FilledButton(
                        onPressed: () {
                          showModalBottomSheet<void>(
                            context: context,
                            isScrollControlled: true,
                            builder:
                                (BuildContext context) =>
                                    const GteThemePickerSheet(),
                          );
                        },
                        child: const Text('Open theme picker'),
                      ),
                    ),
                  ),
            ),
          );
        },
      ),
    );
  }
}

String _readSource(String relativePath) {
  final File file = File(relativePath);
  if (!file.existsSync()) {
    throw TestFailure('Expected source file to exist: $relativePath');
  }
  return file.readAsStringSync();
}

int _indexOfOrThrow(String source, String snippet) {
  final int index = source.indexOf(snippet);
  if (index < 0) {
    throw TestFailure('Expected snippet not found: $snippet');
  }
  return index;
}
