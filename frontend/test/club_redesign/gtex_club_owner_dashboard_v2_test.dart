import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';

void main() {
  testWidgets('owner dashboard shows club sections and squad room', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexClubOwnerDashboardV2(
            clubId: 'demo-club',
            clubName: 'Lagos Eclipse FC',
          ),
        ),
      ),
    );

    expect(find.text('Club command'), findsOneWidget);
    expect(find.text('Overview'), findsWidgets);
    expect(find.text('Squad'), findsWidgets);
    expect(find.text('Lagos Eclipse FC'), findsWidgets);
  });

  testWidgets('public club profile exposes follow and buy shares actions', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexPublicClubProfileV2(
            clubId: 'demo-club',
            clubName: 'Lagos Eclipse FC',
          ),
        ),
      ),
    );

    expect(find.text('Club profile'), findsOneWidget);
    expect(find.text('Follow'), findsWidgets);
    expect(find.text('Buy shares'), findsWidgets);
  });
}
