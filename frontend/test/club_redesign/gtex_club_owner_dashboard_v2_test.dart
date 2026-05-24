import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';

void main() {
  testWidgets('owner dashboard shows club sections and squad room', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    int marketOpens = 0;
    int competitionOpens = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexClubOwnerDashboardV2(
            clubId: 'demo-club',
            clubName: 'Lagos Eclipse FC',
            initialSnapshot: GtexClubWorkspaceSnapshot.demo(
              clubId: 'demo-club',
              clubName: 'Lagos Eclipse FC',
            ),
            onOpenMarket: () => marketOpens += 1,
            onCreateCompetition: () => competitionOpens += 1,
          ),
        ),
      ),
    );

    expect(find.text('Club command'), findsOneWidget);
    expect(find.text('Overview'), findsWidgets);
    expect(find.text('Squad'), findsWidgets);
    expect(find.text('Lagos Eclipse FC'), findsWidgets);

    await tester.tap(find.text('Market'));
    await tester.tap(find.text('Create competition'));

    expect(marketOpens, 1);
    expect(competitionOpens, 1);
  });

  testWidgets('public club profile exposes follow and buy shares actions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexPublicClubProfileV2(
            clubId: 'demo-club',
            clubName: 'Lagos Eclipse FC',
            initialSnapshot: GtexClubWorkspaceSnapshot.demo(
              clubId: 'demo-club',
              clubName: 'Lagos Eclipse FC',
            ),
          ),
        ),
      ),
    );

    expect(find.text('Club profile'), findsOneWidget);
    expect(find.text('Follow'), findsWidgets);
    expect(find.text('Buy shares'), findsWidgets);
  });
}
