import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_variant_dto.dart';
import 'package:gte_frontend/screens/clubs/club_jersey_designer_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club jersey designer switches active kit',
      (WidgetTester tester) async {
    final ClubController controller = ClubController(
      api: ClubApi.fixture(),
      clubId: 'royal-lagos-fc',
    );
    controller.load();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubJerseyDesignerScreen(controller: controller),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.text('Color controls'), findsOneWidget);

    await tester.tap(find.text('Away').first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(controller.selectedKit, JerseyType.away);
  });
}
