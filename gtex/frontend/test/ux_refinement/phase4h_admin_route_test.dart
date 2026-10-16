import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

/// PHASE 4H - the admin entry the personalised Home actually navigates to.
///
/// `/profile/admin` is published in `appRouteInventory` as the
/// permission-gated admin surface and is the destination of HomeScreen's
/// "Admin controls" quick action, but it was never registered in the router,
/// so the tap fell through to the "Route unavailable" screen. That was
/// invisible while Home rendered the command center itself for admin
/// sessions; once Home became the admin's board, it was the way in.
void main() {
  Future<void> pumpAt(
    WidgetTester tester,
    String path, {
    GteAuthSession? session,
  }) async {
    tester.view.physicalSize = const Size(1440, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    if (session != null) {
      controller.session = session;
    }

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
    for (int pump = 0; pump < 60; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  testWidgets('the published admin path reaches the command center', (
    WidgetTester tester,
  ) async {
    await pumpAt(tester, AppRoutes.profileAdmin, session: _adminSession());

    expect(
      find.byType(AdminCommandCenterScreen),
      findsOneWidget,
      reason:
          'the admin path published in the route inventory did not resolve '
          'to the command center',
    );
    expect(
      find.text('Route unavailable'),
      findsNothing,
      reason: 'the published admin path fell through to the router error page',
    );
    tester.takeException();
  });

  testWidgets('the published admin path stays gated for a non-admin', (
    WidgetTester tester,
  ) async {
    // Redirecting the legacy path must not hand a plain session admin
    // tooling: it lands on the canonical route's own blocked state.
    await pumpAt(tester, AppRoutes.profileAdmin, session: _userSession());

    expect(find.byType(AdminCommandCenterScreen), findsNothing);
    expect(
      find.byType(GteRouteIntegrityScreen),
      findsOneWidget,
      reason: 'a non-admin should meet the admin route gate, not the tooling',
    );
    tester.takeException();
  });
}

GteAuthSession _adminSession() => _session(role: 'admin');

GteAuthSession _userSession() => _session(role: 'user');

GteAuthSession _session({required String role}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'phase4h-$role-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    'user': <String, Object?>{
      'id': 'phase4h-$role',
      'email': 'phase4h-$role@gtex.test',
      'username': 'phase4h-$role',
      'display_name': 'Phase 4H $role',
      'role': role,
    },
  });
}
