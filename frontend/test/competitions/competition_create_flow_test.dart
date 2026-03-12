import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/screens/competitions/competition_create_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_publish_preview_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_share_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('create flow reaches publish preview and share screen',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'demo-user',
      currentUserName: 'Demo Fan',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionCreateScreen(
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byType(TextField).first,
      'Friday Skill League',
    );
    await tester.pumpAndSettle();

    expect(find.text('Create a creator competition'), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionPublishPreviewScreen(
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Publish preview'), findsOneWidget);

    await controller.publishDraft();
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionShareScreen(
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Share competition'), findsOneWidget);
    expect(find.text('Invite code'), findsOneWidget);
  });
}
