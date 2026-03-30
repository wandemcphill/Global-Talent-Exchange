import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/match_3d_route_screen.dart';

void main() {
  testWidgets('3D route stays visibly blocked', (WidgetTester tester) async {
    await tester.pumpWidget(_buildWidget());

    await tester.pumpAndSettle();

    expect(find.text('3D Match Viewer'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('BLOCKED'), findsWidgets);
    expect(find.text('FLUTTER_3D'), findsNothing);
  });

  testWidgets('3D route explains the missing live backend contract honestly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_buildWidget());

    await tester.pumpAndSettle();

    expect(find.text('TRUTH PRESERVED'), findsOneWidget);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('NATIVE_3D'), findsNothing);
  });
}

Widget _buildWidget() {
  return const MaterialApp(
    home: Scaffold(body: Match3dRouteScreen(matchKey: 'live-match-001')),
  );
}
