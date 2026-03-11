import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../lib/providers/gte_app_controller.dart';
import '../lib/providers/gte_mock_api.dart';
import '../lib/screens/gte_app_shell_screen.dart';

void main() {
  testWidgets('app shell switches between overview, players, and market',
      (WidgetTester tester) async {
    final GteAppController controller =
        GteAppController(api: const GteMockApi(latency: Duration.zero));

    await tester.pumpWidget(
      MaterialApp(
        home: GteAppShellScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Featured prospects'), findsOneWidget);

    await tester.tap(find.text('Players'));
    await tester.pumpAndSettle();
    expect(find.text('Player hub'), findsOneWidget);

    await tester.tap(find.text('Market'));
    await tester.pumpAndSettle();
    expect(find.text('Market hub'), findsOneWidget);
  });

  testWidgets('app shell opens player profile and transfer room routes',
      (WidgetTester tester) async {
    final GteAppController controller =
        GteAppController(api: const GteMockApi(latency: Duration.zero));

    await tester.pumpWidget(
      MaterialApp(
        home: GteAppShellScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Players'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lamine Yamal').last);
    await tester.pumpAndSettle();

    expect(find.text('Player profile'), findsOneWidget);
    expect(find.text('Scouting report'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Market'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Open transfer room').first);
    await tester.pumpAndSettle();

    expect(find.text('Transfer room'), findsOneWidget);
    expect(find.text('Platform Deals'), findsWidgets);
  });
}
