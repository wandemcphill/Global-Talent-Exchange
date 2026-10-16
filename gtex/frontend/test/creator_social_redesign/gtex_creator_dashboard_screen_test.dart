import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/screens/creators/gtex_creator_dashboard_screen_v2.dart';

void main() {
  testWidgets('creator dashboard renders creator studio sections', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexCreatorDashboardScreenV2(allowFixtureData: true),
      ),
    );

    expect(find.text('Creator Studio'), findsWidgets);
    expect(find.text('Hosted competitions'), findsWidgets);
    expect(find.text('Monetization'), findsWidgets);
    expect(find.text('Create competition'), findsWidgets);
  });

  testWidgets('creator dashboard blocks fixture snapshot by default', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexCreatorDashboardScreenV2()),
    );

    expect(find.text('Live creator workspace unavailable'), findsOneWidget);
    expect(find.text('Hosted competitions'), findsNothing);
  });
}
