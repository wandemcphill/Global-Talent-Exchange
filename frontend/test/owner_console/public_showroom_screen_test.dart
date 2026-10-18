import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/presentation/public_showroom_screen.dart';

void main() {
  test('public card reads only the allowlist', () {
    final PublicClubCard card = PublicClubCard.fromJson(<String, dynamic>{
      'club_name': 'Lagos Lions',
      'short_name': 'LAL',
      'city': 'Lagos',
      'country_code': 'NG',
      'primary_color': '#0F766E',
      'secondary_color': '#0F172A',
      'founded': 1998,
      'crest_url': 'https://cdn.example/lagos.png',
      'trophies': <Map<String, dynamic>>[
        <String, dynamic>{
          'competition': 'GTEX Cup',
          'tier': 'Open',
          'position': 1,
          'year': 2026,
        },
      ],
      'fans': 424242,
      'prestige': 313131,
      'sponsors': <Map<String, dynamic>>[
        <String, dynamic>{'sponsor': 'HiddenSponsorXYZ'},
      ],
      'facilities': <String, dynamic>{'academy': 4},
      'top_players': <Map<String, dynamic>>[
        <String, dynamic>{'name': 'HiddenStrikerXYZ'},
      ],
    });
    expect(card.clubName, 'Lagos Lions');
    expect(card.trophies.single.competition, 'GTEX Cup');
    expect(card.toString(), isNot(contains('HiddenSponsorXYZ')));
  });

  testWidgets(
    'logged-out showroom renders the public card and hides private fields',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: PublicShowroomScreen(
            code: 'lagos-lions-public',
            load:
                () async => PublicClubCard.fromJson(<String, dynamic>{
                  'club_name': 'Lagos Lions',
                  'short_name': 'LAL',
                  'city': 'Lagos',
                  'country_code': 'NG',
                  'founded': 1998,
                  'trophies': <Map<String, dynamic>>[
                    <String, dynamic>{
                      'competition': 'GTEX Cup',
                      'position': 1,
                      'year': 2026,
                    },
                  ],
                  'fans': 424242,
                  'sponsors': <String>['HiddenSponsorXYZ'],
                  'staff': <String>['HiddenExecXYZ'],
                }),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('public-showroom')), findsOneWidget);
      expect(find.byKey(const Key('public-showroom-name')), findsOneWidget);
      expect(find.text('Lagos Lions'), findsOneWidget);
      expect(find.textContaining('GTEX Cup'), findsOneWidget);
      expect(find.textContaining('est. 1998'), findsOneWidget);
      expect(find.textContaining('HiddenSponsorXYZ'), findsNothing);
      expect(find.textContaining('HiddenExecXYZ'), findsNothing);
      expect(find.textContaining('424242'), findsNothing);
    },
  );

  testWidgets('unknown public showroom says it was not found', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: PublicShowroomScreen(
          code: 'missing',
          load: () async => throw Exception('not found'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('public-showroom-missing')), findsOneWidget);
  });
}
