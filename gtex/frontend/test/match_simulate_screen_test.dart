import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_simulate_screen.dart';

void main() {
  testWidgets('simulate screen stays explicitly fixture-mode and local', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MatchSimulateScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Simulate'), findsWidgets);
    expect(
      find.textContaining(
        'Simulation is available only in explicit fixture mode.',
      ),
      findsOneWidget,
    );
    expect(
      find.textContaining(
        'local simulation engine without pretending it is a backend feed',
      ),
      findsOneWidget,
    );
    expect(find.text('Launch simulation'), findsOneWidget);
  });
}
