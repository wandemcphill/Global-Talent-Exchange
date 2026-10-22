import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shared/presentation/gte_no_club_onboarding_view.dart';

void main() {
  testWidgets(
    'a user without a club can open national teams without creating a club',
    (WidgetTester tester) async {
      bool createClubCalled = false;
      bool nationalTeamCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GteNoClubOnboardingView(
              isAuthenticated: true,
              scrollable: true,
              onCreateClub: () => createClubCalled = true,
              onOpenNationalTeam: () => nationalTeamCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('Own a club when you are ready'), findsOneWidget);
      expect(find.text('Manage a national team'), findsOneWidget);
      expect(find.textContaining('No club required'), findsOneWidget);

      await tester.ensureVisible(find.text('Explore national teams'));
      await tester.tap(find.text('Explore national teams'));
      await tester.pump();

      expect(nationalTeamCalled, isTrue);
      expect(createClubCalled, isFalse);
    },
  );
}
