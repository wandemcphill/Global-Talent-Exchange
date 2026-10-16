import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/screens/clubs/club_dynasty_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club dynasty shows timeline and legacy milestones',
      (WidgetTester tester) async {
    final ClubController controller = ClubController(
      api: ClubApi.fixture(),
      clubId: 'atlas-republic',
    );
    controller.load();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubDynastyScreen(controller: controller),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 800));

    expect(find.text('Dynasty progression timeline'), findsOneWidget);
    await tester.drag(find.byType(ListView), const Offset(0, -500));
    await tester.pump();
    expect(find.text('Legacy milestones'), findsOneWidget);
    expect(find.textContaining('Peak '), findsWidgets);
  });
}
