import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/screens/clubs/club_profile_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club profile shows identity summary and routes to showcase', (
    WidgetTester tester,
  ) async {
    final ClubController controller = ClubController(
      api: ClubApi.fixture(),
      clubId: 'royal-lagos-fc',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubProfileScreen(
          clubId: 'royal-lagos-fc',
          controller: controller,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1200));

    expect(find.text('Club profile unavailable'), findsNothing);
    expect(find.widgetWithText(FilledButton, 'Showcase'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Showcase'));
    await tester.pumpAndSettle();

    expect(find.text('Club showcase'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Identity'),
      300,
      scrollable: find.byType(Scrollable).first,
    );

    expect(find.text('Identity'), findsOneWidget);
    expect(find.textContaining('Primary'), findsOneWidget);
  });
}
