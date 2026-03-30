import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/screens/competitions/competition_discovery_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('discovery shows safe sections and seeded creator competitions',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1440, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'studio-kai',
      currentUserName: 'Studio Kai',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDiscoveryScreen(
          controller: controller,
          currentUserId: 'studio-kai',
          currentUserName: 'Studio Kai',
          isAuthenticated: true,
          canHostCompetitions: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Create competition'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Creator competitions'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Creator competitions'));
    await tester.pumpAndSettle();

    expect(find.text('Midnight Skill League'), findsWidgets);
  });
}
