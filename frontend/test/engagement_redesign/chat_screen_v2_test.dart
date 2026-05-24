import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/screens/chat/gtex_chat_screen_v2.dart';

void main() {
  testWidgets('chat screen blocks fixture conversations by default', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: GtexChatScreenV2())),
    );

    expect(find.text('Live chat unavailable'), findsOneWidget);
    expect(find.textContaining('live conversation API'), findsOneWidget);
    expect(find.text('GTEX Chat'), findsNothing);
  });

  testWidgets('chat screen allows fixture conversations in tests only', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: GtexChatScreenV2(allowFixtureData: true)),
      ),
    );

    expect(find.text('GTEX Chat'), findsOneWidget);
    expect(find.textContaining('KYC Review'), findsWidgets);
  });
}
