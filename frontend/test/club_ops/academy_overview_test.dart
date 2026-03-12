import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/academy_overview_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('academy overview shows pathway summary and opens player detail',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: AcademyOverviewScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Academy pathway'), findsOneWidget);
    expect(find.text('Royal Lagos Fc'), findsOneWidget);
    await tester.ensureVisible(find.text('Players'));
    await tester.tap(find.text('Players'));
    await tester.pumpAndSettle();
    expect(find.text('Academy players'), findsOneWidget);

    await tester.tap(find.text('Amara Cole'));
    await tester.pumpAndSettle();
    expect(find.text('Player pathway'), findsOneWidget);
    expect(find.text('Development progress'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Recent promotions'),
      300,
    );
    expect(find.text('Recent promotions'), findsOneWidget);
  });
}
