import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';

void main() {
  testWidgets('club dashboard renders lifecycle readiness from live model', (
    WidgetTester tester,
  ) async {
    // The detail body is a lazy ListView, so the readiness panel is only built
    // when the viewport has room for it. Pin a desktop-sized surface instead of
    // relying on the implicit 800x600 default.
    tester.view.physicalSize = const Size(1400, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GtexClubOperatingDashboard dashboard =
        await GtexClubLifecycleFixtures.seed().dashboard('fixture-club');

    await tester.pumpWidget(
      MaterialApp(
        home: GtexClubOwnerDashboardV2(
          clubId: 'fixture-club',
          clubName: 'Fixture FC',
          lifecycleDashboard: dashboard,
          isAuthenticated: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Launch readiness'), findsOneWidget);
    expect(find.text('88% ready'), findsOneWidget);
    expect(find.text('Squad ready'), findsOneWidget);
  });
}
