import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/competitions/presentation/competition_friend_desk.dart';

void main() {
  testWidgets('competition search box lists the matching fixture', (WidgetTester tester) async {
    String? searched;
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: CompetitionFriendDesk(
              isAuthenticated: true,
              onOpenLogin: () {},
              onHostCanonical: () {},
              onQueryChanged: (String value) => searched = value,
              searchFixtures: (String query) async {
                return <Map<String, dynamic>>[
                  <String, dynamic>{
                    'home_name': 'Alpha FC',
                    'away_name': 'Bravo United',
                    'competition_name': query,
                    'status': 'scheduled',
                  },
                ];
              },
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('gtex-competition-search')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('gtex-competition-search')), 'Friends Cup');
    await tester.tap(find.byKey(const Key('gtex-competition-search-submit')));
    await tester.pump();

    expect(searched, 'Friends Cup');
    expect(find.text('Alpha FC vs Bravo United'), findsOneWidget);
  });

  testWidgets('host opens the user competition screen without a club check', (WidgetTester tester) async {
    var hosted = false;
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: CompetitionFriendDesk(
              isAuthenticated: true,
              onOpenLogin: () {},
              onHostCanonical: () => hosted = true,
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('gtex-host-competition')));
    await tester.pump();
    expect(hosted, isTrue);
  });
}
