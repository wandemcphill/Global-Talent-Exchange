import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_simulate_route_screen.dart';

void main() {
  testWidgets('simulation route is blocked for the 2D manager launch', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: MatchSimulateRouteScreen()),
    );

    expect(find.text('Coming soon'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('Launch simulation'), findsNothing);
  });
}
