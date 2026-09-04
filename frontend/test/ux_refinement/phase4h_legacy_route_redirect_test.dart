import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/match/gte_live_match_hub_route_screen.dart';
import 'package:gte_frontend/features/match/match_viewer_route_screen.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

/// PHASE 4H - the published legacy routes now go where they said they would.
///
/// Each of these had an `appRouteInventory` entry whose summary named its
/// destination - "redirects to the live Competition OS hub", "redirects to
/// the active Matchday surface", "redirects to the canonical 2D match
/// viewer" - and none of them was registered, so every one landed on the
/// router's "Route unavailable" page instead. These assert the redirect the
/// inventory promised, rather than just that the path resolves to something.
void main() {
  Future<void> pumpAt(WidgetTester tester, String path) async {
    tester.view.physicalSize = const Size(1440, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      GteFrontendApp(
        controller: GteExchangeController(api: GteExchangeApiClient.fixture()),
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
        initialPath: path,
      ),
    );
    for (int pump = 0; pump < 60; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  void expectResolved(WidgetTester tester, String path) {
    expect(
      find.text('Route unavailable'),
      findsNothing,
      reason: '$path still falls through to the router error page',
    );
    tester.takeException();
  }

  group('the matchday aliases reach the live match hub', () {
    for (final String path in <String>[
      AppRoutes.matchesNativeThreeD,
      AppRoutes.matchesSpectate,
      AppRoutes.matchesSimulate,
    ]) {
      testWidgets('$path opens Matchday', (WidgetTester tester) async {
        await pumpAt(tester, path);
        expectResolved(tester, path);
        expect(
          find.byType(GteLiveMatchHubRouteScreen),
          findsOneWidget,
          reason:
              '$path is published as redirecting to Matchday, which is the '
              'live match hub at ${AppRoutes.matches}',
        );
      });
    }
  });

  group('the deep match aliases reach the canonical 2D viewer', () {
    for (final String path in <String>[
      '/matches/broadcast/phase4h-match',
      '/matches/3d/phase4h-match',
    ]) {
      testWidgets('$path opens the 2D viewer', (WidgetTester tester) async {
        await pumpAt(tester, path);
        expectResolved(tester, path);
        expect(
          find.byType(MatchViewerRouteScreen),
          findsOneWidget,
          reason:
              '$path is published as redirecting to the canonical 2D match '
              'viewer, and must carry its match key there',
        );
      });
    }

    testWidgets('a deep alias with a blank match key falls back to Matchday', (
      WidgetTester tester,
    ) async {
      // The viewer needs a key. A blank one still matches the pattern, so the
      // alias sends it to the hub rather than opening a viewer on nothing.
      await pumpAt(tester, '/matches/broadcast/%20');
      expectResolved(tester, '/matches/broadcast/%20');
      expect(find.byType(GteLiveMatchHubRouteScreen), findsOneWidget);
      expect(find.byType(MatchViewerRouteScreen), findsNothing);
    });
  });

  testWidgets('the streamer engine alias opens the Competition OS hub', (
    WidgetTester tester,
  ) async {
    await pumpAt(tester, AppRoutes.streamerEngine);
    expectResolved(tester, AppRoutes.streamerEngine);
    // The hub is a shell lane, so arriving there means the shell mounted.
    expect(
      find.text('Matchday'),
      findsWidgets,
      reason:
          '${AppRoutes.streamerEngine} is published as redirecting to the '
          'live Competition OS hub',
    );
  });
}
