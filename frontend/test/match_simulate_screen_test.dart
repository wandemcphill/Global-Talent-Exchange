import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_simulate_screen.dart';

void main() {
  testWidgets('simulate route stays explicitly local and demo-labeled', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MatchSimulateScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Simulate'), findsWidgets);
    expect(find.text('Simulation mode is local by design.'), findsNothing);
    expect(
      find.textContaining('Simulation mode is local by design.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('without pretending it is a backend feed'),
      findsOneWidget,
    );
    expect(find.text('Launch simulation'), findsOneWidget);
  });
}
