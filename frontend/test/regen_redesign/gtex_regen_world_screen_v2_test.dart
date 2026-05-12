import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';

void main() {
  testWidgets('Regen World V2 renders core surfaces', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: GtexRegenWorldScreenV2())));
    await tester.pumpAndSettle();

    expect(find.text('Regen World'), findsOneWidget);
    expect(find.text('Create a Son'), findsWidgets);
    expect(find.text('Prospects'), findsOneWidget);
  });
}
