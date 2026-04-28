import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('3D route never mounts an advanced viewer during launch', (
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
    expect(find.textContaining('2D tactical viewer'), findsWidgets);
  });
}
