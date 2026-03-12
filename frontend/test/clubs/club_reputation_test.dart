import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/screens/clubs/club_reputation_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club reputation shows earned prestige contributors',
      (WidgetTester tester) async {
    final ClubController controller = ClubController(
      api: ClubApi.fixture(),
      clubId: 'royal-lagos-fc',
    );
    controller.load();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubReputationScreen(controller: controller),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.text('Growth contributors'), findsOneWidget);
    await tester.drag(find.byType(ListView), const Offset(0, -500));
    await tester.pump();
    expect(find.text('Recent reputation events'), findsOneWidget);
    expect(find.text('Back-to-Back Champion'), findsWidgets);
  });
}
