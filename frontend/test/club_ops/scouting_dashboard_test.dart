import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/scouting_dashboard_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'recruiter planning board scopes local controls and opens prospect detail',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: ScoutingDashboardScreen(api: ClubOpsApi.fixture()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Recruiter planning board'), findsOneWidget);
      expect(find.text('Overview'), findsOneWidget);
      expect(find.text('Shortlist'), findsOneWidget);
      expect(find.text('Pipeline'), findsOneWidget);
      expect(find.text('Insights'), findsOneWidget);
      expect(find.text('Players viewed'), findsOneWidget);
      expect(
        find.textContaining(
          'Board scope: prospect profiles, reports, and pipeline counts come from live scouting data.',
        ),
        findsOneWidget,
      );

      await tester.tap(find.text('Shortlist'));
      await tester.pumpAndSettle();
      expect(find.text('Lamine Diallo'), findsOneWidget);
      expect(find.text('Queue on board'), findsWidgets);
      expect(find.text('Add local note'), findsWidgets);

      await tester.tap(find.text('Lamine Diallo').first);
      await tester.pumpAndSettle();
      expect(find.text('Prospect detail'), findsOneWidget);
      expect(
        find.text('Midfield profile built for circulation under pressure'),
        findsOneWidget,
      );
    },
  );
}
