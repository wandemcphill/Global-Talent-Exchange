import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_models.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// Regen World was GTEX's most differentiated screen and sat outside the
/// product: a top-level route with no navigation entry, no dark canvas and
/// no back behaviour, and the only signpost on Home pointed at national team
/// competitions instead. These pin it as a lane of the shell.
void main() {
  Future<void> pumpShell(
    WidgetTester tester,
    String path,
    Size size,
    Finder ready,
  ) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: KeyedSubtree(
          key: ValueKey<String>('$path-${size.width}'),
          child: GteExchangeShellScreen.fromPath(
            controller: GteExchangeController(
              api: GteExchangeApiClient.fixture(),
            ),
            apiBaseUrl: '',
            backendMode: GteBackendMode.fixture,
            initialPath: path,
          ),
        ),
      ),
    );
    for (int pump = 0; pump < 200; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
      if (ready.evaluate().isNotEmpty) {
        break;
      }
    }
    // The regen repository resolves through a short delay; pump past it so
    // no timer is left pending when the tree is torn down.
    for (int pump = 0; pump < 10; pump += 1) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  test('regen paths resolve to the regen lane of the shell', () {
    expect(
      GteNavigationRoute.parse('/world/regens').primaryDestination,
      GtePrimaryDestination.regens,
    );
    expect(
      GteNavigationRoute.parse('/app/regens').primaryDestination,
      GtePrimaryDestination.regens,
    );
    expect(
      GteNavigationRoute.parse('/regen-universe').primaryDestination,
      GtePrimaryDestination.regens,
    );
    expect(const GteNavigationRoute.regens().path, '/app/regens');
  });

  test('regen aliases canonicalise to one path', () {
    for (final String alias in <String>[
      '/regens',
      '/app/regens',
      '/regen-universe',
    ]) {
      expect(
        gtexCanonicalGlobalSearchRoute(alias, isAdmin: false),
        '/world/regens',
      );
    }
  });

  testWidgets('regen world mounts inside the shell with GTEX chrome', (
    WidgetTester tester,
  ) async {
    await pumpShell(
      tester,
      '/app/regens',
      const Size(1440, 1000),
      find.byType(GtexRegenWorldScreenV2),
    );

    expect(find.byType(GtexRegenWorldScreenV2), findsOneWidget);
    // Inside the shell it inherits the dark canvas and the navigation rail
    // rather than rendering on a bare white page.
    expect(find.byType(GtexAppShell), findsOneWidget);
    expect(find.text('Regen World'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('regen world is a navigable destination, not a hidden URL', (
    WidgetTester tester,
  ) async {
    await pumpShell(
      tester,
      '/app/home',
      const Size(1440, 1000),
      find.byType(GtexAppShell),
    );

    // The nav rail carries it, so it is reachable without typing a URL.
    expect(find.text('Regen World'), findsWidgets);
  });

  for (final double width in <double>[390, 768, 1024, 1280, 1440]) {
    testWidgets('regen prospects stay unclipped at ${width}px', (
      WidgetTester tester,
    ) async {
      await pumpShell(
        tester,
        '/app/regens',
        Size(width, 1000),
        find.byType(GtexRegenCard),
      );

      final Finder cards = find.byType(GtexRegenCard);
      if (cards.evaluate().isEmpty) {
        // The lane can legitimately be empty; what must not happen is a
        // crash or an overflow while it is.
        expect(tester.takeException(), isNull);
        return;
      }

      expect(
        tester.getSize(cards.first).width,
        greaterThanOrEqualTo(280),
        reason: 'a prospect card must stay wide enough to read at ${width}px',
      );
      expect(
        tester.takeException(),
        isNull,
        reason: 'regen world overflowed at ${width}px',
      );
    });
  }
}
