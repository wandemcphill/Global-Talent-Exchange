import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/shell/presentation/gtex_public_home_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_signup_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('public home explains canonical GTEX guest surfaces', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const GtexPublicHomeScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('GTEX starts with a football account.'), findsOneWidget);
    expect(find.text('Create account'), findsWidgets);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('Public competitions'), findsWidgets);
    expect(find.text('Public newsroom'), findsWidgets);
    expect(find.text('Ecosystem pulse'), findsWidgets);
    expect(
      find.textContaining('Guest views only show confirmed'),
      findsOneWidget,
    );
  });

  testWidgets(
    'canonical signup surface keeps football role access frictionless',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2000);
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Create GTEX account'), findsOneWidget);
      expect(find.text('Player'), findsOneWidget);
      expect(find.text('Organization'), findsOneWidget);
      expect(find.text('Security PIN'), findsOneWidget);
      expect(find.text('Recovery question 1'), findsOneWidget);
      expect(find.text('Apply for creator access'), findsOneWidget);
    },
  );

  testWidgets('region selection stays pending until account policy confirms', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const GtexRegionSelectionScreen(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(
      find.text('Region selection waits for account policy'),
      findsOneWidget,
    );
    expect(find.text('Create account'), findsOneWidget);
  });
}
