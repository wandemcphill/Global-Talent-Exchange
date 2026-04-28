import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('3D route is blocked for the 2D manager launch', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const Match3dRouteScreen(matchKey: 'live-match-001'),
      ),
    );

    expect(find.text('Coming soon'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('FLUTTER_3D'), findsNothing);
    expect(find.text('NATIVE_3D'), findsNothing);
  });
}
