import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_center/match_simulate_screen.dart';

void main() {
  testWidgets('simulate screen is a blocked compatibility wrapper', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MatchSimulateScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Coming soon'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('Launch simulation'), findsNothing);
  });
}
