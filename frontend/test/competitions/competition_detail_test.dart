import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('detail screen renders transparent financials and payout',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Transparent financials'),
      300,
    );
    expect(find.text('Transparent financials'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Transparent payout'),
      300,
    );
    expect(find.text('Transparent payout'), findsOneWidget);
    expect(find.textContaining('secure escrow'), findsWidgets);
    expect(find.textContaining('Platform service fee'), findsOneWidget);
    expect(find.textContaining('Host fee'), findsOneWidget);
    expect(find.textContaining('Prize pool'), findsOneWidget);
  });
}
