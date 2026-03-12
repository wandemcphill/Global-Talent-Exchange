import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/scouting_dashboard_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('scouting dashboard shows pipeline and opens prospect detail',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ScoutingDashboardScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Scouting pipeline'), findsOneWidget);
    expect(find.text('Scout: Nadia Mensah'), findsOneWidget);

    await tester.ensureVisible(find.text('Prospects'));
    await tester.tap(find.text('Prospects'));
    await tester.pumpAndSettle();
    expect(find.text('Youth prospects'), findsOneWidget);
    expect(find.text('Lamine Diallo'), findsOneWidget);

    await tester.tap(find.text('Lamine Diallo').first);
    await tester.pumpAndSettle();
    expect(find.text('Prospect detail'), findsOneWidget);
    expect(find.text('Midfield profile built for circulation under pressure'),
        findsOneWidget);
  });
}
