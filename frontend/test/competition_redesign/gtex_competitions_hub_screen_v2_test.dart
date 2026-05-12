import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/competition_redesign/presentation/gtex_competitions_hub_screen_v2.dart';

void main() {
  testWidgets('competitions hub renders browse panel and action button', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: GtexCompetitionsHubScreenV2())),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX Competitions'), findsWidgets);
    expect(find.text('Create competition'), findsOneWidget);
    expect(find.text('Global Talent Cup'), findsWidgets);
  });
}
