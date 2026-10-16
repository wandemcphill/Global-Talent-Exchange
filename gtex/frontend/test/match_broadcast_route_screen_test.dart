import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_broadcast_screen.dart';

void main() {
  testWidgets('broadcast route is blocked for the 2D manager launch', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: MatchBroadcastScreen(matchKey: 'live-match-001')),
      ),
    );

    expect(find.text('Coming soon'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.textContaining('2D tactical viewer'), findsWidgets);
  });
}
