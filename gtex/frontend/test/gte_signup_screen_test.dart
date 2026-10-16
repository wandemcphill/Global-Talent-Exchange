import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_signup_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('signup surface exposes creator access request entry',
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

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteSignupScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Apply for creator access'), findsOneWidget);

    await tester.ensureVisible(find.text('Apply for creator access'));
    await tester.tap(find.text('Apply for creator access'));
    await tester.pumpAndSettle();

    expect(find.text('Creator access request'), findsOneWidget);
    expect(find.text('Create account to continue'), findsOneWidget);
  });
}
