import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/providers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/features/compete/presentation/screens/competition_discovery_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('discovery shows safe sections and creator filtering', (
    WidgetTester tester,
  ) async {
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

    controller.setSection(CompetitionDiscoverySection.creator);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Midnight Skill League'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(find.text('Midnight Skill League'), findsWidgets);
    expect(find.text('GTEX Spotlight Cup'), findsNothing);
  });
}
