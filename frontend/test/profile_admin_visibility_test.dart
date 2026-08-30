import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// Admin-entry visibility used to be asserted against the legacy
/// `ProfileScreen`/`ProfileAdminScreen` pair, which were removed with the
/// legacy router cluster. The live application gates the admin entry in the
/// active navigation shell (`_isAdminSession`), so the coverage is retargeted
/// there rather than at a surface no user can reach.
void main() {
  testWidgets('authenticated admins see the active-shell admin entry', (
    WidgetTester tester,
  ) async {
    await _pumpShellWithRole(tester, role: 'admin');

    expect(find.byTooltip('Admin dashboard'), findsOneWidget);
  });

  testWidgets('non-admin users do not see the active-shell admin entry', (
    WidgetTester tester,
  ) async {
    await _pumpShellWithRole(tester, role: 'user');

    expect(find.byTooltip('Admin dashboard'), findsNothing);
  });

  testWidgets('scoped admins keep the active-shell admin entry', (
    WidgetTester tester,
  ) async {
    await _pumpShellWithRole(tester, role: 'scoped_admin');

    expect(find.byTooltip('Admin dashboard'), findsOneWidget);
  });

  testWidgets('unauthenticated sessions do not see the admin entry', (
    WidgetTester tester,
  ) async {
    await _pumpShellWithRole(tester, role: null);

    expect(find.byTooltip('Admin dashboard'), findsNothing);
  });
}

/// Mounts the active shell on a non-home route so the assertion targets the
/// shell header gate itself rather than the admin home surface it swaps in.
Future<void> _pumpShellWithRole(
  WidgetTester tester, {
  required String? role,
}) async {
  _setLargeViewport(tester);

  final GteExchangeController controller = GteExchangeController(
    api: GteExchangeApiClient.fixture(),
  );
  if (role != null) {
    controller.session = _sessionWithRole(role);
  }

  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: GteExchangeShellScreen.fromPath(
        controller: controller,
        apiBaseUrl: 'http://127.0.0.1:8000',
        backendMode: GteBackendMode.fixture,
        initialPath: '/app/market',
      ),
    ),
  );
  await _pumpUntilText(tester, 'Transfer Hub');
}

GteAuthSession _sessionWithRole(String role) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token',
    'session_id': 'session-$role',
    'token_type': 'bearer',
    'expires_in': 3600,
    'user': <String, Object?>{
      'id': '$role-1',
      'email': '$role@gtex.test',
      'username': role,
      'display_name': 'Session $role',
      'role': role,
    },
  });
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(2400, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Future<void> _pumpUntilText(
  WidgetTester tester,
  String text, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 120,
}) async {
  final Finder finder = find.text(text);
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for "$text".');
}
