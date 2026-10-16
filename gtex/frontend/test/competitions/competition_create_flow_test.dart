import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/screens/competitions/competition_create_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_publish_preview_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_share_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('create flow reaches publish preview and share screen', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionCreateScreen(
          controller: controller,
          isAuthenticated: true,
          hostEligible: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'Friday Skill League');
    await tester.pumpAndSettle();

    expect(find.text('Create competition'), findsWidgets);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionPublishPreviewScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Publish preview'), findsOneWidget);

    await controller.publishDraft();
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionShareScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Share competition'), findsOneWidget);
    expect(find.text('Invite code'), findsOneWidget);
  });

  testWidgets('create flow is visible for authenticated launch users', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    bool openedCreatorAccess = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionCreateScreen(
          controller: controller,
          isAuthenticated: true,
          hostEligible: false,
          onOpenCreatorAccessRequest: () {
            openedCreatorAccess = true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Create competition'), findsWidgets);
    expect(find.byType(TextField), findsWidgets);
    await tester.scrollUntilVisible(
      find.text('Preview & publish'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Preview & publish'), findsOneWidget);
    expect(find.text('Competition creation unavailable'), findsNothing);
    expect(openedCreatorAccess, isFalse);
  });
}
