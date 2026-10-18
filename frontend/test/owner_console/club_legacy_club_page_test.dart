import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_club_page.dart';

ClubLegacyClubPageData _page({bool modelFailed = false}) {
  return ClubLegacyClubPageData(
    locationLines: const <String>['Lagos', 'NG', 'Africa'],
    history: const <String>[],
    roster: const <String>['Ada Okonkwo · goalkeeper'],
    honours: const <String>[],
    staff: const <String>['Ada Okonkwo · gm'],
    facilities: const <String>['academy · 1'],
    commercial: const <String>[],
    ownershipLabels: const <String>['Club', 'Owner', 'Player', 'Manager', 'Not owned'],
    modelFailed: modelFailed,
  );
}

Future<void> _pump(WidgetTester tester, ClubLegacyClubPageData data) {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: ClubLegacyClubPage(data: data)),
    ),
  );
}

void main() {
  test('club page json keeps an empty honour list', () {
    final ClubLegacyClubPageData data = ClubLegacyClubPageData.fromJson(<String, dynamic>{
      'sections': <String, dynamic>{
        'location': <String, dynamic>{'city': 'Lagos', 'country_code': 'NG', 'continent_name': 'Africa'},
        'history': <Map<String, dynamic>>[],
        'roster': <Map<String, dynamic>>[],
        'honours': <Map<String, dynamic>>[],
        'staff': <Map<String, dynamic>>[],
        'facilities': <Map<String, dynamic>>[],
        'commercial': <Map<String, dynamic>>[],
      },
      'showroom': <String, dynamic>{
        'mode': 'static-fallback',
        'fallback': 'static-card',
        'model_error': 'MissingModel',
        'exhibits': <Map<String, dynamic>>[
          <String, dynamic>{'ownership_label': 'Club'},
          <String, dynamic>{'ownership_label': 'Not owned'},
        ],
      },
    });
    expect(data.honours, isEmpty);
    expect(data.locationLines, <String>['Lagos', 'NG', 'Africa']);
    expect(data.modelFailed, isTrue);
    expect(data.ownershipLabels, contains('Not owned'));
  });

  testWidgets('phone width shows real sections and no invented trophy', (WidgetTester tester) async {
    await _pump(tester, _page());
    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('club-page')), findsOneWidget);
    expect(find.text('Lagos'), findsOneWidget);
    expect(find.text('Champions League'), findsNothing);
    expect(find.text('Club'), findsOneWidget);
    expect(find.text('Owner'), findsOneWidget);
    expect(find.text('Player'), findsOneWidget);
    expect(find.text('Manager'), findsOneWidget);
    expect(find.text('Not owned'), findsOneWidget);
    expect(find.byKey(const Key('club-page-static-fallback')), findsNothing);

    await tester.ensureVisible(find.byKey(const Key('club-page-tab-honours')));
    await tester.tap(find.byKey(const Key('club-page-tab-honours')));
    await tester.pumpAndSettle();
    expect(find.text('No honours yet'), findsOneWidget);
    expect(find.text('Champions League'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('a failed model keeps the phone club page on the static card', (WidgetTester tester) async {
    await _pump(tester, _page(modelFailed: true));
    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('club-page')), findsOneWidget);
    expect(find.byKey(const Key('club-page-static-fallback')), findsOneWidget);
    expect(find.text('Static card'), findsOneWidget);
    expect(find.byKey(const Key('club-page-tab-roster')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('club-page-tab-honours')));
    await tester.tap(find.byKey(const Key('club-page-tab-honours')));
    await tester.pumpAndSettle();
    expect(find.text('No honours yet'), findsOneWidget);
    expect(find.byKey(const Key('club-page-static-fallback')), findsOneWidget);
    await tester.tap(find.byKey(const Key('club-page-tab-roster')));
    await tester.pumpAndSettle();
    expect(find.text('Ada Okonkwo · goalkeeper'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
