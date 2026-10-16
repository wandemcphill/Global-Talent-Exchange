import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';
import 'package:gte_frontend/features/regens/regens_screen_v2.dart';

void main() {
  testWidgets('Regen World V2 renders core surfaces', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: GtexRegenWorldScreenV2.fixture())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Regen World'), findsOneWidget);
    expect(find.text('Create a Son'), findsWidgets);
    expect(find.text('Prospects'), findsOneWidget);
  });

  testWidgets('live regen route fails closed without API base URL', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: RegensScreenV2(backendMode: GteBackendMode.live)),
      ),
    );

    expect(find.text('Regen world configuration missing'), findsOneWidget);
    expect(find.text('Regen World'), findsNothing);
  });
}
