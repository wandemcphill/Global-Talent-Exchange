import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/owner_console/presentation/owner_inbox_screen.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

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

  group('Owner Decision Inbox routing and legacy redirect', () {
    testWidgets('canonical route /app/inbox mounts GtexOwnerInboxScreen', (WidgetTester tester) async {
      await pumpAt(tester, AppRoutes.inbox);
      expectResolved(tester, AppRoutes.inbox);
      expect(find.byType(GtexOwnerInboxScreen), findsOneWidget);
    });

    testWidgets('legacy /inbox redirects to canonical /app/inbox', (WidgetTester tester) async {
      await pumpAt(tester, AppRoutes.ownerInbox);
      expectResolved(tester, AppRoutes.ownerInbox);
      // Confirms legacy /inbox lands on owner decision inbox screen
      expect(find.byType(GtexOwnerInboxScreen), findsOneWidget);
    });

    testWidgets('legacy /inbox preserves query parameters on redirect', (WidgetTester tester) async {
      await pumpAt(tester, '/inbox?status=resolved&club_id=c-test&category=staff_recommendations');
      expectResolved(tester, '/inbox?status=resolved&club_id=c-test&category=staff_recommendations');
      final inboxFinder = find.byType(GtexOwnerInboxScreen);
      expect(inboxFinder, findsOneWidget);
      final GtexOwnerInboxScreen screen = tester.widget<GtexOwnerInboxScreen>(inboxFinder);
      expect(screen.clubId, 'c-test');
      expect(screen.initialStatus, 'resolved');
      expect(screen.initialCategory, 'staff_recommendations');
    });

    testWidgets('community routes are not hijacked by inbox redirect', (WidgetTester tester) async {
      // Community chat remains accessible on /app/community, /community, /social, /chat
      await pumpAt(tester, '/community');
      expectResolved(tester, '/community');
      expect(find.byType(GtexOwnerInboxScreen), findsNothing);

      await pumpAt(tester, '/social');
      expectResolved(tester, '/social');
      expect(find.byType(GtexOwnerInboxScreen), findsNothing);

      await pumpAt(tester, '/chat');
      expectResolved(tester, '/chat');
      expect(find.byType(GtexOwnerInboxScreen), findsNothing);

      await pumpAt(tester, '/app/community');
      expectResolved(tester, '/app/community');
      expect(find.byType(GtexOwnerInboxScreen), findsNothing);
    });
  });
}
