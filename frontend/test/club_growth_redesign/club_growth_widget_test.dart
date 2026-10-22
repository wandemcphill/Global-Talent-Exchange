import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';

void main() {
  testWidgets('club dashboard renders growth loops inside existing shell', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GtexClubGrowthDashboard dashboard =
        await GtexClubGrowthFixtures.seed().dashboard('fixture-club');

    await tester.pumpWidget(
      MaterialApp(
        home: GtexClubOwnerDashboardV2(
          clubId: 'fixture-club',
          clubName: 'Fixture FC',
          growthDashboard: dashboard,
          isAuthenticated: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Staff'), findsOneWidget);

    await tester.tap(find.text('Staff'));
    await tester.pumpAndSettle();

    expect(find.text('Staff marketplace'), findsOneWidget);
    expect(find.text('Staff effects'), findsOneWidget);
    expect(find.text('Available staff'), findsOneWidget);

    expect(find.text('Academy'), findsOneWidget);
    await tester.tap(find.text('Academy'));
    await tester.pumpAndSettle();

    expect(find.text('Academy pipeline'), findsOneWidget);
    expect(find.text('Generate'), findsOneWidget);
    expect(find.text('newgen bank only'), findsOneWidget);
  });
}
