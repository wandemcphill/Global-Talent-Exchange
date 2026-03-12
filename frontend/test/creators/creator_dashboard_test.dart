import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/screens/creators/creator_dashboard_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('creator dashboard shows growth summary and creator competitions',
      (WidgetTester tester) async {
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Creator dashboard'), findsOneWidget);
    expect(find.text('Maya Scout'), findsOneWidget);
    expect(find.text('Creator stats'), findsOneWidget);
    expect(find.text('Growth summary'), findsOneWidget);
    expect(find.text('Creator competitions'), findsWidgets);
    expect(find.text('Spring Scout Sprint'), findsOneWidget);
  });

  testWidgets('creator dashboard opens profile and share surfaces',
      (WidgetTester tester) async {
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(find.text('Creator profile'), findsOneWidget);
    expect(find.text('Creator profile link'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Share').first);
    await tester.tap(find.text('Share').first);
    await tester.pumpAndSettle();
    expect(find.text('Creator competition share'), findsOneWidget);
    expect(find.text('Invite friends to join creator competition'),
        findsOneWidget);
  });
}
