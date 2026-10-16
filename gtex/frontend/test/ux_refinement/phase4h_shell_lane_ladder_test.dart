import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// PHASE 4H - the responsive gate for the whole shell.
///
/// The Transfer Hub audit hardened one lane against one class of layout bug.
/// This sweeps every lane of the navigation shell across the mandated
/// breakpoint ladder, signed out and signed in, and fails on anything the
/// framework reports as unrenderable - the state the Matchday summary rail
/// was in at every desktop width before this phase, where 213px of the live
/// payload panel sat below a clipped edge with no way to scroll to it.
///
/// Each width is pumped, then every scrollable on the surface is dragged, so
/// content that only builds after a scroll is exercised too.
void main() {
  /// The breakpoints Phase 4H is contracted to hold: two phone widths, a
  /// tablet, a small laptop, and three desktop widths.
  const List<double> ladder = <double>[390, 430, 768, 1024, 1280, 1440, 1920];

  /// Every primary destination the shell can route to.
  const Map<String, String> lanes = <String, String>{
    'home': '/app/home',
    'matchday': '/app/play',
    'market': '/app/market',
    'regens': '/app/regens',
    'community': '/app/community',
    'club': '/app/club',
    'capital': '/app/capital',
    'holdings': '/app/capital/holdings',
    'orders': '/app/capital/orders',
    'studio': '/app/hub',
  };

  List<String> drainExceptions(WidgetTester tester) {
    final List<String> found = <String>[];
    for (int i = 0; i < 40; i += 1) {
      final Object? error = tester.takeException();
      if (error == null) {
        break;
      }
      found.add(error.toString().split('\n').first);
    }
    return found;
  }

  Future<GteExchangeController> signedInController(WidgetTester tester) async {
    late GteExchangeController controller;
    await tester.runAsync(() async {
      controller = GteExchangeController(api: GteExchangeApiClient.fixture());
      await controller.bootstrap();
      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
    });
    return controller;
  }

  Future<void> pumpLane(
    WidgetTester tester, {
    required double width,
    required String path,
    required GteExchangeController controller,
  }) async {
    tester.view.physicalSize = Size(width, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        // Keyed by width so sweeping the ladder in one test remounts the
        // shell rather than reusing the previous width's state.
        home: KeyedSubtree(
          key: ValueKey<String>('lane-$path-$width'),
          child: GteExchangeShellScreen.fromPath(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialPath: path,
          ),
        ),
      ),
    );
    for (int pump = 0; pump < 60; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  for (final MapEntry<String, String> lane in lanes.entries) {
    for (final bool authenticated in <bool>[false, true]) {
      final String session = authenticated ? 'signed in' : 'signed out';
      testWidgets('${lane.key} lays out across the ladder ($session)', (
        WidgetTester tester,
      ) async {
        final List<String> failures = <String>[];
        for (final double width in ladder) {
          final GteExchangeController controller =
              authenticated
                  ? await signedInController(tester)
                  : GteExchangeController(api: GteExchangeApiClient.fixture());
          await pumpLane(
            tester,
            width: width,
            path: lane.value,
            controller: controller,
          );
          for (final String error in drainExceptions(tester)) {
            failures.add('${width.toInt()}px on load: $error');
          }

          // Scroll each scrollable so content that only builds below the
          // fold is laid out too.
          final Finder scrollables = find.byType(Scrollable);
          final int scrollableCount = scrollables.evaluate().length;
          for (int i = 0; i < scrollableCount && i < 8; i += 1) {
            try {
              await tester.drag(scrollables.at(i), const Offset(0, -1200));
              await tester.pump(const Duration(milliseconds: 120));
            } catch (_) {
              // Not draggable at this width - nothing to exercise.
            }
          }
          for (final String error in drainExceptions(tester)) {
            failures.add('${width.toInt()}px after scroll: $error');
          }
        }
        expect(
          failures,
          isEmpty,
          reason:
              'the ${lane.key} lane reported unrenderable layout '
              '($session):\n  ${failures.join('\n  ')}',
        );
      });
    }
  }

  testWidgets('primary navigation stays reachable at every width', (
    WidgetTester tester,
  ) async {
    for (final double width in ladder) {
      await pumpLane(
        tester,
        width: width,
        path: '/app/home',
        controller: GteExchangeController(api: GteExchangeApiClient.fixture()),
      );

      // Below the shell's mobile breakpoint the rail becomes a bottom bar
      // that shows four destinations plus a "More" sheet; above it every
      // destination is a rail item. Either way there must be a way to leave
      // the current lane.
      final bool hasRail = find.byType(NavigationBar).evaluate().isEmpty;
      if (hasRail) {
        // The market lane is labelled "Transfer Hub" in the shell's own
        // destination model - the rail must carry it at every rail width.
        expect(
          find.text(GtePrimaryDestination.market.label),
          findsWidgets,
          reason: 'the nav rail lost its destinations at ${width}px',
        );
      } else {
        expect(
          find.byType(NavigationDestination),
          findsWidgets,
          reason: 'the bottom nav lost its destinations at ${width}px',
        );
        expect(
          find.byKey(const Key('gtex-shell-more-destination')),
          findsOneWidget,
          reason:
              'the overflow destinations became unreachable at ${width}px - '
              'the shell has more lanes than the bar can show',
        );
      }
      tester.takeException();
    }
  });
}
